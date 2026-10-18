"""Human-vs-model and model-vs-model agreement evaluation.

Computes agreement, Cohen's kappa, precision, recall, F1, Wilson 95% CI,
and confusion breakdown.
"""

import csv
import json
import math
import os
from collections import Counter, defaultdict

__all__ = ["cohen_kappa", "evaluate", "evaluate_files", "wilson_ci"]


def wilson_ci(k, n, z=1.96):
    """Wilson score confidence interval for a binomial proportion.

    Args:
        k: Number of successes (agreements).
        n: Number of trials.
        z: Normal quantile; ``1.96`` gives a 95% interval.

    Returns:
        A ``(low, high)`` pair. For ``n == 0`` both bounds are ``nan``.
    """
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - half, center + half


def cohen_kappa(pairs):
    """Compute Cohen's kappa over aligned label pairs.

    Args:
        pairs: Iterable of ``(label_a, label_b)`` pairs.

    Returns:
        Cohen's kappa, or ``nan`` for no pairs and ``1.0`` when both raters
        used a single identical label (expected agreement is 1).
    """
    n = len(pairs)
    if n == 0:
        return float("nan")
    p_o = sum(1 for a, b in pairs if a == b) / n
    counts_a = Counter(a for a, _ in pairs)
    counts_b = Counter(b for _, b in pairs)
    labels = set(counts_a) | set(counts_b)
    p_e = sum((counts_a[lbl] / n) * (counts_b[lbl] / n) for lbl in labels)
    if abs(1.0 - p_e) < 1e-12:
        return 1.0
    return (p_o - p_e) / (1.0 - p_e)


def _as_pairs(human_labels, model_labels):
    if isinstance(human_labels, dict):
        ids = [i for i in human_labels if i in model_labels]
        return [(human_labels[i], model_labels[i]) for i in ids]
    return list(zip(human_labels, model_labels))


def evaluate(human_labels, model_labels):
    """Compare aligned human and model labels.

    Args:
        human_labels: A sequence of labels, or a mapping ``id -> label``.
        model_labels: A sequence aligned with ``human_labels``, or a
            mapping ``id -> label`` (only shared ids are compared).

    Returns:
        A dict with ``n``, ``agreement``, ``kappa``, ``precision``,
        ``recall``, ``f1``, ``wilson95`` (``(low, high)``), ``confusion``
        (``tp``/``fp``/``fn``/``tn``), ``labels``, and the raw ``pairs``.
        The positive class is ``"quantum"`` when present, otherwise the
        first sorted label. Metrics are ``nan`` when undefined.
    """
    pairs = _as_pairs(human_labels, model_labels)
    n = len(pairs)
    if n == 0:
        return {
            "n": 0,
            "agreement": float("nan"),
            "kappa": float("nan"),
            "precision": float("nan"),
            "recall": float("nan"),
            "f1": float("nan"),
            "wilson95": (float("nan"), float("nan")),
            "confusion": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
            "labels": [],
            "pairs": [],
        }

    model_labels_seen = sorted({m for _, m in pairs})
    positive = "quantum" if "quantum" in model_labels_seen else model_labels_seen[0]
    agree = sum(1 for h, m in pairs if h == m)
    tp = sum(1 for h, m in pairs if m == positive and h == positive)
    fp = sum(1 for h, m in pairs if m == positive and h != positive)
    fn = sum(1 for h, m in pairs if m != positive and h == positive)
    tn = sum(1 for h, m in pairs if m != positive and h != positive)
    prec = tp / (tp + fp) if (tp + fp) else float("nan")
    rec = tp / (tp + fn) if (tp + fn) else float("nan")
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) and not math.isnan(prec) and not math.isnan(rec) else float("nan")
    lo, hi = wilson_ci(agree, n)
    kappa = cohen_kappa(pairs)
    return {
        "n": n,
        "agreement": agree / n,
        "kappa": kappa,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "wilson95": (lo, hi),
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "labels": sorted({h for h, _ in pairs} | {m for _, m in pairs}),
        "pairs": pairs,
    }


def evaluate_files(
    csv_path=None,
    jsonl_path=None,
    key_path=None,
    id_join="no",
    contaminated=None,
    human_values=("quantum", "non-quantum"),
):
    """Evaluate a human spot-check export against a model answer key.

    The annotation file needs a human label column (``human_label`` by
    default), a join key (``id_join``), and optionally ``repo``,
    ``comment_type``, ``code_entity_type``, and ``comment_text`` fields.
    The key file is JSONL with the same join key and a ``model_label`` (or
    ``label``) field.

    Args:
        csv_path: Annotation CSV (preferred when it exists).
        jsonl_path: Annotation JSONL, used when ``csv_path`` is absent.
        key_path: Model answer-key JSONL. Required.
        id_join: Column used to join annotations and key (default ``"no"``).
        contaminated: Optional iterable of ids to exclude (for example
            units that appeared in training data).
        human_values: Accepted normalized human labels; other rows are
            counted as ``skipped``.

    Returns:
        The :func:`evaluate` result plus ``by_repo`` (per-repository
        metrics), ``disagreements``, ``skipped``, and ``excluded`` counts.

    Raises:
        ValueError: If ``key_path`` or an annotation path is missing, or
            the key is empty.
    """
    if key_path is None:
        raise ValueError("key_path (model answer key JSONL) is required")
    if csv_path is None and jsonl_path is None:
        raise ValueError("either csv_path or jsonl_path is required")

    if csv_path and os.path.exists(csv_path):
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            annotations = list(csv.DictReader(f))
    elif jsonl_path:
        with open(jsonl_path, encoding="utf-8") as f:
            annotations = [json.loads(l) for l in f if l.strip()]
    else:
        raise ValueError(
            f"annotation file not found: {csv_path or jsonl_path!r}"
        )

    with open(key_path, encoding="utf-8") as f:
        key_rows = [json.loads(l) for l in f if l.strip()]
    if not key_rows:
        raise ValueError(f"key file is empty: {key_path}")
    model_field = "model_label" if "model_label" in key_rows[0] else "label"
    key = {str(r[id_join]): r[model_field] for r in key_rows}

    contaminated = {str(c) for c in (contaminated or [])}
    pairs_by_repo = defaultdict(list)
    disagreements = []
    skipped = excluded = 0
    for r in annotations:
        h = str(r.get("human_label", "")).strip().lower()
        if h not in human_values:
            skipped += 1
            continue
        rid = str(r[id_join])
        if rid in contaminated:
            excluded += 1
            continue
        m = key[rid]
        repo = r.get("repo", "overall")
        pairs_by_repo[repo].append((h, m))
        if h != m:
            disagreements.append({
                "no": rid,
                "id": r.get("id", rid),
                "repo": repo,
                "comment_type": r.get("comment_type", ""),
                "code_entity_type": r.get("code_entity_type", ""),
                "comment_text": r.get("comment_text", ""),
                "human_label": h,
                "model_label": m,
            })

    all_pairs = [p for pairs in pairs_by_repo.values() for p in pairs]
    result = evaluate([h for h, _ in all_pairs], [m for _, m in all_pairs])
    result["by_repo"] = {
        repo: evaluate([h for h, _ in pairs], [m for _, m in pairs])
        for repo, pairs in sorted(pairs_by_repo.items())
    }
    result["disagreements"] = disagreements
    result["skipped"] = skipped
    result["excluded"] = excluded
    return result
