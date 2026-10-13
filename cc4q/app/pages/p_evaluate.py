"""Page — Build step 4: Evaluate (compare two models on a shared corpus)."""

import json

import pandas as pd
import streamlit as st

from cc4q.app import model_select, registry, stepper
from cc4q.app import data_io

MAX_EVAL = 500


def _corpus_options():
    opts = []
    if st.session_state.get("build_labeled"):
        opts.append("Build corpus (labeled)")
    if st.session_state.get("build_corpus"):
        opts.append("Build corpus (unlabeled)")
    opts.append("Precomputed SDK sample")
    return opts


def _load_corpus(choice, sdk):
    if choice.startswith("Build corpus"):
        key = "build_labeled" if "labeled" in choice else "build_corpus"
        return [dict(r) for r in st.session_state[key]]
    df = data_io.load_units_df(sdk)
    return df.to_dict(orient="records")


def _model_choices():
    choices = [("released", "Released checkpoints")]
    for e in registry.list_models():
        choices.append((e["id"], f"{e['name']} ({', '.join(e['axes'])})"))
    return choices


def _handle(model_id):
    if model_id == "released":
        from cc4q.models.hub import load_models
        return load_models()
    from cc4q.models.hub import load_models_from
    entry = next(e for e in registry.list_models() if e["id"] == model_id)
    pkg = registry.package_dir(model_id)
    return load_models_from({a: f"{pkg}/{a}" for a in entry["axes"]})


def _axis_labels(handle, texts):
    from cc4q.predict import predict_labels
    qr, di, cat = predict_labels(texts, handle, batch=64)
    return qr, di, cat


def render():
    st.header("4 · Evaluate")
    st.write("Compare two models on the same corpus sample — how often they "
             "agree, and where their quantum-knowledge profiles differ.")

    if stepper.render_stepper(4):
        st.rerun()

    choices = _model_choices()
    trained_default = next(
        (e["id"] for e in registry.list_models()
         if e["source"] == "trained"), None)
    c1, c2 = st.columns(2)
    a = c1.selectbox(
        "Model A", range(len(choices)),
        format_func=lambda i: choices[i][1], index=0, key="eval_a")
    default_b = 0
    if trained_default:
        for i, (mid, _) in enumerate(choices):
            if mid == trained_default:
                default_b = i
                break
    b = c2.selectbox(
        "Model B", range(len(choices)),
        format_func=lambda i: choices[i][1], index=default_b, key="eval_b")
    if choices[a][0] == choices[b][0]:
        st.warning("Pick two different models.")

    c3, c4 = st.columns(2)
    corpus_choice = c3.selectbox("Corpus", _corpus_options())
    sdk = None
    if corpus_choice == "Precomputed SDK sample":
        sdk = c4.selectbox("SDK", sorted(data_io.load_manifest()["repos"]))

    if st.button("Run comparison", type="primary"):
        records = _load_corpus(corpus_choice, sdk)
        records = records[:MAX_EVAL]
        texts = [str(r["comment_text"]) for r in records]
        with st.spinner(f"Scoring {len(texts)} units with both models…"):
            try:
                ha, hb = _handle(choices[a][0]), _handle(choices[b][0])
                qa, dia, cata = _axis_labels(ha, texts)
                qb, dib, catb = _axis_labels(hb, texts)
            except Exception as exc:
                st.error(f"Comparison failed: {exc}")
                return

        from cc4q.evaluate import evaluate
        labels_a = ["quantum" if q else "non-quantum" for q in qa]
        labels_b = ["quantum" if q else "non-quantum" for q in qb]
        res = evaluate(labels_a, labels_b)
        st.subheader("Agreement")
        st.markdown(
            f"| metric | value |\n|---|---|\n"
            f"| units compared | {res['n']} |\n"
            f"| agreement | {res['agreement']:.1%} |\n"
            f"| precision (A vs B) | {res['precision']:.1%} |\n"
            f"| recall (A vs B) | {res['recall']:.1%} |\n"
            f"| Wilson 95% CI | {res['wilson95'][0]:.1%}–"
            f"{res['wilson95'][1]:.1%} |")

        st.subheader("Quantum-knowledge profiles")
        import plotly.graph_objects as go
        from cc4q.viz.charts import RADAR_LABELS, CATEGORY_ORDER

        def shares(cats):
            q = [c for c in cats if c]
            total = len(q) or 1
            counts = pd.Series(q).value_counts()
            return [counts.get(k, 0) / total for k in CATEGORY_ORDER]

        sa, sb = shares(cata), shares(catb)
        fig = go.Figure()
        for name, s, color in ((choices[a][1], sa, "#6C3FC5"),
                               (choices[b][1], sb, "#2ca02c")):
            fig.add_trace(go.Scatterpolar(
                r=s + s[:1], theta=RADAR_LABELS + RADAR_LABELS[:1],
                name=name, fill="toself", fillcolor=color + "2E",
                line=dict(color=color, width=2.5)))
        fig.update_layout(
            legend=dict(orientation="h", y=-0.12),
            margin=dict(l=60, r=60, t=30, b=30),
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#6B7280", size=12),
            polar=dict(bgcolor="rgba(0,0,0,0)",
                       radialaxis=dict(visible=True, tickformat=".0%",
                                       gridcolor="#ECECEF", range=[0, None]),
                       angularaxis=dict(gridcolor="#ECECEF")))
        st.plotly_chart(fig, width="stretch")
        st.session_state["build_eval"] = {
            "a": choices[a][1], "b": choices[b][1],
            "n": res["n"], "agreement": res["agreement"]}
        st.success("Evaluation complete — report stashed in the stepper "
                   "state.")


render()
