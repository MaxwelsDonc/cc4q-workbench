"""Workspace: the "everything is an asset" persistence layer (WP1A).

A workspace is a directory holding an ``index.json`` asset index plus
per-asset payload files under ``assets/<type>/<id>/``.

Asset types:

- ``corpus`` — SCCU records (raw or labeled). Fields: ``name``,
  ``source`` (url | dir | upload | precomputed), ``sccus``,
  ``quantum_pct`` (labeled only), ``labeled`` (bool),
  ``files`` = {"corpus": <jsonl path>, "labeled"?: <jsonl path>}.
- ``annotation_session`` — schema/mode/progress of an annotation round.
  Fields: ``name``, ``schema``, ``mode``, ``total``, ``labeled_count``,
  ``export_path?``.
- ``evaluation`` — a model-pair comparison report. Fields: ``name``,
  ``pair`` = [model_a, model_b], ``corpus``,
  ``metrics`` = {n, agreement, precision, recall, wilson95},
  ``report_path``.
- ``model`` — NOT stored here; models live in ``cc4q.registry`` and
  are referenced by id (see :func:`list_models`).

Directory resolution: ``$CC4Q_WORKSPACE`` > ``.cc4q_workspace/`` next to a
source checkout (detected by pyproject.toml at the repo root) >
``~/.cache/cc4q/workspace/`` for wheel installs. The workspace and index
are created on demand. The index is written atomically (tmp file + rename)
and a corrupted ``index.json`` is backed up to ``index.json.bak`` and
rebuilt empty (with a logged warning).
"""

import json
import logging
import os
import shutil
import tempfile
import time
import uuid
import zipfile

logger = logging.getLogger(__name__)

ASSET_TYPES = ("corpus", "annotation_session", "evaluation")

_REQUIRED = {
    "corpus": ("name", "source"),
    "annotation_session": ("name", "schema", "mode"),
    "evaluation": ("name", "pair"),
}
SOURCES = ("url", "dir", "upload", "precomputed")

__all__ = [
    "asset_path",
    "create_asset",
    "delete_asset",
    "export_asset",
    "get_asset",
    "list_assets",
    "list_models",
    "read_jsonl",
    "rename_asset",
    "update_asset",
    "workspace_dir",
    "write_jsonl",
]


# ------------------------------------------------------------- resolution

def workspace_dir():
    """Resolve (and create) the workspace directory."""
    env = os.environ.get("CC4Q_WORKSPACE")
    if env:
        path = env
    else:
        from cc4q.pipeline.paths import REPO_ROOT
        if os.path.isfile(os.path.join(REPO_ROOT, "pyproject.toml")):
            path = os.path.join(REPO_ROOT, ".cc4q_workspace")
        else:
            path = os.path.expanduser(os.path.join(
                "~", ".cache", "cc4q", "workspace"))
    os.makedirs(path, exist_ok=True)
    return path


def _index_path():
    return os.path.join(workspace_dir(), "index.json")


def _asset_dir(type_, asset_id):
    return os.path.join(workspace_dir(), "assets", type_, asset_id)


# ----------------------------------------------------------------- index

def _empty_index():
    return {"version": 1, "assets": []}


def _load():
    path = _index_path()
    if not os.path.isfile(path):
        return _empty_index()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not isinstance(
                data.get("assets"), list):
            raise ValueError("unexpected index shape")
        return data
    except (json.JSONDecodeError, ValueError) as exc:
        backup = path + ".bak"
        shutil.copy2(path, backup)
        logger.warning("workspace index corrupted (%s) - backed up to %s "
                       "and rebuilt empty", exc, backup)
        return _empty_index()


