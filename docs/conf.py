"""Sphinx configuration for the CC4Q docs."""

import os
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

project = "CC4Q Workbench"
copyright = "2026, CC4Q authors"
author = "CC4Q authors"
release = "0.2.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

autodoc_member_order = "bysource"
autoclass_content = "both"
autodoc_preserve_defaults = True
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_use_param = True
napoleon_use_rtype = False

templates_path = ["_templates"]
exclude_patterns = ["_build", "_redirects", "Thumbs.db", ".DS_Store"]

# Static redirects for pages that existed in the old autosummary tree.
html_extra_path = ["_redirects"]

html_theme = "furo"
html_title = "CC4Q Workbench"
html_static_path = ["_static"]
