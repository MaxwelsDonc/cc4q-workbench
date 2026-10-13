"""Shared visual chrome for the CC4Q Workbench demo.

Kimi-style minimal product language (design doc §6): white / very light
neutral surfaces, near-black text, black primary buttons, hairline #E5E7EB
borders, and the quantum purple #6C3FC5 reserved for quantum badges/chips
and small highlights. All helpers are plain functions returning
HTML/markdown so pages stay declarative.

Theme delivery is dual on purpose: `.streamlit/config.toml` covers launches
from the repo root, and the CSS overrides below cover launches from any
other working directory (Streamlit only discovers project config relative
to the CWD it is invoked from).
"""

import html

import streamlit as st

PRIMARY = "#6C3FC5"        # quantum accent — sparing use only
PRIMARY_DARK = "#4E2D94"
INK = "#1A1A1A"            # near-black primary text / black buttons
MUTED = "#6B7280"          # secondary text
BORDER = "#E5E7EB"         # hairline card/widget borders
BG = "#FBFBFC"             # app background (very light neutral)
NON_QUANTUM_GRAY = "#9E9E9E"

# Fixed colorblind-aware category palette (design doc §6). Developer-intent
# colors are not needed: intent stays in the data layer, out of the UI.
CATEGORY_COLORS = {
    "Mathematics for quantum information": "#1f77b4",
    "Quantum algorithms": "#d62728",
    "Quantum circuit model": "#6C3FC5",
    "Quantum hardware": "#2ca02c",
    "Quantum software framework": "#ff7f0e",
    "Others": "#7f7f7f",
}


