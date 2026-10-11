"""Lazily cached access to the three BERT classifiers (shared by pages)."""

import os
import sys

import streamlit as st

DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DEMO_DIR)
if os.path.join(PROJECT_ROOT, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts"))

import cc4q_analysis as analysis  # noqa: E402
from download_models import missing_checkpoints  # noqa: E402


CKPT_DIR = os.path.join(PROJECT_ROOT, "models_checkpoints")
REQUIRED = ("quantum_related", "quantum_category", "developer_intent")


def checkpoints_missing():
    """Names of missing checkpoint dirs ([] when the demo can classify).

    Only a missing checkpoints root is treated as "all missing"; any other
    error from the completeness check propagates (fail loudly, never
    silently claim checkpoints exist).
    """
    if not os.path.isdir(CKPT_DIR):
        return list(REQUIRED)
    return missing_checkpoints()


def missing_checkpoints_warning():
    """st.warning telling the user exactly how to fetch the checkpoints."""
    st.warning(
        "Model checkpoints are not present in `models_checkpoints/`, so "
        "classification is unavailable. Download them once from the GitHub "
        "release (≈1.2 GB):\n\n"
        "```\npython scripts/download_models.py\n```\n\n"
        "Precomputed dashboards and the corpus explorer work without them.",
        icon="⚠️",
    )


@st.cache_resource(show_spinner=False)
def get_models():
    missing = checkpoints_missing()
    if missing:
        raise RuntimeError(
            f"Missing model checkpoints: {', '.join(missing)}. "
            "Run: python scripts/download_models.py"
        )
    return analysis.load_models()
