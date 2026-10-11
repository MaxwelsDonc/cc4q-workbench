"""Download and verify the CC4Q model checkpoints from the GitHub release.

The three fine-tuned BERT classifiers (one directory per label axis) are
shipped as release assets because they are too large for git:

    https://github.com/MaxwelsDonc/cc4q-checkpoints/releases/tag/v0.1.0

Usage (from the workbench root, Python >= 3.11, no extra deps):

    python scripts/download_models.py            # download what is missing
    python scripts/download_models.py --check    # verify only, exit 1 if incomplete

Each asset is a tar.gz of one checkpoint directory. After download the
SHA256 checksum is verified before extraction into models_checkpoints/.
"""

import argparse
import hashlib
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CKPT_ROOT = os.path.join(PROJECT_ROOT, "models_checkpoints")

# Checkpoints are hosted in a separate public repository so they are
# anonymously downloadable even while the workbench repository is private.
REPO = "MaxwelsDonc/cc4q-checkpoints"
RELEASE = "v0.1.0"
BASE_URL = f"https://github.com/{REPO}/releases/download/{RELEASE}"

# asset name -> (checkpoint dir name, SHA256 of the .tar.gz)
CHECKPOINTS = {
    "quantum_related.tar.gz": (
        "quantum_related",
        "3a519c5173f323f735434065d248b50bc58a8a36d0ce6f59f6f21196b10f7bdd",
    ),
    "quantum_category.tar.gz": (
        "quantum_category",
        "de17c00707c23adcb8818844e84a1acb0b03486cb655999e8513989ab3c81b32",
    ),
    "developer_intent.tar.gz": (
        "developer_intent",
        "3e397e177f1479ab2d91d2d6de7233bb2c7f4b19de37dfa9fbeba7f3849b8286",
    ),
}

# files that must exist for a checkpoint dir to count as usable
REQUIRED_FILES = ("config.json", "model.safetensors", "tokenizer_config.json")


def checkpoint_complete(name):
    path = os.path.join(CKPT_ROOT, name)
    return all(os.path.isfile(os.path.join(path, f)) for f in REQUIRED_FILES)


def missing_checkpoints():
    return [name for name, _ in CHECKPOINTS.values()
            if not checkpoint_complete(name)]


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
            "- check https://github.com/MaxwelsDonc/cc4q-checkpoints/releases"
        ) from exc
    except Exception:
        # one retry (transient network errors), then give up
        try:
            _download_once(asset, dest_path)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"Release asset not found at {BASE_URL}/{asset} (HTTP {exc.code}) "
                "- check https://github.com/MaxwelsDonc/cc4q-checkpoints/releases"
            ) from exc


def fetch_missing(verbose=True):
    """Download + verify + extract any missing checkpoint. Returns list of
    checkpoint names that are still missing afterwards."""
    missing = missing_checkpoints()
    if not missing:
        if verbose:
            print(f"All checkpoints already present in {CKPT_ROOT}")
        return []

    os.makedirs(CKPT_ROOT, exist_ok=True)
    tmpdir = tempfile.mkdtemp(prefix="cc4q_models_")
    try:
        for asset, (name, expected_sha) in CHECKPOINTS.items():
            if name not in missing:
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
                tar.extractall(CKPT_ROOT, filter="data")
            if not checkpoint_complete(name):
                raise RuntimeError(
                    f"Extraction of {asset} did not produce a usable "
                    f"checkpoint at {os.path.join(CKPT_ROOT, name)}"
                )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return missing_checkpoints()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="verify only; exit 1 if any checkpoint is missing")
    args = parser.parse_args()

    missing = missing_checkpoints()
    if args.check:
        if missing:
            print(f"MISSING: {', '.join(missing)}")
            print("Run: python scripts/download_models.py")
            sys.exit(1)
        print("OK: all model checkpoints present.")
        return

    still_missing = fetch_missing()
    if still_missing:
        print(f"FAILED: still missing {', '.join(still_missing)}")
        sys.exit(1)
    print("Done — all model checkpoints present in", CKPT_ROOT)


if __name__ == "__main__":
    main()
