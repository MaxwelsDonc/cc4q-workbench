"""Page — Train & Evaluate: in-page fine-tuning with live metrics."""

import json
import os
import tempfile

import os

import streamlit as st

from cc4q.app import PAGES_DIR, registry, stepper

TASKS = ("quantum_related", "quantum_category", "developer_intent")
INTENT_ORDER = ["What", "How-to-use", "How-it-is-done", "Property", "Why",
                "Others"]
CATEGORY_ORDER = ["Mathematics for quantum information", "Quantum algorithms",
                  "Quantum circuit model", "Quantum hardware",
                  "Quantum software framework", "Others"]


def _load_rows(source, upload):
    if source == "Stashed from the Annotate page":
        return st.session_state.get("train_stash") or []
    if upload is None:
        return []
    import pandas as pd
    name = upload.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(upload).to_dict(orient="records")
    return pd.read_json(upload, lines=True).to_dict(orient="records")


def _to_training_records(rows, task):
    """Map free-form annotation rows onto the task contract; raises
    ValueError with an example row on violation."""
    text_col = "comment" if task == "quantum_related" else "text"
    canonical = CATEGORY_ORDER if task == "quantum_category" else \
        INTENT_ORDER if task == "developer_intent" else None
    out = []
    for i, r in enumerate(rows, 1):
        text = r.get(text_col) or r.get("comment_text") or r.get("text")
        label = r.get("label")
        if not isinstance(text, str) or label is None:
            raise ValueError(
                f"row {i}: need a text column ('{text_col}' or "
                f"'comment_text') and a 'label'; got keys {sorted(r)}")
        if canonical is None:  # quantum_related: accept 0/1 or words
            if isinstance(label, str):
                low = label.strip().lower()
                if low in ("quantum", "1", "true"):
                    label = 1
                elif low in ("non-quantum", "0", "false"):
                    label = 0
        elif isinstance(label, str):
            label = canonical.index(label) if label in canonical else -1
        out.append({text_col: text, "label": label})
    return out


class _StreamlitCallback:  # duck-typed transformers TrainerCallback
    def __init__(self, placeholder):
        self.ph = placeholder
        self.lines = []

    def on_log(self, args, state, control, logs=None, **kwargs):
        if not logs:
            return
        keep = {k: v for k, v in logs.items()
                if isinstance(v, (int, float))}
        if keep:
            self.lines.append(
                f"step {state.global_step}: " + ", ".join(
                    f"{k}={v:.4g}" for k, v in keep.items()))
            self.ph.code("\n".join(self.lines[-12:]), language=None)


def render():
    st.header("3 · Train")
    st.write("Fine-tune a classifier on your annotated data, right in the "
             "browser — the result registers in ⚙ Models and feeds step 4.")

    if stepper.render_stepper(3):
        st.rerun()

    source = st.radio("Annotated data", [
        "Stashed from the Annotate page", "Upload JSONL / CSV"],
        horizontal=True)
    upload = None
    if source.startswith("Upload"):
        upload = st.file_uploader("Annotated file", type=["jsonl", "csv"])
    rows = _load_rows(source, upload)
    if not rows:
        st.info("No annotated rows yet — annotate a sample on the **Annotate**"
                " page or upload a file.")
        return
    st.caption(f"{len(rows):,} annotated rows loaded.")
    if len(rows) > 2000:
        st.warning(f"{len(rows):,} rows is a lot for in-browser training — "
                   "the CLI (`cc4q train`) is recommended for large corpora.")

    c1, c2 = st.columns(2)
    with c1:
        task = st.selectbox("Task", TASKS)
        base_model = st.text_input("Base model", value="bert-base-uncased")
    with c2:
        epochs = st.slider("Epochs", 1, 30, 3,
                           help="the released models trained for 30; 1-5 "
                                "epochs is a sensible first pass")
        batch_size = st.slider("Batch size", 8, 64, 32)

    try:
        train_records = _to_training_records(rows, task)
        from cc4q.train import TASKS as SPEC, _validate
        _validate(task, _write_tmp(train_records), SPEC[task]["text_column"],
                  SPEC[task]["num_labels"])
        st.success("Data honors the training contract.")
        valid = True
    except ValueError as exc:
        st.error(str(exc))
        valid = False

    if st.button("Start training", type="primary", disabled=not valid):
        _run_training(task, train_records, base_model, epochs, batch_size)


def _write_tmp(records):
    fd, path = tempfile.mkstemp(suffix=".jsonl", prefix="cc4q_train_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path


def _run_training(task, train_records, base_model, epochs, batch_size):
    import cc4q.train as train_mod
    from cc4q.models.hub import default_model_dir, missing_checkpoints

    out_dir = tempfile.mkdtemp(prefix="cc4q_trained_")
    metrics = st.empty()
    with st.spinner("Training (this runs in your browser session — keep it "
                    "open)…"):
        try:
            result = train_mod.train(
                task, _write_tmp(train_records), out_dir,
                base_model=base_model, epochs=epochs,
                batch_size=batch_size,
                callbacks=[_StreamlitCallback(metrics)])
        except Exception as exc:
            st.error(f"Training failed: {exc}")
            return
    st.success(f"Training finished — model saved to {out_dir}")
    st.json(result["test_results"])

    entry = registry.register(
        name=f"{task}-{epochs}ep", path=out_dir, source="trained")
    st.session_state["model_handle_cache"] = {}
    st.session_state["build_trained"] = entry["id"]
    st.balloons()
    st.markdown(f"Registered as **{entry['name']}** in ⚙ Models "
                f"(axes: {', '.join(entry['axes'])}).")

    # auto-evaluate against the released model on the training texts
    if missing_checkpoints(default_model_dir()):
        st.caption("Released checkpoints not available — skipping the "
                   "comparison against the released model.")
        return
    with st.spinner("Comparing against the released model…"):
        try:
            from cc4q.evaluate import evaluate
            from cc4q.models.hub import load_models, load_models_from
            texts = [r["comment" if task == "quantum_related" else "text"]
                     for r in train_records]
            released = load_models()
            trained = load_models_from({task: out_dir})
            r_preds = _axis_labels(released, task, texts)
            t_preds = _axis_labels(trained, task, texts)
            res = evaluate(r_preds, t_preds)
        except Exception as exc:
            st.warning(f"Comparison failed: {exc}")
            st.session_state["build_eval_skipped"] = str(exc)
            return
    st.subheader("Trained vs released (on your training texts)")
    st.markdown(f"| metric | value |\n|---|---|\n"
                f"| agreement | {res['agreement']:.1%} |\n"
                f"| precision | {res['precision']:.1%} |\n"
                f"| recall | {res['recall']:.1%} |\n"
                f"| Wilson 95% CI | "
                f"{res['wilson95'][0]:.1%}–{res['wilson95'][1]:.1%} |")
    if st.button("Continue to Evaluate →", type="primary",
                 key="to_evaluate"):
        st.switch_page(os.path.join(PAGES_DIR, "p_evaluate.py"))


def _axis_labels(handle, task, texts):
    from cc4q.predict import predict_labels, INTENT_MAPPING, CATEGORY_MAPPING
    _, di, cat = predict_labels(texts, handle, batch=64)
    if task == "quantum_related":
        qr, _, _ = predict_labels(texts, handle, batch=64)
        return ["quantum" if q else "non-quantum" for q in qr]
    if task == "developer_intent":
        return di
    return [c or "None" for c in cat]


render()
