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

__all__ = [
    "CATEGORY_LIST",
    "CATEGORY_MAPPING",
    "analyze_snippet",
    "classify_units",
    "compact_snippet",
    "extract_units",
    "predict_corpus",
    "predict_labels",
    "predict_quantum_detailed",
    "predict_snippet",
    "raw_text_units",
]


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

    Task 1 (binary) runs on every text; Task 2 (six categories) runs only
    on texts classified as quantum-specific.

    Args:
        texts: Comment/unit strings to classify.
        models: A :class:`cc4q.models.hub.ModelHandle`.
        batch: Inference batch size.

    Returns:
        One dict per text with these keys:

        ``quantum_related``
            ``True`` when the unit is quantum-specific.
        ``quantum_confidence``
            Probability of the predicted binary class.
        ``quantum_prob``
            Probability that the unit is quantum-specific.
        ``quantum_category``
            Category name, or ``None`` for non-quantum units.
        ``category_confidence``
            Probability of the predicted category, or ``None``.
        ``category_probs``
            Mapping from category name to probability, or ``None``.
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
    """Run the quantum classifiers over raw texts.

    Args:
        texts: Comment/unit strings to classify.
        models: A :class:`cc4q.models.hub.ModelHandle`.
        batch: Inference batch size.

    Returns:
        A ``(quantum_related, quantum_category)`` pair of lists, where
        ``quantum_related`` contains booleans and ``quantum_category``
        contains category names or ``None`` for non-quantum units.
    """
    details = predict_quantum_detailed(texts, models, batch=batch)
    qr = [d["quantum_related"] for d in details]
    categories = [d["quantum_category"] for d in details]
    return qr, categories


def compact_snippet(code_snippet, comment_text, max_lines=32, max_chars=1200):
    """Extract a concise, readable window of code around a comment.

    Used by the Workbench API and the demo-data build so long function
    bodies do not overwhelm the UI/JSON payloads.

    Args:
        code_snippet: Full enclosing code context.
        comment_text: Comment text used to locate the interesting window.
        max_lines: Maximum number of lines to keep.
        max_chars: Maximum number of characters to keep.

    Returns:
        The trimmed snippet (with ``# ... [truncated] ...`` markers when
        content was removed), or an empty string for empty input.
    """
    if not code_snippet:
        return ""
    lines = code_snippet.splitlines()
    if len(lines) <= max_lines and len(code_snippet) <= max_chars:
        return code_snippet.strip()

    probe = (comment_text or "").strip()[:36]
    hit_idx = 0
    if probe:
        for i, line in enumerate(lines):
            if probe.lower() in line.lower():
                hit_idx = i
                break

    if hit_idx <= 12:
        selected = lines[:max_lines]
        if len(lines) > max_lines:
            selected.append("    # ... [truncated] ...")
    else:
        header = lines[:3]
        start = max(3, hit_idx - 6)
        end = min(len(lines), start + (max_lines - 5))
        selected = header + ["    # ..."] + lines[start:end]
        if end < len(lines):
            selected.append("    # ... [truncated] ...")

    out = "\n".join(selected).strip()
    if len(out) > max_chars:
        out = out[:max_chars].rsplit("\n", 1)[0] + "\n    # ... [truncated] ..."
    return out


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
    """Build SCCU-like units for non-Python input, line by line.

    This is the fallback used by :func:`analyze_snippet` when LibCST cannot
    parse the snippet: each non-empty line becomes one unit with
    ``comment_type="raw"``.

    Args:
        raw_text: Arbitrary text (source code, logs, prose, ...).

    Returns:
        A list of unit dictionaries with the same keys as regular SCCUs.
    """
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
    """Extract and segment a Python snippet into SCCU dictionaries.

    Args:
        source_code: Python source text.

    Returns:
        A ``(units, error)`` tuple. On parse failure, ``units`` is empty
        and ``error`` is a human-readable message; callers can fall back to
        :func:`raw_text_units`.
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
    """Label SCCU dictionaries in place with detailed quantum predictions.

    Args:
        units: Mutable unit dictionaries (uses ``text`` or ``comment_text``).
        models: A :class:`cc4q.models.hub.ModelHandle`.
        batch: Inference batch size.

    Returns:
        The same ``units`` list, with ``quantum_related``,
        ``quantum_confidence``, ``quantum_prob``, ``quantum_category``,
        ``category_confidence``, and ``category_probs`` set on each item.
    """
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
    """Run extract -> segment -> classify on a code snippet.

    Args:
        source_code: Python source text (or arbitrary text for fallback).
        models: Optional model handle. When ``None``, units are extracted
            and segmented but not classified.

    Returns:
        A ``(units, parse_error, fallback_used)`` tuple. ``parse_error`` is
        ``None`` on success; ``fallback_used`` is ``True`` when the input
        was processed line by line with :func:`raw_text_units`.
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
    """Analyze and label one code snippet.

    Args:
        code: Python source text.
        models: Optional model handle; loaded lazily when ``None``.
        auto_download: Download checkpoints when ``models`` is ``None`` and
            the released checkpoints are missing.

    Returns:
        The ``(units, parse_error, fallback_used)`` tuple from
        :func:`analyze_snippet`, with each unit labeled.
    """
    if models is None:
        from cc4q.models.hub import load_models
        models = load_models(auto_download=auto_download)
    return analyze_snippet(code, models=models)


def predict_corpus(units_or_path, models=None, batch=32, auto_download=True):
    """Label an SCCU corpus on both quantum axes.

    Args:
        units_or_path: A JSON file (list of records), a JSONL path, or an
            iterable of SCCU dictionaries. Records need a ``comment_text``
            or ``text`` field.
        models: Optional model handle; loaded lazily when ``None``.
        batch: Inference batch size.
        auto_download: Download checkpoints when ``models`` is ``None`` and
            the released checkpoints are missing.

    Returns:
        The labeled records. Each record gains ``quantum_related`` (0/1),
        ``quantum_prob``, ``quantum_category``, and
        ``category_confidence``. Records are labeled in place and the list
        is returned for convenience.
    """
    if models is None:
        from cc4q.models.hub import load_models
        models = load_models(auto_download=auto_download)

    if isinstance(units_or_path, (str, os.PathLike)):
        with open(units_or_path, "r", encoding="utf-8") as f:
            text = f.read()
        if text.lstrip().startswith("["):
            records = json.loads(text)
        else:
            records = [
                json.loads(line) for line in text.splitlines() if line.strip()
            ]
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
