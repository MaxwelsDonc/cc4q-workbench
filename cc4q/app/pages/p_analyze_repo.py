"""Page — Analyze Repository: Build → Inspect → Profile (the hero page)."""

import streamlit as st

from cc4q.app import dashboard  # noqa: E402
from cc4q.app import data_io  # noqa: E402
from cc4q.app.model_cache import checkpoints_missing, get_models, missing_checkpoints_warning  # noqa: E402
from cc4q.app.ui import footer  # noqa: E402

STAGE_NUM = {"Cloning": 1, "Extracting": 2, "Segmenting": 3, "Labeling": 4}
VALIDATION_TEXT = (
    "**How trustworthy are the labels?** Live results and the three newest "
    "SDKs are labeled by the release classifiers (fine-tuned "
    "`bert-base-uncased`) and marked *model-labeled*. The three original "
    "SDKs ship a human-validated gold corpus. In a human spot-check of "
    "**379 SCCUs**, annotators agreed with the model labels **85.0%** of "
    "the time (companion paper, validation section)."
)


def _render_precomputed(sdk, manifest):
    stats = manifest["repos"][sdk]
    df = data_io.load_units_df(sdk)
    dashboard.render_dashboard(stats, df)


def _render_live(url):
    key = f"live_result:{url.strip()}"
    if key in st.session_state:
        stats, df = st.session_state[key]
        dashboard.render_dashboard(stats, df)
        return

    models = get_models()  # cached resource; models load once per session
    status = st.status("Stage 1/4 — Cloning…", state="running", expanded=True)
    last = {"stage": None}

    def progress(stage):
        if last["stage"] == stage:
            return
        last["stage"] = stage
        status.update(label=f"Stage {STAGE_NUM[stage]}/4 — {stage}…",
                      state="running")

    try:
        from repo_live import RepoRefusedError, analyze_live_repo

        stats, df = analyze_live_repo(url, models, progress=progress)
    except RepoRefusedError as exc:
        status.update(label="Cannot analyze this repository", state="error")
        st.warning(str(exc))
        return
    except Exception as exc:  # clone/network/pipeline failures
        status.update(label="Analysis failed", state="error")
        st.error(f"Live analysis failed: {exc}")
        return
    status.update(label="Done — all 4 stages complete", state="complete")
    st.session_state[key] = (stats, df)
    dashboard.render_dashboard(stats, df)


def render():
    st.header("Analyze Repository")
    st.write(
        "Build a labeled comment corpus from a repository, inspect how much "
        "quantum knowledge it carries and where it lives, then profile the "
        "six-category quantum-knowledge distribution. Precomputed results for "
        "six Qiskit-ecosystem SDKs render instantly; live mode runs the full "
        "pipeline on any small GitHub repo (≤200 Python files)."
    )

    manifest = data_io.load_manifest()
    options = data_io.repo_options(manifest)
    sdk_labels = {label: sdk for sdk, label in options}
    labels = list(sdk_labels)
    sdks_in_order = [sdk_labels[l] for l in labels]

    tab_pre, tab_live = st.tabs(["Precomputed SDKs", "Live repository"])

    with tab_pre:
        label = st.selectbox("SDK", labels, index=0)
        _render_precomputed(sdk_labels[label], manifest)

    with tab_live:
        url = st.text_input(
            "GitHub URL",
            placeholder="https://github.com/owner/repo",
            label_visibility="collapsed",
        )
        no_models = bool(checkpoints_missing())
        run_live = st.button("Analyze repository", type="primary",
                             disabled=not url.strip() or no_models)
        if no_models:
            missing_checkpoints_warning()
        if run_live and url.strip():
            _render_live(url)

    st.divider()
    st.subheader("Compare mode")
    manifest_for_compare = manifest

    def _index(preferred):
        return sdks_in_order.index(preferred) if preferred in sdks_in_order else 0

    c1, c2 = st.columns(2)
    with c1:
        a = st.selectbox("SDK A", labels, index=_index("qiskit"))
    with c2:
        b = st.selectbox("SDK B", labels, index=_index("qiskit-machine-learning"))
    dashboard.render_compare(manifest["repos"][sdk_labels[a]],
                             manifest["repos"][sdk_labels[b]],
                             manifest_for_compare)

    with st.expander("About the labels · human verification"):
        st.markdown(VALIDATION_TEXT)

    footer()


render()
