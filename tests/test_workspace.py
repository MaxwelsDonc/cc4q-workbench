"""Workspace persistence layer tests (isolated via CC4Q_WORKSPACE)."""

import json
import os
import zipfile

import pytest

import cc4q.workspace as ws


@pytest.fixture()
def space(tmp_path, monkeypatch):
    root = tmp_path / "ws"
    monkeypatch.setenv("CC4Q_WORKSPACE", str(root))
    return str(root)


def _corpus(**over):
    fields = {"name": "qiskit-algorithms", "source": "url", "sccus": 3535,
              "labeled": True, "quantum_pct": 0.259,
              "files": {"corpus": "a.jsonl", "labeled": "b.jsonl"}}
    fields.update(over)
    return fields


# ------------------------------------------------------------ resolution

def test_dir_resolution_env(space):
    assert ws.workspace_dir() == space
    assert os.path.isdir(space)


def test_dir_resolution_checkout(monkeypatch, tmp_path):
    monkeypatch.delenv("CC4Q_WORKSPACE", raising=False)
    import cc4q.pipeline.paths as paths
    root = tmp_path / "checkout"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='x'")
    monkeypatch.setattr(paths, "REPO_ROOT", str(root))
    assert ws.workspace_dir() == os.path.join(str(root), ".cc4q_workspace")


def test_dir_resolution_wheel(monkeypatch, tmp_path):
    monkeypatch.delenv("CC4Q_WORKSPACE", raising=False)
    import cc4q.pipeline.paths as paths
    root = tmp_path / "sitepkgs"          # no pyproject.toml -> wheel path
    root.mkdir()
    monkeypatch.setattr(paths, "REPO_ROOT", str(root))
    monkeypatch.setattr(os.path, "expanduser",
                        lambda p: p.replace("~", str(tmp_path / "home")))
    assert ws.workspace_dir() == os.path.join(
        str(tmp_path / "home"), ".cache", "cc4q", "workspace")


# ------------------------------------------------------------------ CRUD

def test_create_and_get(space):
    a = ws.create_asset("corpus", **_corpus())
    assert a["id"] and len(a["id"]) == 8
    assert a["created_at"]
    got = ws.get_asset(a["id"])
    assert got["name"] == "qiskit-algorithms" and got["sccus"] == 3535


def test_create_requires_fields_and_valid_source(space):
    with pytest.raises(ValueError, match="required"):
        ws.create_asset("corpus", source="url")
    with pytest.raises(ValueError, match="source"):
        ws.create_asset("corpus", name="x", source="bogus")
    with pytest.raises(ValueError, match="unknown asset type"):
        ws.create_asset("model", name="x")


def test_list_assets_filter_and_order(space):
    a = ws.create_asset("corpus", **_corpus())
    s = ws.create_asset("annotation_session", name="round-1",
                        schema={"labels": ["a"]}, mode="blind")
    both = ws.list_assets()
    assert {x["id"] for x in both} == {a["id"], s["id"]}
    assert [x["id"] for x in ws.list_assets("corpus")] == [a["id"]]
    with pytest.raises(ValueError):
        ws.list_assets("nope")


def test_update_and_rename(space):
    a = ws.create_asset("corpus", **_corpus())
    ws.update_asset(a["id"], sccus=4000)
    assert ws.get_asset(a["id"])["sccus"] == 4000
    ws.rename_asset(a["id"], "renamed")
    assert ws.get_asset(a["id"])["name"] == "renamed"


def test_update_missing_raises(space):
    with pytest.raises(KeyError):
        ws.update_asset("deadbeef", name="x")


def test_session_gets_updated_at(space):
    s = ws.create_asset("annotation_session", name="r", schema={},
                        mode="blind")
    assert "updated_at" in s and s["labeled_count"] == 0
    s2 = ws.update_asset(s["id"], labeled_count=10)
    assert s2["labeled_count"] == 10


# ------------------------------------------------------- delete / export

def test_delete_removes_files(space):
    a = ws.create_asset("corpus", **_corpus())
    ws.write_jsonl(a["id"], "corpus.jsonl", [{"id": "1"}])
    fdir = os.path.join(space, "assets", "corpus", a["id"])
    assert os.path.isdir(fdir)
    ws.delete_asset(a["id"])
    assert ws.list_assets("corpus") == []
    assert not os.path.isdir(fdir)
    with pytest.raises(KeyError):
        ws.get_asset(a["id"])


def test_export_zip_roundtrip(space, tmp_path):
    a = ws.create_asset("corpus", **_corpus())
    ws.write_jsonl(a["id"], "labeled.jsonl", [{"id": "1-1", "label": 1}])
    dest = ws.export_asset(a["id"], str(tmp_path / "out"))
    assert dest.endswith(f"{a['id']}.zip")
    with zipfile.ZipFile(dest) as zf:
        names = zf.namelist()
        assert "labeled.jsonl" in names and "asset.json" in names
        manifest = json.loads(zf.read("asset.json"))
        assert manifest["id"] == a["id"]
        rows = [json.loads(l) for l in
                zf.read("labeled.jsonl").decode().splitlines()]
        assert rows == [{"id": "1-1", "label": 1}]


# ------------------------------------------------------ robustness paths

def test_corrupted_index_rebuilt(space, caplog):
    a = ws.create_asset("corpus", **_corpus())
    with open(os.path.join(space, "index.json"), "w") as f:
        f.write("{not json")
    with caplog.at_level("WARNING"):
        assets = ws.list_assets()
    assert assets == []                      # rebuilt empty
    assert os.path.isfile(os.path.join(space, "index.json.bak"))
    assert any("corrupted" in r.message for r in caplog.records)
    # index works again afterwards
    b = ws.create_asset("corpus", name="x", source="dir")
    assert ws.get_asset(b["id"])["name"] == "x"


def test_atomic_index_write(space):
    a = ws.create_asset("corpus", **_corpus())
    # no tmp files left behind; index is a single valid json
    leftovers = [f for f in os.listdir(space) if f.startswith(".index-")]
    assert leftovers == []
    with open(os.path.join(space, "index.json"), encoding="utf-8") as f:
        assert json.load(f)["assets"][0]["id"] == a["id"]


def test_persistence_across_calls(space):
    a = ws.create_asset("evaluation", name="cmp",
                        pair=["released", "abc"],
                        corpus="builtin-qiskit",
                        metrics={"n": 100, "agreement": 0.85,
                                 "precision": 0.8, "recall": 0.9,
                                 "wilson95": [0.8, 0.9]})
    # simulate a restart: a fresh read sees the same asset
    assert ws.get_asset(a["id"])["metrics"]["agreement"] == 0.85


# --------------------------------------------------------- model delegate

def test_model_delegation(monkeypatch, tmp_path):
    monkeypatch.setenv("CC4Q_WORKSPACE", str(tmp_path / "ws"))
    from cc4q.app import registry
    called = {}

    def fake_list(root=None):
        called["yes"] = True
        return [{"id": "m1", "name": "m"}]

    monkeypatch.setattr(registry, "list_models", fake_list)
    models = ws.list_models()
    assert called["yes"] and models[0]["id"] == "m1"
    # no model assets in the workspace index
    assert ws.list_assets() == [] or all(
        a["type"] != "model" for a in ws.list_assets())
