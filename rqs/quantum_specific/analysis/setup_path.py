import os
import sys
file_root = os.path.dirname(__file__)
parent_root = os.path.dirname(file_root)
candidate_roots = [parent_root, os.path.dirname(parent_root)]
for candidate_root in candidate_roots:
    if candidate_root not in sys.path:
        sys.path.append(candidate_root)
from config import cat2tex, figure_global
__all__ = ['parent_root', 'cat2tex', 'figure_global']
