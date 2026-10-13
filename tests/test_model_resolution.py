"""Model-default resolution tests: registry default beats released; single-axis
packages compose with released fallback (mocked loaders — no torch)."""

import json
import os

import pytest

import cc4q.app.model_select as ms


def _fake_package(root, name, axes):
    pkg = os.path.join(root, "_src", name)
    for axis in axes:
        d = os.path.join(pkg, axis)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "config.json"), "w") as f:
            json.dump({"num_labels": 2}, f)
    return pkg


def test_released_when_registry_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("CC4Q_USER_MODELS", str(tmp_path))
    seen = {}

    def fake_released(auto_download=True):
        seen["which"] = "released"
        return "HANDLE-RELEASED"

    monkeypatch.setattr(ms, "load_models", fake_released)
    assert ms.resolve_default_handle() == "HANDLE-RELEASED"
    assert seen["which"] == "released"


def test_registry_default_wins_and_composes(tmp_path, monkeypatch):
    monkeypatch.setenv("CC4Q_USER_MODELS", str(tmp_path))
    pkg = _fake_package(str(tmp_path), "m", axes=("quantum_related",))
    entry = ms.registry.register("m", pkg, root=str(tmp_path))
    monkeypatch.setattr(ms.registry, "registry_root", lambda: str(tmp_path))

    seen = {}

    def fake_from(axis_dirs, auto_download=True):
        seen["axis_dirs"] = axis_dirs
        return "HANDLE-COMPOSED"

    monkeypatch.setattr(ms, "load_models_from", fake_from)
    assert ms.resolve_default_handle() == "HANDLE-COMPOSED"
    assert set(seen["axis_dirs"]) == {"quantum_related"}


def test_non_default_entry_not_used(tmp_path, monkeypatch):
    monkeypatch.setenv("CC4Q_USER_MODELS", str(tmp_path))
    pkg = _fake_package(str(tmp_path), "m", axes=("quantum_related",))
    ms.registry.register("m", pkg, root=str(tmp_path))
    # not the default (another model holds the star)
    pkg2 = _fake_package(str(tmp_path), "n", axes=("developer_intent",))
    ms.registry.register("n", pkg2, root=str(tmp_path))
    ms.registry.set_default(
        ms.registry.list_models(root=str(tmp_path))[1]["id"],
        root=str(tmp_path))
    monkeypatch.setattr(ms.registry, "registry_root", lambda: str(tmp_path))

    seen = {}

    def fake_from(axis_dirs, auto_download=True):
        seen["axes"] = sorted(axis_dirs)
        return "HANDLE"

    monkeypatch.setattr(ms, "load_models_from", fake_from)
    ms.resolve_default_handle()
    assert seen["axes"] == ["developer_intent"]
