"""Starlette/Uvicorn backend for the redesigned CC4Q Workbench.

Provides a fast, zero-flicker JSON API and serves the modern single-page Web
Workbench UI under ``cc4q/web/static/``. Focuses exclusively on Quantum-Specific
comment analysis (Binary Quantum-Relatedness + 6-Category Quantum Knowledge
Taxonomy), interactive data labeling (Annotation Studio), and in-tool model
training & evaluation.
"""

import csv
import json
import math
import os
import shutil
import tempfile
import threading
import time
import uuid
from collections import Counter
import re

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import FileResponse, JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

import cc4q.workspace as ws
from cc4q.evaluate import cohen_kappa, evaluate, wilson_ci
from cc4q import registry
from cc4q.web import DATA_DIR
from cc4q.models.hub import (
    checkpoint_complete,
    default_model_dir,
    load_models,
    load_models_from,
    missing_checkpoints,
    resolve_device,
)
from cc4q.pipeline.paths import REPO_ROOT
from cc4q.predict import (
    CATEGORY_LIST,
    CATEGORY_MAPPING,
    analyze_snippet,
    predict_corpus,
    predict_quantum_detailed,
)
from cc4q.web import STATIC_DIR

UNITS_DIR = os.path.join(DATA_DIR, "units")
MANIFEST_PATH = os.path.join(DATA_DIR, "manifest.json")

_MODEL_CACHE = {}
_PIPELINE_JOBS = {}
_TRAIN_JOBS = {}

# Curated quantum code presets for Live Code Inspector
CODE_PRESETS = [
    {
        "id": "bell_circuit",
        "title": "Bell State & Entanglement Circuit",
        "subtitle": "Quantum circuit model · Gate operations & measurement",
        "code": '''"""Bell-state preparation and noisy measurement routine for superconducting backends."""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister


class EntanglementBuilder:
    """Constructs maximally entangled multi-qubit states on a quantum register.

    The generated circuit prepares a Bell or GHZ state $|\\Phi^+\\rangle = (|00\\rangle + |11\\rangle)/\\sqrt{2}$
    using a Hadamard gate followed by a cascade of CNOT (cx) entangling gates.
    """

    def __init__(self, num_qubits: int = 2):
        # Validate the number of qubits before allocating the quantum register
        if num_qubits < 2:
            raise ValueError("Entanglement requires at least 2 qubits.")
        self.num_qubits = num_qubits

    def build_bell_circuit(self, measure: bool = True) -> QuantumCircuit:
        """Build a quantum circuit that prepares the Bell state |Phi+>.

        Args:
            measure: If True, append Z-basis projective measurements to all qubits.

        Returns:
            QuantumCircuit: The constructed entangled quantum circuit.
        """
        qreg = QuantumRegister(self.num_qubits, "q")
        creg = ClassicalRegister(self.num_qubits, "c")
        qc = QuantumCircuit(qreg, creg)

        qc.h(0)  # Put the control qubit q[0] into an equal superposition state |+>
        for target in range(1, self.num_qubits):
            qc.cx(0, target)  # Entangle target qubit with control qubit q[0] via CNOT

        if measure:
            # Collapse the multi-qubit statevector onto the computational basis
            qc.measure(qreg, creg)
        return qc
''',
    },
    {
        "id": "vqe_algorithm",
        "title": "Variational Quantum Eigensolver (VQE)",
        "subtitle": "Quantum algorithms + Mathematics · Ground-state energy estimation",
        "code": '''"""Variational Quantum Eigensolver (VQE) ground-state energy solver."""

import numpy as np


class MinimumEigensolverVQE:
    """Computes the ground-state eigenvalue of a Hermitian Hamiltonian operator.

    By the Rayleigh-Ritz variational principle, the expectation value
    $\\langle \\psi(\\theta) | \\hat{H} | \\psi(\\theta) \\rangle$ is bounded below
    by the minimum eigenvalue $E_0$ of the molecular Hamiltonian.
    """

    def __init__(self, ansatz, estimator, optimizer, max_iter: int = 100):
        # Store classical optimizer configuration and iteration bounds
        self.ansatz = ansatz
        self.estimator = estimator
        self.optimizer = optimizer
        self.max_iter = max_iter

    def evaluate_energy(self, parameters: np.ndarray, hamiltonian) -> float:
        """Evaluate the Pauli observable expectation value on the parameterized ansatz circuit."""
        # Bind variational circuit parameters theta to the parameterized quantum circuit
        job = self.estimator.run([(self.ansatz, hamiltonian, parameters)])
        result = job.result()[0]
        return float(result.data.evs)
''',
    },
    {
        "id": "hardware_transpiler",
        "title": "Hardware Noise & Coupling-Map Transpiler",
        "subtitle": "Quantum hardware + Software framework · Qubit routing & decoherence",
        "code": '''"""Hardware-aware transpilation and T1/T2 thermal relaxation calibration."""

from qiskit.transpiler import PassManager, CouplingMap


def configure_backend_routing(backend, optimization_level: int = 3):
    """Configure a SabreSwap routing pass tailored to the superconducting processor topology.

    Physical qubits on heavy-hex QPU architectures only support two-qubit ECR or CZ
    gates along connected coupling-map edges and suffer from T1 amplitude damping
    and T2 dephasing noise during readout.
    """
    # Extract the directed coupling map and native basis gates from the target backend
    coupling_map = backend.coupling_map
    basis_gates = backend.operation_names

    # Return configuration dictionary for the Qiskit transpiler pipeline
    return {
        "coupling_map": coupling_map,
        "basis_gates": basis_gates,
        "optimization_level": optimization_level,  # 3 enables aggressive gate cancellation
    }
''',
    },
]

# Official TOSEM Quantum-Specific Taxonomy Reference
TAXONOMY_GUIDE = {
    "binary_criteria": [
        {
            "name": "1. Domain Relevance",
            "desc": "Relates to principles, concepts, techniques, or phenomena of quantum physics or quantum computing (e.g., qubits, superposition, Hamiltonians, transpilation).",
        },
        {
            "name": "2. Exclusivity",
            "desc": "Excludes general notions shared with classical computing (e.g., generic registers, classical optimizers, array indexing, logging, or Python type checks).",
        },
        {
            "name": "3. Explicitness",
            "desc": "Relevance to quantum computing is direct and explicit in the sentence rather than vague or purely structural.",
        },
    ],
    "categories": [
        {
            "id": "Mathematics for quantum information",
            "short": "Mathematics",
            "color": "#2563EB",
            "key": "1",
            "desc": "Mathematical foundations of quantum mechanics & quantum information: Hilbert spaces, unitary/Hermitian matrices, Pauli/fermionic operators, eigenstates, tensor products, and probability amplitudes.",
            "example": "Compute the eigenvalues of a Hermitian operator H on the n-qubit Hilbert space.",
        },
        {
            "id": "Quantum algorithms",
            "short": "Algorithms",
            "color": "#DC2626",
            "key": "2",
            "desc": "High-level quantum and hybrid quantum-classical algorithms, subroutines, and problem mappings: VQE, QAOA, Grover, Shor, QPE, amplitude estimation, and quantum kernels.",
            "example": "Run the Variational Quantum Eigensolver (VQE) to approximate the ground-state energy.",
        },
        {
            "id": "Quantum circuit model",
            "short": "Circuit Model",
            "color": "#7C3AED",
            "key": "3",
            "desc": "Quantum circuit construction and gate-level abstractions: qubits, quantum/classical registers, single- and multi-qubit gates (H, CX, RZ), state preparation, and measurements.",
            "example": "Put the control qubit q[0] into superposition and apply a CNOT gate to target q[1].",
        },
        {
            "id": "Quantum hardware",
            "short": "Hardware",
            "color": "#059669",
            "key": "4",
            "desc": "Physical quantum processors and hardware constraints: qubit connectivity/coupling maps, T1/T2 decoherence, gate/readout error rates, pulse schedules, and physical backends.",
            "example": "Account for T1 thermal relaxation and readout error mitigation on superconducting qubits.",
        },
        {
            "id": "Quantum software framework",
            "short": "Software Stack",
            "color": "#D97706",
            "key": "5",
            "desc": "Quantum SDK architecture, compilers, transpilers, simulators, primitives (Estimator/Sampler), OpenQASM intermediate representations, and cloud runtime job management.",
            "example": "Transpile the circuit to the target backend's basis gates using the Qiskit PassManager.",
        },
        {
            "id": "Others",
            "short": "Others",
            "color": "#64748B",
            "key": "6",
            "desc": "Quantum-specific comments whose content spans multiple domains or is too general to assign to a single primary category above.",
            "example": "Quantum chemistry driver configuration for molecular electronic structure problems.",
        },
    ],
}


