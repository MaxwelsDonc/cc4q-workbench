Sampling and annotation
=======================

CC4Q Workbench samples a small, reproducible spot-check from a labeled corpus, then
collects human labels in a schema-driven Streamlit UI. The same session can
be exported directly as a training file.

.. py:module:: cc4q.sample

Sampling
--------

Three modes are available over any list of records or JSONL file:

* **random** — ``sample(data, n=200)`` or ``frac=0.1``;
* **stratified** — ``sample(data, by=["SDK"], n=200)`` allocates the sample
  proportionally across strata;
* **quota** — ``sample(data, by=["SDK"], quotas={"qiskit": 100})`` uses
  explicit per-stratum sizes.

.. autofunction:: cc4q.sample.sample

Annotation
----------

.. py:module:: cc4q.annotate

The standalone UI is launched by :func:`cc4q.annotate.annotate` (or
``cc4q annotate``). The UI is schema-driven: any text column, id column,
and label vocabulary can be used. Progress is written to
``<output_dir>/annotations.jsonl`` and resumes after a restart.

.. autofunction:: cc4q.annotate.prepare

.. autofunction:: cc4q.annotate.annotate

Schema
------

.. code-block:: yaml

   text_column: comment_text
   id_column: id
   labels: [quantum, non-quantum]
   title: Quantum comment spot-check   # optional

Modes
-----

``blind``
   No model input; pure human labeling.

``adjudicate``
   A predictions file joined by the id column shows the model suggestion
   for every item. The human still confirms or overrides every item.

Embedding the UI
----------------

.. autofunction:: cc4q.annotate.ui.render_annotation

The Workbench embeds :func:`~cc4q.annotate.ui.render_annotation` in its
Annotate page; the standalone app in ``cc4q/annotate/app.py`` is a thin
launcher around the same renderer. ``cc4q.annotate.prepare`` is also useful
for validating a session in CI without starting Streamlit.

Example
-------

.. code-block:: python

   from cc4q.sample import sample
   from cc4q.annotate import annotate

   spot = sample("out/labeled.jsonl", by=["SDK"], n=200, seed=42)
   annotate(
       spot,
       schema={"text_column": "comment_text", "id_column": "id",
               "labels": ["quantum", "non-quantum"]},
       mode="adjudicate",
       model_predictions="out/labeled.jsonl",
       output_dir="out/ann",
   )

.. note::

   ``cc4q.annotate.app`` is a Streamlit entrypoint, not an importable API.
   Use :func:`cc4q.annotate.annotate` or the ``cc4q annotate`` command.
