"""Analysis helpers for the CC4Q Streamlit demo.

Thin wrapper over the cc4q package: the pipeline implementation lives in
cc4q.pipeline / cc4q.predict / cc4q.models.hub; this module keeps the demo's
historic import surface (QISKIT_SNIPPET, analyze_code, load_models, DEVICE)
and is importable without Streamlit for smoke tests:

    from cc4q.app.analysis import analyze_code, load_models
    models = load_models()
    units, error, fallback = analyze_code(QISKIT_SNIPPET, models)
"""

import cc4q.predict as _predict  # noqa: F401
from cc4q.models.hub import load_models, resolve_device  # noqa: F401
from cc4q.predict import (analyze_snippet, classify_units, extract_units,  # noqa: F401
                          raw_text_units)

# historic API name used by the pages and smoke tests
analyze_code = analyze_snippet
# predict_snippet defaults to lazy model loading when models=None; the demo
# always passes an explicit handle, but keep the old permissive signature.
_DEVICE_RESOLVER = resolve_device
DEVICE = _DEVICE_RESOLVER()

QISKIT_SNIPPET = '''from qiskit import QuantumCircuit, transpile


def build_bell_state(backend):
    """Create a Bell state circuit on two qubits.

    The circuit applies a Hadamard gate on the first qubit
    followed by a CNOT gate, which entangles the two qubits.

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


def classify_sccu_records(records, models):
    """Label pipeline-style SCCU records (``comment_text`` key), in place.

    Kept for the live-repo path; equivalent to cc4q.predict.predict_corpus
    on an in-memory list.
    """
    import cc4q.predict
    return cc4q.predict.predict_corpus(records, models=models)
