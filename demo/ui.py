"""Shared visual chrome for the CC4Q Workbench demo.

Quantum-purple theme (#6C3FC5) over dark space-blue accents. All helpers are
plain functions returning HTML/markdown so pages stay declarative.
"""

import html

import streamlit as st

PRIMARY = "#6C3FC5"
PRIMARY_DARK = "#4E2D94"
SPACE = "#0B1026"
SPACE_2 = "#161D3F"
INK = "#1B1B2B"

INTENT_COLORS = {
    "What": "#3E63DD",
    "How-to-use": "#0E9F6E",
    "How-it-is-done": "#D97706",
    "Property": "#0EA5E9",
    "Why": "#DB2777",
    "Others": "#6B7280",
}
CATEGORY_COLORS = {
    "Mathematics for quantum information": "#7C3AED",
    "Quantum algorithms": "#2563EB",
    "Quantum circuit model": "#0891B2",
    "Quantum hardware": "#B45309",
    "Quantum software framework": "#6C3FC5",
    "Others": "#6B7280",
}


def apply_theme():
    st.markdown(
        """
        <style>
        :root {
            --cc4q-primary: #6C3FC5;
            --cc4q-primary-dark: #4E2D94;
            --cc4q-space: #0B1026;
            --cc4q-space-2: #161D3F;
        }
        .stApp { background: #F7F6FC; }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0B1026 0%, #1A1340 100%);
        }
        section[data-testid="stSidebar"] * { color: #E6E1F7; }
        section[data-testid="stSidebar"] .stMarkdown a { color: #C4B0F5; }
        h1, h2, h3 { color: #22174A; letter-spacing: -0.01em; }
        div[data-testid="stMetric"] {
            background: white; border: 1px solid #E4DEF6; border-radius: 14px;
            padding: 14px 16px;
            box-shadow: 0 1px 3px rgba(76, 42, 133, 0.07);
        }
        div[data-testid="stMetric"] label { color: #6A6390 !important; }
        .cc4q-hero {
            background: linear-gradient(135deg, #0B1026 0%, #2A1B5E 55%, #6C3FC5 100%);
            border-radius: 20px; padding: 44px 48px; color: white;
            margin-bottom: 28px;
        }
        .cc4q-hero h1 { color: white; font-size: 2.4rem; margin: 0 0 8px 0; }
        .cc4q-hero p { color: #D9D2F2; font-size: 1.12rem; margin: 0; }
        .cc4q-card {
            background: white; border: 1px solid #E4DEF6; border-radius: 16px;
            padding: 20px 22px; height: 100%;
            box-shadow: 0 1px 3px rgba(76, 42, 133, 0.07);
        }
        .cc4q-card h3 { margin-top: 0; color: #2E2060; }
        .cc4q-metric-card {
            background: white; border: 1px solid #E4DEF6; border-radius: 16px;
            padding: 22px 24px; text-align: center; height: 100%;
            box-shadow: 0 1px 3px rgba(76, 42, 133, 0.07);
        }
        .cc4q-metric-card .value {
            font-size: 2.1rem; font-weight: 700; color: #6C3FC5; line-height: 1.1;
        }
        .cc4q-metric-card .label { color: #6A6390; font-size: 0.95rem; margin-top: 6px; }
        .cc4q-unit-card {
            background: white; border: 1px solid #E7E2F7; border-left: 4px solid #6C3FC5;
            border-radius: 12px; padding: 12px 16px; margin-bottom: 10px;
        }
        .cc4q-unit-card .text { color: #26203F; font-size: 0.98rem; margin-bottom: 8px;
            white-space: pre-wrap; word-break: break-word; }
        .cc4q-chip {
            display: inline-block; border-radius: 999px; padding: 2px 11px;
            font-size: 0.78rem; font-weight: 600; margin-right: 6px; line-height: 1.6;
        }
        .cc4q-chip.solid { color: white; }
        .cc4q-chip.outline { background: white; border: 1.5px solid; }
        .cc4q-chip.dim { background: #F1F0F7; color: #6A6390; border: 1px solid #DDD8EE; }
        .cc4q-footer {
            margin-top: 48px; padding-top: 18px; border-top: 1px solid #E0DBF2;
            color: #857FAC; font-size: 0.9rem; text-align: center;
        }
        .cc4q-entity { color: #9A93BE; font-size: 0.8rem; font-weight: 500;
            text-transform: uppercase; letter-spacing: 0.04em; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(value, label):
    st.markdown(
        f'<div class="cc4q-metric-card"><div class="value">{value}</div>'
        f'<div class="label">{html.escape(label)}</div></div>',
        unsafe_allow_html=True,
    )


def _chip(text, color=None, solid=False, dim=False):
    if dim:
        return f'<span class="cc4q-chip dim">{html.escape(text)}</span>'
    style = f'background:{color};border-color:{color};' if solid else f'color:{color};border-color:{color};'
    cls = "cc4q-chip solid" if solid else "cc4q-chip outline"
    return f'<span class="{cls}" style="{style}">{html.escape(text)}</span>'


def unit_card(text, comment_type, entity_type, quantum, intent, category):
    """Render one labeled comment unit as a card with badge chips."""
    if quantum:
        chips = _chip("✓ quantum", color=PRIMARY, solid=True)
    else:
        chips = _chip("✗ non-quantum", dim=True)
    chips += _chip(f"intent · {intent}", color=INTENT_COLORS.get(intent, "#6B7280"))
    if quantum and category:
        chips += _chip(category, color=CATEGORY_COLORS.get(category, PRIMARY))
    meta = f'<span class="cc4q-entity">{html.escape(comment_type)} · {html.escape(entity_type)}</span>'
    st.markdown(
        f'<div class="cc4q-unit-card"><div class="text">{html.escape(text)}</div>'
        f'<div>{chips}&nbsp;&nbsp;{meta}</div></div>',
        unsafe_allow_html=True,
    )


def footer():
    st.markdown(
        '<div class="cc4q-footer">CC4Q Workbench · '
        '<a href="https://www.buaa.edu.cn">Beihang University</a> · '
        '<a href="https://github.com/MaxwelsDonc/cc4q-workbench">GitHub</a></div>',
        unsafe_allow_html=True,
    )


def plotly_layout(fig, height=360):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#4A4370", size=12),
        title_font=dict(color="#2E2060", size=15),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        yaxis=dict(gridcolor="#E8E4F5", zerolinecolor="#E8E4F5"),
        xaxis=dict(gridcolor="#E8E4F5", zerolinecolor="#E8E4F5"),
        hovermode="x unified",
    )
    return fig
