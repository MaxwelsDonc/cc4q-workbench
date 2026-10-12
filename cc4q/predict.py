"""Snippet/corpus prediction with the three-axis CC4Q classifiers.

Pure inference layer — no streamlit. The label mappings are identical to
the ones used to produce the released corpora.
"""

import json
import os

INTENT_MAPPING = {0: "What", 1: "How-to-use", 2: "How-it-is-done",
                  3: "Property", 4: "Why", 5: "Others"}
CATEGORY_MAPPING = {0: "Mathematics for quantum information", 1: "Quantum algorithms",
                    2: "Quantum circuit model", 3: "Quantum hardware",
                    4: "Quantum software framework", 5: "Others"}

MAX_LENGTH = 512


def _axes(models):
    return (models.quantum_related, models.quantum_category,
            models.developer_intent)


def _batch_predict(tokenizer, model, texts, device, batch=32):
    import torch
    preds = []
    for i in range(0, len(texts), batch):
        inputs = tokenizer(texts[i:i + batch], return_tensors="pt",
                           padding=True, truncation=True, max_length=MAX_LENGTH)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.inference_mode():
            logits = model(**inputs).logits
        preds.extend(logits.argmax(dim=1).cpu().tolist())
    return preds


def predict_labels(texts, models, batch=32):
    """Run the three-axis classifiers over raw texts.

    ``models`` is a cc4q ModelHandle (or any object with
    quantum_related/quantum_category/developer_intent attributes and a
    ``device``). Returns (quantum_related[bool], developer_intent[str],
    quantum_category[str|None]) per text.
    """
    device = getattr(models, "device", None) or _resolve_device()
    qr_tok, qr_model = models.quantum_related
    qc_tok, qc_model = models.quantum_category
    di_tok, di_model = models.developer_intent

    qr = _batch_predict(qr_tok, qr_model, texts, device, batch)
    di = _batch_predict(di_tok, di_model, texts, device, batch)
    quantum_idx = [i for i, v in enumerate(qr) if v == 1]
    categories = [None] * len(texts)
    if quantum_idx:
        cat_preds = _batch_predict(
            qc_tok, qc_model, [texts[i] for i in quantum_idx], device, batch)
        for i, p in zip(quantum_idx, cat_preds):
            categories[i] = CATEGORY_MAPPING[p]
    return ([bool(v) for v in qr],
            [INTENT_MAPPING[v] for v in di],
            categories)


def _resolve_device():
    from cc4q.models.hub import resolve_device
    return resolve_device()


def _segment_record(record):
    """Split one CommentRecord into sentence-level comment units."""
    from cc4q.pipeline.segment.block import segment_block_comment
    from cc4q.pipeline.segment.docstring import segment_docstring
    from cc4q.pipeline.segment.inline import segment_inline_comment

    text = record["comment_text"].strip()
    ctype = record["comment_type"]
    if ctype == "docstring":
        units = [b["content"].strip() for b in segment_docstring(text)]
        units = [u for u in units if u and len(u) >= 3]
    elif ctype == "inline":
        units = segment_inline_comment(text)
    else:  # block
        units = segment_block_comment(text)
    return [{"text": u, "comment_type": ctype,
             "entity_type": record.get("code_entity_type", "—")}
            for u in units if u.strip()]


def raw_text_units(raw_text):
    """Automatic fallback: classify non-parseable input line by line."""
    return [{"text": line.strip().lstrip("#").strip(), "comment_type": "raw"}
            for line in raw_text.splitlines()
            if line.strip().lstrip("#").strip()]


def extract_units(source_code):
    """Extract + segment a Python snippet -> list of SCCU dicts.

    Returns (units, error). error is a short user-facing message when the
    snippet could not be parsed at all.
    """
    from cc4q.pipeline.extract import python_extract_comment_pairs
    from cc4q.pipeline.ids import id_generator

    try:
        records = python_extract_comment_pairs(
            source_code=source_code, rel_path="snippet.py", sdk="demo",
            id_gen=id_generator(), version="demo",
            host_language="python", clean_mode="current_only")
    except Exception as exc:
        detail = f"{type(exc).__name__}: {str(exc).splitlines()[0][:300]}"
        return [], f"Could not parse the snippet as Python ({detail})."
    units = []
    for record in records:
        units.extend(_segment_record(record))
    return units, None


def classify_units(units, models, batch=32):
    """Label SCCU dicts (``text`` key) in place; returns the units."""
    qr, di, categories = predict_labels([u["text"] for u in units], models,
                                        batch=batch)
    for unit, qr_v, di_v, cat in zip(units, qr, di, categories):
        unit["quantum_related"] = qr_v
        unit["developer_intent"] = di_v
        unit["quantum_category"] = cat
    return units


def analyze_snippet(source_code, models=None):
    """Full pipeline on a code snippet: extract -> segment -> (classify).

    Falls back to line-by-line classification when the input cannot be
    parsed as Python or yields no comments. ``models=None`` skips labeling
    (pure extract/segment — no checkpoints needed). Returns
    (units, parse_error, fallback_used).
    """
    units, error = extract_units(source_code)
    fallback = False
    if error or not units:
        raw = raw_text_units(source_code)
        if raw:
            units = raw
            fallback = True
        else:
            return [], error, False
    if models is not None:
        classify_units(units, models)
    return units, error, fallback


def predict_snippet(code, models=None, auto_download=True):
    """Labeled snippet analysis; loads the classifiers lazily when
    ``models`` is None. Same return shape as :func:`analyze_snippet`."""
    if models is None:
        from cc4q.models.hub import load_models
        models = load_models(auto_download=auto_download)
    return analyze_snippet(code, models=models)


def predict_corpus(units_or_path, models=None, batch=32, auto_download=True):
    """Label an SCCU corpus (pipeline stage-03 records).

    ``units_or_path`` is a list of records (each with ``comment_text``) or a
    path to a segmented JSON file. Adds ``quantum_related`` (0/1),
    ``developer_intent`` (str) and ``quantum_category`` (str|None) keys —
    the exact schema of the released labeled corpora — and returns the
    records.
    """
    if models is None:
        from cc4q.models.hub import load_models
        models = load_models(auto_download=auto_download)

    if isinstance(units_or_path, (str, os.PathLike)):
        with open(units_or_path, "r", encoding="utf-8") as f:
            records = json.load(f)
    else:
        records = list(units_or_path)
    if not records:
        return records

    qr, di, categories = predict_labels([r["comment_text"] for r in records],
                                        models, batch=batch)
    for rec, qr_v, di_v, cat in zip(records, qr, di, categories):
        rec["quantum_related"] = 1 if qr_v else 0
        rec["developer_intent"] = di_v
        rec["quantum_category"] = cat
    return records
