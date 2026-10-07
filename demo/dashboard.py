"""Quantum-centric dashboard: §1 Corpus Built, §2 Quantum Density Check,
§3 Knowledge Profile, plus SDK compare mode (design doc §3.3 / §4).

No developer-intent analyses live here — intent appears only as a unit-card
badge (Analyze Code) and a collapsed Explore filter.
"""

import plotly.graph_objects as go
import streamlit as st

from data_io import (
    CATEGORY_ORDER, ctype_entity_frame, quantum_residence_frame,
    radar_labels, radar_shares, units_to_jsonl_bytes,
)
from ui import CATEGORY_COLORS, PRIMARY, metric_card, plotly_layout

CTYPE_COLORS = {"docstring": PRIMARY, "block": "#9F7AEA", "inline": "#4E2D94"}
PALETTE = [PRIMARY, "#2ca02c"]


def _type_entity_chart(stats):
    frame = ctype_entity_frame(stats)
    fig = go.Figure()
    for ctype in frame.columns:
        fig.add_bar(x=frame.index, y=frame[ctype], name=ctype,
                    marker_color=CTYPE_COLORS.get(ctype, PRIMARY))
    fig.update_layout(barmode="group", title="Comment type × code entity level",
                      xaxis_title="Code entity level", yaxis_title="SCCUs")
    return plotly_layout(fig)


def _quantum_residence_heatmap(stats):
    shares = quantum_residence_frame(stats)
    fig = go.Figure(go.Heatmap(
        z=shares.values,
        x=[c.capitalize() for c in shares.columns],
        y=[e.capitalize() for e in shares.index],
        zmin=0, zmax=max(0.01, float(shares.max().max()) or 0.01),
        colorscale=[[0, "#F4F0FC"], [1, PRIMARY]],
        text=[[f"{v:.1%}" if v == v else "—" for v in row] for row in shares.values],
        texttemplate="%{text}",
        colorbar=dict(title="Share of<br>quantum SCCUs"),
    ))
    fig.update_layout(title="Quantum residence: share of quantum SCCUs by "
                            "entity level × comment form",
                      xaxis_title="Comment form", yaxis_title="Code entity level")
    return plotly_layout(fig, height=340)


def _radar_figure(pairs, title):
    """pairs: [(label, stats)]. One overlaid Scatterpolar trace per pair."""
    labels = radar_labels()
    fig = go.Figure()
    for i, (label, stats) in enumerate(pairs):
        shares = radar_shares(stats)
        color = PALETTE[i % len(PALETTE)]
        fig.add_trace(go.Scatterpolar(
            r=shares + shares[:1],
            theta=labels + labels[:1],
            name=label,
            fill="toself",
            fillcolor=color + "2E",
            line=dict(color=color, width=2.5),
        ))
    fig.update_layout(
        title=title,
        legend=dict(orientation="h", y=-0.12),
        margin=dict(l=60, r=60, t=48, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#4A4370", size=12),
        title_font=dict(color="#2E2060", size=15),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, tickformat=".0%",
                            gridcolor="#E8E4F5", range=[0, None]),
            angularaxis=dict(gridcolor="#E8E4F5"),
        ),
    )
    return fig


def _interpretation_hint(stats):
    shares = radar_shares(stats)
    if not stats.get("quantum_sccus"):
        return "No quantum SCCUs in this corpus — nothing to profile yet."
    top = max(range(len(shares)), key=lambda i: shares[i])
    return (f"This SDK's quantum comments concentrate on the "
            f"**{radar_labels()[top].lower()}** "
            f"({shares[top]:.1%} of quantum SCCUs).")


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
    st.plotly_chart(_type_entity_chart(stats), width="stretch")
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
        st.plotly_chart(_quantum_residence_heatmap(stats), width="stretch")


def render_section3(stats):
    st.subheader("§3 · Knowledge Profile")
    st.caption("Profile — what kind of quantum knowledge (companion paper RQ6).")
    fig = _radar_figure([(stats["sdk"], stats)],
                        "Six-category quantum-knowledge profile")
    st.plotly_chart(fig, width="stretch")
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
    st.plotly_chart(fig, width="stretch")

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
