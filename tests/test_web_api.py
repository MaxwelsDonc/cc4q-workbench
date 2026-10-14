"""Web-API smoke checks under pytest — drives demo/smoke_test.py check
functions against the in-process Starlette app (TestClient, throwaway
workspace). Checkpoint-dependent checks (live classification, evaluation)
self-skip without models_checkpoints/."""

import smoke_test


def _run(fn):
    smoke_test.FAILURES.clear()
    try:
        fn()
        failures = list(smoke_test.FAILURES)
    finally:
        smoke_test.FAILURES.clear()
    assert not failures, f"smoke checks failed: {failures}"


def test_index_and_static():
    _run(smoke_test.test_index_and_static)


def test_overview_numbers():
    _run(smoke_test.test_overview_numbers)


def test_corpus_units():
    _run(smoke_test.test_corpus_units)


def test_build_job_lifecycle():
    _run(smoke_test.test_build_job_lifecycle)


def test_annotation_lifecycle():
    _run(smoke_test.test_annotation_lifecycle)


def test_models_info_and_train_validation():
    _run(smoke_test.test_models_info_and_train_validation)


def test_spotcheck_agreement():
    _run(smoke_test.test_spotcheck_agreement)


def test_inspect_and_evaluate():
    _run(smoke_test.test_inspect_and_evaluate)
