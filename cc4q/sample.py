"""Sampling utilities for CC4Q corpora (any JSONL).

``sample`` supports three modes over any list of records (or a JSONL path):

- random:        ``sample(data, n=200)`` or ``frac=0.1``
- stratified:    ``sample(data, by=["sdk", "pred_label"], n=200)`` — ``n``
                 (or ``frac``) is allocated proportionally across strata
- quota:         ``sample(data, by=["sdk"], quotas={"qiskit": 100, ...})``
                 — explicit per-stratum sizes

Deterministic for a fixed ``seed``.
"""

import json
import random


def _load_records(data):
    if isinstance(data, (str, bytes, __import__("os").PathLike)):
        with open(data, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]
    return list(data)


def _stratum_key(record, by):
    if len(by) == 1:
        return str(record.get(by[0], ""))
    return "|".join(str(record.get(c, "")) for c in by)


def _group(records, by):
    groups = {}
    for rec in records:
        groups.setdefault(_stratum_key(rec, by), []).append(rec)
    return groups


def _take_size(pool_size, total_size, n, frac):
    if n is not None:
        return max(1, round(n * pool_size / total_size))
    return max(1, round(pool_size * frac))


def sample(data, by=None, n=None, frac=None, quotas=None, seed=42):
    """Sample records from ``data`` (JSONL path or list of dicts).

    Exactly one of ``n`` / ``frac`` applies per stratum (and globally in
    random mode). ``quotas`` maps stratum keys (see ``by``) to explicit
    sample sizes and requires ``by``. Returns a new list; input order is
    not preserved (strata are processed in sorted key order, records drawn
    without replacement via a seeded RNG).
    """
    records = _load_records(data)
    rng = random.Random(seed)

    if n is not None and frac is not None:
        raise ValueError("pass either n or frac, not both")
    if not records:
        return []
    if quotas is None and n is None and frac is None:
        raise ValueError("pass n, frac, or quotas")

    if quotas is not None:
        if not by:
            raise ValueError("quota sampling requires by=<columns>")
        groups = _group(records, by)
        out = []
        for key in sorted(quotas):
            pool = groups.get(key, [])
            k = min(int(quotas[key]), len(pool))
            out.extend(rng.sample(pool, k))
        return out

    if by:
        groups = _group(records, by)
        out = []
        for key in sorted(groups):
            pool = groups[key]
            take = _take_size(len(pool), len(records), n, frac)
            out.extend(rng.sample(pool, min(take, len(pool))))
        return out

    take = n if n is not None else max(1, round(len(records) * frac))
    return rng.sample(records, min(take, len(records)))
