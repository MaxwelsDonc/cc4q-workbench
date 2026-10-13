"""Lazily cached access to the three BERT classifiers (shared by pages)."""

import os

import streamlit as st

from cc4q.models.hub import default_model_dir, load_models, missing_checkpoints

CKPT_DIR = default_model_dir()
REQUIRED = ("quantum_related", "quantum_category", "developer_intent")


def checkpoints_missing():
    """Names of missing checkpoint dirs ([] when the demo can classify).

    Only a missing checkpoints root is treated as "all missing"; any other
    error from the completeness check propagates (fail loudly, never
    silently claim checkpoints exist).
    """
    if not os.path.isdir(CKPT_DIR):
        return list(REQUIRED)
    return missing_checkpoints(CKPT_DIR)


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
    return load_models(model_dir=CKPT_DIR)
