"""CC4Q Workbench Streamlit app, packaged.

Everything the web demo needs lives in this package (pages, precomputed
data, UI helpers), so ``cc4q demo`` works from a plain wheel install — no
source checkout required.
"""

import os

APP_DIR = os.path.dirname(os.path.abspath(__file__))
PAGES_DIR = os.path.join(APP_DIR, "pages")
DATA_DIR = os.path.join(APP_DIR, "data")
MAIN_PATH = os.path.join(APP_DIR, "main.py")
