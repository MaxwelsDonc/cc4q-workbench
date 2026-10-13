"""Page — Analyze Code: snippet in, labeled comment-unit cards out."""

import streamlit as st

from cc4q.app import analysis  # noqa: E402
from cc4q.app.model_cache import checkpoints_missing, get_models, missing_checkpoints_warning  # noqa: E402
from cc4q.app.ui import footer, summary_strip, unit_card  # noqa: E402


def _results(units, fallback):
    n_quantum = sum(1 for u in units if u.get("quantum_related"))
    summary_strip(len(units), n_quantum)
    if fallback:
        st.caption("Line-by-line fallback: input could not be parsed as "
                   "Python, so each non-empty line was classified directly.")

    st.markdown("#### Labeled units")
    for u in units:
        unit_card(
            text=u["text"],
            comment_type=u["comment_type"],
            entity_type=u.get("entity_type", "—"),
            quantum=u.get("quantum_related"),
            category=u.get("quantum_category"),
        )


def render():
    st.header("Analyze Code")
    st.write(
        "Paste a Python snippet. CC4Q extracts its comments and splits them "
        "into sentence-level units (SCCUs). The pipeline labels each unit on "
        "three axes — quantum-relatedness, quantum category, and developer "
        "intent — and this view foregrounds the two quantum axes."
    )

    left, right = st.columns([1, 1], vertical_alignment="top")
    no_models = bool(checkpoints_missing())

    with left:
        code = st.text_area("Python source", value=analysis.QISKIT_SNIPPET,
                            height=360, label_visibility="collapsed")
        st.caption("Prefilled: a minimal Qiskit Bell-state circuit.")
        run = st.button("Analyze", type="primary", use_container_width=True,
                        disabled=no_models)
        st.caption(f"running on: {analysis.DEVICE}")

    with right:
        st.markdown("**Results**")
        if no_models:
            missing_checkpoints_warning()
            return
        if not run:
            st.info("Click **Analyze** to label every comment unit in the "
                    "snippet. Classifiers load lazily on first run.")
            return

        with st.spinner("Loading classifiers (first run takes a few seconds)"):
            models = get_models()
        with st.spinner("Extracting, segmenting and classifying…"):
            units, parse_error, fallback = analysis.analyze_code(code, models=models)

        if parse_error:
            st.warning("Not valid Python — falling back to line-by-line mode.")
            with st.expander("Technical detail"):
                st.code(parse_error)
        if not units:
            st.info("No comments found — nothing to classify. Try adding a "
                    "docstring or a comment.")
            return
        _results(units, fallback)

    footer()


render()
