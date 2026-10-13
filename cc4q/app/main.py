"""CC4Q Workbench — Streamlit entry point (workspace IA, 6 flat pages).

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


def _default_model_indicator():
    """Compact header indicator of the current default model, linking to
    the Models page."""
    from cc4q.app import registry
    entries = registry.list_models()
    default = next((e for e in entries if e["is_default"]), None)
    label = default["name"] if default else "Released checkpoints"
    return label


def main():
    st.set_page_config(
        page_title="CC4Q Workbench",
        page_icon="⚛",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    apply_theme()

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
        st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="cc4q-brand" style="justify-content:flex-end">'
            f'<span class="cc4q-topnav-note">model: '
            f'{_default_model_indicator()}</span></div>',
            unsafe_allow_html=True)

    pages = st.navigation([
        page("Workspace", "p_workspace.py", "🏠", "workspace", default=True),
        page("Corpora", "p_corpora.py", "🗂️", "corpora"),
        page("Annotate", "p_annotate.py", "🏷️", "annotate"),
        page("Models", "p_models.py", "📦", "models"),
        page("Evaluate", "p_evaluate.py", "📏", "evaluate"),
        page("Playground", "p_playground.py", "🧪", "playground"),
    ], position="top")

    pages.run()


if __name__ == "__main__":
    main()
