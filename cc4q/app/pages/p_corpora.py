"""Page — Corpora: corpus asset list, new-corpus flow, corpus detail view."""

import json
import os

import streamlit as st

import cc4q.workspace as ws
from cc4q.app import build_flow, corpus_view, data_io
from cc4q.app.ui import (asset_card_grid, empty_state, page_header,
                         section_divider, status_badge)

SOURCES = ("GitHub repository URL", "Local source directory",
           "Upload a corpus JSONL")
BUILTIN_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), "app", "data", "units")


def _seed_builtins():
    """Create read-only corpus assets for the six precomputed SDKs on first
    run; payload files referenced from the package data dir."""
    manifest = data_io.load_manifest()
    existing = {a.get("sdk") for a in ws.list_assets("corpus")
                if a.get("source") == "precomputed"}
    for sdk, info in sorted(manifest["repos"].items()):
        if sdk in existing:
            continue
        ws.create_asset(
            "corpus", name=f"{sdk} {info['version']}", source="precomputed",
            sdk=sdk, sccus=info["sccus"],
            quantum_pct=info["quantum_proportion"], labeled=True,
            builtin=True,
            files={"corpus": os.path.join(BUILTIN_DIR, f"{sdk}.jsonl")})


def _load_records(asset):
    return ws.read_jsonl(asset["files"]["corpus"])


def _open_asset(asset_id):
    st.session_state["corpus_open"] = asset_id
    st.rerun()


def _delete_asset(asset_id):
    ws.delete_asset(asset_id)
    if st.session_state.get("corpus_open") == asset_id:
        st.session_state["corpus_open"] = None
    st.rerun()


def _corpus_cards(assets):
    items = []
    for a in assets:
        actions = []
        if not a.get("builtin"):
            path = ws.export_asset(a["id"], st.session_state.setdefault(
                "_exp", os.path.join(ws.workspace_dir(), "exports")))
            with open(path, "rb") as f:
                actions.append({"label": "Download",
                                "download": {"data": f.read(),
                                             "file_name": f"{a['id']}.zip"}})
            actions.append({"label": "Rename",
                            "on_click": lambda aid=a["id"]:
                            st.session_state.update(
                                {"_rename": aid, "_rename_val": a["name"]})})
            actions.append({"label": "Delete",
                            "on_click": lambda aid=a["id"]: _delete_asset(aid)})
        actions.insert(0, {"label": "Open",
                           "on_click": lambda aid=a["id"]: _open_asset(aid)})
        qpct = a.get("quantum_pct")
        items.append({
            "title": a["name"],
            "badge": ("built-in", "quantum") if a.get("builtin")
                     else (a.get("source", "?"), "neutral"),
            "meta": [f"!{a.get('sccus', '?')} SCCUs",
                     f"quantum {qpct:.1%}" if qpct is not None
                     else "unlabeled",
                     a.get("created_at", "")],
            "actions": actions,
        })
    return items


