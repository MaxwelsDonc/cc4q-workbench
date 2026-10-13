"""Models page tests (AppTest): header component, released/your-models
sections, registry actions, and the train validation paths."""

import json
import os

import pytest
from streamlit.testing.v1 import AppTest

from cc4q.app import APP_DIR, registry

MODELS_PAGE = os.path.join(APP_DIR, "pages", "p_models.py")


def _fake_package(root, name, axes=("quantum_related",)):
    pkg = os.path.join(root, "_src", name)
    for axis in axes:
        d = os.path.join(pkg, axis)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "config.json"), "w") as f:
            json.dump({"num_labels": 2}, f)
    return pkg


@pytest.fixture
def reg(tmp_path, monkeypatch):
    monkeypatch.setenv("CC4Q_USER_MODELS", str(tmp_path))
    return str(tmp_path)


def _at():
    return AppTest.from_file(MODELS_PAGE, default_timeout=60)


def _open_train_panel(at):
    btn = next(b for b in at.button if b.label == "Train new model")
    btn.click().run()
    return at


def test_models_page_renders_empty_registry(reg):
    at = _at()
    at.run()
    assert not at.exception, str(at.exception)
    md = "\n".join(m.value or "" for m in at.markdown)
    # page header component
    assert "cc4q-page-head" in md
    assert "Released checkpoints and your fine-tuned classifiers" in md
    # released section: three read-only axis cards
    assert "cc4q-section" in md and "Released" in md
    for title in ("Quantum relatedness", "Quantum category",
                  "Developer intent"):
        assert title in md
    # no registry default -> released cards carry the Default badge
    assert "cc4q-badge quantum" in md and "Default" in md
    # empty state + primary CTA
    assert "No custom models yet" in md
    assert any(b.label == "Train new model" for b in at.button)


def test_models_page_lists_registry_cards(reg):
    pkg = _fake_package(reg, "m1",
                        axes=("quantum_related", "quantum_category"))
    registry.register("my-model", pkg, root=reg)
    at = _at()
    at.run()
    assert not at.exception, str(at.exception)
    md = "\n".join(m.value or "" for m in at.markdown)
    assert "my-model" in md
    assert "quantum related + quantum category" in md
    # first registered model is default; released cards fall back
    assert "★ Default" in md and "Fallback" in md
    labels = [b.label for b in at.button]
    assert "Delete" in labels and "★ Set as default" not in labels
    assert any(d.label == "⬇ Download zip" for d in at.download_button)


def _stash_and_pick(at, rows):
    """Stash annotation rows and point the data radio at them (the radio
    keeps its previous selection across runs, like a real session)."""
    at.session_state["train_stash"] = rows
    at.run()
    radio = next(r for r in at.radio if r.label == "Annotated data")
    radio.set_value("Stashed from the Annotate page").run()
    return at


def test_set_default_and_delete(reg):
    pkg1 = _fake_package(reg, "m1")
    pkg2 = _fake_package(reg, "m2")
    registry.register("first", pkg1, root=reg)
    registry.register("second", pkg2, root=reg)

    at = _at()
    at.run()
    star = next(b for b in at.button if b.label == "★ Set as default")
    star.click().run()
    flags = {e["id"]: e["is_default"]
             for e in registry.list_models(root=reg)}
    assert flags == {"first": False, "second": True}

    # delete the default entry ("second", grid row 1) — the registry must
    # re-resolve the default to the remaining model
    delete_second = next(b for b in at.button
                         if b.label == "Delete" and b.key.startswith("models_1_"))
    delete_second.click().run()
    remaining = registry.list_models(root=reg)
    assert [e["id"] for e in remaining] == ["first"]
    assert remaining[0]["is_default"]  # default re-resolves after delete


def test_train_validation_error_path(reg):
    at = _at()
    at.run()
    at = _open_train_panel(at)
    at = _stash_and_pick(at, [{"nothing": "usable"}])
    assert not at.exception, str(at.exception)
    assert any("need a text column" in (e.value or "") for e in at.error)
    # start is gated on a valid contract
    start = next(b for b in at.button if b.label == "Start training")
    assert start.disabled
    check = next(b for b in at.button if b.label == "Check data")
    check.click().run()
    assert any("does not honor the training contract"
               in (e.value or "") for e in at.error)


def test_check_data_dry_run_summary(reg):
    at = _at()
    at.run()
    at = _open_train_panel(at)
    at = _stash_and_pick(at, [
        {"comment_text": "build the bell circuit", "label": "quantum"},
        {"comment_text": "configure logging level", "label": "non-quantum"},
    ])
    assert not at.exception, str(at.exception)
    assert not at.error
    start = next(b for b in at.button if b.label == "Start training")
    assert not start.disabled
    check = next(b for b in at.button if b.label == "Check data")
    check.click().run()
    assert any("Data honors the training contract" in (s.value or "")
               for s in at.success)
    md = "\n".join(m.value or "" for m in at.markdown)
    assert "rows | 2" in md and "`quantum_related`" in md


def test_train_panel_warns_over_2000_rows(reg):
    at = _at()
    at.run()
    at = _open_train_panel(at)
    rows = [{"comment_text": f"comment {i}", "label": "quantum"}
            for i in range(2001)]
    at = _stash_and_pick(at, rows)
    assert not at.exception, str(at.exception)
    assert any("CLI (`cc4q train`) is recommended" in (w.value or "")
               for w in at.warning)


def test_annotation_export_pick(reg, tmp_path, monkeypatch):
    export = tmp_path / "annotations.jsonl"
    export.write_text(
        '\n'.join(json.dumps({"comment_text": f"c{i}", "label": 1})
                  for i in range(4)))
    monkeypatch.setenv("CC4Q_ANNOTATIONS", str(export))

    at = _at()
    at.run()
    at = _open_train_panel(at)
    radio = next(r for r in at.radio if r.label == "Annotated data")
    picked = next(o for o in radio.options
                  if o.startswith("Annotation export: "))
    assert str(export) in picked
    radio.set_value(picked).run()
    assert not at.exception, str(at.exception)
    assert any("4 annotated rows loaded" in (c.value or "")
               for c in at.caption)
    assert not at.error
