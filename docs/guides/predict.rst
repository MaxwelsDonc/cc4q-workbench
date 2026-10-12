Predict with released or custom models
======================================

``cc4q.predict_corpus`` labels SCCU records (pipeline stage-03 output, one
JSON object with a ``comment_text`` field per line) on the three CC4Q
axes:

* ``quantum_related`` -- 0/1, is the unit quantum related?
* ``developer_intent`` -- one of What / How-to-use / How-it-is-done /
  Property / Why / Others.
* ``quantum_category`` -- one of the six quantum-knowledge categories, or
  ``null`` for non-quantum units.

.. code-block:: python

    import cc4q

    models = cc4q.load_models()            # released checkpoints
    labeled = cc4q.predict_corpus("sccus_segmented.json", models=models)

    # or point at your own fine-tuned checkpoints:
    custom = cc4q.load_models(model_dir="/path/to/my_checkpoints",
                              device="cuda")

The returned records carry the exact schema of the released CC4Q corpora,
so they feed directly into sampling, annotation, and evaluation.

For a single code snippet, ``cc4q.predict_snippet`` runs the full
extract -> segment -> classify pipeline and falls back to line-by-line
classification when the input is not valid Python:

.. code-block:: python

    units, error, fallback = cc4q.predict_snippet(code, models=models)

Device selection
----------------

``cc4q.load_models`` resolves the device automatically: explicit ``device``
argument > ``CC4Q_DEVICE`` environment variable > CUDA if available > CPU.
MPS is never selected automatically (it hangs with some torch builds); opt
in with ``CC4Q_DEVICE=mps``.
