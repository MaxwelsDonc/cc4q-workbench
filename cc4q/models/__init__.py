"""Model-layer public re-exports.

The canonical implementation lives in :mod:`cc4q.models.hub`; this module
keeps the shorter ``cc4q.models.*`` import path stable.
"""
from cc4q.models.hub import (
    BASE_URL, CHECKPOINTS, RELEASE, RELEASE_REPO, ModelHandle,
    checkpoint_complete, ensure_checkpoints, load_models,
    missing_checkpoints, resolve_device, load_models_from,
)

__all__ = [
    "BASE_URL", "CHECKPOINTS", "RELEASE", "RELEASE_REPO", "ModelHandle",
    "checkpoint_complete", "ensure_checkpoints", "load_models",
    "missing_checkpoints", "resolve_device", "load_models_from",
]
