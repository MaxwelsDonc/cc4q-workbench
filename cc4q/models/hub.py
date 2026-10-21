"""Model hub: checkpoint download/verification and lazy classifier loading.

Focuses on the two Quantum-Specific classifiers:
  - ``quantum_related`` (Binary: Quantum-Specific vs. Non-Quantum)
  - ``quantum_category`` (6-Class Quantum Knowledge Taxonomy)
"""

import hashlib
import os
import shutil
import tarfile
import tempfile
import urllib.error
import urllib.request

RELEASE_REPO = "MaxwelsDonc/cc4q-workbench"
RELEASE = "v0.2.0"
BASE_URL = f"https://github.com/{RELEASE_REPO}/releases/download/{RELEASE}"

# Primary quantum checkpoints (required for inference)
CHECKPOINTS = {
    "quantum_related.tar.gz": (
        "quantum_related",
        "3033b2ca6d6acb3075b638b07daf63280aa00784f578b1c7113d4adb1ce70309",
    ),
    "quantum_category.tar.gz": (
        "quantum_category",
        "54cc6056171e497ddb66bf9fa995ca63238a46d53b9f475fa4806f8fcbe5d734",
    ),
}

# Optional base model for from-scratch fine-tuning (not needed for inference)
BASE_MODEL = {
    "bert-base-uncased.tar.gz": (
        "bert-base-uncased",
        "dc4c12a087cf2b282d33d23ea47140db287f706c53da68facb8a749a4b13fa2c",
    ),
}

REQUIRED_FILES = ("config.json", "model.safetensors", "tokenizer_config.json")

__all__ = [
    "BASE_MODEL",
    "BASE_URL",
    "CHECKPOINTS",
    "ModelHandle",
    "RELEASE",
    "RELEASE_REPO",
    "checkpoint_complete",
    "default_model_dir",
    "ensure_checkpoints",
    "load_models",
    "load_models_from",
    "missing_checkpoints",
    "resolve_device",
]


def default_model_dir():
    """Return the default checkpoint directory.

    Resolution order: ``$CC4Q_MODEL_DIR`` > ``models_checkpoints/`` next to
    a source checkout > ``~/.cache/cc4q/models_checkpoints`` for wheel
    installs.
    """
    env = os.environ.get("CC4Q_MODEL_DIR")
    if env:
        return env
    from cc4q.pipeline.paths import REPO_ROOT
    if os.path.isdir(os.path.join(REPO_ROOT, "scripts")):
        return os.path.join(REPO_ROOT, "models_checkpoints")
    return os.path.expanduser(os.path.join("~", ".cache", "cc4q",
                                           "models_checkpoints"))


def resolve_device(device=None):
    """Resolve the torch device used for inference.

    Resolution order: explicit ``device`` > ``$CC4Q_DEVICE`` > CUDA when
    available > CPU. MPS is never selected automatically because some torch
    builds hang on it; opt in with ``CC4Q_DEVICE=mps``.

    Args:
        device: Optional device override, e.g. ``"cuda"``, ``"cpu"``,
            ``"mps"``, or ``"cuda:1"``.

    Returns:
        The normalized device string.
    """
    import torch
    forced = (device or os.environ.get("CC4Q_DEVICE", "")).strip().lower()
    if forced:
        return forced
    return "cuda" if torch.cuda.is_available() else "cpu"


def _checkpoint_dir_complete(path):
    """Whether ``path`` itself is a complete checkpoint directory."""
    return all(os.path.isfile(os.path.join(path, f)) for f in REQUIRED_FILES)


def checkpoint_complete(model_dir, name):
    """Return whether a checkpoint directory contains every required file.

    Args:
        model_dir: Directory containing the per-axis checkpoint
            directories.
        name: Axis directory name, e.g. ``"quantum_related"``.

    Returns:
        ``True`` when ``config.json``, ``model.safetensors``, and
        ``tokenizer_config.json`` are all present.
    """
    return _checkpoint_dir_complete(os.path.join(model_dir, name))


