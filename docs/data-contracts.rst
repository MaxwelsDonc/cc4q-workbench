Data contracts
==============

SCCU record (stage-03 / prediction output)
------------------------------------------

One JSON object per line:

.. code-block:: json

    {
      "id": "16-2",
      "SDK": "qiskit-machine-learning",
      "comment_type": "docstring",
      "comment_text": "This class can be used ...",
      "quantum_related": 1,
      "quantum_category": "Quantum circuit model"
    }

Label vocabularies
------------------

Two-stage Quantum-Specific taxonomy (v2.0). Task 1 decides whether a unit
is quantum-specific at all; Task 2 applies only to quantum units (the
retired ``developer_intent`` axis of v1 was dropped when the taxonomy was
refocused on quantum-specific knowledge for the companion study).

Quantum relatedness (2): ``quantum``, ``non-quantum``.

Quantum category (6): ``Mathematics for quantum information``,
``Quantum algorithms``, ``Quantum circuit model``, ``Quantum hardware``,
``Quantum software framework``, ``Others``.

Comment type (3): ``docstring``, ``block``, ``inline``.
Code entity level (3): ``module``, ``class``, ``function``.

Training record per task
------------------------

* ``quantum_related``: ``{"comment": str, "label": 0|1}``
* ``quantum_category``: ``{"text": str, "label": 0..5}`` with indices
  following the category order above (Mathematics=0 .. Others=5).

Annotation schema
-----------------

.. code-block:: yaml

    text_column: comment_text   # record field shown to the annotator
    id_column: id               # join key (items, predictions, state)
    labels: [quantum, non-quantum]  # any cardinality
