"""Plotly chart builders for CC4Q dashboards — pure functions, no streamlit.

Each builder takes plain stats dicts (the manifest-entry shape:
files/ccps/sccus/quantum_sccus/quantum_proportion/ctype_by_entity/
quantum_ctype_by_entity/intent_counts/category_counts) and returns a
plotly Figure.
"""

import plotly.graph_objects as go

PRIMARY = "#6C3FC5"  # quantum accent
CTYPE_COLORS = {"docstring": "#1F2937", "block": "#6B7280", "inline": "#9CA3AF"}
PALETTE = [PRIMARY, "#2ca02c"]
RADAR_LABELS = ["Mathematics", "Algorithms", "Circuit model", "Hardware",
                "Software stack", "Others"]
CATEGORY_ORDER = [
    "Mathematics for quantum information", "Quantum algorithms",
    "Quantum circuit model", "Quantum hardware",
    "Quantum software framework", "Others",
]
ENTITY_ORDER = ["module", "class", "function"]
CTYPE_ORDER = ["docstring", "block", "inline"]


def type_entity_figure(stats, height=360):
    """Grouped bars: comment form × code entity level (SCCU counts)."""
    import pandas as pd
    frame = pd.DataFrame(
        {ctype: pd.Series(entities)
         for ctype, entities in stats["ctype_by_entity"].items()}
    ).fillna(0).astype(int)
    frame = frame.reindex(index=ENTITY_ORDER)
    frame = frame.reindex(columns=CTYPE_ORDER).dropna(axis=1, how="all").fillna(0).astype(int)
    fig = go.Figure()
    for ctype in frame.columns:
        fig.add_bar(x=frame.index, y=frame[ctype], name=ctype,
                    marker_color=CTYPE_COLORS.get(ctype, PRIMARY))
    fig.update_layout(barmode="group", title="Comment type × code entity level",
                      xaxis_title="Code entity level", yaxis_title="SCCUs",
                      height=height)
    return fig


def quantum_residence_heatmap(stats, height=340):
    """Heatmap: share of quantum SCCUs per entity level × comment form."""
    import pandas as pd
    table = stats.get("quantum_ctype_by_entity", {})
    counts = pd.DataFrame(
        {ctype: pd.Series(entities) for ctype, entities in table.items()}
    ).reindex(index=ENTITY_ORDER, columns=CTYPE_ORDER)
    total = counts.sum().sum()
    shares = counts / total if total else counts * float("nan")
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
                      xaxis_title="Comment form", yaxis_title="Code entity level",
                      height=height)
    return fig


def radar_shares(stats):
    """Six category shares of quantum SCCUs, in radar order."""
    n_quantum = stats.get("quantum_sccus", 0)
    counts = stats.get("category_counts", {})
    if not n_quantum:
        return [0.0] * len(CATEGORY_ORDER)
    return [counts.get(k, 0) / n_quantum for k in CATEGORY_ORDER]


def radar_figure(pairs, title, height=None):
    """Scatterpolar over the six quantum categories.

    ``pairs`` is [(label, stats), ...]; one overlaid trace per pair.
    """
    fig = go.Figure()
    for i, (label, stats) in enumerate(pairs):
        shares = radar_shares(stats)
        color = PALETTE[i % len(PALETTE)]
        fig.add_trace(go.Scatterpolar(
            r=shares + shares[:1],
            theta=RADAR_LABELS + RADAR_LABELS[:1],
            name=label,
            fill="toself",
            fillcolor=color + "2E",
            line=dict(color=color, width=2.5),
        ))
    layout = dict(
        title=title,
        legend=dict(orientation="h", y=-0.12),
        margin=dict(l=60, r=60, t=48, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#6B7280", size=12),
        title_font=dict(color="#1A1A1A", size=15),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, tickformat=".0%",
                            gridcolor="#ECECEF", range=[0, None]),
            angularaxis=dict(gridcolor="#ECECEF"),
        ),
    )
    if height:
        layout["height"] = height
    fig.update_layout(**layout)
    return fig


def interpretation_hint(stats):
    """One-line reading of the dominant quantum category."""
    shares = radar_shares(stats)
    if not stats.get("quantum_sccus"):
        return "No quantum SCCUs in this corpus — nothing to profile yet."
    top = max(range(len(shares)), key=lambda i: shares[i])
    return (f"This SDK's quantum comments concentrate on the "
            f"**{RADAR_LABELS[top].lower()}** "
            f"({shares[top]:.1%} of quantum SCCUs).")