def missing_checkpoints(model_dir=None):
    """List the released classifier axes whose checkpoints are missing.

    Args:
        model_dir: Optional checkpoint root; defaults to
            :func:`default_model_dir`.

    Returns:
        Axis names (``"quantum_related"`` / ``"quantum_category"``) that
        are not complete on disk. An empty list means both are ready.
    """
    model_dir = model_dir or default_model_dir()
    return [name for name, _ in CHECKPOINTS.values()
            if not checkpoint_complete(model_dir, name)]


def _sha256(path, chunk_size=1 << 20):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _download_once(asset, dest_path):
    url = f"{BASE_URL}/{asset}"
    req = urllib.request.Request(url, headers={"User-Agent": "cc4q-workbench"})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest_path, "wb") as out:
        shutil.copyfileobj(resp, out, length=1 << 20)


def _download(asset, dest_path):
    try:
        _download_once(asset, dest_path)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Release asset not found at {BASE_URL}/{asset} (HTTP {exc.code}) "
            f"- check https://github.com/{RELEASE_REPO}/releases"
        ) from exc
    except Exception:
        try:
            _download_once(asset, dest_path)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"Release asset not found at {BASE_URL}/{asset} (HTTP {exc.code}) "
                f"- check https://github.com/{RELEASE_REPO}/releases"
            ) from exc


def ensure_checkpoints(model_dir=None, verbose=True, with_base=False):
    """Download, SHA256-verify, and extract any missing checkpoint.

    Args:
        model_dir: Optional checkpoint root; defaults to
            :func:`default_model_dir`.
        verbose: Print download/extraction progress.
        with_base: Also fetch the ``bert-base-uncased`` base model. Only
            needed for from-scratch fine-tuning, not for inference.

    Returns:
        A list of checkpoint names that are still missing after the
        attempt. An empty list means everything is ready.

    Raises:
        RuntimeError: If a release asset cannot be downloaded, its SHA256
            does not match, or extraction does not produce a usable
            checkpoint.
    """
    model_dir = model_dir or default_model_dir()
    missing = missing_checkpoints(model_dir)
    if with_base:
        for asset, (name, _sha) in BASE_MODEL.items():
            if not checkpoint_complete(model_dir, name):
                missing.append(f"base:{name}")
    if not missing:
        if verbose:
            print(f"All quantum checkpoints already present in {model_dir}")
        return []

    os.makedirs(model_dir, exist_ok=True)
    tmpdir = tempfile.mkdtemp(prefix="cc4q_models_")
    try:
        wanted = dict(CHECKPOINTS)
        if with_base:
            wanted.update(BASE_MODEL)
        for asset, (name, expected_sha) in wanted.items():
            if checkpoint_complete(model_dir, name):
                continue
            archive = os.path.join(tmpdir, asset)
            if verbose:
                print(f"Downloading {asset} ({BASE_URL}/{asset}) …")
            _download(asset, archive)
            actual_sha = _sha256(archive)
            if actual_sha != expected_sha:
                raise RuntimeError(
                    f"SHA256 mismatch for {asset}: got {actual_sha}, "
                    f"expected {expected_sha}. Delete {archive} and retry."
                )
            if verbose:
                print(f"  checksum OK ({actual_sha[:16]}…), extracting …")
            with tarfile.open(archive, "r:gz") as tar:
                tar.extractall(model_dir, filter="data")
            dest = os.path.join(model_dir, name)
            if not _checkpoint_dir_complete(dest) and not os.path.exists(dest):
                # Tolerate HF-cache-style packing: the asset nests the
                # checkpoint under a snapshot-hash directory instead of the
                # canonical name. Normalize the first complete candidate.
                for entry in sorted(os.listdir(model_dir)):
                    cand = os.path.join(model_dir, entry)
                    if os.path.isdir(cand) and entry != name \
                            and _checkpoint_dir_complete(cand):
                        os.rename(cand, dest)
                        break
            if not checkpoint_complete(model_dir, name):
                raise RuntimeError(
                    f"Extraction of {asset} did not produce a usable "
                    f"checkpoint at {os.path.join(model_dir, name)}"
                )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    still = missing_checkpoints(model_dir)
    if with_base:
        for asset, (name, _sha) in BASE_MODEL.items():
            if not checkpoint_complete(model_dir, name):
                still.append(name)
    return still


