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


def resolve_default_handle(auto_download=True):
    """The global prediction model: registry default if set, else the
    released checkpoints. Used by pages without a per-page selector."""
    entries = registry.list_models()
    default = next((e for e in entries if e["is_default"]), None)
    if default is None:
        return load_models(auto_download=auto_download)
    pkg = registry.package_dir(default["id"])
    axis_dirs = {a: os.path.join(pkg, a) for a in default["axes"]}
    return load_models_from(axis_dirs, auto_download=auto_download)


@st.dialog("⚙ Models")
def models_dialog():
    """Registry management, available from the gear button on every page."""
    import tempfile
    upload = st.file_uploader("Upload a model zip (one HF directory per "
                              "axis: quantum_related, quantum_category, "
                              "developer_intent)", type=["zip"])
    if upload is not None:
        try:
            entry = registry.register_uploaded_zip(upload)
            st.success(f"Registered **{entry['name']}**.")
        except ValueError as exc:
            st.error(str(exc))
    entries = registry.list_models()
    if not entries:
        st.caption("No custom models — the released checkpoints are the "
                   "default everywhere.")
        return
    for entry in entries:
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        star = "★ " if entry["is_default"] else ""
        c1.markdown(f"{star}**{entry['name']}** — "
                    f"{', '.join(entry['axes'])}")
        if not entry["is_default"]:
            if c2.button("Default", key=f"dlg_def_{entry['id']}"):
                registry.set_default(entry["id"])
                st.session_state[_cache_key] = {}
                st.rerun()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        tmp.close()
        registry.zip_package(entry["id"], tmp.name)
        with open(tmp.name, "rb") as f:
            c3.download_button("⬇", data=f.read(),
                               file_name=f"{entry['id']}.zip",
                               key=f"dlg_dl_{entry['id']}")
        os.unlink(tmp.name)
        if c4.button("🗑", key=f"dlg_del_{entry['id']}"):
            registry.delete(entry["id"])
            st.session_state[_cache_key] = {}
            st.rerun()
