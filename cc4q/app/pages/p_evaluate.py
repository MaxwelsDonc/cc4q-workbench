"""Page — Evaluate: evaluation assets + new-evaluation wizard."""

import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import cc4q.workspace as ws
from cc4q.app import corpus_view, registry
from cc4q.app.ui import (asset_card_grid, empty_state, page_header,
                         section_divider)
from cc4q.viz.charts import CATEGORY_ORDER, RADAR_LABELS

MAX_EVAL = 500


def _model_choices():
    choices = [("released", "Released checkpoints")]
    for e in registry.list_models():
        choices.append((e["id"], f"{e['name']} ({', '.join(e['axes'])})"))
    return choices


def _handle(model_id):
    from cc4q.models.hub import load_models, load_models_from
    if model_id == "released":
        return load_models()
    entry = next(e for e in registry.list_models() if e["id"] == model_id)
    pkg = registry.package_dir(model_id)
    return load_models_from({a: f"{pkg}/{a}" for a in entry["axes"]})


def _shares(cats):
    q = [c for c in cats if c]
    total = len(q) or 1
    counts = pd.Series(q).value_counts()
    return [counts.get(k, 0) / total for k in CATEGORY_ORDER]


def _report_markdown(name, pair, metrics, corpus_name):
    lo, hi = metrics["wilson95"]
    return (f"## {name}\n\n"
            f"- **pair:** {pair[0]} vs {pair[1]}\n"
            f"- **corpus:** {corpus_name}\n"
            f"- **units compared:** {metrics['n']}\n"
            f"- **agreement:** {metrics['agreement']:.1%}\n"
            f"- **precision (A vs B):** {metrics['precision']:.1%}\n"
            f"- **recall (A vs B):** {metrics['recall']:.1%}\n"
            f"- **Wilson 95% CI:** {lo:.1%}–{hi:.1%}\n")


def _save_evaluation(name, pair, corpus_name, corpus_id, texts, ha, hb):
    from cc4q.evaluate import evaluate
    from cc4q.predict import predict_labels
    qa, _, cata = predict_labels(texts, ha, batch=64)
    qb, _, catb = predict_labels(texts, hb, batch=64)
    la = ["quantum" if q else "non-quantum" for q in qa]
    lb = ["quantum" if q else "non-quantum" for q in qb]
    res = evaluate(la, lb)
    metrics = {"n": res["n"], "agreement": res["agreement"],
               "precision": res["precision"], "recall": res["recall"],
               "wilson95": list(res["wilson95"])}
    asset = ws.create_asset("evaluation", name=name, pair=list(pair),
                            corpus=corpus_id, metrics=metrics,
                            report_path="")
    report = _report_markdown(name, pair, metrics, corpus_name)
    report_path = os.path.join(ws.asset_path(asset["id"], "",
                                             create_dir=True), "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    with open(ws.asset_path(asset["id"], "profiles.json"), "w",
              encoding="utf-8") as f:
        json.dump({"a": _shares(cata), "b": _shares(catb)}, f)
    ws.update_asset(asset["id"], report_path=report_path)
    return asset, metrics, report


def _wizard():
    section_divider("New evaluation")
    corpora = ws.list_assets("corpus")
    if not corpora:
        st.info("No corpus assets yet — create one on the Corpora page.")
        return
    choices = _model_choices()
    trained = next((e["id"] for e in registry.list_models()
                    if e["source"] == "trained"), None)
    c1, c2, c3 = st.columns(3)
    with c1:
        a = st.selectbox("Model A", range(len(choices)),
                         format_func=lambda i: choices[i][1], index=0)
    with c2:
        default_b = 0
        if trained:
            for i, (mid, _) in enumerate(choices):
                if mid == trained:
                    default_b = i
                    break
        b = st.selectbox("Model B", range(len(choices)),
                         format_func=lambda i: choices[i][1],
                         index=default_b)
    with c3:
        ci = st.selectbox("Corpus", range(len(corpora)),
                          format_func=lambda i: corpora[i]["name"])
    name = st.text_input("Evaluation name", value="released-vs-trained")
    if st.button("Run evaluation", type="primary"):
        asset = corpora[ci]
        records = ws.read_jsonl(asset["files"].get("labeled")
                                or asset["files"]["corpus"])[:MAX_EVAL]
        texts = [str(r["comment_text"]) for r in records]
        with st.spinner(f"Scoring {len(texts)} units with both models…"):
            try:
                saved, metrics, report = _save_evaluation(
                    name.strip() or "evaluation",
                    (choices[a][1], choices[b][1]), asset["name"],
                    asset["id"], texts, _handle(choices[a][0]),
                    _handle(choices[b][0]))
            except Exception as exc:
                st.error(f"Evaluation failed: {exc}")
                return
        st.session_state["eval_open"] = saved["id"]
        st.success("Evaluation saved.")
        st.rerun()


