"""Page — Workspace: asset overview, recent activity, quick-create."""

import os

import streamlit as st

import cc4q.workspace as ws
from cc4q.app import PAGES_DIR
from cc4q.app.ui import footer, metric_card, page_header, status_badge

TYPE_META = {
    "corpus": ("Corpora", "p_corpora.py", "corpora"),
    "annotation_session": ("Annotations", "p_annotate.py", "annotations"),
    "evaluation": ("Evaluations", "p_evaluate.py", "evaluations"),
    "model": ("Models", "p_models.py", "models"),
}


def _type_card(type_, count, updated):
    label, page_file, _ = TYPE_META[type_]
    col = st.container()
    with col:
        st.markdown(
            f'<div class="cc4q-asset-card"><h3>{label}</h3>'
            f'<div class="meta-line"><b>{count}</b> asset'
            f'{"s" if count != 1 else ""}</div>'
            f'<div class="meta-line">{updated or "—"}</div></div>',
            unsafe_allow_html=True)
        st.page_link(os.path.join(PAGES_DIR, page_file),
                     label=f"Open {label} →", use_container_width=True)


def render():
    page_header("Workspace",
                "Everything you make is an asset — corpora, annotations, "
                "models, evaluations — persisted and resumable.")

    # quick-create
    q1, q2, q3, q4 = st.columns(4)
    quick = (("New corpus", "p_corpora.py"),
             ("New annotation", "p_annotate.py"),
             ("Train model", "p_models.py"),
             ("New evaluation", "p_evaluate.py"))
    for col, (label, page_file) in zip((q1, q2, q3, q4), quick):
        with col:
            st.page_link(os.path.join(PAGES_DIR, page_file),
                         label=f"＋ {label}", use_container_width=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    counts = {t: len(ws.list_assets(t)) for t in ws.ASSET_TYPES}
    counts["model"] = len(ws.list_models())
    cols = st.columns(4)
    for col, type_ in zip(cols, ("corpus", "annotation_session", "model",
                                 "evaluation")):
        with col:
            assets = ws.list_assets(type_) if type_ in ws.ASSET_TYPES \
                else ws.list_models()
            updated = assets[0].get("updated_at", "") if assets else ""
            _type_card(type_, counts[type_], updated)

    st.divider()
    st.subheader("Recent activity")
    # insertion order == true recency; index files are append-only
    recent = list(reversed(ws._load()["assets"]))  # newest last in index
    for m in ws.list_models():
        recent.append({"type": "model", "name": m["name"],
                       "updated_at": m.get("created", "")})
    if not recent:
        st.caption("Nothing yet — create your first corpus to get going.")
    for a in recent[:6]:
        tone = "quantum" if a["type"] == "corpus" else \
               "success" if a["type"] == "model" else "neutral"
        st.markdown(f"{status_badge(a['type'], tone)} **{a['name']}** "
                    f"<span style='color:#9CA3AF'>{a.get('updated_at', '')}"
                    f"</span>", unsafe_allow_html=True)

    st.divider()
    st.subheader("Eight primitives, one workflow")
    import os as _os
    strip = [
        ("🛠️ Build", "p_corpora.py"), ("🔬 Analyze", "p_corpora.py"),
        ("🏷️ Predict", "p_playground.py"), ("🎲 Sample", "p_annotate.py"),
        ("✍️ Annotate", "p_annotate.py"), ("🎓 Train", "p_models.py"),
        ("📏 Evaluate", "p_evaluate.py"), ("📊 Visualize", "p_corpora.py"),
    ]
    for row_start in (0, 4):
        cols = st.columns(4)
        for col, (title, page_file) in zip(cols, strip[row_start:row_start + 4]):
            with col:
                st.markdown(
                    f'<div class="cc4q-asset-card"><h3>{title}</h3></div>',
                    unsafe_allow_html=True)
                st.page_link(_os.path.join(PAGES_DIR, page_file),
                             label="Open →", use_container_width=True)

    st.divider()
    cols = st.columns(3)
    with cols[0]:
        metric_card("6", "Quantum SDKs in the corpus")
    with cols[1]:
        metric_card("39,593", "Labeled SCCUs")
    with cols[2]:
        metric_card("2", "Quantum label axes per unit")

    footer()


render()
