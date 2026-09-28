import os
from typing import List

def get_project_path() -> str:
    current_file = os.path.abspath(__file__)
    return os.path.abspath(os.path.join(current_file, '../../'))

def split_path(path: str) -> List[str]:
    return os.path.normpath(path).split(os.sep)
