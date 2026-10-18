Training and evaluation
=======================

Training fine-tunes one of the two released classifiers on annotated or
corpus-derived records. Evaluation scores a human spot-check against a
model answer key, or compares two model runs on the same corpus.

.. py:module:: cc4q.train

Data contracts
--------------

Training input is JSONL, one record per line, with the task's canonical
text column and an integer label:

.. list-table::
   :header-rows: 1
   :widths: 28 22 50

   * - Task
     - Text column
     - Label
   * - ``quantum_related``
     - ``comment``
     - ``0`` (non-quantum) or ``1`` (quantum-specific)
   * - ``quantum_category``
     - ``text``
     - integer ``0``..``5`` in the category order from
       :doc:`/api/inference`

Annotation exports and corpus records are more flexible; use
:func:`cc4q.train.normalize_training_records` to convert them first.

Training
--------

.. autofunction:: cc4q.train.normalize_training_records

.. autofunction:: cc4q.train.resolve_base_model

.. autofunction:: cc4q.train.train

Example
~~~~~~~

.. code-block:: python

   from cc4q.train import normalize_training_records, train

   rows = [{"comment_text": r["comment_text"],
            "human_label": r["label"]} for r in annotated]
   normalized = normalize_training_records(rows, "quantum_related")
   # write normalized to JSONL, then:
   result = train("quantum_related", "train.jsonl", "out/qr",
                  base_model="released", epochs=10)
   print(result["test_results"])

Evaluation
----------

.. py:module:: cc4q.evaluate

.. autofunction:: cc4q.evaluate.evaluate

.. autofunction:: cc4q.evaluate.evaluate_files

.. autofunction:: cc4q.evaluate.cohen_kappa

.. autofunction:: cc4q.evaluate.wilson_ci

Evaluation output
~~~~~~~~~~~~~~~~~

:func:`~cc4q.evaluate.evaluate` returns ``n``, ``agreement``, ``kappa``,
``precision``, ``recall``, ``f1``, ``wilson95``, ``confusion`` (``tp`` /
``fp`` / ``fn`` / ``tn``), ``labels``, and the raw ``pairs``.
:func:`~cc4q.evaluate.evaluate_files` adds the same metrics per repository
under ``by_repo`` plus a ``disagreements`` list and ``skipped`` /
``excluded`` counts.

.. code-block:: python

   from cc4q.evaluate import evaluate_files

   result = evaluate_files(
       csv_path="ann/annotations.csv",
       key_path="out/key.jsonl",
       id_join="no",
   )
   print(f"{100 * result['agreement']:.1f}% "
         f"(95% CI {result['wilson95'][0]:.3f}-{result['wilson95'][1]:.3f})")
