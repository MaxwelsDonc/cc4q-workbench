"""Streamlit annotation app (launched via cc4q.annotate / `cc4q annotate`).

Configuration comes from the JSON file at CC4Q_ANNOTATE_CONFIG (written by
cc4q.annotate.prepare). Progress persists to
<output_dir>/annotations.jsonl so a closed session resumes. The rendering
lives in cc4q.annotate.ui so the workbench's Annotate page can embed it.
"""

import json
import os

import streamlit as st

from cc4q.annotate.ui import render_annotation


def _load_config():
    path = os.environ.get("CC4Q_ANNOTATE_CONFIG")
    if not path:
        raise SystemExit(
            "CC4Q_ANNOTATE_CONFIG is not set - launch via cc4q.annotate() "
            "or `cc4q annotate`.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


render_annotation(_load_config(), session_prefix="standalone",
                  embedded=False)
