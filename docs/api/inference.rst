Inference
=========

Prediction uses the two-stage taxonomy: Task 1 decides whether a unit is
quantum-specific; Task 2 assigns one of six quantum-knowledge categories
only to quantum units. Both stages return calibrated softmax probabilities
so downstream sampling/annotation can prioritize uncertain units.

.. py:module:: cc4q.predict

Output fields
-------------

:func:`~cc4q.predict.predict_corpus` and
:func:`~cc4q.predict.predict_snippet` add these fields to each SCCU:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Field
     - Meaning
   * - ``quantum_related``
     - ``1``/``0`` in corpus output, boolean in snippet/detailed output.
   * - ``quantum_prob``
     - Probability that the unit is quantum-specific.
   * - ``quantum_category``
     - One of the six category names, or ``None`` for non-quantum units.
   * - ``category_confidence``
     - Probability of the predicted category, or ``None``.
   * - ``category_probs``
     - Full category distribution (detailed/snippet output only).

Category order
--------------

The order is exposed programmatically as ``CATEGORY_LIST`` (names) and
``CATEGORY_MAPPING`` (index -> name) in ``cc4q.predict``.

.. list-table::
   :header-rows: 1
   :widths: 10 90

   * - Index
     - Category
   * - 0
     - Mathematics for quantum information
   * - 1
     - Quantum algorithms
   * - 2
     - Quantum circuit model
   * - 3
     - Quantum hardware
   * - 4
     - Quantum software framework
   * - 5
     - Others

Functions
---------

.. autofunction:: cc4q.predict.predict_quantum_detailed

.. autofunction:: cc4q.predict.predict_labels

.. autofunction:: cc4q.predict.predict_corpus

.. autofunction:: cc4q.predict.predict_snippet

Snippet pipeline
----------------

.. autofunction:: cc4q.predict.extract_units

.. autofunction:: cc4q.predict.classify_units

.. autofunction:: cc4q.predict.analyze_snippet

.. autofunction:: cc4q.predict.raw_text_units

.. autofunction:: cc4q.predict.compact_snippet

Examples
--------

Corpus labeling:

.. code-block:: python

   from cc4q.predict import predict_corpus
   from cc4q.models.hub import load_models

   models = load_models()
   labeled = predict_corpus("out/sccus_segmented.json", models=models)
   quantum = [r for r in labeled if r["quantum_related"]]

Snippet inspection (also handles non-Python input through the line-by-line
fallback):

.. code-block:: python

   from cc4q.predict import predict_snippet

   units, parse_error, fallback = predict_snippet(code, models=models)
   for unit in units:
       print(unit["comment_text"], unit["quantum_related"],
             unit["quantum_category"])
