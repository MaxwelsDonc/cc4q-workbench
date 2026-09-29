"""Smoke tests for the CC4Q Workbench demo.

Run from the workbench root (with .venv activated):

    python demo/smoke_test.py            # data-level checks (fast)
    python demo/smoke_test.py --models   # also run the BERT classifiers
    python demo/smoke_test.py --app      # also run AppTest page rendering

Checks:
  (a) Analyze Code pipeline produces clean labels on the default snippet
  (b) Precomputed repo dashboard data renders for all 6 repos
  (c) Compare-mode aggregation works
  (d) Explore filters return rows
"""

import os
import sys

DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DEMO_DIR)
for path in (DEMO_DIR, os.path.join(DEMO_DIR, "pages"), PROJECT_ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

FAILURES = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(name)


def test_snippet_pipeline(with_models):
    import cc4q_analysis as analysis

    units, error, fallback = analysis.analyze_code(analysis.QISKIT_SNIPPET)
    check("(a) default snippet parses without fallback",
          error is None and not fallback, str(error))
    check("(a) snippet yields comment units", len(units) >= 5,
          f"got {len(units)}")
    check("(a) no mislabel-prone math comment in snippet",
          "sqrt(2)" not in analysis.QISKIT_SNIPPET)
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
    import data_io

    manifest = data_io.load_manifest()
    repos = sorted(manifest["repos"])
    check("(b) manifest has 6 repos", len(repos) == 6, str(repos))
    expected = {"qiskit", "qiskit-aer", "qiskit-ibm-runtime",
                "qiskit-machine-learning", "qiskit-nature", "qiskit-algorithms"}
    check("(b) expected SDK set", set(repos) == expected, str(set(repos) ^ expected))

    import dashboard
    import pandas as pd
    import plotly.graph_objects as go

    frames = {}
    for sdk in repos:
        stats = manifest["repos"][sdk]
        df = data_io.load_units_df(sdk)
        frames[sdk] = df
        if stats.get("sampled"):
            ok = (len(df) == stats.get("sample_size", 2000)
                  and stats["sccus"] == stats["ccps"] > stats.get("sample_size", 0))
        else:
            ok = (stats["sccus"] > 0 and stats["quantum_sccus"] > 0
                  and len(df) == stats["sccus"])
        check(f"(b) {sdk}: stats/units consistent", ok,
              f"sccus={stats['sccus']} rows={len(df)}")
        ctype_entity = data_io.ctype_entity_frame(stats)
        check(f"(b) {sdk}: type×entity table non-empty", not ctype_entity.empty)
        intent_frame = data_io.distribution_frame([stats], "intent_counts",
                                                  data_io.INTENT_ORDER)
        fig = go.Figure()
        fig.add_bar(x=intent_frame.index, y=intent_frame[sdk])
        dashboard.plotly_layout(fig)
        check(f"(b) {sdk}: plotly figure builds", len(fig.data) == 1)

    # (c) compare mode
    a = manifest["repos"]["qiskit"]
    b = manifest["repos"]["qiskit-machine-learning"]
    pair = data_io.distribution_frame([a, b], "intent_counts",
                                      data_io.INTENT_ORDER)
    check("(c) compare frame has both SDKs",
          list(pair.columns) == ["qiskit", "qiskit-machine-learning"],
          str(list(pair.columns)))
    check("(c) quantum proportion differs across SDKs",
          a["quantum_proportion"] != b["quantum_proportion"])

    # (d) explore filters
    all_df = pd.concat(frames.values(), ignore_index=True)
    check("(d) explore corpus row count",
          len(all_df) == manifest["total_demo_units"],
          f"{len(all_df)} vs {manifest['total_demo_units']}")
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


def test_app_rendering():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(os.path.join(DEMO_DIR, "app.py"), default_timeout=180)
    at.run()
    check("app boots to Home", not at.exception, str(at.exception))
    hero = next((m.value for m in at.markdown
                 if "labeled comment corpus" in (m.value or "")), None)
    check("home hero renders", hero is not None)

    # Page 2: Analyze Code — click Analyze and verify labeled unit cards.
    at.switch_page("pages/p_analyze_code.py").run()
    check("page renders: analyze-code", not at.exception, str(at.exception))
    if not at.exception and at.button:
        at.button[0].click().run()
        ok = (not at.exception
              and any("Labeled units" in (m.value or "") for m in at.markdown)
              and any("✓ quantum" in (m.value or "") for m in at.markdown))
        check("analyze-code: Analyze labels default snippet", ok,
              str(at.exception))

    # Page 3: Analyze Repository — precomputed dashboard + compare mode.
    at.switch_page("pages/p_analyze_repo.py").run()
    check("page renders: analyze-repository", not at.exception, str(at.exception))
    if not at.exception:
        check("repo dashboard: metric cards",
              any("Quantum-related" in (m.value or "") for m in at.markdown))
        labels = [o for sb in at.selectbox for o in sb.options]
        check("repo dashboard: 6 precomputed SDKs",
              any("qiskit (" in o for o in labels)
              and any("qiskit-nature" in o for o in labels))
        # switch the precomputed SDK and re-render
        sb = at.selectbox[0]
        other = next(o for o in sb.options if o.startswith("qiskit-nature"))
        sb.set_value(other).run()
        check("repo dashboard: second SDK renders", not at.exception,
              str(at.exception))
        check("compare mode: side-by-side metrics",
              not at.exception
              and sum(1 for m in at.markdown
                      if "Quantum %" in (m.value or "")) == 2,
              "expected 2 compare metric cards")

    # Page 4: Explore Corpus — filters + paginated table.
    at.switch_page("pages/p_explore.py").run()
    check("page renders: explore-corpus", not at.exception, str(at.exception))
    if not at.exception:
        check("explore: dataframe renders", len(at.dataframe) > 0)
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
    if with_app:
        test_app_rendering()

    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
        sys.exit(1)
    print("All smoke tests passed.")


if __name__ == "__main__":
    main()