def _new_corpus_flow():
    section_divider("New corpus")
    source = st.radio("Source", SOURCES, horizontal=True)
    records = None
    src_label = None
    if source == "GitHub repository URL":
        c1, c2 = st.columns([3, 1])
        url = c1.text_input("Repository URL",
                            placeholder="https://github.com/owner/repo")
        ref = c2.text_input("Ref (optional)", placeholder="tag / branch")
        if st.button("Clone and build", type="primary",
                     disabled=not url.strip()):
            bar = st.progress(0.0, text="cloning…")
            try:
                from cc4q.pipeline.files import get_files_from_dir
                import tempfile
                from cc4q.pipeline.download import clone_repo
                workdir = tempfile.mkdtemp(prefix="cc4q_guard_")
                entry = {"url": url.strip(), "ref": ref.strip() or None} \
                    if ref.strip() else url.strip()
                clone_repo(entry, workdir)
                name = url.strip().split("/")[-1].replace(".git", "")
                clone_path = os.path.join(workdir, name)
                n_py = len(get_files_from_dir(clone_path))
                if n_py > 200:
                    st.error(f"That repository has {n_py} Python files — "
                             "over the 200-file limit. Use `cc4q build` from "
                             "the CLI or Docker for large repositories.")
                    return
                records = build_flow.build_from_url(
                    url.strip(), ref.strip() or None,
                    progress=lambda f, m: bar.progress(min(f, 0.99),
                                                       text=m))
                src_label = "url"
            except Exception as exc:
                st.error(f"Build failed: {exc}")
                return
            finally:
                import shutil
                shutil.rmtree(workdir, ignore_errors=True)
            bar.progress(1.0, text="done")
    elif source == "Local source directory":
        path = st.text_input("Directory", placeholder="data/input/qiskit")
        if st.button("Build corpus", type="primary",
                     disabled=not path.strip()):
            try:
                records = build_flow.build_from_dir(path.strip())
                src_label = "dir"
            except Exception as exc:
                st.error(f"Build failed: {exc}")
    else:
        upload = st.file_uploader("Corpus JSONL (records with comment_text)",
                                  type=["jsonl", "json"])
        if upload is not None:
            text = upload.read().decode("utf-8")
            records = json.loads(text) if text.lstrip().startswith("[") \
                else [json.loads(l) for l in text.splitlines() if l.strip()]
            src_label = "upload"

    if records:
        name = st.text_input("Corpus name", value="my-corpus")
        if st.button("Save corpus", type="primary"):
            asset = ws.create_asset("corpus", name=name.strip() or "corpus",
                                    source=src_label, sccus=len(records),
                                    labeled=False, files={})
            corpus_path = ws.write_jsonl(asset["id"], "corpus.jsonl", records)
            ws.update_asset(asset["id"],
                            files={"corpus": corpus_path})
            st.session_state["_new_corpus"] = False
            st.success(f"Corpus **{asset['name']}** saved "
                       f"({len(records):,} SCCUs).")
            want_label = st.checkbox("Label it now with the default model "
                                     "(creates a labeled corpus asset)")
            if want_label:
                with st.spinner("Labeling…"):
                    labeled = corpus_view.predict_records(records)
                lpath = ws.write_jsonl(asset["id"], "labeled.jsonl", labeled)
                nq = sum(1 for r in labeled if r.get("quantum_related"))
                ws.update_asset(
                    asset["id"], labeled=True,
                    quantum_pct=round(nq / len(labeled), 4) if labeled else 0,
                    files={"corpus": corpus_path, "labeled": lpath})
                st.success(f"Labeled: {nq}/{len(labeled)} quantum units.")
            st.rerun()


def render():
    _seed_builtins()
    new = page_header(
        "Corpora",
        "Every corpus you build or upload is an asset — open it for the "
        "full dashboard, or fold it into annotations and evaluations.",
        action_label="New corpus")
    if new:
        st.session_state["_new_corpus"] = not st.session_state.get(
            "_new_corpus")
    if st.session_state.get("_new_corpus"):
        _new_corpus_flow()
        st.divider()

    open_id = st.session_state.get("corpus_open")
    if open_id:
        asset = ws.get_asset(open_id)
        records = _load_records(asset)
        if asset.get("labeled") and asset["files"].get("labeled"):
            records = ws.read_jsonl(asset["files"]["labeled"])
        stats = (corpus_view.builtin_stats(asset["sdk"])
                 if asset.get("builtin")
                 else corpus_view.workspace_stats(records))
        c1, c2 = st.columns([1, 5])
        if c1.button("← All corpora"):
            st.session_state["corpus_open"] = None
            st.rerun()
        corpus_view.render_corpus_detail(asset["name"], records, stats,
                                         read_only=asset.get("builtin", False))
        return

    assets = ws.list_assets("corpus")
    if not assets:
        if empty_state("No corpora yet",
                       "Analyze your first repository, or upload a corpus "
                       "file.", action_label="New corpus"):
            st.session_state["_new_corpus"] = True
            st.rerun()
        return
    asset_card_grid(_corpus_cards(assets), key_prefix="corpus")


render()
