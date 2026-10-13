"""Shared prediction-model selector for the Analyze Code / Analyze
Repository pages.

Choices: the released checkpoints (default) or a package from the user
model registry (trained on the Train page or uploaded on the Your Models
page); single-axis packages fall back to the released checkpoints for the
other axes. Uploading a zip here registers it into the registry too.
"""

import os

import streamlit as st

from cc4q.app import registry
from cc4q.models.hub import ModelHandle, load_models, load_models_from

_cache_key = "model_handle_cache"


def get_model(label="Prediction model", key="model_select",
              auto_download=True):
    """Render the selector; returns a loaded ModelHandle (cached)."""
    options = [("released", "Released checkpoints (default)")]
    entries = registry.list_models()
    for entry in entries:
        axes = "+".join(a.replace("_", " ") for a in entry["axes"])
        suffix = " ★" if entry["is_default"] else ""
        options.append((entry["id"], f"{entry['name']} ({axes}){suffix}"))

    col_sel, col_up = st.columns([3, 1])
    with col_up:
        uploaded = st.file_uploader("Upload model zip", type=["zip"],
                                    key=f"{key}_upload", label_visibility="collapsed")
    if uploaded is not None:
        try:
            entry = registry.register_uploaded_zip(uploaded)
            st.success(f"Registered **{entry['name']}** "
                       f"({' + '.join(entry['axes'])}) — pick it below.")
            st.session_state[_cache_key] = {}
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    with col_sel:
        default_id = next((e["id"] for e in entries if e["is_default"]), None)
        default_index = 0
        if default_id:
            for i, (mid, _) in enumerate(options):
                if mid == default_id:
                    default_index = i
                    break
        choice = st.selectbox(label, range(len(options)),
                              format_func=lambda i: options[i][1],
                              index=default_index, key=key)
    model_id = options[choice][0]

    cache = st.session_state.setdefault(_cache_key, {})
    if model_id in cache:
        return cache[model_id]
    if model_id == "released":
        handle = load_models(auto_download=auto_download)
    else:
        entry = next(e for e in entries if e["id"] == model_id)
        pkg = registry.package_dir(model_id)
        axis_dirs = {a: os.path.join(pkg, a) for a in entry["axes"]}
        handle = load_models_from(axis_dirs, auto_download=auto_download)
    cache[model_id] = handle
    return handle
