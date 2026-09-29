"""Lazily cached access to the three BERT classifiers (shared by pages)."""

import streamlit as st

import cc4q_analysis as analysis


@st.cache_resource(show_spinner=False)
def get_models():
    return analysis.load_models()
