"""Streamlit annotation tool for the CC4Q quantum-axis spot-check.

Launch from the workbench root:
    .venv/bin/streamlit run exp/annotate_spotcheck.py

Reads exp/spotcheck_annotation.csv, shows one SCCU at a time, and saves each
label to the CSV immediately (safe to close and resume at any time). Run
exp/score_spotcheck.py afterwards for agreement / precision / recall / CI.
"""

import os

import pandas as pd
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(ROOT, "exp", "spotcheck_annotation.csv")

st.set_page_config(page_title="CC4Q Spot-check Annotation", layout="centered")


@st.cache_data
def load_data():
    return pd.read_csv(CSV_PATH, dtype={"human_label": str}).fillna({"human_label": ""})


def save(df):
    df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")


df = load_data()
labeled = df["human_label"].isin(["quantum", "non-quantum"]).sum()
total = len(df)

st.title("CC4Q quantum-axis spot-check")
st.caption(f"{labeled} / {total} labeled")

st.progress(labeled / total)

if "idx" not in st.session_state:
    unlabeled = df.index[~df["human_label"].isin(["quantum", "non-quantum"])]
    st.session_state.idx = int(unlabeled[0]) if len(unlabeled) else 0

idx = st.session_state.idx
row = df.iloc[idx]

left, right = st.columns([1, 4])
with left:
    if st.button("◀ Previous", disabled=idx == 0):
        st.session_state.idx = idx - 1
        st.rerun()
with right:
    st.markdown(f"**#{row['no']}** · `{row['repo']}` · *{row['entity']}*")

st.markdown("---")
st.markdown(row["comment_text"])
st.markdown("---")

current = row["human_label"]
if current in ("quantum", "non-quantum"):
    st.info(f"Current label: **{current}** (click a button to change)")


def label(value):
    df.at[st.session_state.idx, "human_label"] = value
    save(df)
    st.cache_data.clear()
    nxt = st.session_state.idx + 1
    if nxt < total:
        st.session_state.idx = nxt


c1, c2, c3 = st.columns(3)
with c1:
    st.button("✅ quantum", type="primary", use_container_width=True,
              on_click=label, args=("quantum",))
with c2:
    st.button("⬜ non-quantum", use_container_width=True,
              on_click=label, args=("non-quantum",))
with c3:
    st.button("⏭ skip", use_container_width=True,
              on_click=lambda: st.session_state.update(idx=min(idx + 1, total - 1)))

if labeled == total:
    st.success("All done! Run `python exp/score_spotcheck.py` for the agreement report.")
