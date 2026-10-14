"""Page — Models: released checkpoints, your model registry, inline training.

Reference implementation of the workspace IA: page header with a primary
action, section dividers, asset card grids, and an inline train-new-model
flow that reuses the cc4q.train contract and the annotation stash from the
Annotate page.
"""

import json
import os
import tempfile

import streamlit as st

from cc4q.app import registry
from cc4q.app.ui import (asset_card_grid, empty_state, page_header,
                         section_divider)

TASKS = ("quantum_related", "quantum_category")
INTENT_ORDER = ["What", "How-to-use", "How-it-is-done", "Property", "Why",
                "Others"]
CATEGORY_ORDER = ["Mathematics for quantum information", "Quantum algorithms",
                  "Quantum circuit model", "Quantum hardware",
                  "Quantum software framework", "Others"]

RELEASED = [
    {"title": "Quantum relatedness",
     "meta": ["Binary call — quantum vs non-quantum comment.",
              "The protagonist axis of every dashboard."]},
    {"title": "Quantum category",
     "meta": ["Six-class quantum-knowledge taxonomy.",
              "Mathematics · algorithms · circuit · hardware · framework · others."]},
    {"title": "Developer intent",
     "meta": ["Six-class intent axis (What / How-to-use / …).",
              "Lives in the data layer; not shown in the UI."]},
]

MAX_BROWSER_ROWS = 2000


def _annotation_exports():
    """Existing annotation-export JSONL files the user can pick directly."""
    cands = []
    env = os.environ.get("CC4Q_ANNOTATIONS")
    if env and os.path.isfile(env):
        cands.append(env)
    from cc4q.pipeline.paths import REPO_ROOT
    for path in (os.path.join(REPO_ROOT, "annotations",
                              "annotations.jsonl"),
                 os.path.join(REPO_ROOT, "annotations.jsonl")):
        if os.path.isfile(path) and path not in cands:
            cands.append(path)
    return cands


