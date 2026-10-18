The annotation loop
====================

Model-assisted annotation closes the CC4Q quality loop: predict, draw a
spot-check sample, have a human confirm or override in the UI, then score
agreement.

Schema
------

The UI is schema-driven -- any labels, any text/id columns:

.. code-block:: yaml

    # schema.yaml
    text_column: comment_text
    id_column: id
    labels: [quantum, non-quantum]

Modes
-----

* ``blind`` -- no model input; pure human labeling.
* ``adjudicate`` -- a predictions file (joined by the id column) shows the
  model suggestion for every item; the human confirms or overrides. Every
  item still requires a human click.

Progress persists to ``<output_dir>/annotations.jsonl``; reopening the UI
resumes at the first unlabeled item. The export (CSV and JSONL) adds a
``label`` column and is train-ready.

.. code-block:: python

    import cc4q

    sample = cc4q.sample(labeled, by=["SDK"], n=200, seed=42)
    cc4q.annotate(sample, schema="schema.yaml", mode="adjudicate",
                  model_predictions="labeled.jsonl",
                  output_dir="ann/")

or from the CLI:

.. code-block:: bash

    cc4q annotate --data sample.jsonl --schema schema.yaml --mode adjudicate --predictions labeled.jsonl --output-dir ann/

Sample -> annotate -> evaluate
------------------------------

.. code-block:: python

    import cc4q

    result = cc4q.evaluate_files(csv_path="ann/annotations.csv",
                                 key_path="labeled_key.jsonl",
                                 id_join="id",
                                 contaminated={"1", "8"})  # calibration items
    print(result["n"], result["agreement"], result["wilson95"])

``evaluate_files`` joins the exported annotations with the model answer
key, skips unlabeled rows, excludes contaminated (calibration) ids, and
reports agreement, precision, recall, and a Wilson 95% CI -- the same
statistics reported for the CC4Q spot-check (n=379, 85.0% agreement).

A runnable end-to-end version of this loop lives in
``examples/recipe_model_assisted_annotation.py`` (``run-all``), and
``walk-spotcheck`` replays the paper's 385-item spot-check through it.
