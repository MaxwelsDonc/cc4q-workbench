"""Page — Build step 1: Get Data (repo URL / local dir / upload -> corpus)."""

import json

import os

import pandas as pd
import streamlit as st

from cc4q.app import PAGES_DIR, stepper

SOURCES = ("GitHub repository URL", "Local source directory",
           "Upload a corpus JSONL")


def _stash(records, source_label):
    st.session_state["build_corpus"] = records
    st.session_state["build_corpus_source"] = source_label
    st.session_state.pop("build_labeled", None)
    st.session_state.pop("train_stash", None)


def render():
    st.header("1 · Get Data")
    st.write("Turn source code into a comment corpus — clone a repository, "
             "point at a local checkout, or upload an existing corpus file.")

    if stepper.render_stepper(1):
        st.rerun()

    source = st.radio("Source", SOURCES, horizontal=True)
    records = None

    if source == "GitHub repository URL":
        c1, c2 = st.columns([3, 1])
        url = c1.text_input("Repository URL",
                            placeholder="https://github.com/owner/repo")
        ref = c2.text_input("Ref (optional)", placeholder="tag / branch")
        if st.button("Clone and build", type="primary",
                     disabled=not url.strip()):
            from cc4q.app import build_flow
            bar = st.progress(0.0, text="cloning…")
            try:
                records = build_flow.build_from_url(
                    url.strip(), ref.strip() or None,
                    progress=lambda f, msg: bar.progress(
                        min(f, 0.99), text=msg))
            except Exception as exc:
                st.error(f"Build failed: {exc}")
                records = None
            bar.progress(1.0, text="done")
    elif source == "Local source directory":
        path = st.text_input("Directory", placeholder="data/input/qiskit")
        if st.button("Build corpus", type="primary",
                     disabled=not path.strip()):
            from cc4q.app import build_flow
            try:
                records = build_flow.build_from_dir(path.strip())
            except Exception as exc:
                st.error(f"Build failed: {exc}")
    else:
        upload = st.file_uploader("Corpus JSONL (records with "
                                  "comment_text)", type=["jsonl", "json"])
        if upload is not None:
            text = upload.read().decode("utf-8")
            records = json.loads(text) if text.lstrip().startswith("[") \
                else [json.loads(l) for l in text.splitlines() if l.strip()]

    if records:
        _stash(records, source)
        st.success(f"{len(records):,} SCCUs ready.")
    stashed = st.session_state.get("build_corpus")
    if stashed:
        st.caption(f"Current corpus ({len(stashed):,} SCCUs, from "
                   f"{st.session_state.get('build_corpus_source', '?')}): "
                   "preview")
        df = pd.DataFrame(stashed)
        cols = [c for c in ("id", "file", "comment_type", "comment_text")
                if c in df.columns]
        st.dataframe(df[cols].head(50), width="stretch", hide_index=True)
        if stepper.continue_button(2, None):
            st.switch_page(os.path.join(PAGES_DIR, "p_label.py"))


render()
