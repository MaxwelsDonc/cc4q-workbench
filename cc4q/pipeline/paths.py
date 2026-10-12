import os
from typing import List

#: repository root for a source checkout / editable install
#: (cc4q/pipeline/ -> up 2 = repo root)
REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def get_project_path() -> str:
    """Repository root of a source checkout (editable install).

    In a plain site-packages install there is no repository root; this
    still returns the directory that *contains* the installed ``cc4q``
    package, which is where relative config paths are expected to live.
    """
    return REPO_ROOT


def split_path(path: str) -> List[str]:
    return os.path.normpath(path).split(os.sep)
