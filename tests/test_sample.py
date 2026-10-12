"""Sampling tests: random / stratified / quota, determinism, validation."""

import pytest

from cc4q.sample import sample


def _records():
    return [{"id": i, "sdk": ["qiskit", "aer", "nature"][i % 3],
             "label": i % 2} for i in range(90)]


def test_random_n():
    out = sample(_records(), n=30, seed=42)
    assert len(out) == 30
    assert len({r["id"] for r in out}) == 30  # no duplicates


def test_random_frac():
    out = sample(_records(), frac=0.1, seed=42)
    assert len(out) == 9


def test_stratified_covers_all_strata():
    out = sample(_records(), by=["sdk"], n=30, seed=42)
    sdks = {r["sdk"] for r in out}
    assert sdks == {"qiskit", "aer", "nature"}
    # proportional allocation: 10 per stratum over 90 records
    counts = {}
    for r in out:
        counts[r["sdk"]] = counts.get(r["sdk"], 0) + 1
    assert all(v == 10 for v in counts.values())


def test_stratified_by_two_columns():
    out = sample(_records(), by=["sdk", "label"], n=12, seed=7)
    keys = {f"{r['sdk']}|{r['label']}" for r in out}
    assert len(keys) == 6  # 3 sdks x 2 labels


def test_quotas():
    out = sample(_records(), by=["sdk"],
                 quotas={"qiskit": 5, "aer": 3}, seed=1)
    counts = {}
    for r in out:
        counts[r["sdk"]] = counts.get(r["sdk"], 0) + 1
    assert counts == {"qiskit": 5, "aer": 3}


def test_deterministic_with_seed():
    a = sample(_records(), by=["sdk"], n=30, seed=42)
    b = sample(_records(), by=["sdk"], n=30, seed=42)
    assert [r["id"] for r in a] == [r["id"] for r in b]
    c = sample(_records(), by=["sdk"], n=30, seed=43)
    assert [r["id"] for r in a] != [r["id"] for r in c]


def test_accepts_jsonl_path(tmp_path):
    import json
    path = tmp_path / "data.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in _records()),
                    encoding="utf-8")
    out = sample(str(path), n=10, seed=1)
    assert len(out) == 10


def test_validation():
    with pytest.raises(ValueError):
        sample(_records(), n=10, frac=0.5)
    with pytest.raises(ValueError):
        sample(_records())  # no size given
    with pytest.raises(ValueError):
        sample(_records(), quotas={"qiskit": 5})  # quotas need by
    assert sample([], n=5, seed=1) == []  # empty input is fine