def _clean_nans(obj):
    """Recursively convert float NaN/Inf to None for valid JSON responses."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: _clean_nans(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean_nans(x) for x in obj]
    return obj


def _json(data, status_code=200):
    return JSONResponse(_clean_nans(data), status_code=status_code)


def _load_manifest():
    if os.path.isfile(MANIFEST_PATH):
        with open(MANIFEST_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"repos": {}, "groups": {}}


def _seed_defaults():
    """Ensure built-in 6 SDK corpora and the unseen-SDK labeling demo session exist."""
    manifest = _load_manifest()
    existing_sdks = {
        a.get("sdk")
        for a in ws.list_assets("corpus")
        if a.get("source") == "precomputed"
    }
    for sdk, info in sorted(manifest.get("repos", {}).items()):
        if sdk in existing_sdks:
            continue
        ws.create_asset(
            "corpus",
            name=f"{sdk} ({info.get('version', '')})",
            source="precomputed",
            sdk=sdk,
            version=info.get("version", ""),
            layer=info.get("layer", "infrastructure" if sdk in ("qiskit", "qiskit-aer", "qiskit-ibm-runtime") else "application"),
            sccus=info.get("sccus", 0),
            ccps=info.get("ccps", 0),
            files_count=info.get("python_files") or info.get("files", 0),
            quantum_pct=info.get("quantum_proportion", 0.0),
            labeled=True,
            builtin=True,
            files={"corpus": os.path.join(UNITS_DIR, f"{sdk}.jsonl")},
        )

    # Seed the 379-unit human-verified unseen-SDK spot-check annotation session
    sessions = ws.list_assets("annotation_session")
    if not any(s.get("builtin_spotcheck") for s in sessions):
        csv_path = os.path.join(REPO_ROOT, "exp", "spotcheck_annotation.csv")
        key_path = os.path.join(REPO_ROOT, "exp", "spotcheck_answer_key.jsonl")
        if os.path.isfile(csv_path) and os.path.isfile(key_path):
            try:
                _seed_spotcheck_session(csv_path, key_path)
            except Exception:
                pass


def _norm_comment_text(t):
    """Normalize comment text for matching: the spot-check CSV stores literal
    \\n/\\t escapes while unit jsonl stores real whitespace."""
    if not t:
        return ""
    t = t.replace("\\n", " ").replace("\\t", " ").replace("\n", " ").replace("\t", " ")
    return re.sub(r"\s+", " ", t).strip().lower()


def _seed_spotcheck_session(csv_path, key_path):
    """Create a built-in labeling demo session from exp/spotcheck_annotation.csv.

    Items carry model predictions but NO human labels, so the user labels from
    scratch (adjudicating against the model). Segmentation-noise comments
    (embedded docutils log lines such as "<string>:14: (ERROR/3) ...") are dropped.
    The CSV has no unit ids, so units are recovered by matching normalized
    comment text against the built-in corpus (exact, then 60-char prefix).
    """
    contaminated = {"1", "8", "16", "25", "62", "132"}
    noise_pat = re.compile(r"<string>:\d+:")
    with open(key_path, encoding="utf-8") as f:
        key_map = {str(r["no"]): r for r in (json.loads(line) for line in f if line.strip())}

    # Index built-in units by normalized comment text (per repo) for context lookup.
    text_lookup = {}
    units_by_repo = {}
    for sdk in ("qiskit-machine-learning", "qiskit-nature", "qiskit-algorithms"):
        repo_units = []
        upath = os.path.join(UNITS_DIR, f"{sdk}.jsonl")
        if os.path.isfile(upath):
            with open(upath, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        u = json.loads(line)
                        repo_units.append(u)
                        text_lookup.setdefault((sdk, _norm_comment_text(u.get("comment_text"))), []).append(u)
        units_by_repo[sdk] = repo_units

    def find_unit(repo, comment_text):
        key = _norm_comment_text(comment_text)
        queue = text_lookup.get((repo, key))
        if queue:
            return queue.pop(0)  # 1:1 assignment when sentences repeat
        prefix = key[:60]
        for u in units_by_repo.get(repo, []):
            if _norm_comment_text(u.get("comment_text")).startswith(prefix):
                return u
        return {}

    items = []
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            no = str(row.get("no", "")).strip()
            if not no or no in contaminated:
                continue
            h_lbl = str(row.get("human_label", "")).strip().lower()
            if h_lbl not in ("quantum", "non-quantum"):
                continue
            comment_text = row.get("comment_text") or ""
            if noise_pat.search(comment_text) or "(ERROR/" in comment_text or "(WARNING/" in comment_text:
                continue
            k_info = key_map.get(no, {})
            m_lbl = str(k_info.get("model_label", "non-quantum")).strip().lower()
            repo = row.get("repo", "")
            u_full = find_unit(repo, comment_text)

            m_q = m_lbl == "quantum"
            m_cat = u_full.get("quantum_category") if m_q else None

            items.append({
                "item_id": f"{repo}:{no}",
                "no": int(no) if no.isdigit() else no,
                "id": str(u_full.get("id", "")),
                "sdk": repo,
                "file": u_full.get("file", ""),
                "comment_type": u_full.get("comment_type", ""),
                "code_entity_type": row.get("entity") or u_full.get("code_entity_type", ""),
                "comment_text": comment_text,
                "code_snippet": u_full.get("code_snippet", ""),
                "comment_line": u_full.get("comment_line") or [],
                "code_line": u_full.get("code_line") or [],
                "model_quantum_related": m_q,
                "model_quantum_category": m_cat,
                # Labeling demo: no human labels yet — the user verifies from scratch.
                "human_quantum_related": None,
                "human_quantum_category": None,
                "notes": row.get("notes", ""),
            })

    if not items:
        return
    session = ws.create_asset(
        "annotation_session",
        name=f"Unseen SDKs Labeling Demo ({len(items)} units)",
        schema={"task": "quantum_related", "labels": ["quantum", "non-quantum"]},
        mode="adjudicate",
        corpus_name="3 Application SDKs (Stratified Cochran Sample)",
        total=len(items),
        labeled_count=0,
        builtin_spotcheck=True,
    )
    path = ws.write_jsonl(session["id"], "items.jsonl", items)
    ws.update_asset(session["id"], export_path=path, labeled_count=0)


def _resolve_model_handle(model_id=None):
    """Resolve a ModelHandle by id ('released' or custom registry id)."""
    entries = registry.list_models()
    if not model_id or model_id == "default":
        default_entry = next((e for e in entries if e.get("is_default")), None)
        model_id = default_entry["id"] if default_entry else "released"

    if model_id in _MODEL_CACHE:
        return _MODEL_CACHE[model_id], model_id

    if model_id == "released":
        handle = load_models(auto_download=False)
        _MODEL_CACHE["released"] = handle
        return handle, "released"

    entry = next((e for e in entries if e["id"] == model_id), None)
    if not entry:
        handle = load_models(auto_download=False)
        return handle, "released"

    pkg = registry.package_dir(model_id)
    axis_dirs = {a: os.path.join(pkg, a) for a in entry.get("axes", []) if os.path.isdir(os.path.join(pkg, a))}
    handle = load_models_from(axis_dirs, auto_download=False)
    _MODEL_CACHE[model_id] = handle
    return handle, model_id


def _compute_corpus_stats(records, sdk_name="custom", version="latest", layer="custom"):
    """Compute manifest-compatible quantum statistics over SCCU records."""
    n = len(records)
    nq = sum(1 for r in records if r.get("quantum_related"))
    cat_counts = Counter(
        r.get("quantum_category")
        for r in records
        if r.get("quantum_related") and r.get("quantum_category")
    )
    ctype_entity = {}
    q_ctype_entity = {}
    for r in records:
        ct = r.get("comment_type", "unknown")
        ent = r.get("code_entity_type") or r.get("entity_type", "unknown")
        ctype_entity.setdefault(ct, Counter())[ent] += 1
        if r.get("quantum_related"):
            q_ctype_entity.setdefault(ct, Counter())[ent] += 1

    return {
        "sdk": sdk_name,
        "version": version,
        "layer": layer,
        "source": "workspace",
        "sampled": False,
        "python_files": len({r.get("file", "") for r in records if r.get("file")}),
        "files": len({r.get("file", "") for r in records if r.get("file")}),
        "ccps": len({str(r.get("id", "")).split("-")[0] for r in records}),
        "sccus": n,
        "quantum_sccus": nq,
        "quantum_proportion": round(nq / n, 4) if n else 0.0,
        "comment_density": {"comment_lines": 0, "code_lines": 0, "value": 0.0},
        "category_counts": {k: cat_counts.get(k, 0) for k in CATEGORY_LIST},
        "ctype_by_entity": {c: dict(e) for c, e in sorted(ctype_entity.items())},
        "quantum_ctype_by_entity": {c: dict(e) for c, e in sorted(q_ctype_entity.items())},
        "comment_type_counts": dict(Counter(r.get("comment_type", "unknown") for r in records)),
        "entity_type_counts": dict(Counter(r.get("code_entity_type") or r.get("entity_type", "unknown") for r in records)),
    }


def _load_corpus_units_and_stats(corpus_id):
    """Return (asset, stats, records) for either a built-in SDK name or workspace asset id."""
    _seed_defaults()
    manifest = _load_manifest()

    # Allow lookup by SDK name directly or by asset_id
    assets = ws.list_assets("corpus")
    asset = next(
        (a for a in assets if a["id"] == corpus_id or a.get("sdk") == corpus_id),
        None,
    )
    if not asset:
        raise KeyError(f"Corpus {corpus_id!r} not found")

    if asset.get("builtin") and asset.get("sdk") in manifest.get("repos", {}):
        sdk = asset["sdk"]
        stats = manifest["repos"][sdk]
        upath = os.path.join(UNITS_DIR, f"{sdk}.jsonl")
        records = ws.read_jsonl(upath) if os.path.isfile(upath) else []
        return asset, stats, records

    files = asset.get("files") or {}
    path = files.get("labeled") or files.get("corpus")
    records = ws.read_jsonl(path) if (path and os.path.isfile(path)) else []
    stats = asset.get("stats") or _compute_corpus_stats(
        records, sdk_name=asset.get("name", "corpus"), version=asset.get("version", "custom")
    )
    return asset, stats, records


# ------------------------------------------------------------------ Routes

async def api_overview(request):
    _seed_defaults()
    manifest = _load_manifest()
    corpora = ws.list_assets("corpus")
    # Sort corpora: built-in infrastructure first, then application, then custom
    order_map = {
        "qiskit": 0,
        "qiskit-aer": 1,
        "qiskit-ibm-runtime": 2,
        "qiskit-nature": 3,
        "qiskit-algorithms": 4,
        "qiskit-machine-learning": 5,
    }
    corpora.sort(key=lambda c: (0 if c.get("builtin") else 1, order_map.get(c.get("sdk", ""), 99), c.get("name", "")))

    # Model status
    mdir = default_model_dir()
    missing = missing_checkpoints(mdir)
    user_models = registry.list_models()
    default_user = next((m for m in user_models if m.get("is_default")), None)
    active_model = default_user["id"] if default_user else "released"
    active_model_name = default_user["name"] if default_user else "Released CC4Q Checkpoints"

    return _json({
        "manifest": manifest,
        "corpora": corpora,
        "models": {
            "active_id": active_model,
            "active_name": active_model_name,
            "checkpoints_ready": len(missing) == 0,
            "missing_checkpoints": missing,
            "released": [
                {
                    "id": "quantum_related",
                    "name": "Task 1 · Quantum Relatedness Classifier",
                    "task": "quantum_related",
                    "classes": 2,
                    "base": "bert-base-uncased",
                    "f1": 0.936,
                    "accuracy": 0.936,
                    "kappa": 0.808,
                    "ready": checkpoint_complete(mdir, "quantum_related"),
                    "desc": "Binary classifier identifying whether an SCCU conveys domain-specific quantum physics or quantum computing concepts.",
                },
                {
                    "id": "quantum_category",
                    "name": "Task 2 · Quantum Knowledge Category Classifier",
                    "task": "quantum_category",
                    "classes": 6,
                    "base": "bert-base-uncased",
                    "f1": 0.840,
                    "accuracy": 0.858,
                    "kappa": 0.771,
                    "ready": checkpoint_complete(mdir, "quantum_category"),
                    "desc": "Six-class classifier profiling quantum SCCUs into Mathematics, Algorithms, Circuit Model, Hardware, Software Framework, and Others.",
                },
            ],
            "user_models": user_models,
        },
        "device": resolve_device(),
        "presets": CODE_PRESETS,
        "taxonomy": TAXONOMY_GUIDE,
        "annotations_count": len(ws.list_assets("annotation_session")),
    })


async def api_corpus_units(request):
    corpus_id = request.path_params["corpus_id"]
    try:
        asset, stats, records = _load_corpus_units_and_stats(corpus_id)
    except KeyError as exc:
        return _json({"error": str(exc)}, status_code=404)

    qp = request.query_params
    q_filter = qp.get("quantum", "all").strip().lower()
    cat_filter = qp.get("category", "").strip()
    ctype_filter = qp.get("comment_type", "").strip().lower()
    etype_filter = qp.get("entity_type", "").strip().lower()
    search_q = qp.get("q", "").strip().lower()
    offset = max(0, int(qp.get("offset", 0)))
    limit = min(200, max(1, int(qp.get("limit", 40))))

    filtered = []
    for r in records:
        is_q = bool(r.get("quantum_related"))
        if q_filter == "quantum" and not is_q:
            continue
        if q_filter == "non-quantum" and is_q:
            continue
        if cat_filter and r.get("quantum_category") != cat_filter:
            continue
        if ctype_filter and str(r.get("comment_type", "")).lower() != ctype_filter:
            continue
        if etype_filter and str(r.get("code_entity_type") or r.get("entity_type", "")).lower() != etype_filter:
            continue
        if search_q:
            haystack = f"{r.get('comment_text', '')} {r.get('file', '')} {r.get('code_snippet', '')}".lower()
            if search_q not in haystack:
                continue
        filtered.append(r)

    total_filtered = len(filtered)
    q_in_filtered = sum(1 for r in filtered if r.get("quantum_related"))
    page = filtered[offset: offset + limit]

    return _json({
        "asset": asset,
        "stats": stats,
        "total": total_filtered,
        "quantum_in_filtered": q_in_filtered,
        "offset": offset,
        "limit": limit,
        "units": page,
    })


async def api_corpus_download(request):
    corpus_id = request.path_params["corpus_id"]
    try:
        asset, _, records = _load_corpus_units_and_stats(corpus_id)
    except KeyError as exc:
        return _json({"error": str(exc)}, status_code=404)
    lines = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
    fname = f"{asset.get('sdk') or asset['id']}_sccus.jsonl"
    return Response(
        content=lines,
        media_type="application/x-jsonlines",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


async def api_corpus_delete(request):
    corpus_id = request.path_params["corpus_id"]
    try:
        asset = ws.get_asset(corpus_id)
        if asset.get("builtin"):
            return _json({"error": "Built-in SDK corpora cannot be deleted."}, status_code=400)
        ws.delete_asset(corpus_id)
        return _json({"ok": True})
    except KeyError as exc:
        return _json({"error": str(exc)}, status_code=404)


def _audit_code_documentation(code: str, units: list):
    """Run an automated Quantum Documentation Audit based on TOSEM guidelines."""
    code_lines = [ln for ln in code.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    comment_lines = [ln for ln in code.splitlines() if ln.strip().startswith("#")]
    total_sccus = len(units)
    quantum_sccus = [u for u in units if u.get("quantum_related")]
    n_q = len(quantum_sccus)
    q_ratio = round(n_q / total_sccus, 4) if total_sccus else 0.0

    # Category coverage
    cats = Counter(u.get("quantum_category") for u in quantum_sccus if u.get("quantum_category"))
    by_entity = Counter(u.get("entity_type", "—") for u in units)
    by_ctype = Counter(u.get("comment_type", "—") for u in units)

    findings = []
    # Check 1: Docstring presence for functions/classes
    if by_ctype.get("docstring", 0) == 0 and total_sccus > 0:
        findings.append({
            "severity": "warn",
            "title": "Missing Structured Docstrings (TOSEM RQ1 Guideline)",
            "detail": "No module, class, or function docstrings were found. In Qiskit SDKs, 69%+ of quantum domain knowledge is carried in structured docstrings rather than inline comments.",
        })
    elif by_ctype.get("docstring", 0) > 0:
        findings.append({
            "severity": "pass",
            "title": "Structured Docstring Coverage Present",
            "detail": f"Extracted {by_ctype.get('docstring', 0)} sentence units from docstrings across {len(by_entity)} entity scopes.",
        })

    # Check 2: Quantum specificity & domain explanations
    if n_q == 0:
        findings.append({
            "severity": "warn",
            "title": "Zero Quantum-Specific Explanations Detected",
            "detail": "All extracted comments describe classical plumbing or generic syntax. Consider documenting qubit roles, gate semantics, or hardware/mathematical constraints.",
        })
    else:
        top_cat, top_cnt = cats.most_common(1)[0] if cats else ("Quantum circuit model", n_q)
        findings.append({
            "severity": "pass",
            "title": f"Strong Quantum Domain Signal ({n_q}/{total_sccus} units · {q_ratio * 100:.0f}%)",
            "detail": f"Primary knowledge domain is '{top_cat}' ({top_cnt} unit{'s' if top_cnt != 1 else ''}).",
        })

    # Check 3: Inline comment context
    inline_q = [u for u in quantum_sccus if u.get("comment_type") == "inline"]
    if inline_q:
        findings.append({
            "severity": "pass",
            "title": "Point-of-Use Inline Quantum Comments",
            "detail": f"{len(inline_q)} inline comment(s) explain quantum operations directly beside gate/circuit calls.",
        })

    return {
        "total_sccus": total_sccus,
        "quantum_sccus": n_q,
        "quantum_ratio": q_ratio,
        "code_lines": len(code_lines),
        "category_counts": {k: cats.get(k, 0) for k in CATEGORY_LIST},
        "entity_counts": dict(by_entity),
        "comment_type_counts": dict(by_ctype),
        "findings": findings,
    }


async def api_inspect_code(request):
    body = await request.json()
    code = (body.get("code") or "").strip()
    model_id = body.get("model_id") or "default"
    if not code:
        return _json({"error": "Please provide Python source code to analyze."}, status_code=400)

    t0 = time.time()
    models = None
    used_model_id = "none"
    try:
        models, used_model_id = _resolve_model_handle(model_id)
    except Exception:
        models = None

    units, parse_error, fallback = analyze_snippet(code, models=models)
    elapsed_ms = int((time.time() - t0) * 1000)
    audit = _audit_code_documentation(code, units)

    return _json({
        "units": units,
        "audit": audit,
        "parse_error": parse_error,
        "fallback_used": fallback,
        "model_id": used_model_id,
        "elapsed_ms": elapsed_ms,
    })


# --------------------------------------------------------- Pipeline Builder

def _run_pipeline_job(job_id, source_type, target, ref, name, run_predict, model_id):
    job = _PIPELINE_JOBS[job_id]
    workdir = tempfile.mkdtemp(prefix="cc4q_pipe_")
    try:
        job["stage"] = 1
        job["stage_name"] = "Stage 1/4 · Acquiring Python Repository"
        job["progress"] = 0.15

        if source_type == "dir":
            src = os.path.abspath(os.path.join(REPO_ROOT, target) if not os.path.isabs(target) else target)
            if not os.path.isdir(src):
                raise RuntimeError(f"Directory not found: {src}")
            sdk_name = name or os.path.basename(src.rstrip(os.sep))
            version = ref or "local"
        else:
            from cc4q.pipeline.download import clone_repo
            entry = {"url": target, "ref": ref} if ref else target
            if not clone_repo(entry, workdir):
                raise RuntimeError(f"Failed to clone repository: {target}")
            repo_folder = target.strip().rstrip("/").split("/")[-1].replace(".git", "")
            src = os.path.join(workdir, repo_folder)
            sdk_name = name or repo_folder
            version = ref or "HEAD"

        from cc4q.pipeline.files import get_files_from_dir
        from cc4q.pipeline.extract import python_extract_comment_pairs
        from cc4q.pipeline.ids import id_generator
        from cc4q.pipeline.metrics import compute_comment_density

        py_files = get_files_from_dir(src, None)
        if not py_files:
            raise RuntimeError(f"No .py files found in {src}")
        if source_type == "url" and len(py_files) > 250:
            raise RuntimeError(
                f"Repository has {len(py_files)} Python files (>250 live UI guardrail). "
                "Use `cc4q build` in CLI for very large repositories."
            )

        job["stage"] = 2
        job["stage_name"] = f"Stage 2/4 · LibCST AST Scope Extraction ({len(py_files)} files)"
        job["progress"] = 0.40

        ccp_records = []
        id_gen = id_generator()
        for fpath in py_files:
            with open(fpath, encoding="utf-8", errors="replace") as f:
                src_text = f.read()
            try:
                ccp_records.extend(
                    python_extract_comment_pairs(
                        source_code=src_text,
                        rel_path=os.path.relpath(fpath, src),
                        sdk=sdk_name,
                        id_gen=id_gen,
                        version=version,
                        host_language="python",
                        clean_mode="current_only",
                    )
                )
            except Exception:
                continue

        job["stage"] = 3
        job["stage_name"] = f"Stage 3/4 · Sphinx-Aware Docstring Segmentation ({len(ccp_records)} CCPs)"
        job["progress"] = 0.65

        from cc4q.predict import _segment_record, compact_snippet as _compact_snippet

        sccus = []
        for rec in ccp_records:
            segs = _segment_record(rec)
            rel_file = "/".join(rec.get("dirPath") or []) if isinstance(rec.get("dirPath"), list) else str(rec.get("dirPath", ""))
            for s in segs:
                sccus.append({
                    "id": s["id"],
                    "sdk": sdk_name,
                    "version": version,
                    "file": rel_file or "(root)",
                    "comment_type": s["comment_type"],
                    "code_entity_type": s["code_entity_type"],
                    "comment_text": s["comment_text"],
                    "code_snippet": _compact_snippet(s.get("code_snippet", ""), s["comment_text"]),
                    "comment_line": s.get("comment_line") or [],
                    "code_line": s.get("code_line") or [],
                    "quantum_related": False,
                    "quantum_category": None,
                })

        if not sccus:
            raise RuntimeError("No comment units (SCCUs) were extracted from the repository.")

        density = compute_comment_density(src, None)

        labeled_flag = False
        if run_predict:
            job["stage"] = 4
            job["stage_name"] = f"Stage 4/4 · Two-Stage Quantum BERT Labeling ({len(sccus)} SCCUs)"
            job["progress"] = 0.85
            handle, _ = _resolve_model_handle(model_id)
            details = predict_quantum_detailed([u["comment_text"] for u in sccus], handle, batch=32)
            for u, d in zip(sccus, details):
                u["quantum_related"] = d["quantum_related"]
                u["quantum_prob"] = d["quantum_prob"]
                u["quantum_category"] = d["quantum_category"]
                u["category_confidence"] = d["category_confidence"]
            labeled_flag = True

        stats = _compute_corpus_stats(sccus, sdk_name=sdk_name, version=version, layer="custom")
        stats["python_files"] = len(py_files)
        stats["ccps"] = len(ccp_records)
        stats["comment_density"] = density

        asset = ws.create_asset(
            "corpus",
            name=f"{sdk_name} ({version})",
            source="dir" if source_type == "dir" else "url",
            sdk=sdk_name,
            version=version,
            layer="custom",
            sccus=len(sccus),
            ccps=len(ccp_records),
            files_count=len(py_files),
            quantum_pct=stats["quantum_proportion"] if labeled_flag else None,
            labeled=labeled_flag,
            builtin=False,
            stats=stats,
            files={},
        )
        cpath = ws.write_jsonl(asset["id"], "corpus.jsonl", sccus)
        ws.update_asset(
            asset["id"],
            files={"corpus": cpath, "labeled": cpath if labeled_flag else None},
        )

        job["status"] = "completed"
        job["progress"] = 1.0
        job["stage_name"] = "Completed · Corpus Built & Indexed"
        job["asset"] = ws.get_asset(asset["id"])
        job["stats"] = stats
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


async def api_pipeline_build(request):
    body = await request.json()
    source_type = body.get("source_type", "dir")
    target = (body.get("target") or "").strip()
    ref = (body.get("ref") or "").strip() or None
    name = (body.get("name") or "").strip() or None
    run_predict = bool(body.get("run_predict", True))
    model_id = body.get("model_id") or "default"

    if not target:
        return _json({"error": "Repository URL or local directory path is required."}, status_code=400)

    job_id = uuid.uuid4().hex[:8]
    _PIPELINE_JOBS[job_id] = {
        "job_id": job_id,
        "status": "running",
        "stage": 1,
        "stage_name": "Initializing pipeline…",
        "progress": 0.05,
        "target": target,
        "started_at": time.strftime("%H:%M:%S"),
    }
    t = threading.Thread(
        target=_run_pipeline_job,
        args=(job_id, source_type, target, ref, name, run_predict, model_id),
        daemon=True,
    )
    t.start()
    return _json(_PIPELINE_JOBS[job_id])


async def api_pipeline_job_status(request):
    job_id = request.path_params["job_id"]
    job = _PIPELINE_JOBS.get(job_id)
    if not job:
        return _json({"error": "Job not found"}, status_code=404)
    return _json(job)


# --------------------------------------------------------- Annotation Studio

def _compute_session_metrics(items):
    """Compute live human-vs-model agreement metrics over labeled items in a session."""
    total = len(items)
    labeled_items = [it for it in items if it.get("human_quantum_related") is not None]
    n_labeled = len(labeled_items)

    if n_labeled == 0:
        return {
            "total": total,
            "labeled_count": 0,
            "quantum_human_count": 0,
            "agreement": None,
            "kappa": None,
            "precision": None,
            "recall": None,
            "f1": None,
            "wilson95": [None, None],
            "confusion": {"tp": 0, "fp": 0, "fn": 0, "tn": 0},
            "category_agreement": None,
            "category_compared": 0,
            "disagreements": [],
        }

    h_seq = ["quantum" if it["human_quantum_related"] else "non-quantum" for it in labeled_items]
    m_seq = ["quantum" if it.get("model_quantum_related") else "non-quantum" for it in labeled_items]
    ev = evaluate(h_seq, m_seq)

    # Category agreement on items where both human and model say quantum and have a category
    both_q = [
        it for it in labeled_items
        if it.get("human_quantum_related")
        and it.get("model_quantum_related")
        and it.get("human_quantum_category")
        and it.get("model_quantum_category")
    ]
    cat_agree = (
        sum(1 for it in both_q if it["human_quantum_category"] == it["model_quantum_category"]) / len(both_q)
        if both_q else None
    )

    disagreements = []
    for idx, it in enumerate(items):
        hq = it.get("human_quantum_related")
        if hq is None:
            continue
        mq = bool(it.get("model_quantum_related"))
        if bool(hq) != mq:
            disagreements.append({
                "index": idx,
                "item_id": it.get("item_id"),
                "sdk": it.get("sdk", ""),
                "comment_text": it.get("comment_text", ""),
                "human_label": "quantum" if hq else "non-quantum",
                "model_label": "quantum" if mq else "non-quantum",
            })

    return {
        "total": total,
        "labeled_count": n_labeled,
        "quantum_human_count": sum(1 for it in labeled_items if it["human_quantum_related"]),
        "agreement": ev["agreement"],
        "kappa": ev["kappa"],
        "precision": ev["precision"],
        "recall": ev["recall"],
        "f1": ev["f1"],
        "wilson95": list(ev["wilson95"]),
        "confusion": ev["confusion"],
        "category_agreement": cat_agree,
        "category_compared": len(both_q),
        "disagreements": disagreements[:50],
    }


async def api_annotations_list(request):
    _seed_defaults()
    sessions = ws.list_assets("annotation_session")
    return _json({"sessions": sessions})


async def api_annotations_create(request):
    body = await request.json()
    name = (body.get("name") or "").strip() or f"annotation-{int(time.time()) % 10000}"
    corpus_id = body.get("corpus_id") or "qiskit-nature"
    sample_size = int(body.get("sample_size") or 50)
    stratify_by = body.get("stratify_by") or []
    mode = body.get("mode") or "adjudicate"
    seed = int(body.get("seed") or 42)
    uploaded_records = body.get("records")

    if uploaded_records and isinstance(uploaded_records, list):
        records = uploaded_records
        corpus_name = "Uploaded JSONL"
    else:
        asset, _, records = _load_corpus_units_and_stats(corpus_id)
        corpus_name = asset.get("name", corpus_id)

    if not records:
        return _json({"error": "Selected source has no records to sample."}, status_code=400)

    from cc4q.sample import sample as cc4q_sample
    sample_n = min(sample_size, len(records))
    valid_strat = [col for col in stratify_by if all(col in r for r in records[:50])]
    sampled = cc4q_sample(records, by=valid_strat or None, n=sample_n, seed=seed)

    items = []
    for idx, r in enumerate(sampled, 1):
        uid = str(r.get("id", idx))
        sdk = r.get("sdk") or r.get("SDK", "corpus")
        mq = bool(r.get("quantum_related"))
        mcat = r.get("quantum_category") if mq else None
        items.append({
            "item_id": f"{sdk}:{uid}:{idx}",
            "no": idx,
            "id": uid,
            "sdk": sdk,
            "file": r.get("file", ""),
            "comment_type": r.get("comment_type", ""),
            "code_entity_type": r.get("code_entity_type") or r.get("entity_type", ""),
            "comment_text": r.get("comment_text") or r.get("text", ""),
            "code_snippet": r.get("code_snippet", ""),
            "comment_line": r.get("comment_line") or [],
            "code_line": r.get("code_line") or [],
            "model_quantum_related": mq,
            "model_quantum_category": mcat,
            "human_quantum_related": None,
            "human_quantum_category": None,
            "notes": "",
        })

    session = ws.create_asset(
        "annotation_session",
        name=name,
        schema={"task": "quantum_two_stage", "labels": ["quantum", "non-quantum"]},
        mode=mode,
        corpus_id=corpus_id,
        corpus_name=corpus_name,
        stratify_by=valid_strat,
        seed=seed,
        total=len(items),
        labeled_count=0,
    )
    path = ws.write_jsonl(session["id"], "items.jsonl", items)
    ws.update_asset(session["id"], export_path=path)
    return _json({"session": ws.get_asset(session["id"])})


async def api_annotation_detail(request):
    session_id = request.path_params["session_id"]
    try:
        session = ws.get_asset(session_id)
    except KeyError as exc:
        return _json({"error": str(exc)}, status_code=404)

    path = session.get("export_path") or ws.asset_path(session_id, "items.jsonl")
    items = ws.read_jsonl(path) if os.path.isfile(path) else []
    metrics = _compute_session_metrics(items)
    return _json({
        "session": session,
        "items": items,
        "metrics": metrics,
    })


async def api_annotation_label(request):
    session_id = request.path_params["session_id"]
    body = await request.json()
    item_id = body.get("item_id")
    index = body.get("index")
    hq = body.get("human_quantum_related")
    hcat = body.get("human_quantum_category")
    notes = body.get("notes")

    try:
        session = ws.get_asset(session_id)
    except KeyError as exc:
        return _json({"error": str(exc)}, status_code=404)

    path = session.get("export_path") or ws.asset_path(session_id, "items.jsonl")
    items = ws.read_jsonl(path) if os.path.isfile(path) else []

    target_item = None
    if index is not None and 0 <= int(index) < len(items):
        target_item = items[int(index)]
    elif item_id is not None:
        target_item = next((it for it in items if it.get("item_id") == item_id), None)

    if target_item is None:
        return _json({"error": "Item not found in annotation session."}, status_code=404)

    target_item["human_quantum_related"] = hq
    if hq is False:
        target_item["human_quantum_category"] = None
    elif hq is True:
        target_item["human_quantum_category"] = (
            hcat or target_item.get("human_quantum_category") or target_item.get("model_quantum_category") or "Quantum circuit model"
        )
    else:
        target_item["human_quantum_category"] = None

    if notes is not None:
        target_item["notes"] = str(notes)

    ws.write_jsonl(session_id, "items.jsonl", items)
    metrics = _compute_session_metrics(items)
    updated_session = ws.update_asset(
        session_id,
        labeled_count=metrics["labeled_count"],
        agreement=round(metrics["agreement"], 4) if metrics["agreement"] is not None else None,
    )
    return _json({
        "session": updated_session,
        "item": target_item,
        "metrics": metrics,
    })


async def api_annotation_export(request):
    session_id = request.path_params["session_id"]
    task = request.query_params.get("task", "full")
    try:
        session = ws.get_asset(session_id)
    except KeyError as exc:
        return _json({"error": str(exc)}, status_code=404)

    path = session.get("export_path") or ws.asset_path(session_id, "items.jsonl")
    items = ws.read_jsonl(path) if os.path.isfile(path) else []
    labeled = [it for it in items if it.get("human_quantum_related") is not None]

    if task == "quantum_related":
        from cc4q.train import normalize_training_records
        out_rows = normalize_training_records(labeled, "quantum_related")
        fname = f"{session['name']}_quantum_related_train.jsonl"
    elif task == "quantum_category":
        from cc4q.train import normalize_training_records
        q_only = [it for it in labeled if it.get("human_quantum_related") and it.get("human_quantum_category")]
        out_rows = normalize_training_records(q_only, "quantum_category")
        fname = f"{session['name']}_quantum_category_train.jsonl"
    else:
        out_rows = labeled
        fname = f"{session['name']}_annotations_full.jsonl"

    content = "\n".join(json.dumps(r, ensure_ascii=False) for r in out_rows)
    return Response(
        content=content,
        media_type="application/x-jsonlines",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


async def api_annotation_delete(request):
    session_id = request.path_params["session_id"]
    try:
        ws.delete_asset(session_id)
        return _json({"ok": True})
    except KeyError as exc:
        return _json({"error": str(exc)}, status_code=404)


# ------------------------------------------------ Model Trainer & Registry

def _gold_training_path(task):
    if task == "quantum_related":
        return os.path.join(REPO_ROOT, "model", "quantum_related_classifier", "data", "train", "all_data.jsonl")
    return os.path.join(REPO_ROOT, "model", "quantum_category_classifier", "data", "all_data_r12_balanced.jsonl")


async def api_models_info(request):
    _seed_defaults()
    sessions = ws.list_assets("annotation_session")
    qr_gold = _gold_training_path("quantum_related")
    qc_gold = _gold_training_path("quantum_category")

    def _count_lines(p):
        if not os.path.isfile(p):
            return 0
        with open(p, encoding="utf-8") as f:
            return sum(1 for ln in f if ln.strip())

    return _json({
        "user_models": registry.list_models(),
        "training_sources": {
            "gold": {
                "quantum_related": {"path": qr_gold, "rows": _count_lines(qr_gold), "name": "TOSEM Gold Dataset · Quantum Relatedness (Binary)"},
                "quantum_category": {"path": qc_gold, "rows": _count_lines(qc_gold), "name": "TOSEM Gold Dataset · Quantum Knowledge Category (6-Class)"},
            },
            "sessions": [
                {
                    "id": s["id"],
                    "name": s["name"],
                    "labeled_count": s.get("labeled_count", 0),
                    "total": s.get("total", 0),
                }
                for s in sessions if s.get("labeled_count", 0) > 0
            ],
        },
        "jobs": list(_TRAIN_JOBS.values()),
    })


async def api_models_set_default(request):
    body = await request.json()
    model_id = body.get("model_id", "released")
    if model_id == "released":
        idx_path = os.path.join(registry.registry_root(), "registry.json")
        if os.path.isfile(idx_path):
            with open(idx_path, encoding="utf-8") as f:
                data = json.load(f)
            data["default"] = None
            with open(idx_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        return _json({"ok": True, "active_id": "released"})
    try:
        registry.set_default(model_id)
        return _json({"ok": True, "active_id": model_id})
    except KeyError:
        return _json({"error": f"Model {model_id!r} not found"}, status_code=404)


async def api_models_delete(request):
    model_id = request.path_params["model_id"]
    registry.delete(model_id)
    _MODEL_CACHE.pop(model_id, None)
    return _json({"ok": True})


async def api_models_download(request):
    model_id = request.path_params["model_id"]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    tmp.close()
    registry.zip_package(model_id, tmp.name)
    return FileResponse(tmp.name, filename=f"{model_id}.zip", media_type="application/zip")


def _run_training_job(job_id, task, train_records, model_name, base_model, epochs, batch_size, learning_rate, max_samples):
    from transformers import TrainerCallback
    import cc4q.train as train_mod

    job = _TRAIN_JOBS[job_id]
    fd, tmp_data = tempfile.mkstemp(suffix=".jsonl", prefix="cc4q_train_")
    pkg_root = tempfile.mkdtemp(prefix="cc4q_pkg_")
    axis_out = os.path.join(pkg_root, task)
    os.makedirs(axis_out, exist_ok=True)

    class _WebCallback(TrainerCallback):
        def on_train_begin(self, args, state, control, **kwargs):
            job["total_steps"] = max(1, int(state.max_steps or 1))
            job["stage"] = f"Fine-tuning BERT ({job['total_steps']} steps)…"

        def on_step_end(self, args, state, control, **kwargs):
            job["step"] = int(state.global_step)
            job["total_steps"] = max(1, int(state.max_steps or 1))
            job["progress"] = round(min(0.95, 0.10 + 0.85 * (state.global_step / job["total_steps"])), 3)

        def on_log(self, args, state, control, logs=None, **kwargs):
            if not logs:
                return
            entry = {"step": int(state.global_step), "epoch": round(float(state.epoch or 0), 2)}
            if "loss" in logs:
                entry["loss"] = round(float(logs["loss"]), 4)
            if "eval_f1" in logs:
                entry["eval_f1"] = round(float(logs["eval_f1"]), 4)
            if "eval_accuracy" in logs:
                entry["eval_accuracy"] = round(float(logs["eval_accuracy"]), 4)
            if "loss" in entry or "eval_f1" in entry:
                job["history"].append(entry)

    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for r in train_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        job["stage"] = "Tokenizing & splitting dataset (80/10/10)…"
        job["progress"] = 0.10

        res = train_mod.train(
            task=task,
            data=tmp_data,
            output_dir=axis_out,
            base_model=base_model,
            batch_size=batch_size,
            epochs=epochs,
            learning_rate=learning_rate,
            max_length=128,
            max_samples=max_samples,
            callbacks=[_WebCallback()],
        )

        # Remove checkpoints subdirs produced by Trainer before registering package
        for sub in os.listdir(axis_out):
            sub_p = os.path.join(axis_out, sub)
            if os.path.isdir(sub_p) and sub.startswith("checkpoint-"):
                shutil.rmtree(sub_p, ignore_errors=True)

        entry = registry.register(name=model_name, path=pkg_root, source="trained")
        _MODEL_CACHE.clear()

        tr = res["test_results"]
        job["status"] = "completed"
        job["progress"] = 1.0
        job["stage"] = f"Completed · Saved as '{entry['name']}'"
        job["registered_model"] = entry
        job["saved_to"] = registry.package_dir(entry["id"])
        job["test_results"] = {
            "accuracy": round(float(tr.get("eval_accuracy", 0.0)), 4),
            "precision": round(float(tr.get("eval_precision", 0.0)), 4),
            "recall": round(float(tr.get("eval_recall", 0.0)), 4),
            "f1": round(float(tr.get("eval_f1", 0.0)), 4),
            "loss": round(float(tr.get("eval_loss", 0.0)), 4),
            "train_rows": res.get("train_rows", 0),
            "val_rows": res.get("val_rows", 0),
            "test_rows": res.get("test_rows", 0),
        }
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc)
    finally:
        if os.path.exists(tmp_data):
            os.remove(tmp_data)
        shutil.rmtree(pkg_root, ignore_errors=True)


async def api_models_train(request):
    from cc4q.train import normalize_training_records

    body = await request.json()
    task = body.get("task", "quantum_related")
    if task not in ("quantum_related", "quantum_category"):
        return _json({"error": "Task must be 'quantum_related' or 'quantum_category'."}, status_code=400)

    source_type = body.get("source_type", "gold")
    session_id = body.get("session_id")
    uploaded_rows = body.get("records")
    base_model = body.get("base_model", "released")
    epochs = max(1, min(30, int(body.get("epochs", 2))))
    batch_size = max(4, min(64, int(body.get("batch_size", 16))))
    learning_rate = float(body.get("learning_rate", 2e-5))
    max_samples = body.get("max_samples")
    if max_samples is not None and str(max_samples).strip() != "":
        max_samples = max(20, int(max_samples))
    else:
        max_samples = None

    model_name = (body.get("model_name") or "").strip() or f"{task}-{epochs}ep"

    # Only one training job at a time: concurrent Trainer instances crash the
    # Apple MPS backend (Metal command-buffer assertion, abort trap 6).
    if any(j.get("status") == "running" for j in _TRAIN_JOBS.values()):
        return _json(
            {"error": "A training job is already running. Wait for it to finish (or reload the page) before starting another."},
            status_code=409,
        )

    try:
        if source_type == "session":
            session = ws.get_asset(session_id)
            path = session.get("export_path") or ws.asset_path(session_id, "items.jsonl")
            raw_rows = ws.read_jsonl(path)
            raw_rows = [r for r in raw_rows if r.get("human_quantum_related") is not None]
            if task == "quantum_category":
                raw_rows = [r for r in raw_rows if r.get("human_quantum_related") and r.get("human_quantum_category")]
            train_records = normalize_training_records(raw_rows, task)
        elif source_type == "upload" and isinstance(uploaded_rows, list):
            train_records = normalize_training_records(uploaded_rows, task)
        else:
            gpath = _gold_training_path(task)
            if not os.path.isfile(gpath):
                return _json({"error": f"Gold training file not found: {gpath}"}, status_code=400)
            raw_rows = ws.read_jsonl(gpath)
            train_records = normalize_training_records(raw_rows, task)

        if len(train_records) < 12:
            return _json(
                {"error": f"Need at least 12 labeled rows to split train/val/test (got {len(train_records)})."},
                status_code=400,
            )
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=400)

    job_id = uuid.uuid4().hex[:8]
    _TRAIN_JOBS[job_id] = {
        "job_id": job_id,
        "task": task,
        "model_name": model_name,
        "base_model": base_model,
        "epochs": epochs,
        "batch_size": batch_size,
        "total_input_rows": min(len(train_records), max_samples) if max_samples else len(train_records),
        "status": "running",
        "stage": "Preparing dataset…",
        "progress": 0.05,
        "step": 0,
        "total_steps": 1,
        "history": [],
        "started_at": time.strftime("%H:%M:%S"),
    }

    t = threading.Thread(
        target=_run_training_job,
        args=(job_id, task, train_records, model_name, base_model, epochs, batch_size, learning_rate, max_samples),
        daemon=True,
    )
    t.start()
    return _json(_TRAIN_JOBS[job_id])


async def api_models_train_status(request):
    job_id = request.path_params["job_id"]
    job = _TRAIN_JOBS.get(job_id)
    if not job:
        return _json({"error": "Training job not found"}, status_code=404)
    return _json(job)


# ------------------------------------------------------------ Evaluations

async def api_evaluations_run(request):
    body = await request.json()
    model_a_id = body.get("model_a", "released")
    model_b_id = body.get("model_b", "released")
    corpus_id = body.get("corpus_id", "qiskit-nature")
    max_units = min(500, max(20, int(body.get("max_units", 200))))

    try:
        asset, _, records = _load_corpus_units_and_stats(corpus_id)
        records = records[:max_units]
        texts = [r["comment_text"] for r in records]
        handle_a, id_a = _resolve_model_handle(model_a_id)
        handle_b, id_b = _resolve_model_handle(model_b_id)

        det_a = predict_quantum_detailed(texts, handle_a, batch=64)
        det_b = predict_quantum_detailed(texts, handle_b, batch=64)

        la = ["quantum" if d["quantum_related"] else "non-quantum" for d in det_a]
        lb = ["quantum" if d["quantum_related"] else "non-quantum" for d in det_b]
        ev = evaluate(la, lb)

        cats_a = Counter(d["quantum_category"] for d in det_a if d["quantum_related"] and d["quantum_category"])
        cats_b = Counter(d["quantum_category"] for d in det_b if d["quantum_related"] and d["quantum_category"])

        disagreements = []
        for r, da, db in zip(records, det_a, det_b):
            if da["quantum_related"] != db["quantum_related"] or da["quantum_category"] != db["quantum_category"]:
                disagreements.append({
                    "id": r.get("id", ""),
                    "file": r.get("file", ""),
                    "comment_text": r.get("comment_text", ""),
                    "a_quantum": da["quantum_related"],
                    "a_category": da["quantum_category"],
                    "b_quantum": db["quantum_related"],
                    "b_category": db["quantum_category"],
                })

        result = {
            "corpus": asset.get("name", corpus_id),
            "model_a": id_a,
            "model_b": id_b,
            "n": ev["n"],
            "agreement": ev["agreement"],
            "kappa": ev["kappa"],
            "precision": ev["precision"],
            "recall": ev["recall"],
            "f1": ev["f1"],
            "wilson95": list(ev["wilson95"]),
            "confusion": ev["confusion"],
            "category_counts_a": {k: cats_a.get(k, 0) for k in CATEGORY_LIST},
            "category_counts_b": {k: cats_b.get(k, 0) for k in CATEGORY_LIST},
            "disagreements": disagreements[:50],
        }
        return _json(result)
    except Exception as exc:
        return _json({"error": str(exc)}, status_code=400)


async def index_page(request):
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


class NoCacheStaticMiddleware:
    """Static assets must be revalidated on every load — the workbench UI is
    iterated on frequently and stale cached app.js causes silent breakage."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith("/static"):
            await self.app(scope, receive, send)
            return

        async def send_no_cache(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                headers = [(k, v) for k, v in headers if k.lower() != b"cache-control"]
                headers.append((b"cache-control", b"no-cache, must-revalidate"))
                message = dict(message)
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_no_cache)