def _load_rows(source, upload):
    if source == "Stashed from the Annotate page":
        return st.session_state.get("train_stash") or []
    if source.startswith("Annotation export: "):
        path = source[len("Annotation export: "):]
        with open(path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    if upload is None:
        return []
    import pandas as pd
    name = upload.name.lower()
    if name.endswith(".csv"):
        return pd.read_csv(upload).to_dict(orient="records")
    return pd.read_json(upload, lines=True).to_dict(orient="records")


def _to_training_records(rows, task):
    """Map free-form annotation rows onto the task contract; raises
    ValueError with an example row on violation (ported from the Build
    train page)."""
    text_col = "comment" if task == "quantum_related" else "text"
    canonical = CATEGORY_ORDER if task == "quantum_category" else \
        None
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


def _write_tmp(records):
    fd, path = tempfile.mkstemp(suffix=".jsonl", prefix="cc4q_train_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path


def _validate(task, train_records):
    """Dry-run validation against the cc4q.train contract."""
    from cc4q.train import TASKS as SPEC, _validate
    _validate(task, _write_tmp(train_records),
              SPEC[task]["text_column"], SPEC[task]["num_labels"])


class _StreamlitCallback:  # duck-typed transformers TrainerCallback
    """Streams loss/F1 to a code log + a placeholder line chart."""

    def __init__(self, log_area, chart_area):
        self.log_area = log_area
        self.chart_area = chart_area
        self.lines = []
        self.history = []

    def on_log(self, args, state, control, logs=None, **kwargs):
        if not logs:
            return
        keep = {k: float(v) for k, v in logs.items()
                if isinstance(v, (int, float))}
        if not keep:
            return
        self.lines.append(
            f"step {state.global_step}: " + ", ".join(
                f"{k}={v:.4g}" for k, v in keep.items()))
        self.log_area.code("\n".join(self.lines[-12:]), language=None)
        self.history.append({"step": state.global_step, **keep})
        cols = [c for c in ("loss", "f1") if c in keep]
        if cols:
            import pandas as pd
            df = pd.DataFrame(self.history).set_index("step")[cols]
            self.chart_area.line_chart(df, height=180)


def _run_training(task, train_records, base_model, epochs, batch_size):
    import cc4q.train as train_mod

    out_dir = tempfile.mkdtemp(prefix="cc4q_trained_")
    log_area = st.empty()
    chart_area = st.empty()
    with st.spinner("Training (this runs in your browser session — keep it "
                    "open)…"):
        try:
            result = train_mod.train(
                task, _write_tmp(train_records), out_dir,
                base_model=base_model, epochs=epochs,
                batch_size=batch_size,
                callbacks=[_StreamlitCallback(log_area, chart_area)])
        except Exception as exc:
            st.error(f"Training failed: {exc}")
            return
    st.success(f"Training finished — model saved to {out_dir}")
    st.json(result["test_results"])

    entry = registry.register(
        name=f"{task}-{epochs}ep", path=out_dir, source="trained")
    st.session_state["model_handle_cache"] = {}
    st.session_state["models_new_entry"] = entry["id"]
    st.balloons()
    st.markdown(f"Registered as **{entry['name']}** in Your models "
                f"(axes: {', '.join(entry['axes'])}).")


def _train_panel():
    """Inline train-new-model flow (toggled from the page header)."""
    section_divider(
        "Train new model",
        "Fine-tune a classifier on annotated data — the checkpoint lands "
        "in Your models and feeds every prediction page.")

    stash = st.session_state.get("train_stash") or []
    exports = _annotation_exports()
    sources = []
    if stash:
        sources.append("Stashed from the Annotate page")
    sources += [f"Annotation export: {p}" for p in exports]
    sources.append("Upload JSONL / CSV")
    source = st.radio("Annotated data", sources, horizontal=True,
                      key="models_data_source")

    upload = None
    if source == "Upload JSONL / CSV":
        upload = st.file_uploader("Annotated file", type=["jsonl", "csv"],
                                  key="models_data_upload")
    rows = _load_rows(source, upload)
    if not rows:
        st.info("No annotated rows here yet — annotate a sample on the "
                "**Annotate** page, export annotations, or upload a file.")
        return
    st.caption(f"{len(rows):,} annotated rows loaded.")
    if len(rows) > MAX_BROWSER_ROWS:
        st.warning(f"{len(rows):,} rows is a lot for in-browser training — "
                   "the CLI (`cc4q train`) is recommended for large corpora.")

    c1, c2 = st.columns(2)
    with c1:
        task = st.selectbox("Task", TASKS, key="models_task")
        base_model = st.text_input("Base model", value="bert-base-uncased",
                                   key="models_base")
    with c2:
        epochs = st.slider("Epochs", 1, 30, 3,
                           help="the released models trained for 30; 1-5 "
                                "epochs is a sensible first pass",
                           key="models_epochs")
        batch_size = st.slider("Batch size", 8, 64, 32,
                               key="models_batch")

    try:
        train_records = _to_training_records(rows, task)
        _validate(task, train_records)
        valid = True
    except ValueError as exc:
        st.error(str(exc))
        train_records, valid = [], False

    if st.button("Check data", key="models_check",
                 help="Dry-run the cc4q.train data-contract validation "
                      "and show label statistics."):
        if not valid:
            st.error("Data does not honor the training contract — fix the "
                     "errors above before training.")
        else:
            labels = [r["label"] for r in train_records]
            from collections import Counter
            dist = ", ".join(f"{k}: {v}" for k, v in
                             sorted(Counter(labels).items()))
            st.success("Data honors the training contract (dry run — no "
                       "training started).")
            st.markdown(
                f"| | |\n|---|---|\n"
                f"| rows | {len(train_records):,} |\n"
                f"| task | `{task}` |\n"
                f"| text column | "
                f"`{'comment' if task == 'quantum_related' else 'text'}` |\n"
                f"| labels | {dist} |\n"
                f"| base model | `{base_model}` · {epochs} epochs · "
                f"batch {batch_size} |")

    if st.button("Start training", type="primary", key="models_start",
                 disabled=not valid):
        _run_training(task, train_records, base_model, epochs, batch_size)


def _clear_model_cache():
    st.session_state["model_handle_cache"] = {}


def _model_items(entries):
    items = []
    for entry in entries:
        badge = ("★ Default", "quantum") if entry["is_default"] \
            else ("Custom", "neutral")
        axes = " + ".join(a.replace("_", " ") for a in entry["axes"])
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        tmp.close()
        try:
            registry.zip_package(entry["id"], tmp.name)
            with open(tmp.name, "rb") as f:
                data = f.read()
        finally:
            os.unlink(tmp.name)
        actions = []
        if not entry["is_default"]:
            actions.append({
                "label": "★ Set as default",
                "on_click": lambda e=entry: (
                    registry.set_default(e["id"]), _clear_model_cache(),
                    st.rerun()),
            })
        actions.append({"label": "⬇ Download zip",
                        "download": {"data": data,
                                     "file_name": f"{entry['id']}.zip"}})
        actions.append({
            "label": "Delete",
            "on_click": lambda e=entry: (
                registry.delete(e["id"]), _clear_model_cache(),
                st.rerun()),
        })
        items.append({
            "title": entry["name"],
            "badge": badge,
            "meta": [f"{axes} · {entry['source']}",
                     f"registered {entry.get('created', '?')}"],
            "actions": actions,
        })
    return items


def render():
    entries = registry.list_models()
    has_default = any(e["is_default"] for e in entries)

    if page_header("Models",
                   "Released checkpoints and your fine-tuned classifiers",
                   action_label="Train new model",
                   action_help="Open the inline training flow on this page.",
                   key="models_train_toggle"):
        st.session_state["models_train_open"] = \
            not st.session_state.get("models_train_open", False)

    if st.session_state.get("models_train_open"):
        _train_panel()

    # ---- Released -----------------------------------------------------
    section_divider("Released",
                    "Companion-paper checkpoints, downloaded on first use.")
    released_items = []
    for spec in RELEASED:
        released_items.append({
            "title": spec["title"],
            "badge": ("Default", "quantum") if not has_default
                     else ("Fallback", "neutral"),
            "meta": spec["meta"],
            "actions": [],
        })
    asset_card_grid(released_items, key_prefix="released")

    # ---- Your models ---------------------------------------------------
    section_divider("Your models",
                    "Trained or uploaded packages — the ★ default answers "
                    "every prediction.")
    st.caption(f"Registry: {registry.registry_root()}")

    upload = st.file_uploader(
        "Upload a model zip (one Hugging Face directory per axis: "
        "quantum_related, quantum_category)", type=["zip"],
        key="models_upload")
    if upload is not None:
        try:
            entry = registry.register_uploaded_zip(upload)
            _clear_model_cache()
            st.success(f"Registered **{entry['name']}** "
                       f"({' + '.join(entry['axes'])}).")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    if not entries:
        if empty_state(
                "No custom models yet",
                "Train a classifier on your annotations, or upload a model "
                "package — it becomes the default wherever predictions run.",
                action_label="Train new model"):
            st.session_state["models_train_open"] = True
            st.rerun()
    else:
        asset_card_grid(_model_items(entries), key_prefix="models")

    new_id = st.session_state.pop("models_new_entry", None)
    if new_id:
        entry = next((e for e in registry.list_models()
                      if e["id"] == new_id), None)
        if entry and not entry["is_default"]:
            st.info(f"**{entry['name']}** is not the default yet.")
            if st.button("★ Set as default", key="models_set_default_new"):
                registry.set_default(new_id)
                _clear_model_cache()
                st.rerun()


render()
