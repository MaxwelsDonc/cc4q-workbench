"""Human-vs-model agreement evaluation (generalizes exp/score_spotcheck.py).

``evaluate`` compares aligned human and model label sequences and returns
agreement / precision / recall plus a Wilson 95% CI; ``evaluate_files``
joins a spot-check annotation file (CSV or JSONL) with a model answer key
(JSONL), excluding calibration-contaminated ids by default.
"""

import csv
import json
import math
import os
from collections import defaultdict


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


def _as_pairs(human_labels, model_labels):
    if isinstance(human_labels, dict):  # id -> label mappings
        ids = [i for i in human_labels if i in model_labels]
        return [(human_labels[i], model_labels[i]) for i in ids]
    return list(zip(human_labels, model_labels))


def evaluate(human_labels, model_labels):
    """Compare aligned label sequences (or id->label dicts).

    The positive class is whichever label appears as the model's
    "quantum" prediction — pass the label set explicitly via the dict form
    if ambiguous. Returns a dict with n, agreement (fraction), precision,
    recall, wilson95 (lo, hi), per_label counts, and the raw pairs.
    """
    pairs = _as_pairs(human_labels, model_labels)
    n = len(pairs)
    if n == 0:
        return {"n": 0, "agreement": float("nan"), "precision": float("nan"),
                "recall": float("nan"), "wilson95": (float("nan"), float("nan")),
                "labels": [], "pairs": []}

    model_labels_seen = sorted({m for _, m in pairs})
    positive = "quantum" if "quantum" in model_labels_seen else model_labels_seen[0]
    agree = sum(1 for h, m in pairs if h == m)
    tp = sum(1 for h, m in pairs if m == positive and h == positive)
    fp = sum(1 for h, m in pairs if m == positive and h != positive)
    fn = sum(1 for h, m in pairs if m != positive and h == positive)
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec = tp / (tp + fn) if (tp + fn) else float("nan")
    lo, hi = wilson_ci(agree, n)
    return {
        "n": n,
        "agreement": agree / n,
        "precision": prec,
        "recall": rec,
        "wilson95": (lo, hi),
        "labels": sorted({h for h, _ in pairs} | {m for _, m in pairs}),
        "pairs": pairs,
    }


def evaluate_files(csv_path=None, jsonl_path=None, key_path=None,
                   id_join="no", contaminated=None,
                   human_values=("quantum", "non-quantum")):
    """Spot-check evaluation from files.

    Reads annotations from ``csv_path`` (preferred; needs a ``human_label``
    column) or ``jsonl_path``, joins with the model answer key (JSONL with
    ``id_join`` and a model-label column inferable from the data) on
    ``id_join``, skips rows whose human label is not in ``human_values``,
    and drops ids in ``contaminated``. Returns the :func:`evaluate` dict
    plus per-repo breakdown under "by_repo".
    """
    if key_path is None:
        raise ValueError("key_path (model answer key JSONL) is required")
    if csv_path is None and jsonl_path is None:
        raise ValueError("either csv_path or jsonl_path is required")

    if csv_path and os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            annotations = list(csv.DictReader(f))
    else:
        with open(jsonl_path, encoding="utf-8") as f:
            annotations = [json.loads(l) for l in f if l.strip()]

    with open(key_path, encoding="utf-8") as f:
        key_rows = [json.loads(l) for l in f if l.strip()]
    model_field = "model_label" if "model_label" in key_rows[0] else "label"
    key = {str(r[id_join]): r[model_field] for r in key_rows}

    contaminated = {str(c) for c in (contaminated or [])}
    pairs_by_repo = defaultdict(list)
    skipped = excluded = 0
    for r in annotations:
        h = str(r.get("human_label", "")).strip().lower()
        if h not in human_values:
            skipped += 1
            continue
        if str(r[id_join]) in contaminated:
            excluded += 1
            continue
        pairs_by_repo[r.get("repo", "overall")].append(
            (h, key[str(r[id_join])]))

    all_pairs = [p for pairs in pairs_by_repo.values() for p in pairs]
    result = evaluate([h for h, _ in all_pairs], [m for _, m in all_pairs])
    result["by_repo"] = {
        repo: evaluate([h for h, _ in pairs], [m for _, m in pairs])
        for repo, pairs in sorted(pairs_by_repo.items())
    }
    result["skipped"] = skipped
    result["excluded"] = excluded
    return result