class ModelHandle:
    """The fine-tuned quantum classifiers plus the device they live on.

    A handle behaves like a small mapping over the two axes
    (``quantum_related`` and ``quantum_category``). Each value is a
    ``(tokenizer, model)`` tuple; both models are in eval mode.

    Attributes:
        device: Torch device string used by both classifiers.
        model_dir: Checkpoint root the handle was loaded from.

    Example:
        >>> models = load_models()
        >>> tokenizer, model = models["quantum_related"]
        >>> models.quantum_category[1].eval()
    """

    AXES = ("quantum_related", "quantum_category")

    def __init__(self, models, device, model_dir):
        self._models = dict(models)
        self.device = device
        self.model_dir = model_dir

    def __getattr__(self, name):
        if name in self._models:
            return self._models[name]
        raise AttributeError(name)

    def __getitem__(self, name):
        return self._models[name]

    def __contains__(self, name):
        return name in self._models

    def keys(self):
        return self._models.keys()


def _load_axis(model_dir, name, device):
    from transformers import BertForSequenceClassification, BertTokenizer
    path = os.path.join(model_dir, name) if name else model_dir
    tokenizer = BertTokenizer.from_pretrained(path)
    model = BertForSequenceClassification.from_pretrained(path)
    model.to(device)
    model.eval()
    return tokenizer, model


def load_models(model_dir=None, device=None, auto_download=True):
    """Load both quantum classifiers in eval mode.

    Args:
        model_dir: Optional checkpoint root; defaults to
            :func:`default_model_dir`.
        device: Optional torch device override; see :func:`resolve_device`.
        auto_download: Download missing checkpoints instead of raising.

    Returns:
        A :class:`ModelHandle` with a ``(tokenizer, model)`` tuple for each
        axis.

    Raises:
        RuntimeError: If checkpoints are missing and ``auto_download`` is
            ``False``, or the download cannot be completed.
    """
    model_dir = model_dir or default_model_dir()
    missing = missing_checkpoints(model_dir)
    if missing:
        if not auto_download:
            raise RuntimeError(
                f"Missing model checkpoints: {', '.join(missing)}. "
                f"Run: cc4q download-models"
            )
        still = ensure_checkpoints(model_dir)
        if still:
            raise RuntimeError(
                f"Checkpoint download incomplete, still missing: "
                f"{', '.join(still)}"
            )

    device = resolve_device(device)
    models = {name: _load_axis(model_dir, name, device)
              for name in ModelHandle.AXES}
    return ModelHandle(models, device, model_dir)


def load_models_from(axis_dirs, device=None, auto_download=True):
    """Compose a handle from per-axis model directories.

    Args:
        axis_dirs: Mapping from axis name (``"quantum_related"`` /
            ``"quantum_category"``) to a Hugging Face model directory.
            Missing or ``None`` axes fall back to the released checkpoint.
        device: Optional torch device override.
        auto_download: Download missing released checkpoints instead of
            raising.

    Returns:
        A :class:`ModelHandle` combining the provided and released models.

    Raises:
        RuntimeError: If a required released checkpoint is missing and
            ``auto_download`` is ``False``.
    """
    device = resolve_device(device)
    released_dir = None
    models = {}
    for name in ModelHandle.AXES:
        if axis_dirs.get(name):
            models[name] = _load_axis(axis_dirs[name], "", device) \
                if os.path.isfile(os.path.join(axis_dirs[name],
                                               "config.json")) \
                else _load_axis(axis_dirs[name], name, device)
        else:
            if released_dir is None:
                released_dir = default_model_dir()
                if missing_checkpoints(released_dir):
                    if not auto_download:
                        raise RuntimeError(
                            f"No model provided for '{name}' and the released "
                            "checkpoints are missing. Run: cc4q "
                            "download-models")
                    ensure_checkpoints(released_dir)
            models[name] = _load_axis(released_dir, name, device)
    return ModelHandle(models, device, released_dir or "")