def apply_theme():
    """Apply the Kimi-style theme (light mode only)."""
    st.markdown(
        """
        <style>
        /* ---- Kimi-style chrome: black accents, hairline borders ---- */
        :root {
            --primary-color: #1A1A1A;
            --primary-color-light: #374151;
            --primary-color-dark: #000000;
            --cc4q-quantum: #6C3FC5;
            --cc4q-ink: #1A1A1A;
            --cc4q-muted: #6B7280;
            --cc4q-border: #E5E7EB;
            --cc4q-bg: #FBFBFC;
        }
        .stApp { background: #FBFBFC; color: #1A1A1A; }
        .stApp a { color: #1A1A1A; text-decoration: underline;
                   text-underline-offset: 2px; }
        .stApp a:hover { color: #000000; }
        h1, h2, h3 { color: #1A1A1A; letter-spacing: -0.01em; font-weight: 700; }
        h3 { font-weight: 650; }
        /* Primary buttons: Kimi signature black */
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="baseButton-primary"] {
            background-color: #1A1A1A; border-color: #1A1A1A; color: #FFFFFF;
            border-radius: 10px; box-shadow: none;
        }
        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="baseButton-primary"]:hover {
            background-color: #000000; border-color: #000000; color: #FFFFFF;
        }
        /* Secondary / outline buttons: white, dark text, hairline border */
        .stButton > button[kind="secondary"],
        .stButton > button[data-testid="baseButton-secondary"],
        .stLinkButton > a {
            background-color: #FFFFFF; color: #1A1A1A;
            border: 1px solid #E5E7EB; border-radius: 10px; box-shadow: none;
        }
        .stButton > button[kind="secondary"]:hover,
        .stButton > button[data-testid="baseButton-secondary"]:hover,
        .stLinkButton > a:hover {
            background-color: #FFFFFF; color: #1A1A1A;
            border-color: #9CA3AF;
        }
        /* Tabs, checkboxes, toggle, tags: neutral chrome */
        .stTabs [data-baseweb="tab-list"] [aria-selected="true"] { color: #1A1A1A; }
        .stTabs [data-baseweb="tab-highlight"] { background-color: #1A1A1A; }
        .stCheckbox [data-checked="true"] div[role="checkbox"] {
            background-color: #1A1A1A; border-color: #1A1A1A;
        }
        .stToggle [role="switch"][aria-checked="true"] { background-color: #1A1A1A; }
        .stMultiSelect [data-baseweb="tag"] {
            background-color: #F3F4F6; color: #1A1A1A;
        }
        :focus-visible { outline-color: #1A1A1A; }
        /* Native streamlit metric widgets */
        div[data-testid="stMetric"] {
            background: white; border: 1px solid #E5E7EB; border-radius: 12px;
            padding: 14px 16px;
        }
        div[data-testid="stMetric"] label { color: #6B7280 !important; }
        </style>
        <style>
        /* ---- CC4Q components ---- */
        .cc4q-brand {
            display: flex; align-items: baseline; gap: 12px;
            padding: 18px 0 6px 0;
        }
        .cc4q-brand .name { font-size: 1.25rem; font-weight: 800; color: #111111; }
        .cc4q-brand .tag { color: #6B7280; font-size: 0.95rem; }
        .cc4q-topnav-note { color: #9CA3AF; font-size: 0.85rem; }
        .cc4q-hero {
            padding: 44px 4px 28px 4px; color: #1A1A1A;
            border-bottom: 1px solid #E5E7EB; margin-bottom: 28px;
        }
        .cc4q-hero h1 { color: #111111; font-size: 2.7rem; margin: 0 0 6px 0;
            font-weight: 800; letter-spacing: -0.02em; }
        .cc4q-hero .accent-line { width: 56px; height: 4px; background: #6C3FC5;
            border-radius: 2px; margin: 18px 0; }
        .cc4q-hero p { color: #6B7280; font-size: 1.12rem; margin: 0; }
        .cc4q-card {
            background: white; border: 1px solid #E5E7EB; border-radius: 12px;
            padding: 22px 24px; height: 100%; min-height: 220px;
            box-shadow: none;
        }
        .cc4q-card h3 { margin-top: 0; color: #1A1A1A; font-weight: 700; }
        .cc4q-card p { color: #6B7280; font-size: 0.96rem; }
        .cc4q-metric-card {
            background: white; border: 1px solid #E5E7EB; border-radius: 12px;
            padding: 22px 24px; text-align: center; height: 100%;
            box-shadow: none;
        }
        .cc4q-metric-card .value {
            font-size: 2.1rem; font-weight: 700; color: #111111; line-height: 1.1;
        }
        .cc4q-metric-card .label { color: #6B7280; font-size: 0.95rem; margin-top: 6px; }
        .cc4q-unit-card {
            background: white; border: 1px solid #E5E7EB;
            border-left: 4px solid #6C3FC5;
            border-radius: 12px; padding: 12px 16px; margin-bottom: 10px;
        }
        .cc4q-unit-card.nonquantum { border-left-color: #D1D5DB; }
        .cc4q-unit-card .text { color: #1A1A1A; font-size: 0.98rem; margin-bottom: 8px;
            white-space: pre-wrap; word-break: break-word; }
        .cc4q-chip {
            display: inline-block; border-radius: 999px; padding: 2px 11px;
            font-size: 0.78rem; font-weight: 600; margin-right: 6px; line-height: 1.6;
        }
        .cc4q-chip.solid { color: white; }
        .cc4q-chip.outline { background: white; border: 1.5px solid; }
        .cc4q-chip.big {
            font-size: 0.92rem; padding: 4px 16px; font-weight: 700;
        }
        .cc4q-chip.nonquantum {
            background: white; color: #757575; border: 1.5px dashed #9E9E9E;
        }
        .cc4q-summary {
            background: #F6F3FC;
            border: 1px solid #E5DDF7; border-radius: 12px;
            padding: 12px 18px; margin-bottom: 14px;
            color: #374151; font-size: 1.02rem; font-weight: 600;
        }
        .cc4q-summary b { color: #6C3FC5; font-size: 1.15rem; }
        .cc4q-footer {
            margin-top: 48px; padding-top: 18px; border-top: 1px solid #E5E7EB;
            color: #9CA3AF; font-size: 0.9rem; text-align: center;
        }
        .cc4q-entity { color: #9CA3AF; font-size: 0.8rem; font-weight: 500;
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


def unit_card(text, comment_type, entity_type, quantum, category):
    """Render one labeled comment unit as a card: big quantum badge,
    quantum-category chip (quantum units only), entity/type caption.
    Developer intent stays in the data layer, not in the UI."""
    if quantum:
        chips = (f'<span class="cc4q-chip solid big" '
                 f'style="background:{PRIMARY};border-color:{PRIMARY};">'
                 f'✓ quantum</span>')
        card_cls = "cc4q-unit-card"
    else:
        chips = ('<span class="cc4q-chip big nonquantum">'
                 '✗ non-quantum</span>')
        card_cls = "cc4q-unit-card nonquantum"
    if quantum and category:
        color = CATEGORY_COLORS.get(category, PRIMARY)
        chips += _chip(category, color=color)
    meta = f'<span class="cc4q-entity">{html.escape(comment_type)} · {html.escape(entity_type)}</span>'
    st.markdown(
        f'<div class="{card_cls}"><div class="text">{html.escape(text)}</div>'
        f'<div>{chips}&nbsp;&nbsp;{meta}</div></div>',
        unsafe_allow_html=True,
    )


def summary_strip(n_units, n_quantum):
    """'N units · M quantum-related (P%)' strip (no intent)."""
    pct = f"{100 * n_quantum / n_units:.1f}%" if n_units else "0.0%"
    st.markdown(
        f'<div class="cc4q-summary"><b>{n_units}</b> units · '
        f'<b>{n_quantum}</b> quantum-related ({pct})</div>',
        unsafe_allow_html=True,
    )


def footer():
    st.markdown(
        '<div class="cc4q-footer">CC4Q Workbench · '
        '<a href="https://www.buaa.edu.cn">Beihang University</a> · '
        'Released under the MIT License · '
        '<a href="https://github.com/MaxwelsDonc/cc4q-workbench">GitHub</a> · '
        '<a href="https://github.com/MaxwelsDonc/cc4q-workbench/releases">Releases</a>'
        '</div>',
        unsafe_allow_html=True,
    )


def plotly_layout(fig, height=360):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#6B7280", size=12),
        title_font=dict(color="#1A1A1A", size=15),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        yaxis=dict(gridcolor="#ECECEF", zerolinecolor="#ECECEF"),
        xaxis=dict(gridcolor="#ECECEF", zerolinecolor="#ECECEF"),
        hovermode="x unified",
    )
    return fig
