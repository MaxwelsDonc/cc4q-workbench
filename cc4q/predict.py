"""Snippet and corpus prediction with CC4Q quantum classifiers.

Focuses exclusively on Quantum-Specific analysis:
  1. Task 1 (Binary): ``quantum_related`` (Quantum-Specific vs. Non-Quantum)
  2. Task 2 (6-Class): ``quantum_category`` (Mathematics, Algorithms,
     Circuit model, Hardware, Software framework, Others)
"""

import json
import os

CATEGORY_MAPPING = {
    0: "Mathematics for quantum information",
    1: "Quantum algorithms",
    2: "Quantum circuit model",
    3: "Quantum hardware",
    4: "Quantum software framework",
    5: "Others",
}
CATEGORY_LIST = [CATEGORY_MAPPING[i] for i in range(6)]

MAX_LENGTH = 512


def _resolve_device():
    from cc4q.models.hub import resolve_device
    return resolve_device()


def _batch_predict_with_probs(tokenizer, model, texts, device, batch=32):
    """Run batch inference returning (pred_indices, max_probs, all_probs)."""
    import torch
    preds = []
    max_probs = []
    all_probs = []
    if not texts:
        return preds, max_probs, all_probs
    for i in range(0, len(texts), batch):
        inputs = tokenizer(texts[i:i + batch], return_tensors="pt",
                           padding=True, truncation=True, max_length=MAX_LENGTH)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.inference_mode():
            logits = model(**inputs).logits
            probs = torch.softmax(logits, dim=-1).cpu()
        top_p, top_idx = probs.max(dim=-1)
        preds.extend(top_idx.tolist())
        max_probs.extend([round(float(x), 4) for x in top_p.tolist()])
        all_probs.extend([[round(float(p), 4) for p in row] for row in probs.tolist()])
    return preds, max_probs, all_probs


def _batch_predict(tokenizer, model, texts, device, batch=32):
    preds, _, _ = _batch_predict_with_probs(tokenizer, model, texts, device, batch=batch)
    return preds


def predict_quantum_detailed(texts, models, batch=32):
    """Run the two-stage quantum classifiers with confidence scores.

    Returns a list of dicts per text:
      {
        "quantum_related": bool,
        "quantum_confidence": float,      # probability of predicted binary class
        "quantum_prob": float,            # probability of being quantum-specific
        "quantum_category": str | None,
        "category_confidence": float | None,
        "category_probs": dict[str, float] | None
      }
    """
    if not texts:
        return []
    device = getattr(models, "device", None) or _resolve_device()
    qr_tok, qr_model = models.quantum_related
    qc_tok, qc_model = models.quantum_category

    qr_preds, qr_conf, qr_probs = _batch_predict_with_probs(
        qr_tok, qr_model, texts, device, batch=batch
    )
    quantum_idx = [i for i, v in enumerate(qr_preds) if v == 1]

    cat_map = {}
    if quantum_idx:
        q_texts = [texts[i] for i in quantum_idx]
        c_preds, c_conf, c_probs = _batch_predict_with_probs(
            qc_tok, qc_model, q_texts, device, batch=batch
        )
        for idx, p, conf, row_probs in zip(quantum_idx, c_preds, c_conf, c_probs):
            cat_map[idx] = (
                CATEGORY_MAPPING[p],
                conf,
                {CATEGORY_MAPPING[k]: row_probs[k] for k in range(len(row_probs))},
            )

    results = []
    for i, (pred, conf, row_p) in enumerate(zip(qr_preds, qr_conf, qr_probs)):
        is_q = bool(pred == 1)
        q_prob = row_p[1] if len(row_p) > 1 else (conf if is_q else round(1.0 - conf, 4))
        if is_q and i in cat_map:
            cat_name, cat_conf, cat_probs = cat_map[i]
        else:
            cat_name, cat_conf, cat_probs = None, None, None
        results.append({
            "quantum_related": is_q,
            "quantum_confidence": conf,
            "quantum_prob": q_prob,
            "quantum_category": cat_name,
            "category_confidence": cat_conf,
            "category_probs": cat_probs,
        })
    return results


def predict_labels(texts, models, batch=32):
    """Run quantum classifiers over raw texts.

    Returns (quantum_related[bool], quantum_category[str|None]) per text.
    """
    details = predict_quantum_detailed(texts, models, batch=batch)
    qr = [d["quantum_related"] for d in details]
    categories = [d["quantum_category"] for d in details]
    return qr, categories


