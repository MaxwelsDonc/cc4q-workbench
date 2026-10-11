import os
from typing import List, Optional


def get_files_from_dir(directory: str, include_dirs: Optional[List[str]] = None) -> List[str]:
    """.py files under ``directory``, restricted to ``include_dirs`` (paths
    relative to ``directory``).

    Empty or None ``include_dirs`` means the whole ``directory`` tree.
    Matching uses an exact-or-path-boundary rule, so a package dir like
    ``qiskit_aer`` does not swallow a sibling ``qiskit_aer_extra``.
    Results are sorted for deterministic file order.
    """
    directory = os.path.abspath(directory)
    if include_dirs:
        bases = [os.path.abspath(os.path.join(directory, d)) for d in include_dirs]
    else:
        bases = None
    files_path = []
    for root, dirnames, filenames in os.walk(directory):
        dirnames.sort()
        if bases is not None and not any(
            root == b or root.startswith(b + os.sep) for b in bases
        ):
            continue
        for file in sorted(filenames):
            if file.endswith('.py'):
                files_path.append(os.path.join(root, file))
    return files_path
