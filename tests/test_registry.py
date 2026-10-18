"""User model registry tests (tmp registry root via the CC4Q_USER_MODELS env
or explicit root argument)."""

import json
import os

import pytest

from cc4q import registry


def _fake_package(root, name, axes=("quantum_related",)):
    src_root = os.path.join(root, "_src")
    os.makedirs(src_root, exist_ok=True)
    pkg = os.path.join(src_root, name)
    for axis in axes:
        d = os.path.join(pkg, axis)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "config.json"), "w") as f:
            json.dump({"num_labels": 2}, f)
    return pkg


def test_register_list_default(tmp_path):
    pkg = _fake_package(str(tmp_path), "src_model")
    entry = registry.register("My model", pkg, root=str(tmp_path))
    assert entry["axes"] == ["quantum_related"]
    entries = registry.list_models(root=str(tmp_path))
    assert len(entries) == 1 and entries[0]["is_default"]

    pkg2 = _fake_package(str(tmp_path), "src_model2")
    entry2 = registry.register("My model", pkg2, root=str(tmp_path))
    assert entry2["id"] != entry["id"]  # deduped id
    registry.set_default(entry["id"], root=str(tmp_path))
    flags = {e["id"]: e["is_default"] for e in
             registry.list_models(root=str(tmp_path))}
    assert flags[entry["id"]] and not flags[entry2["id"]]


def test_register_rejects_non_model_dir(tmp_path):
    bad = os.path.join(str(tmp_path), "not_a_model")
    os.makedirs(bad)
    with pytest.raises(ValueError, match="does not look like"):
        registry.register("bad", bad, root=str(tmp_path))


def test_delete(tmp_path):
    pkg = _fake_package(str(tmp_path), "m")
    entry = registry.register("m", pkg, root=str(tmp_path))
    registry.delete(entry["id"], root=str(tmp_path))
    assert registry.list_models(root=str(tmp_path)) == []
    assert not os.path.isdir(registry.package_dir(entry["id"],
                                                  root=str(tmp_path)))


def test_zip_roundtrip(tmp_path):
    pkg = _fake_package(str(tmp_path), "m", axes=("quantum_related",
                                                  "quantum_category"))
    entry = registry.register("m", pkg, root=str(tmp_path))
    dest = str(tmp_path / "out.zip")
    registry.zip_package(entry["id"], dest, root=str(tmp_path))
    import zipfile
    with zipfile.ZipFile(dest) as zf:
        names = zf.namelist()
    assert any(n.startswith("quantum_related/") for n in names)
    assert any(n.startswith("quantum_category/") for n in names)


def test_register_uploaded_zip(tmp_path):
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("quantum_related/config.json", '{"num_labels": 2}')

    class Uploaded:
        name = "upload.zip"

        @staticmethod
        def getvalue():
            return buf.getvalue()

    entry = registry.register_uploaded_zip(
        Uploaded(), name="uploaded", root=str(tmp_path)
    )
    assert entry["axes"] == ["quantum_related"]
    saved = os.path.join(
        registry.package_dir(entry["id"], root=str(tmp_path)),
        "quantum_related",
        "config.json",
    )
    assert os.path.isfile(saved)


def test_register_uploaded_zip_rejects_traversal(tmp_path):
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../escape.txt", "nope")

    class Uploaded:
        name = "upload.zip"

        @staticmethod
        def getvalue():
            return buf.getvalue()

    with pytest.raises(ValueError, match="escapes"):
        registry.register_uploaded_zip(Uploaded(), root=str(tmp_path))
