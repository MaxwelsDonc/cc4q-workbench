"""Reusable annotation UI.

``render_annotation`` powers both the standalone app (``cc4q annotate`` /
``streamlit run cc4q/annotate/app.py``) and embedded use inside the CC4Q
workbench's Annotate page. All session state is namespaced by
``session_prefix`` so embedded instances never clash with each other or the
host page.
"""

import json
import os

import pandas as pd
import streamlit as st


def _resolve(config):
    """Normalize a config dict into (items, preds, state_path, schema,
    mode). Items/predictions may be given in memory (``items`` /
    ``predictions_map``) or as file paths (``data`` / ``predictions``)."""
    schema = config["schema"]
    id_col = schema["id_column"]
    mode = config.get("mode", "blind")

    if "items" in config:
        items = config["items"]
    else:
        with open(config["data"], encoding="utf-8") as f:
            items = [json.loads(line) for line in f if line.strip()]

    preds = {}
    if mode == "adjudicate":
        if "predictions_map" in config:
            preds = {str(k): str(v) for k, v in
                     config["predictions_map"].items()}
        elif config.get("predictions"):
            with open(config["predictions"], encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        r = json.loads(line)
                        preds[str(r[id_col])] = str(r.get(
                            "model_label", r.get("label", "")))

    state_path = None
    if config.get("output_dir"):
        state_path = os.path.join(config["output_dir"], "annotations.jsonl")
    return items, preds, state_path, schema, mode


def _load_state(state_path, id_col):
    state = {}
    if state_path and os.path.exists(state_path):
        with open(state_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    state[str(r.get(id_col))] = r.get("label") or None
    return state


def _save_state(state_path, id_col, state):
    if not state_path:
        return
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        for k, v in state.items():
            f.write(json.dumps({id_col: k, "label": v},
                               ensure_ascii=False) + "\n")


def render_annotation(config, session_prefix="ann", embedded=False):
    """Render the click-through annotation UI.

    ``config`` keys: schema (text_column/id_column/labels/title?), mode
    (blind|adjudicate), items or data, predictions_map or predictions,
    output_dir (optional persistence). Returns the list of annotated rows
    (records + ``label`` column) for host pages to consume.
    """
    items, preds, state_path, schema, mode = _resolve(config)
    text_col = schema["text_column"]
    id_col = schema["id_column"]
    labels = schema["labels"]
    pos_key = f"{session_prefix}_pos"

    if not embedded:
        st.set_page_config(page_title="cc4q annotate", layout="centered")
    st.title(schema.get("title", "cc4q annotation"))
    if mode == "adjudicate":
        st.caption("adjudicate mode — model suggestions shown; confirm or "
                   "override. Every item still requires a human click.")

    # state: session_state overlay (embedded) + on-disk persistence
    disk_state = _load_state(state_path, id_col)
    ss_key = f"{session_prefix}_labels"
    state = dict(disk_state)
    state.update(st.session_state.get(ss_key, {}))

    labeled = sum(1 for it in items if state.get(str(it[id_col])))
    st.progress(labeled / len(items),
                text=f"{labeled} / {len(items)} annotated")

    if pos_key not in st.session_state:
        for i, it in enumerate(items):  # resume at first unlabeled
            if not state.get(str(it[id_col])):
                st.session_state[pos_key] = i
                break
        else:
            st.session_state[pos_key] = 0
    pos = min(st.session_state[pos_key], len(items) - 1)
    item = items[pos]
    item_id = str(item[id_col])
    current = state.get(item_id)

    st.caption(f"item {pos + 1} of {len(items)} — {id_col}={item_id}")
    st.markdown(f"**{item.get('entity', item.get('code_entity_type', ''))}**"
                if item.get("entity") or item.get("code_entity_type")
                else "")
    st.text(str(item[text_col]))

    if mode == "adjudicate":
        suggestion = preds.get(item_id)
        if suggestion:
            st.info(f"Model suggests: **{suggestion}**")

    def decide(label):
        state[item_id] = label
        st.session_state[ss_key] = dict(state)
        _save_state(state_path, id_col, state)
        st.session_state[pos_key] = min(pos + 1, len(items) - 1)
        st.rerun()

    nav_l, nav_r = st.columns(2)
    with nav_l:
        if st.button("← Previous", disabled=pos == 0,
                     use_container_width=True,
                     key=f"{session_prefix}_prev"):
            st.session_state[pos_key] = pos - 1
            st.rerun()
    with nav_r:
        if st.button("Skip →", disabled=pos == len(items) - 1,
                     use_container_width=True,
                     key=f"{session_prefix}_skip"):
            st.session_state[pos_key] = pos + 1
            st.rerun()

    st.markdown("**Your label:**")
    cols = st.columns(len(labels))
    for col, label in zip(cols, labels):
        suggested = mode == "adjudicate" and preds.get(item_id) == label
        with col:
            if st.button(("✓ " if suggested else "") + label,
                         type="primary" if suggested else "secondary",
                         use_container_width=True,
                         key=f"{session_prefix}_lbl_{label}"):
                decide(label)

    if current:
        st.success(f"labeled: {current}")

    annotated = [it for it in items if state.get(str(it[id_col]))]
    rows = []
    for it in annotated:
        row = dict(it)
        row["label"] = state[str(it[id_col])]
        rows.append(row)
    if rows:
        df = pd.DataFrame(rows)
        st.download_button(
            "Download annotated CSV",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name="annotations.csv", mime="text/csv",
            key=f"{session_prefix}_csv")
        st.download_button(
            "Download annotated JSONL",
            data="\n".join(json.dumps(r, ensure_ascii=False)
                           for r in rows),
            file_name="annotations.jsonl",
            mime="application/x-jsonlines",
            key=f"{session_prefix}_jsonl")
    return rows
