"""Shared sys.path bootstrap for the demo entrypoint and every page file."""

import os
import sys

DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DEMO_DIR)

_booted = False


def boot():
    """Make demo/ and demo/pages/ importable. Idempotent."""
    global _booted
    if _booted:
        return
    for path in (DEMO_DIR, os.path.join(DEMO_DIR, "pages"), PROJECT_ROOT):
        if path not in sys.path:
            sys.path.insert(0, path)
    _booted = True
