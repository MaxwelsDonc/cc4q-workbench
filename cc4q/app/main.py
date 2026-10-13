"""CC4Q Workbench — Streamlit entry point.

Run via ``cc4q demo`` / ``cc4q serve``, or from a source checkout with
``streamlit run demo/app.py`` (a thin launcher over this module).
"""

import os

import streamlit as st

from cc4q.app import MAIN_PATH, PAGES_DIR  # noqa: F401
from cc4q.app.ui import apply_theme


def page(name, fname, icon, url_path, default=False):
    return st.Page(os.path.join(PAGES_DIR, fname), title=name, icon=icon,
                   url_path=url_path, default=default)


def main():
    st.set_page_config(
        page_title="CC4Q Workbench",
        page_icon="⚛",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    apply_theme()

    # Brand block, top-left; gear button opens the Models settings dialog.
    from cc4q.app.model_select import models_dialog
    b1, b2, b3 = st.columns([2, 2, 1])
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
    with b3:
        st.markdown('<div style="height:14px"></div>',
                    unsafe_allow_html=True)
        if st.button("⚙ Models", key="models_settings", type="secondary",
                     use_container_width=False):
            models_dialog()

    pages = st.navigation({
        "Explore": [
            page("Home", "p_home.py", "🏠", "home", default=True),
            page("SDK Dashboards", "p_analyze_repo.py", "🗂️", "dashboards"),
            page("Playground", "p_analyze_code.py", "🧪", "playground"),
            page("Corpus", "p_explore.py", "🔎", "corpus"),
        ],
        "Build": [
            page("1. Get Data", "p_get_data.py", "⬇️", "build-data"),
            page("2. Label", "p_label.py", "🏷️", "label"),
            page("3. Train", "p_train.py", "🎓", "train"),
            page("4. Evaluate", "p_evaluate.py", "📏", "evaluate"),
        ],
        "Models": [
            page("Models", "p_models.py", "🧠", "models"),
        ],
    }, position="top")

    pages.run()


if __name__ == "__main__":
    main()
