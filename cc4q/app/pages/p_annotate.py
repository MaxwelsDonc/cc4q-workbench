"""Page — Annotate: annotation session assets + new-annotation wizard."""

import json

import pandas as pd
import streamlit as st

import cc4q.workspace as ws
from cc4q.annotate.ui import render_annotation
from cc4q.app.ui import (asset_card_grid, empty_state, page_header,
                         section_divider)


def _session_records(session):
    path = session.get("export_path") or ws.asset_path(
        session["id"], "items.jsonl")
    return ws.read_jsonl(path) if __import__("os").path.isfile(path) else []


def _resume(session):
    st.session_state["ann_resume"] = session["id"]
    st.rerun()


def _delete(session):
    ws.delete_asset(session["id"])
    if st.session_state.get("ann_resume") == session["id"]:
        st.session_state["ann_resume"] = None
    st.rerun()


def _session_cards(sessions):
    items = []
    for s in sessions:
        total = s.get("total", 0)
        done = s.get("labeled_count", 0)
        actions = [
            {"label": "Resume",
             "on_click": lambda sid=s["id"]: _resume(
                 next(x for x in ws.list_assets("annotation_session")
                      if x["id"] == sid))},
            {"label": "Delete",
             "on_click": lambda sid=s["id"]: _delete(
                 next(x for x in ws.list_assets("annotation_session")
                      if x["id"] == sid))},
        ]
        items.append({
            "title": s["name"],
            "badge": (s.get("mode", "blind"), "neutral"),
            "meta": [f"!{done}/{total} labeled" if total else "!0 labeled",
                     f"updated {s.get('updated_at', '')}"],
            "actions": actions,
        })
    return items


def _wizard():
    section_divider("New annotation")
    # 1. source
    sources = ["Corpus asset"]
    if st.session_state.get("predict_output"):
        sources.append("Session predict output")
    sources.append("Upload a corpus JSONL")
    source = st.selectbox("Source", sources)
    records, preds_map = None, {}
    if source == "Corpus asset":
        corpora = [a for a in ws.list_assets("corpus")]
        if not corpora:
            st.info("No corpus assets yet — create one on the Corpora page.")
            return
        pick = st.selectbox("Corpus", range(len(corpora)),
                            format_func=lambda i: corpora[i]["name"])
        asset = corpora[pick]
        key = "labeled" if asset.get("labeled") and asset["files"].get(
            "labeled") else "corpus"
        records = ws.read_jsonl(asset["files"][key])
        if key == "labeled":
            for r in records:
                val = r.get("quantum_related")
                val = val if isinstance(val, int) else int(bool(val))
                preds_map[str(r.get("id", ""))] = \
                    "quantum" if val == 1 else "non-quantum"
    elif source == "Session predict output":
        records = [dict(r) for r in st.session_state["predict_output"]]
        for r in records:
            val = r.get("quantum_related")
            val = val if isinstance(val, int) else int(bool(val))
            preds_map[str(r.get("id", ""))] = \
                "quantum" if val == 1 else "non-quantum"
    else:
        upload = st.file_uploader("Corpus JSONL", type=["jsonl", "json"])
        if upload is not None:
            records = pd.read_json(upload, lines=True).to_dict(
                orient="records")
    if not records:
        st.info("Pick a source with records.")
        return

    # 2. sampling
    c1, c2, c3 = st.columns(3)
    cols = sorted({k for r in records[:200] for k in r.keys()})
    with c1:
        by = st.multiselect("Stratify by (empty = random)", cols, default=[])
        n = st.number_input("Sample size n", min_value=1,
                            max_value=len(records),
                            value=min(50, len(records)))
    with c2:
        seed = st.number_input("Seed", min_value=0, value=42, step=1)
        quotas_json = st.text_input("Quotas (optional JSON)")
    if st.button("Draw sample"):
        from cc4q.sample import sample as cc4q_sample
        quotas = json.loads(quotas_json) if quotas_json.strip() else None
        sampled = cc4q_sample(records, by=by or None, n=int(n),
                              quotas=quotas, seed=int(seed))
        st.session_state["ann_items"] = sampled
        st.session_state.pop("annotate_labels", None)
        st.rerun()
    sampled = st.session_state.get("ann_items") or records[: int(n)]

    # 3. schema + mode + embedded UI
    f1, f2 = st.columns(2)
    with f1:
        labels = st.text_input("Labels (comma-separated)",
                               value="quantum,non-quantum").split(",")
        labels = [l.strip() for l in labels if l.strip()]
        mode = st.selectbox("Mode", ["adjudicate", "blind"],
                            disabled=not preds_map,
                            help="adjudicate needs model predictions")
    with f2:
        text_col = st.text_input("Text column", value="comment_text")
        id_col = st.text_input("ID column", value="id")
    id_guess = id_col if all(id_col in r for r in sampled) else None
    if id_guess is None:
        for cand in ("id", "no", "uid"):
            if all(cand in r for r in sampled):
                id_guess = cand
                break
    if id_guess is None:
        st.warning("No usable id column found.")
        return
    name = st.text_input("Session name", value="annotation-1")

    if not st.session_state.get("ann_session_id"):
        session = ws.create_asset(
            "annotation_session", name=name.strip() or "annotation",
            schema={"text_column": text_col, "id_column": id_guess,
                    "labels": labels},
            mode=mode, total=len(sampled), labeled_count=0)
        ws.write_jsonl(session["id"], "items.jsonl", sampled)
        ws.update_asset(session["id"], export_path=ws.asset_path(
            session["id"], "items.jsonl"))
        st.session_state["ann_session_id"] = session["id"]

    sid = st.session_state["ann_session_id"]
    session = ws.get_asset(sid)
    config = {"schema": session["schema"], "mode": session["mode"],
              "items": ws.read_jsonl(session["export_path"]),
              "predictions_map": preds_map}
    rows = render_annotation(config, session_prefix=f"ann_{sid}",
                             embedded=True)

    done = sum(1 for r in rows)
    if done != session.get("labeled_count"):
        ws.update_asset(sid, labeled_count=done, total=len(config["items"]))

    if rows:
        export_path = ws.write_jsonl(sid, "annotations.jsonl", rows)
        ws.update_asset(sid, export_path=export_path,
                        labeled_count=len(rows))
        st.download_button(
            "Export annotated JSONL",
            data="\n".join(json.dumps(r, ensure_ascii=False) for r in rows),
            file_name="annotations.jsonl", mime="application/x-jsonlines",
            key=f"ann_export_{sid}")
        st.caption("This export is the training-data pick on the Models "
                   "page.")
        if st.button("Finish session", type="primary"):
            st.session_state.pop("ann_session_id", None)
            st.session_state.pop("ann_items", None)
            st.session_state.pop("annotate_labels", None)
            st.rerun()