routes = [
    Route("/", index_page),
    Route("/api/overview", api_overview),
    Route("/api/corpora/{corpus_id}/units", api_corpus_units),
    Route("/api/corpora/{corpus_id}/download", api_corpus_download),
    Route("/api/corpora/{corpus_id}", api_corpus_delete, methods=["DELETE"]),
    Route("/api/inspect", api_inspect_code, methods=["POST"]),
    Route("/api/pipeline/build", api_pipeline_build, methods=["POST"]),
    Route("/api/pipeline/jobs/{job_id}", api_pipeline_job_status),
    Route("/api/annotations", api_annotations_list, methods=["GET"]),
    Route("/api/annotations", api_annotations_create, methods=["POST"]),
    Route("/api/annotations/{session_id}", api_annotation_detail, methods=["GET"]),
    Route("/api/annotations/{session_id}/label", api_annotation_label, methods=["POST"]),
    Route("/api/annotations/{session_id}/export", api_annotation_export, methods=["GET"]),
    Route("/api/annotations/{session_id}", api_annotation_delete, methods=["DELETE"]),
    Route("/api/models", api_models_info, methods=["GET"]),
    Route("/api/models/default", api_models_set_default, methods=["POST"]),
    Route("/api/models/train", api_models_train, methods=["POST"]),
    Route("/api/models/train/{job_id}", api_models_train_status, methods=["GET"]),
    Route("/api/models/{model_id}", api_models_delete, methods=["DELETE"]),
    Route("/api/models/{model_id}/download", api_models_download, methods=["GET"]),
    Route("/api/evaluations/run", api_evaluations_run, methods=["POST"]),
    Mount("/static", StaticFiles(directory=STATIC_DIR), name="static"),
]

app = Starlette(debug=False, routes=routes, middleware=[Middleware(NoCacheStaticMiddleware)])


def run_server(host="127.0.0.1", port=8501):
    import uvicorn
    os.makedirs(STATIC_DIR, exist_ok=True)
    _seed_defaults()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    run_server()
