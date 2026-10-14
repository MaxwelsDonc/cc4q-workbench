"""API-level smoke suite for the CC4Q Web Workbench (Starlette server).

Replaces the retired Streamlit AppTest suite. Boots the app in-process via
starlette's TestClient against a throwaway CC4Q_WORKSPACE and walks the same
surface a user touches in the SPA:

  * GET  /                        -> SPA index.html
  * GET  /api/overview            -> 6 SDKs, 39,593 SCCUs, layer aggregates
  * GET  /api/corpora/<id>/units  -> unit rows for the Corpus Explorer
  * POST /api/inspect             -> two-stage live classification   [models]
  * POST /api/pipeline/build      -> 4-stage build job lifecycle (local dir)
  * GET  /api/annotations, POST   -> session create / label / export / delete
  * POST /api/models/train        -> validation path (<12 rows rejected)
  * GET  /api/models              -> released-checkpoint registry info
  * POST /api/evaluations/run     -> model-vs-model agreement          [models]
  * spot-check                    -> seeded 379-unit session agrees 85.0%

Checks marked [models] need the released checkpoints (models_checkpoints/);
they are skipped automatically when absent, or forced with --models.

Runs standalone (``python demo/smoke_test.py [--models]``) and under pytest
(``tests/test_web_api.py`` drives the same check functions).
"""

import json
import os
import sys
import tempfile
import time

DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DEMO_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

FAILURES = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}"
          + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        FAILURES.append(f"{name}: {detail}")


# ---------------------------------------------------------------- client

_CLIENT = None


def get_client():
    """Shared TestClient on a fresh throwaway workspace."""
    global _CLIENT
    if _CLIENT is None:
        from starlette.testclient import TestClient
        from cc4q.web.server import app
        os.environ["CC4Q_WORKSPACE"] = tempfile.mkdtemp(prefix="cc4q_smoke_")
        os.environ.setdefault("CC4Q_SKIP_MODEL_DOWNLOAD", "1")
        _CLIENT = TestClient(app)
    return _CLIENT


def checkpoints_available():
    from cc4q.models.hub import default_model_dir, missing_checkpoints
    return not missing_checkpoints(default_model_dir())


# ---------------------------------------------------------------- checks

def test_index_and_static():
    c = get_client()
    r = c.get("/")
    check("index: SPA served", r.status_code == 200
          and "CC4Q Workbench" in r.text)
    r2 = c.get("/static/app.js")
    check("static: app.js served", r2.status_code == 200
          and len(r2.text) > 1000)


def test_overview_numbers():
    """The headline numbers the SPA renders: 6 SDKs, 39,593 SCCUs, and the
    SCCU-weighted quantum shares (34.3% infrastructure / 26.0% application)."""
    c = get_client()
    d = c.get("/api/overview").json()
    repos = d["manifest"]["repos"]
    check("overview: six SDK corpora", len(repos) == 6,
          f"got {len(repos)}")
    total = sum(info["sccus"] for info in repos.values())
    check("overview: 39,593 SCCUs", total == 39593, f"got {total}")

    def weighted(layer):
        num = sum(i["sccus"] * i["quantum_proportion"]
                  for i in repos.values() if i["layer"] == layer)
        den = sum(i["sccus"] for i in repos.values() if i["layer"] == layer)
        return num / den if den else 0.0

    infra, app_ = weighted("infrastructure"), weighted("application")
    check("overview: infrastructure layer 34.3%",
          round(infra * 100, 1) == 34.3, f"got {infra * 100:.1f}%")
    check("overview: application layer 26.0%",
          round(app_ * 100, 1) == 26.0, f"got {app_ * 100:.1f}%")
    corpora = d["corpora"]
    check("overview: 6 built-in corpus assets seeded",
          sum(1 for a in corpora if a.get("builtin")) == 6)
    check("overview: model registry reports two released tasks",
          len(d["models"]["released"]) == 2)
    check("overview: taxonomy is two-stage (no developer_intent)",
          "developer_intent" not in json.dumps(d["taxonomy"]))


