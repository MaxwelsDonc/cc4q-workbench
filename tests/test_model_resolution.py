"""Model-resolution tests for the web server: registry default beats
released; single-axis packages compose with released fallback (mocked
loaders — no torch). Two-stage axes only (quantum_related, quantum_category);
the retired developer_intent axis is rejected by the registry."""

import json
import os

import pytest

import cc4q.web.server as server


def _fake_package(root, name, axes):
    pkg = os.path.join(root, "_src", name)
    for axis in axes:
        d = os.path.join(pkg, axis)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "config.json"), "w") as f:
            json.dump({"num_labels": 2}, f)
    return pkg


@pytest.fixture
def clean_cache(monkeypatch):
    monkeypatch.setattr(server, "_MODEL_CACHE", {})
    return server._MODEL_CACHE


def test_released_when_registry_empty(tmp_path, monkeypatch, clean_cache):
    monkeypatch.setenv("CC4Q_USER_MODELS", str(tmp_path))
    seen = {}

    def fake_released(auto_download=True):
        seen["which"] = "released"
        return "HANDLE-RELEASED"

    monkeypatch.setattr(server, "load_models", fake_released)
    handle, model_id = server._resolve_model_handle("default")
    assert handle == "HANDLE-RELEASED"
    assert model_id == "released"
    assert seen["which"] == "released"


def test_registry_default_wins_and_composes(tmp_path, monkeypatch,
                                             clean_cache):
    monkeypatch.setenv("CC4Q_USER_MODELS", str(tmp_path))
    pkg = _fake_package(str(tmp_path), "m", axes=("quantum_related",))
    server.registry.register("m", pkg, root=str(tmp_path))
    monkeypatch.setattr(server.registry, "registry_root", lambda: str(tmp_path))

    seen = {}

    def fake_from(axis_dirs, auto_download=True):
        seen["axis_dirs"] = axis_dirs
        return "HANDLE-COMPOSED"

    monkeypatch.setattr(server, "load_models_from", fake_from)
    handle, model_id = server._resolve_model_handle("default")
    assert handle == "HANDLE-COMPOSED"
    assert model_id == "m"
    assert set(seen["axis_dirs"]) == {"quantum_related"}


def test_non_default_entry_not_used(tmp_path, monkeypatch, clean_cache):
    monkeypatch.setenv("CC4Q_USER_MODELS", str(tmp_path))
    pkg = _fake_package(str(tmp_path), "m", axes=("quantum_related",))
    server.registry.register("m", pkg, root=str(tmp_path))
    # not the default (another model holds the star)
    pkg2 = _fake_package(str(tmp_path), "n", axes=("quantum_category",))
    server.registry.register("n", pkg2, root=str(tmp_path))
    server.registry.set_default(
        server.registry.list_models(root=str(tmp_path))[1]["id"],
        root=str(tmp_path))
    monkeypatch.setattr(server.registry, "registry_root", lambda: str(tmp_path))

    seen = {}

    def fake_from(axis_dirs, auto_download=True):
        seen["axes"] = sorted(axis_dirs)
        return "HANDLE"

    monkeypatch.setattr(server, "load_models_from", fake_from)
    server._resolve_model_handle("default")
    assert seen["axes"] == ["quantum_category"]


def test_retired_intent_axis_rejected(tmp_path):
    """The developer_intent axis was removed in the two-stage taxonomy:
    packages carrying only it no longer register."""
    pkg = _fake_package(str(tmp_path), "legacy",
                        axes=("developer_intent",))
    with pytest.raises(ValueError, match="does not look like"):
        server.registry.register("legacy", pkg, root=str(tmp_path))
