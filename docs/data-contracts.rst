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
      "developer_intent": "What",
      "quantum_category": "Quantum circuit model"
    }

Label vocabularies
------------------

Developer intent (6): ``What``, ``How-to-use``, ``How-it-is-done``,
``Property``, ``Why``, ``Others``.

Quantum category (6): ``Mathematics for quantum information``,
``Quantum algorithms``, ``Quantum circuit model``, ``Quantum hardware``,
``Quantum software framework``, ``Others``.

Comment type (3): ``docstring``, ``block``, ``inline``.
Code entity level (3): ``module``, ``class``, ``function``.

Training record per task
------------------------

* ``quantum_related``: ``{"comment": str, "label": 0|1}``
* ``quantum_category`` / ``developer_intent``:
  ``{"text": str, "label": 0..5}`` with indices following the orders above
  (intent: What=0 .. Others=5; category: Mathematics=0 .. Others=5).

Annotation schema
-----------------

.. code-block:: yaml

    text_column: comment_text   # record field shown to the annotator
    id_column: id               # join key (items, predictions, state)
    labels: [quantum, non-quantum]  # any cardinality
