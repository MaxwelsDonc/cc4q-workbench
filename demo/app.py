"""CC4Q workbench — public demo.

Run from the workbench root:
    streamlit run demo/app.py
"""

import json
import os
import sys

import pandas as pd
import streamlit as st

DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DEMO_DIR)
if DEMO_DIR not in sys.path:
    sys.path.insert(0, DEMO_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cc4q_analysis import QISKIT_SNIPPET, analyze_code, load_models

st.set_page_config(page_title="CC4Q Demo", page_icon="⚛", layout="wide")
st.title("CC4Q: Comment Classification for Quantum Software")


@st.cache_resource(show_spinner=False)
def get_models():
    return load_models()


def truncate(text, n=90):
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def page_analyze():
    st.header("Analyze a Python snippet")
    st.write(
        "Paste a Python snippet below. CC4Q extracts its comments, splits them "
        "into sentence-level units, and labels each unit on three axes: "
        "quantum-relatedness, developer intent, and (for quantum units) quantum category."
    )
    code = st.text_area("Python source", value=QISKIT_SNIPPET, height=320)
    force_raw = st.checkbox(
        "Analyze raw comment text (skip code parsing; classify each non-empty line)",
        value=False,
    )

    if not st.button("Analyze", type="primary"):
        return

    with st.spinner(
        "Loading the three BERT classifiers (first run takes a few seconds)…"
    ):
        models = get_models()

    with st.spinner("Running extraction, segmentation and classification…"):
        if force_raw:
            from cc4q_analysis import raw_text_units, classify_units

            units = raw_text_units(code)
            parse_error, fallback = None, True
            if units:
                classify_units(units, models)
        else:
            units, parse_error, fallback = analyze_code(code, models=models)

    if parse_error:
        st.warning(parse_error + " Falling back to line-by-line classification.")
    if not units:
        st.info("No comments found — nothing to classify. Try adding a docstring or comment.")
        return

    n_quantum = sum(1 for u in units if u.get("quantum_related"))
    cols = st.columns(3)
    cols[0].metric("Comment units", len(units))
    cols[1].metric("Quantum-related", n_quantum)
    cols[2].metric("Mode", "raw text" if fallback else "code")
    if fallback:
        st.caption(
            "Fallback mode: the input was classified line by line without "
            "code-comment extraction."
        )

    rows = [
        {
            "Comment text": truncate(u["text"]),
            "Type": u["comment_type"],
            "Quantum?": "✓" if u.get("quantum_related") else "✗",
            "Developer intent": u.get("developer_intent", "—"),
            "Quantum category": u.get("quantum_category") or "—",
        }
        for u in units
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    with st.expander("Show full comment texts"):
        for i, u in enumerate(units, 1):
            st.markdown(f"**{i}.** ({u['comment_type']}) {u['text']}")


def page_explore():
    st.header("Generalization experiment results")
    st.write(
        "The three classifiers (fine-tuned from bert-base-uncased) were applied "
        "to comments from three Qiskit-ecosystem repositories they were **not** "
        "trained on. Stats below are read live from `exp/labeling_summary.json`."
    )

    summary_path = os.path.join(PROJECT_ROOT, "exp", "labeling_summary.json")
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    repos = summary["repos"]
    table = pd.DataFrame(
        [
            {
                "Repository": name,
                "Version": info["version"],
                "SCCUs": info["sccus"],
                "Quantum SCCUs": info["quantum_sccus"],
                "Quantum proportion": f"{info['quantum_proportion']:.1%}",
            }
            for name, info in repos.items()
        ]
    )
    st.subheader("Corpus statistics")
    st.dataframe(table, width="stretch", hide_index=True)

    st.subheader("Developer intent distribution (all SCCUs)")
    intent_df = pd.DataFrame(
        {name: pd.Series(info["intent_counts"]) for name, info in repos.items()}
    ).fillna(0)
    st.bar_chart(intent_df)

    st.subheader("Quantum category distribution (quantum SCCUs only)")
    cat_df = pd.DataFrame(
        {name: pd.Series(info["category_counts"]) for name, info in repos.items()}
    ).fillna(0)
    st.bar_chart(cat_df)

    md_path = os.path.join(PROJECT_ROOT, "exp", "generalization_results.md")
    with open(md_path, "r", encoding="utf-8") as f:
        st.markdown(f.read())


page = st.sidebar.radio("Pages", ["Analyze", "Explore"])
st.sidebar.caption("CC4Q workbench demo — CPU inference, three fine-tuned BERT classifiers.")
if page == "Analyze":
    page_analyze()
else:
    page_explore()
