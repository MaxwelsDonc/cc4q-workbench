"""Data-level checks (checkpoint-independent, always runs).

Thin pytest wrappers around demo/smoke_test.py so the canonical `pytest`
entry point runs the same checks CI runs via `python demo/smoke_test.py`,
plus a model-free snippet-parse acceptance for the two-stage pipeline.
"""

import smoke_test


def _run_clean(fn):
    smoke_test.FAILURES.clear()
    try:
        fn()
        failures = list(smoke_test.FAILURES)
    finally:
        smoke_test.FAILURES.clear()
    assert not failures, f"smoke_test reported failures: {failures}"


def test_snippet_pipeline_parses_without_models():
    """Extraction + segmentation into SCCUs needs no checkpoints."""
    from cc4q.predict import extract_units
    code = ('def f():\n    """Construct the Bell-state quantum circuit."""\n'
            '    pass  # apply a Hadamard gate to the first qubit\n')
    units, err = extract_units(code)
    assert err is None and len(units) >= 2, f"err={err} units={len(units)}"
    assert all("comment_text" in u and "comment_type" in u for u in units)


def test_precomputed_demo_data():
    """The committed two-stage demo manifest: 6 SDKs, 39,593 SCCUs,
    weighted layer shares 34.3% / 26.0%, corpus units load."""
    _run_clean(smoke_test.test_overview_numbers)
    _run_clean(smoke_test.test_corpus_units)


def test_packaging():
    """The demo data ships inside the cc4q.web package (wheel-ready)."""
    import os
    from cc4q.web import DATA_DIR
    manifest = os.path.join(DATA_DIR, "manifest.json")
    assert os.path.isfile(manifest), f"missing {manifest}"
    units = os.path.join(DATA_DIR, "units")
    jsonls = [f for f in os.listdir(units) if f.endswith(".jsonl")]
    assert len(jsonls) == 6, f"expected 6 unit files, got {jsonls}"
