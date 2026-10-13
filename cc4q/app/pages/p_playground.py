"""Page — Analyze Code: snippet in, labeled comment-unit cards out."""

import streamlit as st

from cc4q.app import analysis  # noqa: E402
from cc4q.app import model_select, registry
from cc4q.app.model_cache import checkpoints_missing, missing_checkpoints_warning  # noqa: E402
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
    st.header("Playground")
    st.caption("Scratch space — "
               "experiments here are not saved as assets.")
    st.write(
        "Paste a Python snippet. CC4Q extracts its comments and splits them "
        "into sentence-level units (SCCUs). The pipeline labels each unit on "
        "three axes — quantum-relatedness, quantum category, and developer "
        "intent — and this view foregrounds the two quantum axes."
    )

    left, right = st.columns([1, 1], vertical_alignment="top")
    no_models = bool(checkpoints_missing()) and not registry.list_models()

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
            models = model_select.resolve_default_handle()
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

    st.divider()
    st.subheader("Live repository try-out")
    st.caption("Scratch space — nothing here is saved. To keep results, "
               "build a corpus on the Corpora page.")
    url = st.text_input("GitHub URL",
                        placeholder="https://github.com/owner/repo",
                        key="pg_url")
    if st.button("Analyze repository", type="primary", disabled=not url.strip()):
        from cc4q.app import repo_live
        models = model_select.resolve_default_handle()
        status = st.status("Stage 1/4 — Cloning…", state="running",
                           expanded=True)
        last = {"stage": None}

        def progress(stage):
            nums = {"Cloning": 1, "Extracting": 2, "Segmenting": 3,
                    "Labeling": 4}
            if last["stage"] != stage:
                last["stage"] = stage
                status.update(label=f"Stage {nums[stage]}/4 — {stage}…",
                              state="running")

        try:
            stats, df = repo_live.analyze_live_repo(url, models,
                                                    progress=progress)
        except repo_live.RepoRefusedError as exc:
            status.update(label="Cannot analyze this repository",
                          state="error")
            st.warning(str(exc))
            return
        except Exception as exc:
            status.update(label="Analysis failed", state="error")
            st.error(f"Live analysis failed: {exc}")
            return
        status.update(label="Done — all 4 stages complete", state="complete")
        import cc4q.app.dashboard as dashboard
        dashboard.render_dashboard(stats, df)

    footer()


render()
