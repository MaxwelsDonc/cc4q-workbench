"""Sphinx configuration for the CC4Q docs."""

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

project = "CC4Q"
copyright = "2026, CC4Q authors"
author = "CC4Q authors"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autosummary_generate = True
autodoc_member_order = "bysource"
autoclass_content = "both"
napoleon_google_docstring = True
napoleon_numpy_docstring = False

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_title = "CC4Q"
html_static_path = []
