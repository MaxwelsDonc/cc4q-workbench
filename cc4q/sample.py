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

__all__ = ["sample"]


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
    """Sample records from a corpus.

    Three modes are supported:

    * random: ``sample(data, n=200)`` or ``sample(data, frac=0.1)``.
    * stratified: ``sample(data, by=["SDK"], n=200)`` allocates ``n`` (or
      ``frac``) proportionally across strata.
    * quota: ``sample(data, by=["SDK"], quotas={"qiskit": 100, ...})``
      draws explicit per-stratum sizes.

    Args:
        data: JSONL path or iterable of record dicts.
        by: One or more columns used to form strata.
        n: Total sample size (proportional across strata when ``by`` is
            set). Mutually exclusive with ``frac``.
        frac: Fraction to sample (proportional across strata when ``by`` is
            set). Mutually exclusive with ``n``.
        quotas: Mapping from stratum key to sample size. Requires ``by``.
        seed: Random seed; sampling is deterministic for a fixed seed.

    Returns:
        A new list of sampled records. Input order is not preserved:
        strata are processed in sorted key order and records are drawn
        without replacement.

    Raises:
        ValueError: If both ``n`` and ``frac`` are given, if no sampling
            mode is specified, or if ``quotas`` is used without ``by``.
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