def _resume_view(session):
    records = _session_records(session)
    schema = session["schema"]
    config = {"schema": schema, "mode": session["mode"], "items": records,
              "predictions_map": {}}
    if session["mode"] == "adjudicate":
        labeled_key = session.get("export_path")
        if labeled_key and __import__("os").path.isfile(labeled_key) \
                and "label" in (records[0] if records else {}):
            for r in records:
                if r.get("label"):
                    config["predictions_map"][str(r.get(
                        schema["id_column"], ""))] = str(r["label"])
    rows = render_annotation(config, session_prefix=f"ann_{session['id']}",
                             embedded=True)
    if rows:
        ws.update_asset(session["id"], labeled_count=len(rows))
        export_path = ws.write_jsonl(session["id"], "annotations.jsonl",
                                     rows)
        ws.update_asset(session["id"], export_path=export_path)
    if st.button("← All sessions"):
        st.session_state["ann_resume"] = None
        st.rerun()


def render():
    page_header("Annotate",
                "Review model labels in click-through rounds — every round "
                "is a resumable session asset.")
    resume_id = st.session_state.get("ann_resume")
    if resume_id:
        _resume_view(ws.get_asset(resume_id))
        return
    if st.session_state.get("ann_session_id"):
        _wizard()
        return
    new = st.button("New annotation", type="primary", key="ann_new")
    if new:
        st.session_state["ann_new"] = not st.session_state.get("ann_new")
    if st.session_state.get("ann_new"):
        _wizard()
        st.divider()

    sessions = ws.list_assets("annotation_session")
    if not sessions:
        empty_state("No annotation sessions yet",
                    "Sample a corpus and review it — progress saves as you "
                    "go.")
        return
    asset_card_grid(_session_cards(sessions), key_prefix="ann")


render()
