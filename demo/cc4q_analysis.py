"""Analysis helpers for the CC4Q Streamlit demo.

Importable without Streamlit so it can be smoke-tested directly:

    from demo.cc4q_analysis import analyze_code, load_models
    models = load_models()
    rows = analyze_code(QISKIT_SNIPPET, models)

Pipeline: LibCST comment extraction -> docutils/spaCy segmentation ->
three-axis BERT classification (quantum-related, quantum-category,
developer-intent). Mirrors exp/run_inference.py.
"""

import os
import sys

DEMO_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DEMO_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import torch
from transformers import BertForSequenceClassification, BertTokenizer

from parser_core.python_parser.python_extractor import python_extract_comment_pairs
from segment_core.python_segment.block_comment_segmenter import segment_block_comment
from segment_core.python_segment.docstring_segmenter import segment_docstring
from segment_core.python_segment.inline_comment_segmenter import segment_inline_comment
from utils.id_utils import id_generator

CKPT_DIR = os.path.join(PROJECT_ROOT, "models_checkpoints")
DEVICE = "cpu"  # MPS hangs on this machine; CPU only.
BATCH_SIZE = 32
MAX_LENGTH = 512

INTENT_MAPPING = {0: "What", 1: "How-to-use", 2: "How-it-is-done",
                  3: "Property", 4: "Why", 5: "Others"}
CATEGORY_MAPPING = {0: "Mathematics for quantum information", 1: "Quantum algorithms",
                    2: "Quantum circuit model", 3: "Quantum hardware",
                    4: "Quantum software framework", 5: "Others"}

QISKIT_SNIPPET = '''from qiskit import QuantumCircuit, transpile


def build_bell_state(backend):
    """Create a Bell state circuit on two qubits.

    The circuit applies a Hadamard gate on the first qubit
    followed by a CNOT gate, which entangles the two qubits.
    The resulting state is (|00> + |11>) / sqrt(2).

    Args:
        backend: The backend used to fix the coupling map.

    Returns:
        QuantumCircuit: the entangled Bell circuit.
    """
    qc = QuantumCircuit(2, 2)  # two-qubit register plus two classical bits
    qc.h(0)  # put the first qubit into superposition
    qc.cx(0, 1)  # entangle qubit 1 with qubit 0
    # measurements are deferred so the state stays coherent
    qc.measure([0, 1], [0, 1])
    return transpile(qc, backend)
'''


def load_models():
    """Load the three BERT classifiers (CPU, eval mode). Called lazily."""
    models = {}
    for name in ("quantum_related", "quantum_category", "developer_intent"):
        model_dir = os.path.join(CKPT_DIR, name)
        tokenizer = BertTokenizer.from_pretrained(model_dir)
        model = BertForSequenceClassification.from_pretrained(model_dir)
        model.to(DEVICE)
        model.eval()
        models[name] = (tokenizer, model)
    return models


def _predict(tokenizer, model, texts):
    preds = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = tokenizer(texts[i:i + BATCH_SIZE], return_tensors="pt",
                          padding=True, truncation=True, max_length=MAX_LENGTH)
        batch = {k: v.to(DEVICE) for k, v in batch.items()}
        with torch.inference_mode():
            logits = model(**batch).logits
        preds.extend(logits.argmax(dim=1).cpu().tolist())
    return preds


def _segment_record(record):
    """Split a CommentRecord into sentence-level comment units."""
    text = record["comment_text"].strip()
    ctype = record["comment_type"]
    if ctype == "docstring":
        units = [b["content"].strip() for b in segment_docstring(text)]
        units = [u for u in units if u and len(u) >= 3]
    elif ctype == "inline":
        units = segment_inline_comment(text)
    else:  # block
        units = segment_block_comment(text)
    return [{"text": u, "comment_type": ctype} for u in units if u.strip()]


def extract_units(source_code):
    """Extract + segment a Python snippet -> list of SCCU dicts.

    Returns (units, error). error is a user-facing message when the
    snippet could not be parsed at all.
    """
    try:
        records = python_extract_comment_pairs(
            source_code=source_code, rel_path="snippet.py", sdk="demo",
            id_gen=id_generator(), version="demo",
            host_language="python", clean_mode="current_only")
    except Exception as exc:
        return [], f"Could not parse the snippet as Python ({exc})."
    units = []
    for record in records:
        units.extend(_segment_record(record))
    return units, None


def raw_text_units(raw_text):
    """Fallback mode: classify raw comment text line by line."""
    return [{"text": line.strip().lstrip("#").strip(), "comment_type": "raw"}
            for line in raw_text.splitlines()
            if line.strip().lstrip("#").strip()]


def classify_units(units, models):
    """Run the three-axis classifiers over SCCU dicts (mutates and returns)."""
    texts = [u["text"] for u in units]
    qr = _predict(*models["quantum_related"], texts)
    di = _predict(*models["developer_intent"], texts)
    quantum_idx = [i for i, v in enumerate(qr) if v == 1]
    categories = [None] * len(units)
    if quantum_idx:
        cat_preds = _predict(*models["quantum_category"],
                             [texts[i] for i in quantum_idx])
        for i, p in zip(quantum_idx, cat_preds):
            categories[i] = CATEGORY_MAPPING[p]
    for unit, qr_v, di_v, cat in zip(units, qr, di, categories):
        unit["quantum_related"] = bool(qr_v)
        unit["developer_intent"] = INTENT_MAPPING[di_v]
        unit["quantum_category"] = cat
    return units


def analyze_code(source_code, models=None):
    """Full pipeline on a Python snippet: extract -> segment -> classify.

    Returns (rows, parse_error, fallback_used).
    """
    units, error = extract_units(source_code)
    fallback = False
    if error or not units:
        raw = raw_text_units(source_code)
        if raw:
            units = raw
            fallback = True
        else:
            return [], error, False
    if models is not None:
        classify_units(units, models)
    return units, error, fallback
