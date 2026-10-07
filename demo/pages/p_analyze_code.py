"""Page — Analyze Code: snippet in, labeled comment-unit cards out."""

import streamlit as st

from bootstrap import boot

boot()

import cc4q_analysis as analysis  # noqa: E402
from model_cache import checkpoints_missing, get_models, missing_checkpoints_warning  # noqa: E402
from ui import footer, summary_strip, unit_card  # noqa: E402


def _results(units, fallback):
    n_quantum = sum(1 for u in units if u.get("quantum_related"))
    summary_strip(len(units), n_quantum)
    if fallback:
        st.caption("Raw-text mode: input classified line by line without "
                   "code-comment extraction.")

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
        force_raw = st.checkbox("Analyze as raw comment text "
                                "(skip code parsing; classify each non-empty line)")
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

        with st.spinner("Loading classifiers (first run takes a few seconds)"):
            models = get_models()

        if force_raw:
            units = analysis.raw_text_units(code)
            parse_error, fallback = None, True
            if units:
                with st.spinner("Classifying…"):
                    analysis.classify_units(units, models)
        else:
            with st.spinner("Extracting, segmenting and classifying…"):
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
