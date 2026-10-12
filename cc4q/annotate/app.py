"""Streamlit annotation app (launched via cc4q.annotate / `cc4q annotate`).

Configuration comes from the JSON file at CC4Q_ANNOTATE_CONFIG (written by
cc4q.annotate.prepare). Progress persists to
<output_dir>/annotations.jsonl so a closed session resumes.
"""

import json
import os

import pandas as pd
import streamlit as st


def _load_config():
    path = os.environ.get("CC4Q_ANNOTATE_CONFIG")
    if not path:
        raise SystemExit(
            "CC4Q_ANNOTATE_CONFIG is not set - launch via cc4q.annotate() "
            "or `cc4q annotate`.")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


CONFIG = _load_config()
TEXT_COL = CONFIG["schema"]["text_column"]
ID_COL = CONFIG["schema"]["id_column"]
LABELS = CONFIG["schema"]["labels"]
ARGS_MODE = CONFIG.get("mode", "blind")

STATE_PATH = os.path.join(CONFIG["output_dir"], "annotations.jsonl")


def load_items():
    with open(CONFIG["data"], encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_predictions():
    if not CONFIG.get("predictions") or ARGS_MODE != "adjudicate":
        return {}
    preds = {}
    with open(CONFIG["predictions"], encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                preds[str(r[ID_COL])] = str(r.get("model_label",
                                                   r.get("label", "")))
    return preds


def load_state():
    state = {}
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    state[str(r[ID_COL])] = r.get("label") or None
    return state


def save_decision(item_id, label):
    state = load_state()
    state[str(item_id)] = label
    os.makedirs(CONFIG["output_dir"], exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        for k, v in state.items():
            f.write(json.dumps({ID_COL: k, "label": v}, ensure_ascii=False)
                    + "\n")


items = load_items()
preds = load_predictions()
state = load_state()

st.set_page_config(page_title="cc4q annotate", layout="centered")
st.title(CONFIG["schema"].get("title", "cc4q annotation"))
if ARGS_MODE == "adjudicate":
    st.caption("adjudicate mode — model suggestions shown; confirm or "
               "override. Every item still requires a human click.")

labeled = sum(1 for it in items if state.get(str(it[ID_COL])))
st.progress(labeled / len(items),
            text=f"{labeled} / {len(items)} annotated")

if "pos" not in st.session_state:
    # resume: jump to the first unlabeled item
    for i, it in enumerate(items):
        if not state.get(str(it[ID_COL])):
            st.session_state.pos = i
            break
    else:
        st.session_state.pos = 0
pos = min(st.session_state.pos, len(items) - 1)
item = items[pos]
item_id = str(item[ID_COL])
current = state.get(item_id)

st.caption(f"item {pos + 1} of {len(items)} — {ID_COL}={item_id}")
st.markdown(f"**{item.get('entity', item.get('code_entity_type', ''))}**"
            if item.get("entity") or item.get("code_entity_type") else "")
st.text(str(item[TEXT_COL]))

if ARGS_MODE == "adjudicate":
    suggestion = preds.get(item_id)
    if suggestion:
        st.info(f"Model suggests: **{suggestion}**")

nav_l, nav_r = st.columns(2)
with nav_l:
    if st.button("← Previous", disabled=pos == 0, use_container_width=True):
        st.session_state.pos = pos - 1
        st.rerun()
with nav_r:
    if st.button("Skip →", disabled=pos == len(items) - 1,
                 use_container_width=True):
        st.session_state.pos = pos + 1
        st.rerun()

st.markdown("**Your label:**")
cols = st.columns(len(LABELS))
for col, label in zip(cols, LABELS):
    suggested = (ARGS_MODE == "adjudicate"
                 and preds.get(item_id) == label)
    with col:
        if st.button(("✓ " if suggested else "") + label,
                     type="primary" if suggested else "secondary",
                     use_container_width=True):
            save_decision(item_id, label)
            st.session_state.pos = min(pos + 1, len(items) - 1)
            st.rerun()

if current:
    st.success(f"labeled: {current}")

# export
annotated = [it for it in items if state.get(str(it[ID_COL]))]
if annotated:
    rows = []
    for it in annotated:
        row = dict(it)
        row["label"] = state[str(it[ID_COL])]
        rows.append(row)
    df = pd.DataFrame(rows)
    st.download_button(
        "Download annotated CSV",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name="annotations.csv", mime="text/csv")
    st.download_button(
        "Download annotated JSONL",
        data="\n".join(json.dumps(r, ensure_ascii=False) for r in rows),
        file_name="annotations.jsonl", mime="application/x-jsonlines")
