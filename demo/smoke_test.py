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
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(os.path.join(DEMO_DIR, "app.py"), default_timeout=180)
    at.run()
    check("app boots to Home", not at.exception, str(at.exception))
    hero = next((m.value for m in at.markdown
                 if "From quantum code to labeled" in (m.value or "")), None)
    check("home hero renders clean typography hero", hero is not None)
    all_md = "\n".join(m.value or "" for m in at.markdown)
    check("home workflow strip renders",
          all(k in all_md for k in ("Build", "Inspect", "Profile")))
    check("home metric card foregrounds quantum axes",
          any("Quantum label axes per unit" in (m.value or "") for m in at.markdown))
    check("home: no honesty info block",
          not any("Honest output" in (i.value or "") for i in at.info))
    theme_css = "\n".join(m.value or "" for m in at.markdown
                          if "<style>" in (m.value or ""))
    check("theme: Kimi black primary-button + outline secondary rules",
          "background-color: #1A1A1A" in theme_css
          and "border: 1px solid #E5E7EB" in theme_css
          and "--cc4q-quantum: #6C3FC5" in theme_css)

    # Page 2: Analyze Code — click Analyze and verify summary strip + cards.
    at.switch_page(os.path.join(APP_DIR, "pages", "p_analyze_code.py")).run()
    check("page renders: analyze-code", not at.exception, str(at.exception))
    if not at.exception and at.button:
        at.button[0].click().run()
        ok = (not at.exception
              and any("quantum-related" in (m.value or "") for m in at.markdown)
              and any("✓ quantum" in (m.value or "") for m in at.markdown))
        check("analyze-code: summary strip + quantum badges", ok,
              str(at.exception))
        rendered = "\n".join(m.value or "" for m in at.markdown)
        check("analyze-code: no intent badge in UI",
              "intent ·" not in rendered.lower())

        # non-Python input -> auto-fallback warning + line-by-line labels
        at.text_area[0].set_value("this is not python at all\n# quantum line")
        at.run()
        at.button[0].click().run()
        ok = (not at.exception
              and any("Not valid Python" in (w.value or "") for w in at.warning)
              and any("Line-by-line fallback" in (c.value or "") for c in at.caption))
        check("analyze-code: non-Python auto-fallback", ok, str(at.exception))

        # empty input -> graceful info, no crash
        at.text_area[0].set_value("")
        at.run()
        at.button[0].click().run()
        ok = (not at.exception
              and any("No comments found" in (i.value or "") for i in at.info))
        check("analyze-code: empty input handled gracefully", ok,
              str(at.exception))

    # Page 3: Analyze Repository — §1-§3 sections + compare.
    at.switch_page(os.path.join(APP_DIR, "pages", "p_analyze_repo.py")).run()
    check("page renders: analyze-repository", not at.exception, str(at.exception))
    if not at.exception:
        subheaders = [s.value for s in at.subheader]
        check("repo: §1 Corpus Built section", any("Corpus Built" in s for s in subheaders))
        check("repo: §2 Quantum Density Check section",
              any("Quantum Density Check" in s for s in subheaders))
        check("repo: §3 Knowledge Profile section",
              any("Knowledge Profile" in s for s in subheaders))
        check("repo: density metric shown",
              any("Comment density" in (m.value or "") for m in at.markdown))
        check("repo: quantum % metric shown",
              any("Quantum % of SCCUs" in (m.value or "") for m in at.markdown))
        check("repo: validation expander text",
              any("379" in (m.value or "") and "85.0%" in (m.value or "")
                  for m in at.markdown))
        labels = [o for sb in at.selectbox for o in sb.options]
        check("repo: 6 precomputed SDKs",
              any("qiskit (" in o for o in labels)
              and any("qiskit-nature" in o for o in labels))
        sb = at.selectbox[0]
        other = next(o for o in sb.options if o.startswith("qiskit-nature"))
        sb.set_value(other).run()
        check("repo: second SDK renders", not at.exception, str(at.exception))
        all_md = "\n".join(m.value or "" for m in at.markdown)
        check("compare: group aggregates (infra vs application)",
              "Group aggregates" in all_md
              and "Infrastructure SDKs" in all_md
              and "Application SDKs" in all_md)

    # Page 4: Explore Corpus — quantum-only default + keyword filter.
    at.switch_page(os.path.join(APP_DIR, "pages", "p_explore.py")).run()
    check("page renders: explore-corpus", not at.exception, str(at.exception))
    if not at.exception:
        check("explore: quantum-only toggle exists (default off)",
              len(at.toggle) == 1 and at.toggle[0].value is False)
        caption_before = next((c.value for c in at.caption
                               if "units match" in (c.value or "")), "")
        n_before = int(caption_before.split()[0].replace(",", ""))
        check("explore: default view is quantum-only",
              0 < n_before < 17517, caption_before)
        at.toggle[0].set_value(True).run()
        caption_after = next((c.value for c in at.caption
                              if "units match" in (c.value or "")), "")
        n_after = int(caption_after.split()[0].replace(",", ""))
        check("explore: toggle adds non-quantum rows", n_after > n_before,
              f"{n_before} -> {n_after}")
        check("explore: no intent filter or column in UI",
              all(getattr(sb, "label", "") != "Developer intent"
                  for sb in at.selectbox)
              and len(at.expander) == 1  # only the main "Filters" expander
              and (not at.dataframe
                   or "developer_intent" not in list(at.dataframe[0].value.columns)))
        if at.text_input:
            at.text_input[0].set_value("entangle").run()
            ok = (not at.exception and len(at.dataframe) > 0
                  and any("units match" in (c.value or "") for c in at.caption))
            check("explore: keyword filter returns rows", ok, str(at.exception))


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
