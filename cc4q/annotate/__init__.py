"""Interactive schema-driven annotation UI (Streamlit).

Launch programmatically::

    import cc4q
    cc4q.annotate("items.jsonl", schema={
        "text_column": "comment_text", "id_column": "id",
        "labels": ["quantum", "non-quantum"]}, mode="blind")

or via the CLI::

    cc4q annotate --data items.jsonl --schema schema.yaml --mode adjudicate \
        --model-predictions preds.jsonl --output-dir out/

Modes:
- blind: no model input, pure human labeling.
- adjudicate: a model-predictions file (joined by id) shows the suggestion
  for confirmation or override.

Progress persists to ``<output_dir>/annotations.jsonl`` (resume after
close); CSV/JSONL export includes the label column and is train-ready.
"""

import json
import os
import subprocess
import sys

APP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.py")


def _load_records(data):
    if isinstance(data, (str, os.PathLike)):
        path = str(data)
        if path.endswith(".csv"):
            import csv
            with open(path, encoding="utf-8-sig", newline="") as f:
                return list(csv.DictReader(f))
        with open(path, encoding="utf-8") as f:
            text = f.read()
        stripped = text.lstrip()
        if stripped.startswith("["):
            return json.loads(text)  # pretty-printed JSON array
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return list(data)


def _write_jsonl(path, records):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _normalize_schema(schema, records):
    """schema: dict, or path to a YAML/JSON file; values may be overridden
    by inference from the records."""
    if schema is None:
        schema = {}
    elif isinstance(schema, (str, os.PathLike)):
        with open(schema, encoding="utf-8") as f:
            text = f.read()
        if str(schema).endswith((".yaml", ".yml")):
            import yaml
            schema = yaml.safe_load(text) or {}
        else:
            schema = json.loads(text)
    schema = dict(schema)
    if "labels" not in schema or not schema["labels"]:
        raise ValueError("schema must define 'labels' (list of label names)")
    if "text_column" not in schema:
        raise ValueError("schema must define 'text_column'")
    if "id_column" not in schema:
        for candidate in ("id", "no", "uuid"):
            if records and candidate in records[0]:
                schema["id_column"] = candidate
                break
        else:
            raise ValueError("schema must define 'id_column'")
    schema["labels"] = [str(l) for l in schema["labels"]]
    return schema


def prepare(data, schema=None, mode="blind", model_predictions=None,
            output_dir="annotations"):
    """Materialize the annotation session under ``output_dir`` and return
    the session config path. The Streamlit app reads that config from the
    CC4Q_ANNOTATE_CONFIG env var (AppTest-friendly). Raises on invalid
    inputs (also used by the CLI --dry-run path)."""
    records = _load_records(data)
    if not records:
        raise ValueError("no records to annotate")
    schema = _normalize_schema(schema, records)

    os.makedirs(output_dir, exist_ok=True)
    items_path = os.path.join(output_dir, ".cc4q_items.jsonl")
    _write_jsonl(items_path, records)

    config = {"data": items_path, "schema": schema, "mode": mode,
              "predictions": None,
              "output_dir": os.path.abspath(output_dir)}
    if model_predictions is not None:
        preds = _load_records(model_predictions)
        pred_path = os.path.join(output_dir, ".cc4q_predictions.jsonl")
        _write_jsonl(pred_path, preds)
        config["predictions"] = pred_path

    config_path = os.path.join(output_dir, ".cc4q_session.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return config_path


def annotate(data, schema=None, mode="blind", model_predictions=None,
             output_dir="annotations", streamlit_args=None):
    """Launch the annotation UI in Streamlit (blocking until closed)."""
    config_path = prepare(data, schema=schema, mode=mode,
                          model_predictions=model_predictions,
                          output_dir=output_dir)
    env = dict(os.environ, CC4Q_ANNOTATE_CONFIG=config_path)
    cmd = [sys.executable, "-m", "streamlit", "run", APP_PATH]
    cmd += list(streamlit_args or [])
    return subprocess.call(cmd, env=env)
