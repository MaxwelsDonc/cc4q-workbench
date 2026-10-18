"""User model registry for the web workbench.

A small JSON index over a directory of user-provided model packages. Each
package is a directory in the same layout as ``models_checkpoints/``: one
sub-directory per label axis it provides (``quantum_related`` /
``quantum_category``), each a Hugging Face model
directory. Packages may provide a single axis (e.g. a freshly trained
classifier); missing axes fall back to the released checkpoints at
prediction time.

The registry lives in ``user_models/`` next to a source checkout, or in
``~/.cache/cc4q/user_models`` for wheel installs.
"""

import json
import os
import shutil
import zipfile

from cc4q.pipeline.paths import REPO_ROOT

AXES = ("quantum_related", "quantum_category")

__all__ = [
    "delete",
    "list_models",
    "package_dir",
    "register",
    "register_uploaded_zip",
    "registry_root",
    "set_default",
    "zip_package",
]


def registry_root():
    """Return the user-model registry directory.

    Resolution order: ``$CC4Q_USER_MODELS`` > ``user_models/`` next to a
    source checkout > ``~/.cache/cc4q/user_models`` for wheel installs.
    """
    env = os.environ.get("CC4Q_USER_MODELS")
    if env:
        return env
    if os.path.isdir(os.path.join(REPO_ROOT, "scripts")):
        return os.path.join(REPO_ROOT, "user_models")
    return os.path.expanduser(os.path.join("~", ".cache", "cc4q",
                                           "user_models"))


def _index_path(root=None):
    return os.path.join(root or registry_root(), "registry.json")


def _load(root=None):
    path = _index_path(root)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"models": [], "default": None}


def _save(index, root=None):
    os.makedirs(root or registry_root(), exist_ok=True)
    with open(_index_path(root), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def list_models(root=None):
    """Registry entries (newest first), with ``is_default`` set."""
    index = _load(root)
    default = index.get("default")
    out = []
    for entry in index.get("models", []):
        entry = dict(entry)
        entry["is_default"] = entry["id"] == default
        out.append(entry)
    return sorted(out, key=lambda e: e.get("created", ""), reverse=True)


def package_dir(model_id, root=None):
    """Return the directory holding one registered model package.

    Args:
        model_id: Registry id (for example ``"my-bert-3ep"``).
        root: Optional registry root override.

    Returns:
        Path to the package directory (which may not exist).
    """
    return os.path.join(root or registry_root(), model_id)


def _axes_of(path):
    return [a for a in AXES if os.path.isfile(os.path.join(path, a,
                                                           "config.json"))]


def register(name, path, source="trained", root=None):
    """Register an existing model package directory (copied into the
    registry). Returns the new entry."""
    import re
    import time

    axes = _axes_of(path)
    if not axes:
        raise ValueError(
            f"{path} does not look like a model package: expected one of "
            f"{AXES} sub-directories with a config.json")
    model_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", name).strip("-").lower() \
        or "model"
    base, i = model_id, 2
    existing = {m["id"] for m in _load(root).get("models", [])}
    while model_id in existing:
        model_id = f"{base}-{i}"
        i += 1
    dest = package_dir(model_id, root)
    shutil.copytree(path, dest)
    entry = {"id": model_id, "name": name, "source": source,
             "axes": axes, "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    index = _load(root)
    index.setdefault("models", []).append(entry)
    if not index.get("default"):
        index["default"] = model_id
    _save(index, root)
    return entry


def _safe_extract_zip(zf, dest):
    """Extract a zip after rejecting entries that escape ``dest``.

    ``zipfile.extractall`` grew a ``filter=`` argument in newer Pythons, so
    we validate paths explicitly and then call the plain API. This keeps the
    registry upload path working on Python 3.11-3.13 and still blocks ``..``
    or absolute-path traversal.
    """
    root = os.path.realpath(dest)
    root_key = os.path.normcase(root)
    for member in zf.infolist():
        target = os.path.realpath(os.path.join(root, member.filename))
        try:
            inside = (
                os.path.normcase(os.path.commonpath([root, target]))
                == root_key
            )
        except ValueError:  # different drive on Windows
            inside = False
        if not inside:
            raise ValueError(
                f"zip entry escapes the target directory: {member.filename}"
            )
    zf.extractall(root)


def register_uploaded_zip(uploaded_file, name=None, root=None):
    """Extract an uploaded zip into the registry and register it."""
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="cc4q_upload_")
    archive = os.path.join(tmpdir, "upload.zip")
    with open(archive, "wb") as f:
        f.write(uploaded_file.getvalue())
    with zipfile.ZipFile(archive) as zf:
        _safe_extract_zip(zf, tmpdir)
    os.remove(archive)
    # accept either the package root or a single nested directory
    candidates = [d for d in os.listdir(tmpdir)
                  if os.path.isdir(os.path.join(tmpdir, d))]
    pkg = None
    for cand in [tmpdir] + [os.path.join(tmpdir, c) for c in candidates]:
        if _axes_of(cand):
            pkg = cand
            break
    if pkg is None:
        shutil.rmtree(tmpdir, ignore_errors=True)
        raise ValueError(
            "the zip must contain a Hugging Face model directory (or one "
            f"per axis: {', '.join(AXES)}), each with a config.json")
    entry = register(name or uploaded_file.name.rsplit(".", 1)[0], pkg,
                     source="upload", root=root)
    shutil.rmtree(tmpdir, ignore_errors=True)
    return entry


def set_default(model_id, root=None):
    """Mark one registered model as the default for the Workbench.

    Args:
        model_id: Registry id to activate.
        root: Optional registry root override.

    Raises:
        KeyError: If ``model_id`` is not registered.
    """
    index = _load(root)
    ids = {m["id"] for m in index.get("models", [])}
    if model_id not in ids:
        raise KeyError(model_id)
    index["default"] = model_id
    _save(index, root)


def delete(model_id, root=None):
    """Remove a model package from the registry and delete its directory.

    If the deleted model was the default, the next remaining model becomes
    the default (or the default is cleared when the registry is empty).

    Args:
        model_id: Registry id to delete.
        root: Optional registry root override.
    """
    index = _load(root)
    index["models"] = [m for m in index.get("models", [])
                       if m["id"] != model_id]
    if index.get("default") == model_id:
        index["default"] = index["models"][0]["id"] if index["models"] \
            else None
    _save(index, root)
    shutil.rmtree(package_dir(model_id, root), ignore_errors=True)


def zip_package(model_id, dest_path, root=None):
    """Write a zip archive of one model package.

    Args:
        model_id: Registry id to archive.
        dest_path: Destination ``.zip`` path.
        root: Optional registry root override.

    Returns:
        ``dest_path``.
    """
    src = package_dir(model_id, root)
    with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dirpath, _, files in os.walk(src):
            for fn in files:
                full = os.path.join(dirpath, fn)
                zf.write(full, os.path.relpath(full, src))
    return dest_path