def _save(index):
    root = workspace_dir()
    fd, tmp = tempfile.mkstemp(dir=root, prefix=".index-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _index_path())  # atomic on POSIX
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


# ---------------------------------------------------------------- assets

def create_asset(type_, root=None, **fields):
    """Create an asset of ``type_`` with the given fields. Injects ``id``
    (short uuid), ``created_at``, and (for sessions) ``updated_at``.
    Returns the stored asset dict."""
    if type_ not in ASSET_TYPES:
        raise ValueError(f"unknown asset type {type_!r}; expected one of "
                         f"{ASSET_TYPES}")
    missing = [k for k in _REQUIRED[type_] if k not in fields]
    if missing:
        raise ValueError(f"{type_} asset missing required fields: "
                         f"{', '.join(missing)}")
    if type_ == "corpus" and fields["source"] not in SOURCES:
        raise ValueError(f"corpus source must be one of {SOURCES}")
    index = _load()
    asset = {"id": uuid.uuid4().hex[:8], "type": type_}
    asset.update(fields)
    asset.setdefault("created_at", time.strftime("%Y-%m-%d %H:%M:%S"))
    if type_ == "annotation_session":
        asset.setdefault("updated_at", asset["created_at"])
        asset.setdefault("labeled_count", 0)
    index["assets"].append(asset)
    _save(index)
    return dict(asset)


def list_assets(type_=None):
    """All assets (newest-updated first); filter by type when given."""
    assets = _load()["assets"]
    if type_:
        if type_ not in ASSET_TYPES:
            raise ValueError(f"unknown asset type {type_!r}")
        assets = [a for a in assets if a["type"] == type_]
    return sorted(assets,
                  key=lambda a: a.get("updated_at") or a.get("created_at", ""),
                  reverse=True)


def get_asset(asset_id):
    """Return one asset by id.

    Args:
        asset_id: Short asset id (for example ``"a1b2c3d4"``).

    Returns:
        A copy of the asset dictionary.

    Raises:
        KeyError: If no asset with that id exists.
    """
    for a in _load()["assets"]:
        if a["id"] == asset_id:
            return dict(a)
    raise KeyError(f"no asset with id {asset_id!r}")


def update_asset(asset_id, **fields):
    """Merge fields into an asset; bumps ``updated_at``. Returns the
    updated dict."""
    index = _load()
    for a in index["assets"]:
        if a["id"] == asset_id:
            a.update(fields)
            a["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _save(index)
            return dict(a)
    raise KeyError(f"no asset with id {asset_id!r}")


def rename_asset(asset_id, name):
    """Set an asset's display name.

    Args:
        asset_id: Asset id.
        name: New display name.

    Returns:
        The updated asset dictionary.

    Raises:
        KeyError: If no asset with that id exists.
    """
    return update_asset(asset_id, name=name)


def delete_asset(asset_id):
    """Remove the asset from the index and delete its payload directory."""
    index = _load()
    target = next((a for a in index["assets"] if a["id"] == asset_id), None)
    if target is None:
        raise KeyError(f"no asset with id {asset_id!r}")
    index["assets"] = [a for a in index["assets"] if a["id"] != asset_id]
    _save(index)
    shutil.rmtree(_asset_dir(target["type"], asset_id), ignore_errors=True)


def export_asset(asset_id, dest_dir):
    """Zip the asset's payload directory into ``dest_dir`` (created as
    needed) as ``<id>.zip`` including an ``asset.json`` manifest.
    Returns the zip path."""
    asset = get_asset(asset_id)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, f"{asset_id}.zip")
    src = _asset_dir(asset["type"], asset_id)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.isdir(src):
            for dirpath, _, files in os.walk(src):
                for fn in files:
                    full = os.path.join(dirpath, fn)
                    zf.write(full, os.path.relpath(full, src))
        zf.writestr("asset.json", json.dumps(asset, ensure_ascii=False,
                                             indent=2))
    return dest


# --------------------------------------------------------------- payloads

def asset_path(asset_id, filename, type_=None, create_dir=False):
    """Payload file path for an asset: ``assets/<type>/<id>/<filename>``.
    The type is looked up from the index when not given."""
    if type_ is None:
        type_ = get_asset(asset_id)["type"]
    path = _asset_dir(type_, asset_id)
    if create_dir:
        os.makedirs(path, exist_ok=True)
    return os.path.join(path, filename)


def write_jsonl(asset_id, filename, records):
    """Write records to a JSONL payload file inside an asset directory.

    Args:
        asset_id: Asset id whose payload directory should receive the file.
        filename: File name relative to the asset directory.
        records: Iterable of JSON-serializable records.

    Returns:
        The full path to the written file.
    """
    path = asset_path(asset_id, filename, create_dir=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def read_jsonl(path):
    """Read a JSONL file into a list of records (blank lines ignored)."""
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# ----------------------------------------------------------------- models

def list_models():
    """Model assets are delegated to the user model registry — the
    workspace only references model ids. Returns the registry entries."""
    from cc4q.registry import list_models as registry_list
    return registry_list()
