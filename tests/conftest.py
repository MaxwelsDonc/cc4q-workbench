"""Shared pytest setup: make the repo and demo/ importable."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for path in (ROOT, os.path.join(ROOT, "demo"), os.path.join(ROOT, "demo", "pages")):
    if path not in sys.path:
        sys.path.insert(0, path)
