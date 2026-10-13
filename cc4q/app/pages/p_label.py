"""Page — Build step 2: Label (predict -> sample -> annotate -> export)."""

import json
import os

import pandas as pd
import streamlit as st

from cc4q.app import PAGES_DIR, data_io, model_select, stepper
from cc4q.annotate.ui import render_annotation

SOURCES = ("Build corpus from Get Data", "Precomputed SDK corpus",
           "Upload a corpus JSONL", "Session predict output")


def _records(source, upload, sdk, quantum_only):
    if source == "Build corpus from Get Data":
        recs = st.session_state.get("build_corpus")
        if not recs:
            return None
        return [dict(r) for r in recs]
    if source == "Upload a corpus JSONL":
        if upload is None:
            return None
        return pd.read_json(upload, lines=True).to_dict(orient="records")
    if source == "Session predict output":
        recs = st.session_state.get("predict_output")
        return [dict(r) for r in recs] if recs else None
    df = data_io.load_units_df(sdk)
    if quantum_only:
        df = df[df["quantum_related"]]
    return df.to_dict(orient="records")


def render():
    st.header("2 · Label")
    st.write("Label the corpus with the default prediction model (set in "
             "⚙ Models), then review a sample: confirm, fix, or skip each "
             "item in the annotation UI.")

    if stepper.render_stepper(2):
        st.rerun()

    # step 1: corpus
    c1, c2, c3 = st.columns(3)
    with c1:
        source = st.selectbox("Corpus", SOURCES)
    with c2:
        sdk = None
        if source == "Precomputed SDK corpus":
            sdk = st.selectbox("SDK", sorted(data_io.load_manifest()["repos"]))
    with c3:
        upload = None
        quantum_only = False
        if source == "Upload a corpus JSONL":
            upload = st.file_uploader("Corpus JSONL", type=["jsonl", "json"])
        if source == "Precomputed SDK corpus":
            quantum_only = st.checkbox("Quantum units only", value=False)

    records = _records(source, upload, sdk, quantum_only)
    if not records:
        st.info("Pick a source with records — the fastest path is step 1 · "
                "Get Data.")
        return
    st.caption(f"{len(records):,} records loaded.")

    # step 2: predict with the global default model
    labeled = st.session_state.get("build_labeled")
    if st.button("Predict with default model", type="primary"):
        with st.spinner("Labeling with the default model…"):
            try:
                models = model_select.resolve_default_handle()
                from cc4q.predict import predict_corpus
                labeled = predict_corpus([dict(r) for r in records],
                                         models=models)
            except Exception as exc:
                st.error(f"Prediction failed: {exc}")
                labeled = None
        if labeled:
            st.session_state["build_labeled"] = labeled
            st.session_state["predict_output"] = labeled
            st.success(f"{len(labeled):,} units labeled.")
            st.rerun()
    if not labeled:
        st.info("Run prediction to enable sampling and review.")
        return

    # step 3: sampling
    st.subheader("Sampling")
    cols = sorted({k for r in labeled[:200] for k in r.keys()})
    s1, s2, s3 = st.columns(3)
    with s1:
        by = st.multiselect("Stratify by (empty = random)", cols, default=[])
        n = st.number_input("Sample size n", min_value=1,
                            max_value=len(labeled),
                            value=min(50, len(labeled)))
    with s2:
        seed = st.number_input("Seed", min_value=0, value=42, step=1)
        quotas_json = st.text_input("Quotas (optional JSON)")
    if st.button("Draw sample"):
        from cc4q.sample import sample as cc4q_sample
        quotas = json.loads(quotas_json) if quotas_json.strip() else None
        sampled = cc4q_sample(labeled, by=by or None, n=int(n),
                              quotas=quotas, seed=int(seed))
        st.session_state["annotate_items"] = sampled
        st.session_state.pop("annotate_labels", None)
        st.rerun()
    sampled = st.session_state.get("annotate_items") or labeled[: int(n)]
    st.caption(f"Reviewing {len(sampled)} items.")

    # step 4: review + export
    st.subheader("Review")
    f1, f2, f3 = st.columns(3)
    with f1:
        labels = st.text_input("Labels (comma-separated)",
                               value="quantum,non-quantum").split(",")
        labels = [l.strip() for l in labels if l.strip()]
    with f2:
        mode = st.selectbox("Mode", ["adjudicate", "blind"])
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
        st.warning("No usable id column found.")
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
        b1, b2 = st.columns(2)
        if b1.button("Send to Train page →"):
            st.session_state["train_stash"] = rows
            st.success(f"{len(rows)} annotated rows stashed.")
        if b2.button("Continue to Train →", type="primary"):
            st.switch_page(os.path.join(PAGES_DIR, "p_train.py"))


render()
