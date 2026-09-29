"""Page — Analyze Code: snippet in, labeled comment-unit cards out."""

import streamlit as st

from bootstrap import boot

boot()

import cc4q_analysis as analysis  # noqa: E402
from model_cache import checkpoints_missing, get_models, missing_checkpoints_warning  # noqa: E402
from ui import footer, metric_card, unit_card  # noqa: E402


def _results(units, fallback):
    n_quantum = sum(1 for u in units if u.get("quantum_related"))
    cols = st.columns(3)
    with cols[0]:
        metric_card(str(len(units)), "Comment units")
    with cols[1]:
        metric_card(str(n_quantum), "Quantum-related")
    with cols[2]:
        metric_card("raw text" if fallback else "code", "Analysis mode")
    if fallback:
        st.caption("Fallback mode: input classified line by line without "
                   "code-comment extraction.")

    st.markdown("#### Labeled units")
    for u in units:
        unit_card(
            text=u["text"],
            comment_type=u["comment_type"],
            entity_type=u.get("entity_type", "—"),
            quantum=u.get("quantum_related"),
            intent=u.get("developer_intent", "—"),
            category=u.get("quantum_category"),
        )


def render():
    st.header("Analyze Code")
    st.write(
        "Paste a Python snippet. CC4Q extracts its comments, splits them into "
        "sentence-level units (SCCUs), and labels each unit on three axes — "
        "quantum-relatedness, developer intent, and quantum category."
    )

    left, right = st.columns([1, 1], vertical_alignment="top")
    no_models = bool(checkpoints_missing())

    with left:
        code = st.text_area("Python source", value=analysis.QISKIT_SNIPPET,
                            height=380, label_visibility="collapsed")
        st.caption("Prefilled: a minimal Qiskit Bell-state circuit.")
        run = st.button("Analyze", type="primary", use_container_width=True,
                        disabled=no_models)

    with right:
        st.markdown("**Results**")
        if no_models:
            missing_checkpoints_warning()
            return
        if not run:
            st.info("Click **Analyze** to label every comment unit in the "
                    "snippet. Classifiers load lazily on first run (CPU).")
            return

        with st.spinner("Loading the three BERT classifiers (first run only)…"):
            models = get_models()
        with st.spinner("Extracting, segmenting and classifying comments…"):
            units, parse_error, fallback = analysis.analyze_code(code, models=models)

        if parse_error:
            st.warning(parse_error + " Falling back to line-by-line classification.")
        if not units:
            st.info("No comments found — nothing to classify. Try adding a "
                    "docstring or a comment.")
            return
        _results(units, fallback)

    footer()


render()
