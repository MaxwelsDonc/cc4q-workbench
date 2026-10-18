"""CC4Q Web Workbench (Starlette/Uvicorn server + single-page UI)."""

import os

WEB_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(WEB_DIR, "static")
# Precomputed demo corpora (manifest.json + units/*.jsonl) that power the
# Corpus Explorer. Formerly cc4q/app/data; moved here with the Streamlit
# retirement so the web stack has no dependency on cc4q.app.
DATA_DIR = os.path.join(WEB_DIR, "data")

__all__ = ["DATA_DIR", "STATIC_DIR", "WEB_DIR"]
