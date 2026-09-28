import os
from typing import List

def get_files_from_dir(directory: str, include_dirs: List[str]) -> List[str]:
    files_path = []
    abs_include_dirs = [os.path.abspath(os.path.join(directory, d)) for d in include_dirs]
    for root, _, files in os.walk(directory):
        if not any((root.startswith(d) for d in abs_include_dirs)):
            continue
        for file in files:
            if file.endswith('.py'):
                files_path.append(os.path.join(root, file))
    return files_path
