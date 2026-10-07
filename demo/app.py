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
    initial_sidebar_state="expanded",
)

apply_theme()

pages = st.navigation([
    st.Page("pages/p_home.py", title="Home", icon="🏠", url_path="home",
            default=True),
    st.Page("pages/p_analyze_code.py", title="Analyze Code", icon="🧪",
            url_path="analyze-code"),
    st.Page("pages/p_analyze_repo.py", title="Analyze Repository", icon="🗂️",
            url_path="analyze-repository"),
    st.Page("pages/p_explore.py", title="Explore Corpus", icon="🔎",
            url_path="explore-corpus"),
])

with st.sidebar:
    st.markdown("### ⚛ CC4Q Workbench")
    st.caption("From quantum code to labeled comment corpora: "
               "build, inspect, profile.\n\n"
               "CPU inference · three fine-tuned BERT classifiers · "
               "no data leaves your machine.")

pages.run()
