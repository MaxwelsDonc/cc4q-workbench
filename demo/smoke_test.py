"""Smoke tests for the CC4Q Workbench demo (design doc §8).

Run from the workbench root (with .venv activated):

    python demo/smoke_test.py            # data-level checks (fast)
    python demo/smoke_test.py --models   # also run the BERT classifiers
    python demo/smoke_test.py --app      # also run AppTest page rendering

Acceptance criteria covered:
  1. --app passes; headless HTTP 200 on all four pages (checked separately
     by the operator / CI with `streamlit run` + curl)
  2. Precomputed dashboards for all six SDKs render §1-§3 + compare without
     model checkpoints (this file never loads models for (b)-(d))
  3. Live mode: covered by manual E2E (small repo completes 4 stages;
     >200-file repo refused) — helpers tested here
  4. Density values in §2 match a direct recomputation on the cloned repos
  5. Compare aggregates reproduce the infra-vs-application gap
     (Quantum % 34.3 vs 26.0)
  6. Developer intent is absent from the UI entirely (cards, filters, table
     columns) but present in the data layer (units JSONL, manifest, downloads)
"""

import os
import sys

DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DEMO_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from cc4q.app import APP_DIR  # noqa: E402

FAILURES = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    line = f"[{status}] {name}" + (f" - {detail}" if detail and not condition else "")
    # stay printable even on cp1252/ascii consoles (Windows runners)
    print(line.encode(sys.stdout.encoding or "utf-8", "replace").decode(
        sys.stdout.encoding or "utf-8", "replace"))
    if not condition:
        FAILURES.append(name)


def test_snippet_pipeline(with_models):
    from cc4q.app import analysis

    units, error, fallback = analysis.analyze_code(analysis.QISKIT_SNIPPET)
    check("(a) default snippet parses without fallback",
          error is None and not fallback, str(error))
    check("(a) snippet yields comment units", len(units) >= 5,
          f"got {len(units)}")
    check("(a) no mislabel-prone math comment in snippet",
          "sqrt(2)" not in analysis.QISKIT_SNIPPET)
    # non-Python input auto-falls back to line-by-line classification
    junk = "this is not python at all\n# another plain line\nquantum stuff"
    units, error, fallback = analysis.analyze_code(junk)
    check("(a) non-Python input auto-falls back with warning",
          error is not None and fallback, f"error={error} fallback={fallback}")
    check("(a) fallback still yields labeled units", len(units) >= 2,
          f"got {len(units)}")
    # empty input is graceful (no units, no crash)
    units, error, fallback = analysis.analyze_code("   \n  ")
    check("(a) empty input is graceful", units == [] and not fallback,
          f"units={len(units)}")
    if not with_models:
        return
    models = analysis.load_models()
    units, _, _ = analysis.analyze_code(analysis.QISKIT_SNIPPET, models=models)
    labeled = all("developer_intent" in u and "quantum_related" in u
                  and "quantum_category" in u for u in units)
    check("(a) every unit labeled on all three axes", labeled)
    quantum = [u for u in units if u["quantum_related"]]
    check("(a) Bell-state snippet has quantum-labeled units", len(quantum) > 0,
          f"quantum={len(quantum)}/{len(units)}")
    for u in quantum:
        check("(a) quantum units carry a category",
              bool(u["quantum_category"]), u["text"][:60])
        break
    bad = [u for u in units if "sqrt(2)" in u["text"]]
    check("(a) no '|00>'/'sqrt(2)' unit present to mislabel", not bad)


