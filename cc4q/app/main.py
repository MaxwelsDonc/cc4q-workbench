"""CC4Q Workbench — Streamlit entry point.

Run via ``cc4q demo`` / ``cc4q serve``, or from a source checkout with
``streamlit run demo/app.py`` (a thin launcher over this module).
"""

import os

import streamlit as st

from cc4q.app import MAIN_PATH, PAGES_DIR
from cc4q.app.ui import apply_theme


def main():
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
            '<div class="cc4q-brand"><span class="name">⚛ CC4Q '
            'Workbench</span></div>',
            unsafe_allow_html=True,
        )
    with b2:
        st.markdown(
            '<div class="cc4q-brand" style="justify-content:flex-end">'
            '<span class="cc4q-topnav-note">Local inference · no data '
            'leaves your machine</span></div>',
            unsafe_allow_html=True,
        )

    def page(name, fname, icon, url_path, default=False):
        return st.Page(os.path.join(PAGES_DIR, fname), title=name, icon=icon,
                       url_path=url_path, default=default)

    pages = st.navigation([
        page("Home", "p_home.py", "🏠", "home", default=True),
        page("Analyze Code", "p_analyze_code.py", "🧪", "analyze-code"),
        page("Analyze Repository", "p_analyze_repo.py", "🗂️",
             "analyze-repository"),
        page("Annotate", "p_annotate.py", "🏷️", "annotate"),
        page("Train & Evaluate", "p_train.py", "🎓", "train"),
        page("Your Models", "p_models.py", "📦", "models"),
        page("Explore Corpus", "p_explore.py", "🔎", "explore-corpus"),
    ], position="top")

    pages.run()


if __name__ == "__main__":
    main()
