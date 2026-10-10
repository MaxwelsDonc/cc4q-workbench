"""Checkpoint-dependent tests: BERT classification + Streamlit page rendering.

Skipped automatically when models_checkpoints/ is absent (e.g. fresh CI
checkouts before `python scripts/download_models.py`); everything else in
tests/ runs without the ~1.2 GB checkpoints.
"""

import os

import pytest

import smoke_test

CKPT_DIR = os.path.join(smoke_test.PROJECT_ROOT, "models_checkpoints")
REQUIRED = ("quantum_related", "quantum_category", "developer_intent")

needs_checkpoints = pytest.mark.skipif(
    not all(os.path.isfile(os.path.join(CKPT_DIR, m, "model.safetensors"))
            for m in REQUIRED),
    reason="model checkpoints not present (run: python scripts/download_models.py)",
)


def _run_clean(fn):
    smoke_test.FAILURES.clear()
    try:
        fn()
        failures = list(smoke_test.FAILURES)
    finally:
        smoke_test.FAILURES.clear()
    assert not failures, f"smoke_test reported failures: {failures}"


@needs_checkpoints
def test_snippet_three_axis_classification():
    _run_clean(lambda: smoke_test.test_snippet_pipeline(True))


@needs_checkpoints
def test_streamlit_pages_renders():
    _run_clean(smoke_test.test_app_rendering)
