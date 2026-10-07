"""CC4Q Workbench — public demo app.

Run from the workbench root:
    streamlit run demo/app.py
"""

import streamlit as st

from bootstrap import boot

boot()

from ui import apply_theme  # noqa: E402

st.set_page_config(
    page_title="CC4Q Workbench",
    page_icon="⚛",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_theme()

# Brand block, top-left, above the navigation bar.
b1, b2 = st.columns([3, 2])
with b1:
    st.markdown(
        '<div class="cc4q-brand"><span class="name">⚛ CC4Q Workbench</span>'
        '<span class="tag">From quantum code to labeled comment corpora: '
        'build, inspect, profile.</span></div>',
        unsafe_allow_html=True,
    )
with b2:
    st.markdown(
        '<div class="cc4q-brand" style="justify-content:flex-end">'
        '<span class="cc4q-topnav-note">CPU inference · no data leaves '
        'your machine</span></div>',
        unsafe_allow_html=True,
    )

pages = st.navigation([
    st.Page("pages/p_home.py", title="Home", icon="🏠", url_path="home",
            default=True),
    st.Page("pages/p_analyze_code.py", title="Analyze Code", icon="🧪",
            url_path="analyze-code"),
    st.Page("pages/p_analyze_repo.py", title="Analyze Repository", icon="🗂️",
            url_path="analyze-repository"),
    st.Page("pages/p_explore.py", title="Explore Corpus", icon="🔎",
            url_path="explore-corpus"),
], position="top")

pages.run()
