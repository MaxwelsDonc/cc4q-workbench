"""Repository/path helpers shared by the pipeline and the model hub."""

import os
from typing import List

#: Repository root for a source checkout / editable install
#: (``cc4q/pipeline/`` -> up two = repo root).
REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)

__all__ = ["get_project_path", "split_path"]


def get_project_path() -> str:
    """Repository root of a source checkout (editable install).

    In a plain site-packages install there is no repository root; this
    still returns the directory that *contains* the installed ``cc4q``
    package, which is where relative config paths are expected to live.

    Returns:
        Absolute path to the repository/package parent directory.
    """
    return REPO_ROOT


def split_path(path: str) -> List[str]:
    """Normalize a path and split it into components.

    Args:
        path: Relative or absolute path.

    Returns:
        Path components produced by :func:`os.path.normpath` and
        :func:`os.path.split` semantics.
    """
    return os.path.normpath(path).split(os.sep)
