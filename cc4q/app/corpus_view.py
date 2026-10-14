"""Shared corpus rendering: the three-section dashboard + filter table for
corpus assets (built-in SDK corpora and workspace corpora)."""

import pandas as pd
import streamlit as st

from cc4q.app import dashboard, data_io


def corpus_stats(records):
    """Manifest-entry-shaped stats over SCCU records (dashboard input)."""
    from collections import Counter
    n = len(records)
    nq = sum(1 for r in records if r.get("quantum_related"))
    # intent removed
    intent = {}
    cat = Counter(r["quantum_category"] for r in records
                  if r.get("quantum_related") and r.get("quantum_category"))
    ctype_entity, quantum_ctype = {}, {}
    for r in records:
        ct, ent = r.get("comment_type", ""), r.get("code_entity_type", "")
        ctype_entity.setdefault(ct, Counter())[ent] += 1
        if r.get("quantum_related"):
            quantum_ctype.setdefault(ct, Counter())[ent] += 1
    return {
        "sdk": "", "version": "", "source": "workspace",
        "files": len({r.get("file", "") for r in records}),
        "ccps": n, "sccus": n, "quantum_sccus": nq,
        "quantum_proportion": round(nq / n, 4) if n else 0.0,
        "comment_density": {"comment_lines": 0, "code_lines": 0,
                            "value": 0.0},
        "intent_counts": dict(intent),
        "category_counts": dict(cat),
        "ctype_by_entity": {c: dict(e) for c, e in ctype_entity.items()},
        "quantum_ctype_by_entity": {c: dict(e)
                                    for c, e in quantum_ctype.items()},
    }


def records_to_df(records):
    df = pd.DataFrame(records)
    if "quantum_related" in df.columns:
        df["quantum_related"] = df["quantum_related"].astype(bool)
    return df


def builtin_stats(sdk):
    return data_io.load_manifest()["repos"][sdk]


def workspace_stats(records):
    return corpus_stats(records)


def render_corpus_detail(name, records, stats, read_only=False):
    """Render §1–§3 dashboard + filter table + download for one corpus."""
    df = records_to_df(records)
    st.markdown(f"### {name}")
    dashboard.render_dashboard(stats, df)

    st.divider()
    st.subheader("Units")
    view = df
    if "quantum_related" in df.columns:
        only_q = st.toggle("Quantum units only", value=False,
                           key=f"q_only_{name}")
        if only_q:
            view = view[view["quantum_related"]]
    kw = st.text_input("Keyword filter", placeholder="e.g. entangle",
                       key=f"kw_{name}")
    if kw.strip() and "comment_text" in view.columns:
        view = view[view["comment_text"].str.contains(kw.strip(), case=False,
                                                      na=False)]
    st.caption(f"{len(view):,} units shown.")
    cols = [c for c in ("sdk", "file", "comment_type", "code_entity_type",
                        "comment_text", "quantum_related", "quantum_category")
            if c in view.columns]
    st.dataframe(view[cols].head(500), width="stretch", hide_index=True)
    if not read_only:
        st.download_button(
            "Download corpus (JSONL)",
            data="\n".join(
                __import__("json").dumps(r, ensure_ascii=False)
                for r in records),
            file_name=f"{name}.jsonl", mime="application/x-jsonlines",
            key=f"dl_{name}")


def predict_records(records, models=None, batch=64):
    """Label raw records with the default model; returns labeled records."""
    from cc4q.app.model_select import resolve_default_handle
    from cc4q.predict import predict_corpus
    models = models or resolve_default_handle()
    return predict_corpus([dict(r) for r in records], models=models,
                          batch=batch)
