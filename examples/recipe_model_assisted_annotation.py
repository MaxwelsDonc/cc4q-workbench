#!/usr/bin/env python3
"""Recipe 1 — model-assisted annotation, end to end.

The full CC4Q loop: build (extract + segment) -> predict (two-stage
quantum labels) -> sample (stratified) -> annotate (human spot-check,
blind or adjudicate) -> evaluate (agreement / precision / recall / Wilson CI).

Every step is also runnable standalone:

    python examples/recipe_model_assisted_annotation.py build \
        --source-dir examples/test_dir --output-dir /tmp/recipe
    python examples/recipe_model_assisted_annotation.py predict \
        --input /tmp/recipe/sccus.jsonl --output /tmp/recipe/labeled.jsonl
    python examples/recipe_model_assisted_annotation.py sample \
        --input /tmp/recipe/labeled.jsonl --by SDK --n 20 \
        --output /tmp/recipe/sample.jsonl
    python examples/recipe_model_assisted_annotation.py annotate \
        --input /tmp/recipe/sample.jsonl \
        --schema /tmp/recipe/schema.yaml --mode adjudicate \
        --predictions /tmp/recipe/labeled.jsonl --output-dir /tmp/recipe/ann
    python examples/recipe_model_assisted_annotation.py evaluate \
        --annotations /tmp/recipe/ann/annotations.csv \
        --key /tmp/recipe/key.jsonl --id-join id

`run-all` executes build -> predict -> sample with one command (annotate
launches the interactive UI unless --auto is given, which simulates the
human by confirming every model suggestion — a fixture for CI/demo only)
and writes ``key.jsonl`` (``id`` + ``model_label``) for the evaluate step.
`walk-spotcheck` replays the paper's 385-item spot-check through
predict -> sample -> annotate -> evaluate and asserts 85.0% agreement.
"""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_jsonl(path, records):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- build

