"""Corpus-building helpers for the Get Data page (clone/build/upload)."""

import json
import os
import shutil
import tempfile


def build_from_dir(source_dir, progress=None):
    """Extract + segment a local source directory; returns the SCCU records."""
    from cc4q.pipeline.extract import python_extract_comment_pairs
    from cc4q.pipeline.files import get_files_from_dir
    from cc4q.pipeline.ids import id_generator
    from cc4q.pipeline.segment_pairs import segment_comment_pairs

    py_files = get_files_from_dir(source_dir)
    if not py_files:
        raise ValueError(f"no .py files found under {source_dir}")
    records = []
    id_gen = id_generator()
    for i, path in enumerate(py_files):
        if progress:
            progress(i / len(py_files), f"extracting {os.path.basename(path)}")
        with open(path, encoding="utf-8") as f:
            src = f.read()
        records.extend(python_extract_comment_pairs(
            source_code=src, rel_path=os.path.relpath(path, source_dir),
            sdk=os.path.basename(os.path.abspath(source_dir)),
            id_gen=id_gen, version="local", host_language="python",
            clean_mode="current_only"))
    workdir = tempfile.mkdtemp(prefix="cc4q_getdata_")
    try:
        pairs_path = os.path.join(workdir, "pairs.json")
        with open(pairs_path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False)
        seg_path = os.path.join(workdir, "sccus.json")
        if progress:
            progress(0.95, "segmenting")
        segment_comment_pairs(pairs_path, seg_path)
        with open(seg_path, encoding="utf-8") as f:
            return json.load(f)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def build_from_url(url, ref=None, progress=None):
    """Clone a GitHub URL (shallow) and build its corpus."""
    import subprocess
    from cc4q.pipeline.download import clone_repo

    workdir = tempfile.mkdtemp(prefix="cc4q_clone_")
    try:
        entry = {"url": url, "ref": ref} if ref else url
        clone_repo(entry, workdir)
        name = url.strip().split("/")[-1].replace(".git", "")
        src = os.path.join(workdir, name)
        if not os.path.isdir(src):
            raise RuntimeError(f"clone did not produce {src}: "
                               + (subprocess.run(
                                   ["git", "clone", "--depth", "1", url,
                                    "/tmp/cc4q_diag"], capture_output=True,
                                   text=True).stderr or "")[:300])
        return build_from_dir(src, progress=progress)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