def test_corpus_units():
    c = get_client()
    d = c.get("/api/overview").json()
    nid = next(a["id"] for a in d["corpora"] if a.get("sdk") == "qiskit-nature")
    units = c.get(f"/api/corpora/{nid}/units").json()
    rows = units.get("units") or units.get("records") or []
    check("corpus units: qiskit-nature rows returned", len(rows) > 0)
    if rows:
        r0 = rows[0]
        check("corpus units: two-stage fields present",
              "quantum_related" in r0 and "quantum_category" in r0)
        check("corpus units: no developer_intent field",
              "developer_intent" not in r0)
    dl = c.get(f"/api/corpora/{nid}/download")
    check("corpus download: JSONL attachment", dl.status_code == 200
          and len(dl.text) > 0)


def test_build_job_lifecycle():
    """Local-directory build (no Stage-4 labeling -> fast, model-free)."""
    c = get_client()
    target = os.path.join(PROJECT_ROOT, "examples", "tiny_repo")
    r = c.post("/api/pipeline/build", json={
        "source_type": "dir", "target": target,
        "name": "tiny-quantum-demo", "run_predict": False,
    })
    check("build: job accepted", r.status_code == 200, r.text)
    job_id = r.json()["job_id"]
    final = None
    for _ in range(75):
        final = c.get(f"/api/pipeline/jobs/{job_id}").json()
        if final["status"] in ("completed", "done", "failed", "error"):
            break
        time.sleep(0.4)
    check("build: job completes", final["status"] in ("completed", "done"),
          f"status={final.get('status')} error={final.get('error')}")
    if final["status"] in ("completed", "done"):
        d = c.get("/api/overview").json()
        custom = [a for a in d["corpora"] if not a.get("builtin")]
        check("build: corpus asset registered", len(custom) >= 1)
        if custom:
            units = c.get(f"/api/corpora/{custom[0]['id']}/units").json()
            rows = units.get("units") or units.get("records") or []
            check("build: built corpus has SCCU units", len(rows) > 0,
                  f"got {len(rows)}")


def test_annotation_lifecycle():
    c = get_client()
    d = c.get("/api/overview").json()
    cid = next(a["id"] for a in d["corpora"]
               if a.get("sdk") == "qiskit-algorithms")
    r = c.post("/api/annotations", json={
        "name": "smoke-session", "corpus_id": cid,
        "sample_size": 8, "mode": "blind", "seed": 7,
    })
    check("annotation: session created", r.status_code == 200, r.text)
    sid = r.json()["session"]["id"]
    try:
        det = c.get(f"/api/annotations/{sid}").json()
        check("annotation: items sampled", len(det["items"]) == 8,
              f"got {len(det.get('items', []))}")

        r1 = c.post(f"/api/annotations/{sid}/label",
                    json={"index": 0, "human_quantum_related": True,
                          "human_quantum_category": "Quantum circuit model"})
        r2 = c.post(f"/api/annotations/{sid}/label",
                    json={"index": 1, "human_quantum_related": False})
        check("annotation: labels recorded",
              r1.status_code == 200 and r2.status_code == 200)
        m = c.get(f"/api/annotations/{sid}").json()["metrics"]
        check("annotation: metrics count 2 labeled",
              m["labeled_count"] == 2, f"got {m.get('labeled_count')}")
        check("annotation: agreement computed",
              m["agreement"] is not None and 0.0 <= m["agreement"] <= 1.0)

        exp = c.get(f"/api/annotations/{sid}/export")
        rows = [json.loads(l) for l in exp.text.splitlines() if l.strip()]
        check("annotation: full export has 2 rows", len(rows) == 2)
        exp_t = c.get(f"/api/annotations/{sid}/export",
                      params={"task": "quantum_related"})
        train_rows = [json.loads(l) for l in exp_t.text.splitlines()
                      if l.strip()]
        # canonical training rows: {text, label:int} for every labeled item
        check("annotation: quantum_related train export",
              len(train_rows) == 2
              and all(isinstance(r.get("label"), int) for r in train_rows))
    finally:
        c.delete(f"/api/annotations/{sid}")
    gone = c.get(f"/api/annotations/{sid}")
    check("annotation: session deleted", gone.status_code == 404)