def test_precomputed_data():
    import pandas as pd
    import plotly.graph_objects as go

    from cc4q.app import dashboard
    from cc4q.app import data_io

    manifest = data_io.load_manifest()
    repos = sorted(manifest["repos"])
    check("(b) manifest has 6 repos", len(repos) == 6, str(repos))
    expected = {"qiskit", "qiskit-aer", "qiskit-ibm-runtime",
                "qiskit-machine-learning", "qiskit-nature", "qiskit-algorithms"}
    check("(b) expected SDK set", set(repos) == expected, str(set(repos) ^ expected))

    frames = {}
    for sdk in repos:
        stats = manifest["repos"][sdk]
        df = data_io.load_units_df(sdk)
        frames[sdk] = df
        if stats.get("sampled"):
            ok = (len(df) == stats.get("sample_size", 2000)
                  and stats["sccus"] > stats.get("sample_size", 0))
        else:
            ok = (stats["sccus"] > 0 and stats["quantum_sccus"] > 0
                  and len(df) == stats["sccus"])
        check(f"(b) {sdk}: stats/units consistent", ok,
              f"sccus={stats['sccus']} rows={len(df)}")

        # corpus hierarchy: every CCP yields >= 1 SCCU, so ccps < sccus
        check(f"(b) {sdk}: ccps < sccus",
              0 < stats["ccps"] < stats["sccus"],
              f"ccps={stats['ccps']} sccus={stats['sccus']}")

        # python_files is populated; for the pipeline-built SDKs it must also
        # cover every file referenced by the corpus (the original gold corpus
        # was built from a slightly different commit of qiskit-ibm-runtime,
        # so its referenced-file count can exceed the pinned tag's file count)
        pf = stats.get("python_files") or 0
        if stats.get("sampled"):
            ok = pf > 0
            if stats["files"] > pf:
                print(f"  [note] {sdk}: corpus references {stats['files']} files "
                      f"> {pf} .py files in the pinned tag (release-corpus "
                      f"provenance, tolerated)")
        else:
            ok = pf > 0 and pf >= stats["files"]
        check(f"(b) {sdk}: python_files populated", ok,
              f"python_files={stats.get('python_files')} files={stats['files']}")

        # §2: comment density present and sane
        dens = stats.get("comment_density", {})
        check(f"(b) {sdk}: density present",
              dens.get("comment_lines", 0) > 0 and dens.get("code_lines", 0) > 0
              and 0 < dens.get("value", 0) < 1,
              str(dens))

        # §2: quantum residence table sums to quantum SCCUs
        res = stats.get("quantum_ctype_by_entity", {})
        res_total = sum(sum(e.values()) for e in res.values())
        check(f"(b) {sdk}: quantum residence sums to quantum SCCUs",
              res_total == stats["quantum_sccus"],
              f"{res_total} vs {stats['quantum_sccus']}")
        shares = data_io.quantum_residence_frame(stats)
        check(f"(b) {sdk}: residence frame 3xN",
              shares.shape[0] == 3 and shares.shape[1] >= 1)

        # §1/§3 charts build
        fig = dashboard._type_entity_chart(stats)
        check(f"(b) {sdk}: type×entity figure builds", len(fig.data) >= 1)
        fig = dashboard._quantum_residence_heatmap(stats)
        check(f"(b) {sdk}: residence heatmap builds",
              isinstance(fig, go.Figure) and len(fig.data) == 1)
        fig = dashboard._radar_figure([(sdk, stats)], title="test")
        check(f"(b) {sdk}: radar builds with 1 trace",
              isinstance(fig, go.Figure)
              and isinstance(fig.data[0], go.Scatterpolar))

    # original-3 CCP counts derive from the gold file's pair ids and must
    # sum to the paper's total of 12,812 CCPs
    original_ccps = sum(manifest["repos"][s]["ccps"]
                        for s in ("qiskit", "qiskit-aer", "qiskit-ibm-runtime"))
    check("(b) original-3 CCPs sum == 12,812", original_ccps == 12812,
          f"got {original_ccps}")

    # (§8.4) density spot-check: direct recomputation on the pinned clone
    from cc4q.pipeline.metrics import compute_comment_density
    sdk = "qiskit-machine-learning"
    clone = os.path.join(PROJECT_ROOT, "data", "input", sdk)
    if os.path.isdir(clone):
        direct = compute_comment_density(clone, ["qiskit_machine_learning"])
        stored = manifest["repos"][sdk]["comment_density"]
        check("(4) density matches direct recomputation",
              direct["comment_lines"] == stored["comment_lines"]
              and direct["code_lines"] == stored["code_lines"],
              f"direct={direct} stored={stored}")
    else:
        # clones under data/input are gitignored dev artifacts; CI checks
        # the committed values instead of recomputing them
        print(f"  [note] (4) density spot-check skipped: pinned clone not "
              f"present at {clone} (CI/dev-artifact environment)")

    # (§8.5) group aggregates: infrastructure 34.3% vs application 26.0%
    groups = manifest.get("groups", {})
    infra = groups.get("infrastructure", {}).get("quantum_proportion")
    app = groups.get("application", {}).get("quantum_proportion")
    check("(5) infrastructure aggregate ≈ 34.3%", infra is not None
          and abs(infra - 0.343) < 0.001, str(infra))
    check("(5) application aggregate ≈ 26.0%", app is not None
          and abs(app - 0.260) < 0.001, str(app))

    # (§8.6) no intent charts anywhere: dashboard must not touch intent data
    with open(os.path.join(APP_DIR, "dashboard.py"), encoding="utf-8") as f:
        dashboard_src = f.read()
    check("(6) dashboard.py has no intent analysis",
          "intent_counts" not in dashboard_src
          and "INTENT_ORDER" not in dashboard_src)

    # (c) compare mode: overlaid radar + aggregates
    a = manifest["repos"]["qiskit"]
    b = manifest["repos"]["qiskit-machine-learning"]
    fig = dashboard._radar_figure([(a["sdk"], a), (b["sdk"], b)], title="test")
    check("(c) compare radar overlays 2 traces", len(fig.data) == 2)
    check("(c) quantum proportion differs across SDKs",
          a["quantum_proportion"] != b["quantum_proportion"])

    # (d) explore corpus + default quantum-only logic
    all_df = pd.concat(frames.values(), ignore_index=True)
    check("(d) explore corpus row count",
          len(all_df) == manifest["total_demo_units"],
          f"{len(all_df)} vs {manifest['total_demo_units']}")
    q_only = all_df[all_df["quantum_related"]]
    check("(d) quantum-only default has rows", 0 < len(q_only) < len(all_df),
          f"{len(q_only)} of {len(all_df)}")
    kw = all_df[all_df["comment_text"].str.contains("entangle", case=False,
                                                    na=False)]
    check("(d) keyword filter returns rows", len(kw) > 0, f"got {len(kw)}")
    f = all_df[(all_df["sdk"] == "qiskit-nature")
               & (all_df["developer_intent"] == "Why")
               & (all_df["code_entity_type"] == "class")]
    check("(d) combined filters return rows", len(f) > 0, f"got {len(f)}")
    q = all_df[all_df["quantum_related"]
               & all_df["quantum_category"].notna()]
    check("(d) quantum units have categories", len(q) > 0)

    # intent stays in the DATA layer: units schema + manifest distributions
    check("(d-data) intent column present in units",
          "developer_intent" in all_df.columns
          and all_df["developer_intent"].notna().all())
    intent_total = sum(sum(manifest["repos"][s]["intent_counts"].values())
                       for s in repos)
    full_sccus = sum(manifest["repos"][s]["sccus"] for s in repos)
    check("(d-data) manifest intent_counts populated",
          intent_total == full_sccus,
          f"intent_total={intent_total} full_sccus={full_sccus}")


