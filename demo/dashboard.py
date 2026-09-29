"""Dashboard rendering for repository analysis results (precomputed or live)."""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_io import (
    CATEGORY_ORDER, INTENT_ORDER, ctype_entity_frame, distribution_frame,
    units_to_jsonl_bytes,
)
from ui import PRIMARY, CATEGORY_COLORS, INTENT_COLORS, metric_card, plotly_layout

CTYPE_COLORS = {"docstring": PRIMARY, "block": "#9F7AEA", "inline": "#4E2D94"}
PALETTE = [PRIMARY, "#B794F6", "#4E2D94", "#9F7AEA"]


def render_metrics(stats):
    cols = st.columns(4)
    with cols[0]:
        metric_card(f"{stats['files']:,}", "Python files")
    with cols[1]:
        metric_card(f"{stats['ccps']:,}", "CCPs")
    with cols[2]:
        metric_card(f"{stats['sccus']:,}", "SCCUs")
    with cols[3]:
        metric_card(f"{stats['quantum_proportion']:.1%}", "Quantum-related")
    if stats.get("sampled"):
        st.caption(
            f"Stats computed over the full corpus; charts and download show a "
            f"{stats.get('sample_size', 2000):,}-row random sample (seed "
            f"{stats.get('sample_seed', 42)})."
        )


def render_charts(stats):
    left, right = st.columns(2)
    with left:
        ctype_entity = ctype_entity_frame(stats)
        if ctype_entity.empty:
            st.info("No comment-type distribution available.")
        else:
            fig = go.Figure()
            for ctype in ctype_entity.columns:
                fig.add_bar(x=ctype_entity.index, y=ctype_entity[ctype],
                            name=ctype,
                            marker_color=CTYPE_COLORS.get(ctype, PRIMARY))
            fig.update_layout(barmode="group",
                              title="Comment type × code entity level",
                              xaxis_title="Code entity level", yaxis_title="SCCUs")
            st.plotly_chart(plotly_layout(fig), width="stretch")

        intent = {k: stats["intent_counts"].get(k, 0) for k in INTENT_ORDER}
        fig = px.bar(x=list(intent), y=list(intent.values()),
                     color=list(intent), color_discrete_map=INTENT_COLORS,
                     title="Developer intent distribution (all SCCUs)")
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="SCCUs")
        st.plotly_chart(plotly_layout(fig), width="stretch")
    with right:
        cat = {k: stats["category_counts"].get(k, 0) for k in CATEGORY_ORDER}
        fig = px.bar(x=list(cat), y=list(cat.values()),
                     color=list(cat), color_discrete_map=CATEGORY_COLORS,
                     title="Quantum-category distribution (quantum SCCUs only)")
        fig.update_layout(showlegend=False, xaxis_title="", yaxis_title="SCCUs")
        st.plotly_chart(plotly_layout(fig), width="stretch")


def render_download(stats, df):
    st.download_button(
        "Download labeled corpus (JSONL)",
        data=units_to_jsonl_bytes(df),
        file_name=f"{stats['sdk']}_sccus_labeled.jsonl",
        mime="application/x-jsonlines",
    )


def render_dashboard(stats, df):
    render_metrics(stats)
    render_charts(stats)
    render_download(stats, df)


def render_compare(stats_a, stats_b):
    """Side-by-side comparison of two SDKs (infrastructure vs application)."""
    col_a, col_b = st.columns(2)
    for col, stats in ((col_a, stats_a), (col_b, stats_b)):
        with col:
            st.markdown(f"**{stats['sdk']}** ({stats['version']})")
            c = st.columns(2)
            with c[0]:
                metric_card(f"{stats['sccus']:,}", "SCCUs")
            with c[1]:
                metric_card(f"{stats['quantum_proportion']:.1%}", "Quantum %")

    pair = [stats_a, stats_b]
    intent_frame = distribution_frame(pair, "intent_counts", INTENT_ORDER)
    fig = go.Figure()
    for i, col in enumerate(intent_frame.columns):
        fig.add_bar(x=intent_frame.index, y=intent_frame[col], name=col,
                    marker_color=PALETTE[i % len(PALETTE)])
    fig.update_layout(barmode="group", title="Developer intent: side by side",
                      xaxis_title="", yaxis_title="SCCUs")
    st.plotly_chart(plotly_layout(fig), width="stretch")

    cat_frame = distribution_frame(pair, "category_counts", CATEGORY_ORDER)
    fig = go.Figure()
    for i, col in enumerate(cat_frame.columns):
        fig.add_bar(x=cat_frame.index, y=cat_frame[col], name=col,
                    marker_color=PALETTE[i % len(PALETTE)])
    fig.update_layout(barmode="group", title="Quantum category: side by side",
                      xaxis_title="", yaxis_title="SCCUs")
    st.plotly_chart(plotly_layout(fig), width="stretch")
