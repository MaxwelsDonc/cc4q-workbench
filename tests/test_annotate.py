"""Annotation platform tests: schema validation, blind + adjudicate UI
drives via AppTest, persistence/resume, and an EXTERNAL JSONL (data the
sample/predict machinery never touched)."""

import json
import os

import pytest
from streamlit.testing.v1 import AppTest

from cc4q.annotate import APP_PATH, prepare

SCHEMA = {"text_column": "body", "id_column": "uid",
          "labels": ["bug", "docs", "other"]}

EXTERNAL = [  # arbitrary schema/content - nothing to do with CC4Q corpora
    {"uid": f"ext-{i}", "body": f"External review note number {i}",
     "source": "external-tool"} for i in range(4)
]


def _apptest(config_path):
    os.environ["CC4Q_ANNOTATE_CONFIG"] = str(config_path)
    return AppTest(APP_PATH, default_timeout=120)


def _run(tmp_path, records, mode, preds=None):
    args = prepare(records, schema=SCHEMA, mode=mode,
                   model_predictions=preds, output_dir=str(tmp_path))
    at = _apptest(args)
    at.run()
    return at


def test_prepare_validates_schema(tmp_path):
    with pytest.raises(ValueError, match="labels"):
        prepare(EXTERNAL, schema={"text_column": "body"},
                output_dir=str(tmp_path))
    with pytest.raises(ValueError, match="text_column"):
        prepare(EXTERNAL, schema={"labels": ["a"]},
                output_dir=str(tmp_path))


def test_blind_labeling_and_persistence(tmp_path):
    at = _run(tmp_path, EXTERNAL, "blind")
    assert not at.exception
    # label first two items
    for i in range(2):
        btn = next(b for b in at.button if b.label == "bug")
        btn.click().run()
    state = [json.loads(l) for l in
             open(tmp_path / "annotations.jsonl", encoding="utf-8")]
    assert [s["uid"] for s in state] == ["ext-0", "ext-1"]
    assert all(s["label"] == "bug" for s in state)
    # export buttons appear once something is labeled
    assert len(at.download_button) == 2


def test_resume_after_close(tmp_path):
    at = _run(tmp_path, EXTERNAL, "blind")
    next(b for b in at.button if b.label == "docs").click().run()
    # new session on the same output dir resumes (state on disk)
    at2 = _run(tmp_path, EXTERNAL, "blind")
    next(b for b in at2.button if b.label == "docs").click().run()
    state = [json.loads(l) for l in
             open(tmp_path / "annotations.jsonl", encoding="utf-8")]
    assert len(state) == 2  # appended, not overwritten


def test_adjudicate_suggestion_and_override(tmp_path):
    preds = [{"uid": "ext-0", "model_label": "docs"},
             {"uid": "ext-1", "model_label": "docs"}]
    at = _run(tmp_path, EXTERNAL, "adjudicate", preds=preds)
    # the suggested label is marked with a check
    labels = [(b.label or "") for b in at.button]
    assert "✓ docs" in labels
    # human overrides the suggestion with "bug"
    next(b for b in at.button if b.label == "bug").click().run()
    state = [json.loads(l) for l in
             open(tmp_path / "annotations.jsonl", encoding="utf-8")]
    assert state[0]["label"] == "bug"  # override recorded


def test_external_jsonl_end_to_end(tmp_path):
    """Standalone acceptance: annotate an arbitrary external JSONL."""
    data = tmp_path / "external.jsonl"
    data.write_text("\n".join(json.dumps(r) for r in EXTERNAL),
                    encoding="utf-8")
    args = prepare(str(data), schema=SCHEMA, mode="blind",
                   output_dir=str(tmp_path / "out"))
    at = _apptest(args)
    at.run()
    assert not at.exception
    for label in ["bug", "docs", "other", "bug"]:
        next(b for b in at.button if b.label == label).click().run()
    state = [json.loads(l) for l in
             open(tmp_path / "out" / "annotations.jsonl", encoding="utf-8")]
    assert [s["label"] for s in state] == ["bug", "docs", "other", "bug"]