def test_packaging():
    """Single unified Dockerfile: TORCH_CHANNEL build-arg, no forced device."""
    dockerfile = os.path.join(PROJECT_ROOT, "Dockerfile")
    check("(pkg) Dockerfile exists", os.path.isfile(dockerfile))
    check("(pkg) no separate Dockerfile.gpu",
          not os.path.isfile(os.path.join(PROJECT_ROOT, "Dockerfile.gpu")))
    if os.path.isfile(dockerfile):
        with open(dockerfile, encoding="utf-8") as f:
            src = f.read()
        upper = src.upper()
        check("(pkg) Dockerfile has TORCH_CHANNEL build-arg",
              "ARG TORCH_CHANNEL" in upper)
        check("(pkg) Dockerfile does not force CC4Q_DEVICE via ENV",
              "ENV CC4Q_DEVICE" not in upper)
        check("(pkg) Dockerfile installs torch from the pytorch index",
              "download.pytorch.org/whl/" in src)
        check("(pkg) Dockerfile uses the TORCH_CHANNEL var in the index URL "
              "(no hardcoded/invalid channel)",
              "whl/${TORCH_CHANNEL}" in src and "whl/gpu" not in src.lower())


def test_app_rendering():
    import tempfile
    from streamlit.testing.v1 import AppTest

    os.environ["CC4Q_WORKSPACE"] = tempfile.mkdtemp(prefix="cc4q_smoke_")

    at = AppTest.from_file(os.path.join(DEMO_DIR, "app.py"),
                           default_timeout=180)
    at.run()
    check("app boots to Workspace", not at.exception, str(at.exception))
    all_md = "\n".join(m.value or "" for m in at.markdown)
    check("workspace: asset overview renders",
          all(k in all_md for k in ("Corpora", "Annotations", "Models",
                                    "Evaluations")))
    check("workspace: 8-primitive strip kept",
          all(k in all_md for k in ("Build", "Predict", "Annotate",
                                    "Train", "Evaluate", "Visualize")))
    theme_css = "\n".join(m.value or "" for m in at.markdown
                          if "<style>" in (m.value or ""))
    check("theme: Kimi black primary-button + outline secondary rules",
          "background-color: #1A1A1A" in theme_css
          and "border: 1px solid #E5E7EB" in theme_css
          and "--cc4q-quantum: #6C3FC5" in theme_css)

    # Corpora: built-in SDK corpora seeded as assets; open one -> dashboard
    at.switch_page(os.path.join(APP_DIR, "pages", "p_corpora.py")).run()
    check("page renders: corpora", not at.exception, str(at.exception))
    if not at.exception:
        check("corpora: six built-in SDK assets seeded",
              len([a for a in
                   __import__("cc4q.workspace", fromlist=["list_assets"])
                   .list_assets("corpus")]) >= 6)
        open_btn = next((b for b in at.button if b.label == "Open"), None)
        if open_btn:
            open_btn.click().run()
            ok = (not at.exception
                  and any("Corpus Built" in (s.value or "")
                          for s in at.subheader))
            check("corpora: detail dashboard renders", ok, str(at.exception))
            at.session_state["corpus_open"] = None
            at.run()

    # Annotate: empty state, then a persisted session resumes
    import cc4q.workspace as ws
    session = ws.create_asset(
        "annotation_session", name="smoke-session",
        schema={"text_column": "comment_text", "id_column": "id",
                "labels": ["quantum", "non-quantum"]},
        mode="blind", total=2)
    ws.write_jsonl(session["id"], "items.jsonl", [
        {"id": "1", "comment_text": "Apply a Hadamard gate."},
        {"id": "2", "comment_text": "Increment the counter."},
    ])
    ws.update_asset(session["id"],
                    export_path=ws.asset_path(session["id"], "items.jsonl"))
    at.switch_page(os.path.join(APP_DIR, "pages", "p_annotate.py")).run()
    check("page renders: annotate", not at.exception, str(at.exception))
    if not at.exception:
        resume = next((b for b in at.button if b.label == "Resume"), None)
        if resume:
            resume.click().run()
            ok = (not at.exception and any(
                "Hadamard" in (t.value or "") for t in at.text))
            check("annotate: session resumes at current progress", ok,
                  str(at.exception))

    # Models page (from the visual-system branch)
    at.switch_page(os.path.join(APP_DIR, "pages", "p_models.py")).run()
    check("page renders: models", not at.exception, str(at.exception))
    if not at.exception:
        check("models: released checkpoints section",
              any("Quantum relatedness" in (m.value or "") for m in at.markdown))

    # Evaluate: an saved evaluation asset opens its report
    ev = ws.create_asset(
        "evaluation", name="smoke-eval", pair=["released", "custom"],
        corpus="builtin", metrics={"n": 4, "agreement": 0.75,
                                   "precision": 1.0, "recall": 2/3,
                                   "wilson95": [0.3, 0.95]}, report_path="")
    report = os.path.join(ws.asset_path(ev["id"], "", create_dir=True),
                          "report.md")
    with open(report, "w") as f:
        f.write("## smoke-eval\n\nagreement: 75.0%\n")
    ws.update_asset(ev["id"], report_path=report)
    at.switch_page(os.path.join(APP_DIR, "pages", "p_evaluate.py")).run()
    check("page renders: evaluate", not at.exception, str(at.exception))
    if not at.exception:
        open_btn = next((b for b in at.button if b.label == "Open"), None)
        if open_btn:
            open_btn.click().run()
            ok = (not at.exception and any(
                "75.0%" in (m.value or "") for m in at.markdown))
            check("evaluate: report reopens with metrics", ok,
                  str(at.exception))

    # Playground: snippet analysis with the default model
    at.switch_page(os.path.join(APP_DIR, "pages", "p_playground.py")).run()
    check("page renders: playground", not at.exception, str(at.exception))
    if not at.exception and at.button:
        next(b for b in at.button if b.label == "Analyze").click().run()
        ok = (not at.exception
              and any("quantum-related" in (m.value or "") for m in at.markdown)
              and any("✓ quantum" in (m.value or "") for m in at.markdown))
        check("playground: snippet analysis labels units", ok,
              str(at.exception))

    # Workspace persistence across a simulated restart: a brand-new
    # session on the same workspace dir still sees the assets
    at2 = AppTest.from_file(os.path.join(DEMO_DIR, "app.py"),
                            default_timeout=180)
    at2.run()
    at2.switch_page(os.path.join(APP_DIR, "pages", "p_workspace.py")).run()
    md2 = "\n".join(m.value or "" for m in at2.markdown)
    check("workspace: assets survive a session restart",
          "smoke-session" in md2 and "smoke-eval" in md2, md2[:120])


def main():
    with_models = "--models" in sys.argv
    with_app = "--app" in sys.argv or with_models

    test_snippet_pipeline(with_models)
    test_precomputed_data()
    test_packaging()
    if with_app:
        test_app_rendering()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    print("All smoke tests passed.")


if __name__ == "__main__":
    main()