def _segment_record(record):
    """Split one CommentRecord into sentence-level comment units with full AST metadata."""
    from cc4q.pipeline.segment.block import segment_block_comment
    from cc4q.pipeline.segment.docstring import segment_docstring
    from cc4q.pipeline.segment.inline import segment_inline_comment

    text = record["comment_text"].strip()
    ctype = record["comment_type"]
    ccp_id = str(record.get("id", "1"))
    if ctype == "docstring":
        blocks = segment_docstring(text)
        units_with_type = [
            (b["content"].strip(), b.get("type", "paragraph"))
            for b in blocks if b.get("content", "").strip() and len(b["content"].strip()) >= 3
        ]
    elif ctype == "inline":
        units_with_type = [(u.strip(), "inline") for u in segment_inline_comment(text) if u.strip()]
    else:  # block
        units_with_type = [(u.strip(), "block") for u in segment_block_comment(text) if u.strip()]

    out = []
    for idx, (u_text, seg_type) in enumerate(units_with_type, 1):
        out.append({
            "id": f"{ccp_id}-{idx}",
            "ccp_id": ccp_id,
            "text": u_text,
            "comment_text": u_text,
            "comment_type": ctype,
            "segment_type": seg_type,
            "entity_type": record.get("code_entity_type", "—"),
            "code_entity_type": record.get("code_entity_type", "—"),
            "comment_line": record.get("comment_line") or [],
            "code_line": record.get("code_line") or [],
            "code_snippet": record.get("code_snippet", ""),
        })
    return out


def raw_text_units(raw_text):
    """Automatic fallback: classify non-parseable input line by line."""
    out = []
    for idx, line in enumerate(raw_text.splitlines(), 1):
        cleaned = line.strip().lstrip("#").strip()
        if cleaned:
            out.append({
                "id": f"raw-{idx}",
                "ccp_id": f"raw-{idx}",
                "text": cleaned,
                "comment_text": cleaned,
                "comment_type": "raw",
                "segment_type": "raw_line",
                "entity_type": "—",
                "code_entity_type": "—",
                "comment_line": [idx, idx],
                "code_line": [idx, idx],
                "code_snippet": line,
            })
    return out


def extract_units(source_code):
    """Extract + segment a Python snippet -> list of SCCU dicts.

    Returns (units, error).
    """
    from cc4q.pipeline.extract import python_extract_comment_pairs
    from cc4q.pipeline.ids import id_generator

    try:
        records = python_extract_comment_pairs(
            source_code=source_code, rel_path="snippet.py", sdk="live",
            id_gen=id_generator(), version="live",
            host_language="python", clean_mode="current_only")
    except Exception as exc:
        detail = f"{type(exc).__name__}: {str(exc).splitlines()[0][:300]}"
        return [], f"Could not parse the snippet as Python ({detail})."
    units = []
    for record in records:
        units.extend(_segment_record(record))
    return units, None


def classify_units(units, models, batch=32):
    """Label SCCU dicts (``text`` key) in place with detailed quantum predictions."""
    texts = [u.get("text") or u.get("comment_text", "") for u in units]
    details = predict_quantum_detailed(texts, models, batch=batch)
    for unit, det in zip(units, details):
        unit["quantum_related"] = det["quantum_related"]
        unit["quantum_confidence"] = det["quantum_confidence"]
        unit["quantum_prob"] = det["quantum_prob"]
        unit["quantum_category"] = det["quantum_category"]
        unit["category_confidence"] = det["category_confidence"]
        unit["category_probs"] = det["category_probs"]
    return units


def analyze_snippet(source_code, models=None):
    """Full pipeline on a code snippet: extract -> segment -> (classify).

    Returns (units, parse_error, fallback_used).
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
    """Labeled snippet analysis; loads the classifiers lazily when ``models`` is None."""
    if models is None:
        from cc4q.models.hub import load_models
        models = load_models(auto_download=auto_download)
    return analyze_snippet(code, models=models)


def predict_corpus(units_or_path, models=None, batch=32, auto_download=True):
    """Label an SCCU corpus (pipeline stage-03 records) on the Quantum axes."""
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

    details = predict_quantum_detailed(
        [r.get("comment_text") or r.get("text", "") for r in records],
        models, batch=batch
    )
    for rec, det in zip(records, details):
        rec["quantum_related"] = 1 if det["quantum_related"] else 0
        rec["quantum_prob"] = det["quantum_prob"]
        rec["quantum_category"] = det["quantum_category"]
        rec["category_confidence"] = det["category_confidence"]
    return records