def cmd_build(args):
    from cc4q.pipeline.extract import python_extract_comment_pairs
    from cc4q.pipeline.ids import id_generator
    from cc4q.pipeline.segment_pairs import segment_comment_pairs

    pairs_path = os.path.join(args.output_dir, "comment_pairs.json")
    seg_path = os.path.join(args.output_dir, "sccus.jsonl")
    os.makedirs(args.output_dir, exist_ok=True)

    import cc4q.pipeline.files as files_mod
    py_files = files_mod.get_files_from_dir(args.source_dir)
    if not py_files:
        raise SystemExit(f"no .py files under {args.source_dir}")
    records = []
    id_gen = id_generator()
    for path in py_files:
        with open(path, encoding="utf-8") as f:
            src = f.read()
        rel = os.path.relpath(path, args.source_dir)
        records.extend(python_extract_comment_pairs(
            source_code=src, rel_path=rel, sdk="recipe", id_gen=id_gen,
            version="recipe", host_language="python",
            clean_mode="current_only"))
    with open(pairs_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    raw_seg = os.path.join(args.output_dir, "sccus_tmp.json")
    n = segment_comment_pairs(pairs_path, raw_seg)
    with open(raw_seg, encoding="utf-8") as f:
        _write_jsonl(seg_path, json.load(f))
    os.remove(raw_seg)
    print(f"[build] {len(records)} CCPs -> {n} SCCUs -> {seg_path}")
    return seg_path


# ---------------------------------------------------------------- predict

def cmd_predict(args):
    from cc4q.models.hub import load_models
    from cc4q.predict import predict_corpus

    records = _read_jsonl(args.input)
    models = load_models() if args.models_dir is None \
        else load_models(model_dir=args.models_dir)
    labeled = predict_corpus(records, models=models, batch=args.batch)
    _write_jsonl(args.output, labeled)
    n_q = sum(1 for r in labeled if r["quantum_related"] == 1)
    print(f"[predict] {len(labeled)} SCCUs labeled, {n_q} quantum -> {args.output}")
    return args.output


# ---------------------------------------------------------------- sample

def cmd_sample(args):
    from cc4q.sample import sample

    records = _read_jsonl(args.input)
    quotas = json.loads(args.quotas) if args.quotas else None
    drawn = sample(records, by=args.by or None, n=args.n, frac=args.frac,
                   quotas=quotas, seed=args.seed)
    _write_jsonl(args.output, drawn)
    print(f"[sample] {len(drawn)} of {len(records)} records -> {args.output}")
    return args.output


# ---------------------------------------------------------------- annotate

def cmd_annotate(args):
    import cc4q.annotate as ann

    schema = None
    if args.schema:
        schema = args.schema
    else:
        schema = {"text_column": args.text_column, "id_column": args.id_column,
                  "labels": args.labels.split(",")}
    if args.auto:
        # fixture: simulate the human by confirming every model suggestion
        if isinstance(schema, str):
            import yaml
            with open(schema, encoding="utf-8") as f:
                schema = yaml.safe_load(f)
        records = _read_jsonl(args.input)
        preds = {str(r[schema["id_column"]]): str(r.get("quantum_category") or
                 ("quantum" if r.get("quantum_related") else "non-quantum"))
                 for r in _read_jsonl(args.predictions)} if args.predictions else {}
        os.makedirs(args.output_dir, exist_ok=True)
        rows = []
        for rec in records:
            row = dict(rec)
            row["label"] = preds.get(str(rec[schema["id_column"]]),
                                     args.labels.split(",")[0])
            rows.append(row)
        import pandas as pd
        pd.DataFrame(rows).to_csv(os.path.join(args.output_dir,
                                               "annotations.csv"),
                                  index=False, encoding="utf-8-sig")
        _write_jsonl(os.path.join(args.output_dir, "annotations.jsonl"), rows)
        print(f"[annotate --auto] {len(rows)} items 'annotated' (fixture)")
        return os.path.join(args.output_dir, "annotations.csv")
    ann.annotate(args.input, schema=schema, mode=args.mode,
                 model_predictions=args.predictions,
                 output_dir=args.output_dir)
    return os.path.join(args.output_dir, "annotations.csv")


# ---------------------------------------------------------------- evaluate

def cmd_evaluate(args):
    from cc4q.evaluate import evaluate_files

    contaminated = set(args.contaminated.split(",")) if args.contaminated else None
    res = evaluate_files(csv_path=args.annotations,
                         jsonl_path=(None if args.annotations.endswith(".csv")
                                     else args.annotations),
                         key_path=args.key, id_join=args.id_join,
                         contaminated=contaminated)
    print(f"[evaluate] n={res['n']} agreement={100 * res['agreement']:.1f}% "
          f"(95% CI {100 * res['wilson95'][0]:.1f}-"
          f"{100 * res['wilson95'][1]:.1f}) "
          f"precision={100 * res['precision']:.1f}% "
          f"recall={100 * res['recall']:.1f}%")
    return res


# ---------------------------------------------------------------- run-all

def cmd_run_all(args):
    seg = cmd_build(argparse.Namespace(source_dir=args.source_dir,
                                       output_dir=args.output_dir))
    labeled = cmd_predict(argparse.Namespace(input=seg, output=os.path.join(
        args.output_dir, "labeled.jsonl"), models_dir=None, batch=32))
    key = os.path.join(args.output_dir, "key.jsonl")
    _write_jsonl(key, [{"id": str(r["id"]),
                        "model_label": ("quantum" if r["quantum_related"] else
                                        "non-quantum")}
                       for r in _read_jsonl(labeled)])
    sample_out = cmd_sample(argparse.Namespace(
        input=labeled, by=["SDK"], n=args.n, frac=None, quotas=None,
        seed=42, output=os.path.join(args.output_dir, "sample.jsonl")))
    schema_path = os.path.join(args.output_dir, "schema.yaml")
    with open(schema_path, "w", encoding="utf-8") as f:
        f.write("text_column: comment_text\nid_column: id\n"
                "labels: [quantum, non-quantum]\n")
    if args.auto:
        cmd_annotate(argparse.Namespace(
            input=sample_out, schema=schema_path, mode="adjudicate",
            predictions=labeled, output_dir=os.path.join(args.output_dir, "ann"),
            auto=True, text_column="comment_text", id_column="id",
            labels="quantum,non-quantum"))
    else:
        print("[annotate] launching the interactive UI (Ctrl-C to stop)...")
        cmd_annotate(argparse.Namespace(
            input=sample_out, schema=schema_path, mode="adjudicate",
            predictions=labeled, output_dir=os.path.join(args.output_dir, "ann"),
            auto=False, text_column="comment_text", id_column="id",
            labels="quantum,non-quantum"))
    cmd_evaluate(argparse.Namespace(
        annotations=os.path.join(args.output_dir, "ann", "annotations.csv"),
        key=key, id_join="id", contaminated=None))


# ------------------------------------------------------------- spot-check

CONTAMINATED = {"1", "8", "16", "25", "62", "132"}


def cmd_walk_spotcheck(args):
    """Replay the paper's 385-item spot-check: predict -> sample ->
    annotate (real UI via AppTest; the human clicks the recorded label) ->
    evaluate. Asserts 85.0% agreement."""
    import csv
    import tempfile
    from streamlit.testing.v1 import AppTest

    from cc4q.annotate import APP_PATH, prepare
    from cc4q.models.hub import load_models
    from cc4q.predict import predict_corpus
    from cc4q.sample import sample as cc4q_sample

    exp_dir = os.path.join(ROOT, "exp")
    with open(os.path.join(exp_dir, "spotcheck_annotation.csv"),
              encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    key = {str(r["no"]): r["model_label"]
           for r in _read_jsonl(os.path.join(exp_dir,
                                             "spotcheck_answer_key.jsonl"))}

    # 1. corpus + 2. predict (pipeline-consistency check against the key;
    # the key is the released r2 labeling artifact under validation, and the
    # 85.0% figure is defined against it)
    corpus = [{"no": r["no"], "repo": r["repo"], "entity": r["entity"],
               "comment_text": r["comment_text"]} for r in rows]
    models = load_models()
    labeled = predict_corpus([dict(c) for c in corpus], models=models)
    mismatches = []
    for rec, c in zip(labeled, corpus):
        fresh = ("quantum" if rec["quantum_related"] else "non-quantum")
        if fresh != key[str(c["no"])]:
            mismatches.append(str(c["no"]))
    consistency = 1 - len(mismatches) / len(corpus)
    print(f"[walk] predict vs answer key: {consistency:.3f} consistent "
          f"({len(mismatches)} drifted: {', '.join(mismatches) or 'none'})")
    assert consistency >= 0.99, "predict diverges from the released key"

    # 3. sample (stratified by repo, take all 385 deterministically)
    drawn = cc4q_sample(corpus, by=["repo"], n=len(corpus), seed=42)
    assert len(drawn) == 385
    print(f"[walk] sampled {len(drawn)} items across {len({d['repo'] for d in drawn})} repos")

    # 4. annotate (adjudicate) — drive the real UI with the recorded labels
    workdir = tempfile.mkdtemp(prefix="cc4q_walk_")
    preds_path = os.path.join(workdir, "predictions.jsonl")
    _write_jsonl(preds_path, [{"no": k, "model_label": v}
                              for k, v in key.items()])
    config_path = prepare(drawn, schema={"text_column": "comment_text",
                                        "id_column": "no",
                                        "labels": ["quantum", "non-quantum"]},
                         mode="adjudicate", model_predictions=preds_path,
                         output_dir=workdir)
    os.environ["CC4Q_ANNOTATE_CONFIG"] = str(config_path)
    at = AppTest(APP_PATH, default_timeout=300)
    at.run()
    human = {str(r["no"]): r["human_label"] for r in rows}
    clicked = 0
    for i in range(len(drawn)):
        item_id = str(drawn[i]["no"])
        target = human[item_id]
        btn = next(b for b in at.button
                   if (b.label or "").replace("✓ ", "") == target)
        btn.click().run()
        clicked += 1
    state_path = os.path.join(workdir, "annotations.jsonl")
    done = _read_jsonl(state_path)
    print(f"[walk] annotate: clicked {clicked} labels, "
          f"{len(done)} persisted")

    # 5. evaluate
    from cc4q.evaluate import evaluate
    pairs = [(d["label"], key[str(d["no"])]) for d in done
             if str(d["no"]) not in CONTAMINATED]
    res = evaluate([h for h, _ in pairs], [m for _, m in pairs])
    print(f"[walk] n={res['n']} agreement={100 * res['agreement']:.1f}%")
    assert res["n"] == 379 and abs(res["agreement"] - 0.85) < 0.001
    print("WALK OK: spot-check pipeline reproduces 85.0% agreement")


# ---------------------------------------------------------------- main

def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="step", required=True)

    b = sub.add_parser("build", help="extract + segment a source dir")
    b.add_argument("--source-dir", required=True)
    b.add_argument("--output-dir", required=True)

    pr = sub.add_parser("predict", help="two-stage quantum labeling of SCCUs")
    pr.add_argument("--input", required=True)
    pr.add_argument("--output", required=True)
    pr.add_argument("--models-dir", default=None)
    pr.add_argument("--batch", type=int, default=32)

    s = sub.add_parser("sample", help="random / stratified / quota sampling")
    s.add_argument("--input", required=True)
    s.add_argument("--by", nargs="*", default=None)
    s.add_argument("--n", type=int, default=None)
    s.add_argument("--frac", type=float, default=None)
    s.add_argument("--quotas", default=None,
                   help='JSON dict, e.g. {"qiskit": 100}')
    s.add_argument("--seed", type=int, default=42)
    s.add_argument("--output", required=True)

    a = sub.add_parser("annotate", help="launch the annotation UI")
    a.add_argument("--input", required=True)
    a.add_argument("--schema", default=None)
    a.add_argument("--text-column", default="comment_text")
    a.add_argument("--id-column", default="id")
    a.add_argument("--labels", default="quantum,non-quantum")
    a.add_argument("--mode", default="blind",
                   choices=["blind", "adjudicate"])
    a.add_argument("--predictions", default=None)
    a.add_argument("--output-dir", required=True)
    a.add_argument("--auto", action="store_true",
                   help="fixture: confirm every suggestion without a UI")

    e = sub.add_parser("evaluate", help="human-vs-model agreement")
    e.add_argument("--annotations", required=True)
    e.add_argument("--key", required=True)
    e.add_argument("--id-join", default="no")
    e.add_argument("--contaminated", default=None,
                   help="comma-separated ids excluded from scoring")

    r = sub.add_parser("run-all", help="build -> predict -> sample -> annotate -> evaluate")
    r.add_argument("--source-dir", default=os.path.join(ROOT, "examples", "test_dir"))
    r.add_argument("--output-dir", default="/tmp/cc4q_recipe")
    r.add_argument("--n", type=int, default=20)
    r.add_argument("--auto", action="store_true")

    sub.add_parser("walk-spotcheck",
                   help="385-item spot-check regression (predict->sample->annotate->evaluate)")

    args = p.parse_args()
    fn = {"build": cmd_build, "predict": cmd_predict, "sample": cmd_sample,
          "annotate": cmd_annotate, "evaluate": cmd_evaluate,
          "run-all": cmd_run_all, "walk-spotcheck": cmd_walk_spotcheck}[args.step]
    fn(args)


if __name__ == "__main__":
    main()
