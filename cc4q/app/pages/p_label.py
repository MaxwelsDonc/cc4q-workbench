"""Page — Annotate: sample + human review, embedded annotation UI."""

import json

import streamlit as st

from cc4q.app import data_io
from cc4q.annotate.ui import render_annotation


def _records_from_source(source, upload, sdk, quantum_only):
    if source == "Upload a corpus JSONL":
        if upload is None:
            return None
        import pandas as pd
        df = pd.read_json(upload, lines=True)
        return df.to_dict(orient="records")
    if source == "Session predict output":
        recs = st.session_state.get("predict_output")
        if not recs:
            return None
        return [dict(r) for r in recs]
    # precomputed SDK corpus
    df = data_io.load_units_df(sdk)
    if quantum_only:
        df = df[df["quantum_related"]]
    return df.to_dict(orient="records")


def render():
    st.header("Annotate")
    st.write("Draw a sample from a corpus and review it in the annotation "
             "UI — confirm, fix, or skip each item. Exports are train-ready, "
             "and finished rounds can be sent straight to the Train page.")

    st.subheader("Step 1 — source")
    c1, c2, c3 = st.columns(3)
    with c1:
        source = st.selectbox("Corpus", [
            "Precomputed SDK corpus", "Upload a corpus JSONL",
            "Session predict output"])
    with c2:
        sdk = None
        if source == "Precomputed SDK corpus":
            manifest = data_io.load_manifest()
            sdks = sorted(manifest["repos"])
            sdk = st.selectbox("SDK", sdks)
    with c3:
        upload = None
        quantum_only = False
        if source == "Upload a corpus JSONL":
            upload = st.file_uploader("Corpus JSONL", type=["jsonl", "json"])
        if source == "Precomputed SDK corpus":
            quantum_only = st.checkbox("Quantum units only", value=False)

    records = _records_from_source(source, upload, sdk, quantum_only)
    if not records:
        st.info("Pick a source to load items — the sampling controls appear "
                "once records are loaded.")
        return

    st.caption(f"{len(records):,} records loaded.")
    st.subheader("Step 2 — sampling")
    cols = sorted({k for r in records[:200] for k in r.keys()})
    s1, s2, s3 = st.columns(3)
    with s1:
        by = st.multiselect("Stratify by (empty = random)", cols, default=[])
        n = st.number_input("Sample size n", min_value=1,
                            max_value=len(records),
                            value=min(50, len(records)))
    with s2:
        seed = st.number_input("Seed", min_value=0, value=42, step=1)
        quotas_json = st.text_input("Quotas (optional JSON, e.g. "
                                    "{\"qiskit\": 20})")
    sampled = records
    if st.button("Draw sample", type="primary"):
        from cc4q.sample import sample as cc4q_sample
        quotas = json.loads(quotas_json) if quotas_json.strip() else None
        sampled = cc4q_sample(records, by=by or None, n=int(n),
                              quotas=quotas, seed=int(seed))
        st.session_state["annotate_items"] = sampled
        st.session_state.pop("annotate_labels", None)
        st.rerun()
    sampled = st.session_state.get("annotate_items") or records[: int(n)]
    st.caption(f"Annotating {len(sampled)} items.")

    st.subheader("Step 3 — review")
    f1, f2, f3 = st.columns(3)
    with f1:
        labels = st.text_input("Labels (comma-separated)",
                               value="quantum,non-quantum").split(",")
        labels = [l.strip() for l in labels if l.strip()]
    with f2:
        mode = st.selectbox("Mode", ["adjudicate", "blind"],
                            help="adjudicate shows model suggestions built "
                                 "from quantum_related when available")
    with f3:
        text_col = st.text_input("Text column", value="comment_text")
        id_col = st.text_input("ID column", value="id")

    id_guess = id_col if all(id_col in r for r in sampled) else None
    if id_guess is None:
        for cand in ("id", "no", "uid"):
            if all(cand in r for r in sampled):
                id_guess = cand
                break
    if id_guess is None:
        st.warning("No usable id column found — add one or pick another "
                   "corpus.")
        return

    preds_map = None
    if mode == "adjudicate":
        preds_map = {}
        for r in sampled:
            if "quantum_related" in r:
                val = r["quantum_related"]
                val = val if isinstance(val, int) else int(bool(val))
                preds_map[str(r[id_guess])] = labels[0] if val == 1 \
                    else (labels[1] if len(labels) > 1 else labels[0])
            elif "label" in r:
                preds_map[str(r[id_guess])] = str(r["label"])

    config = {"schema": {"text_column": text_col, "id_column": id_guess,
                         "labels": labels},
              "mode": mode, "items": sampled,
              "predictions_map": preds_map or {}}
    rows = render_annotation(config, session_prefix="annotate_page",
                             embedded=True)
    if rows:
        st.download_button(
            "Export annotated JSONL",
            data="\n".join(json.dumps(r, ensure_ascii=False)
                           for r in rows),
            file_name="annotations.jsonl", mime="application/x-jsonlines",
            key="annotate_page_export")
        if st.button("Send to Train page →", type="primary"):
            st.session_state["train_stash"] = rows
            st.success(f"{len(rows)} annotated rows stashed — open "
                       "**Train & Evaluate** to train on them.")


render()
