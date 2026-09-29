"""Page — Home: positioning, product metrics, entry cards."""

import streamlit as st

from bootstrap import boot

boot()

from ui import footer, metric_card  # noqa: E402

GITHUB_URL = "https://github.com/MaxwelsDonc/cc4q-workbench"


def render():
    st.markdown(
        """
        <div class="cc4q-hero">
            <h1>⚛ CC4Q Workbench</h1>
            <p>Paste a quantum SDK, get a labeled comment corpus.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "CC4Q turns raw Python source from quantum SDKs into **SCCUs** — "
        "sentence-level comment code units — each labeled on three axes: "
        "quantum-relatedness, developer intent, and quantum category. "
        "The workbench wraps the full CC4Q pipeline "
        "(comment-pair extraction → semantic segmentation → three-axis BERT "
        "classification) behind a point-and-click interface."
    )

    cols = st.columns(3)
    with cols[0]:
        metric_card("6", "Quantum SDKs in the corpus")
    with cols[1]:
        metric_card("39,593", "Labeled SCCUs")
    with cols[2]:
        metric_card("3", "Label axes per unit")

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.subheader("Start here")

    entries = [
        ("pages/p_analyze_code.py", "🧪 Analyze Code",
         "Paste any Python snippet and watch each comment get labeled "
         "quantum vs non-quantum, with its developer intent and quantum "
         "category — in seconds, on CPU."),
        ("pages/p_analyze_repo.py", "🗂️ Analyze Repository",
         "Pick one of six precomputed Qiskit-ecosystem SDKs for instant "
         "dashboards, or point the workbench at a new GitHub repo and run "
         "the full pipeline live. Compare SDKs side by side."),
        ("pages/p_explore.py", "🔎 Explore Corpus",
         "Browse, filter and download the labeled corpus: full SCCUs from "
         "the three newest SDKs plus seeded samples from the three "
         "original ones."),
    ]
    cols = st.columns(3)
    for col, (target, title, blurb) in zip(cols, entries):
        with col:
            st.markdown(
                f'<div class="cc4q-card"><h3>{title}</h3><p>{blurb}</p></div>',
                unsafe_allow_html=True,
            )
            st.page_link(target, label=f"Open {title[2:].strip()} →",
                         use_container_width=True)

    footer()


render()
