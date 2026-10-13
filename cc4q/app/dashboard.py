"""Quantum-centric dashboard: §1 Corpus Built, §2 Quantum Density Check,
§3 Knowledge Profile, plus SDK compare mode (design doc §3.3 / §4).

Chart construction lives in cc4q.viz.charts (pure plotly functions); this
module only renders them with the app theme.

No developer-intent analyses live here — intent appears only as a unit-card
badge (Analyze Code) and a collapsed Explore filter.
"""

import streamlit as st

from cc4q.viz.charts import (
    interpretation_hint as _interpretation_hint,
    quantum_residence_heatmap as _quantum_residence_heatmap,
    radar_figure as _radar_figure,
    type_entity_figure as _type_entity_chart,
)
from cc4q.app.data_io import units_to_jsonl_bytes
from cc4q.app.ui import metric_card, plotly_layout


def _styled(fig):
    return plotly_layout(fig)


def render_section1(stats, df):
    st.subheader("§1 · Corpus Built")
    st.caption("Build — repository → labeled comment corpus.")
    cols = st.columns(3)
    with cols[0]:
        metric_card(f"{stats.get('python_files') or stats['files']:,}",
                    "Python files")
    with cols[1]:
        metric_card(f"{stats['ccps']:,}", "CCPs")
    with cols[2]:
        metric_card(f"{stats['sccus']:,}", "SCCUs")
    st.plotly_chart(_styled(_type_entity_chart(stats)), width="stretch")
    st.download_button(
        "Download labeled corpus (JSONL)",
        data=units_to_jsonl_bytes(df),
        file_name=f"{stats['sdk']}_sccus_labeled.jsonl",
        mime="application/x-jsonlines",
    )


def render_section2(stats):
    st.subheader("§2 · Quantum Density Check")
    st.caption("Inspect — how much quantum knowledge, and where it lives "
               "(companion paper RQ2/RQ3).")
    density = stats.get("comment_density", {})
    cols = st.columns([2, 3])
    with cols[0]:
        metric_card(f"{stats['quantum_proportion']:.1%}", "Quantum % of SCCUs")
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        metric_card(f"{density.get('value', 0.0):.3f}",
                    "Comment density (comment lines / code lines)")
        if density.get("code_lines"):
            st.caption(f"{density['comment_lines']:,} comment lines / "
                       f"{density['code_lines']:,} code lines")
    with cols[1]:
        st.plotly_chart(_styled(_quantum_residence_heatmap(stats)), width="stretch")


def render_section3(stats):
    st.subheader("§3 · Knowledge Profile")
    st.caption("Profile — what kind of quantum knowledge (companion paper RQ6).")
    fig = _radar_figure([(stats["sdk"], stats)],
                        "Six-category quantum-knowledge profile")
    st.plotly_chart(_styled(fig), width="stretch")
    st.markdown(_interpretation_hint(stats))


def render_dashboard(stats, df, label=None):
    if label:
        st.markdown(label)
    if stats.get("source") == "live":
        st.caption("⚠️ Model-labeled, unverified — no human spot-check on "
                   "this repository.")
    elif stats.get("source") == "cc4q-pipeline":
        st.caption("Model-labeled (release classifiers); the original three "
                   "SDKs are human-validated.")
    if stats.get("sampled"):
        st.caption(f"Stats computed over the full corpus; charts and "
                   f"download show a {stats.get('sample_size', 2000):,}-row "
                   f"random sample (seed {stats.get('sample_seed', 42)}).")
    render_section1(stats, df)
    st.divider()
    render_section2(stats)
    st.divider()
    render_section3(stats)


def render_compare(stats_a, stats_b, manifest):
    """Two overlaid radar traces + Quantum % side-by-side + the paper's
    infrastructure-vs-application group aggregates."""
    st.caption("Pick two SDKs side by side — the overlaid profile supports "
               "the paper's infrastructure-vs-application-layer finding.")
    col_a, col_b = st.columns(2)
    for col, stats in ((col_a, stats_a), (col_b, stats_b)):
        with col:
            st.markdown(f"**{stats['sdk']}** ({stats['version']})")
            metric_card(f"{stats['quantum_proportion']:.1%}", "Quantum % of SCCUs")

    fig = _radar_figure([(stats_a["sdk"], stats_a), (stats_b["sdk"], stats_b)],
                        "Knowledge profiles compared")
    st.plotly_chart(_styled(fig), width="stretch")

    groups = (manifest or {}).get("groups", {})
    infra = groups.get("infrastructure")
    app = groups.get("application")
    if infra and app:
        st.markdown("**Group aggregates** — the paper's finding:")
        cols = st.columns(2)
        with cols[0]:
            metric_card(f"{infra['quantum_proportion']:.1%}",
                        "Infrastructure SDKs (qiskit, qiskit-aer, "
                        "qiskit-ibm-runtime)")
        with cols[1]:
            metric_card(f"{app['quantum_proportion']:.1%}",
                        "Application SDKs (qiskit-machine-learning, "
                        "qiskit-nature, qiskit-algorithms)")
        st.caption("Infrastructure-level SDKs carry a markedly higher share "
                   "of quantum comments than application-level ones.")