def _open_report(asset_id):
    st.session_state["eval_open"] = asset_id
    st.rerun()


def _delete(asset_id):
    ws.delete_asset(asset_id)
    if st.session_state.get("eval_open") == asset_id:
        st.session_state["eval_open"] = None
    st.rerun()


def _cards(evals):
    items = []
    for a in evals:
        m = a.get("metrics", {})
        actions = [
            {"label": "Open",
             "on_click": lambda aid=a["id"]: _open_report(aid)},
            {"label": "Delete",
             "on_click": lambda aid=a["id"]: _delete(aid)},
        ]
        items.append({
            "title": a["name"],
            "badge": ("evaluation", "neutral"),
            "meta": [f"!agreement {m.get('agreement', 0):.1%}",
                     " vs ".join(a.get("pair", []))[:60],
                     a.get("created_at", "")],
            "actions": actions,
        })
    return items


def render():
    page_header("Evaluate",
                "Compare two models on the same corpus — saved as "
                "resumable evaluation reports.")
    open_id = st.session_state.get("eval_open")
    if open_id:
        asset = ws.get_asset(open_id)
        m = asset["metrics"]
        st.markdown(f"### {asset['name']}")
        st.markdown(f"**pair:** {asset['pair'][0]} vs {asset['pair'][1]} · "
                    f"**corpus:** {asset.get('corpus', '?')}")
        st.markdown(
            f"| metric | value |\n|---|---|\n"
            f"| units compared | {m['n']} |\n"
            f"| agreement | {m['agreement']:.1%} |\n"
            f"| precision (A vs B) | {m['precision']:.1%} |\n"
            f"| recall (A vs B) | {m['recall']:.1%} |\n"
            f"| Wilson 95% CI | {m['wilson95'][0]:.1%}–"
            f"{m['wilson95'][1]:.1%} |")
        profiles_path = ws.asset_path(asset["id"], "profiles.json")
        if os.path.isfile(profiles_path):
            with open(profiles_path, encoding="utf-8") as f:
                prof = json.load(f)
            fig = go.Figure()
            for nm, s, color in ((asset["pair"][0], prof["a"], "#6C3FC5"),
                                 (asset["pair"][1], prof["b"], "#2ca02c")):
                fig.add_trace(go.Scatterpolar(
                    r=s + s[:1], theta=RADAR_LABELS + RADAR_LABELS[:1],
                    name=nm, fill="toself", fillcolor=color + "2E",
                    line=dict(color=color, width=2.5)))
            fig.update_layout(
                legend=dict(orientation="h", y=-0.12),
                margin=dict(l=60, r=60, t=30, b=30),
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#6B7280", size=12),
                polar=dict(bgcolor="rgba(0,0,0,0)",
                           radialaxis=dict(visible=True, tickformat=".0%",
                                           gridcolor="#ECECEF",
                                           range=[0, None]),
                           angularaxis=dict(gridcolor="#ECECEF")))
            st.plotly_chart(fig, width="stretch")
        if st.button("← All evaluations"):
            st.session_state["eval_open"] = None
            st.rerun()
        return

    if st.button("New evaluation", type="primary", key="eval_new"):
        st.session_state["eval_new"] = not st.session_state.get("eval_new")
    if st.session_state.get("eval_new"):
        _wizard()
        st.divider()

    evals = ws.list_assets("evaluation")
    if not evals:
        empty_state("No evaluations yet",
                    "Compare the released model against one you trained — "
                    "agreement, precision, recall, and a radar overlay.")
        return
    asset_card_grid(_cards(evals), key_prefix="eval")


render()
