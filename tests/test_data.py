"""Data-level checks.

Thin pytest wrappers around demo/smoke_test.py so the canonical `pytest`
entry point runs the same checks CI runs via `python demo/smoke_test.py`.
Checkpoint-independent: always runs.
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
    _run_clean(lambda: smoke_test.test_snippet_pipeline(False))


def test_precomputed_demo_data():
    _run_clean(smoke_test.test_precomputed_data)


def test_packaging():
    _run_clean(smoke_test.test_packaging)