def test_models_info_and_train_validation():
    c = get_client()
    # released-checkpoint catalog lives on /api/overview; /api/models is the
    # trainer/registry view (training sources + jobs + user models)
    d = c.get("/api/overview").json()
    released = {m["id"] for m in d["models"]["released"]}
    check("models: two released tasks", released ==
          {"quantum_related", "quantum_category"}, f"got {released}")
    info = c.get("/api/models").json()
    check("models: training sources expose both tasks",
          set(info.get("training_sources", {}).get("gold", {})) ==
          {"quantum_related", "quantum_category"})
    # validation path: fewer than 12 labeled rows must be rejected cleanly
    r = c.post("/api/models/train", json={
        "task": "quantum_related", "source_type": "upload",
        "records": [{"text": f"note {i}", "label": "quantum"}
                    for i in range(3)],
    })
    check("models: train rejects <12 rows with 400",
          r.status_code == 400 and "12" in r.json().get("error", ""),
          f"status={r.status_code} body={r.text[:200]}")
    bad = c.post("/api/models/train", json={"task": "developer_intent"})
    check("models: retired intent task rejected",
          bad.status_code == 400)
    missing = c.get("/api/models/train/doesnotexist")
    check("models: unknown train job 404", missing.status_code == 404)


def test_spotcheck_agreement():
    """The seeded TOSEM spot-check session must report 85.0% human-model
    agreement (Task 1) — the number the SPA shows in Annotation Studio."""
    c = get_client()
    sessions = c.get("/api/annotations").json()["sessions"]
    spot = next((s for s in sessions if s.get("builtin_spotcheck")), None)
    check("spot-check: seeded session present", spot is not None)
    if spot:
        det = c.get(f"/api/annotations/{spot['id']}").json()
        check("spot-check: 379 units", len(det["items"]) == 379,
              f"got {len(det.get('items', []))}")
        agree = det["metrics"].get("agreement")
        # the SPA displays one decimal (85.0%); the raw ratio is 0.8496…
        check("spot-check: 85.0% agreement", agree is not None
              and round(agree * 100, 1) == 85.0, f"got {agree}")


def test_inspect_and_evaluate():
    """Live two-stage classification + model-vs-model evaluation.
    Requires the released checkpoints (--models or auto-detected)."""
    if not checkpoints_available():
        print("[SKIP] inspect/evaluate: checkpoints not on disk")
        return
    c = get_client()
    r = c.post("/api/inspect", json={
        "code": 'def f():\n    """Construct the Bell-state quantum circuit."""\n'
                '    pass  # apply a Hadamard gate to the first qubit\n'})
    check("inspect: two-stage units returned", r.status_code == 200,
          r.text[:200])
    if r.status_code == 200:
        units = r.json().get("units") or r.json().get("sccus") or []
        check("inspect: units classified on both axes", len(units) > 0 and all(
            "quantum_related" in u and "quantum_category" in u
            for u in units))
    d = c.get("/api/overview").json()
    cid = next(a["id"] for a in d["corpora"] if a.get("sdk") == "qiskit-aer")
    ev = c.post("/api/evaluations/run", json={
        "model_a": "released", "model_b": "released",
        "corpus_id": cid, "max_units": 60,
    })
    check("evaluate: run completes", ev.status_code == 200, ev.text[:300])
    if ev.status_code == 200:
        body = ev.json()
        check("evaluate: identical models agree 100%",
              body["agreement"] == 1.0 and body["kappa"] == 1.0,
              f"got agreement={body.get('agreement')}")
        check("evaluate: kappa + Wilson CI present",
              "wilson95" in body and len(body["wilson95"]) == 2)


ALL_CHECKS = [
    test_index_and_static,
    test_overview_numbers,
    test_corpus_units,
    test_build_job_lifecycle,
    test_annotation_lifecycle,
    test_models_info_and_train_validation,
    test_spotcheck_agreement,
    test_inspect_and_evaluate,
]


def main(with_models=False):
    if with_models:
        os.environ["CC4Q_SKIP_MODEL_DOWNLOAD"] = "0"
    for fn in ALL_CHECKS:
        print(f"\n=== {fn.__name__} ===")
        fn()
    print(f"\n{'-' * 50}")
    if FAILURES:
        print(f"{len(FAILURES)} smoke check(s) FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("All smoke tests passed.")


if __name__ == "__main__":
    main(with_models="--models" in sys.argv[1:])
