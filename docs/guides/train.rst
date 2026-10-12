Train on your annotated data
=============================

``cc4q.train`` fine-tunes one of the three classifiers with the HF
Trainer, using the same recipe as the released models.

Data contract
-------------

JSONL, one record per line:

.. list-table::
   :header-rows: 1

   * - task
     - text column
     - label column
   * - ``quantum_related``
     - ``comment``
     - int ``0`` or ``1``
   * - ``quantum_category``
     - ``text``
     - int ``0``..``5``
   * - ``developer_intent``
     - ``text``
     - int ``0``..``5``

The label indices follow the category order documented in
:doc:`../data-contracts`. Violations raise a ``ValueError`` that names the
problem rows and shows an example record.

.. code-block:: python

    import cc4q

    cc4q.train("quantum_related", "my_annotations.jsonl",
               output_dir="out/my_qr_classifier",
               base_model="bert-base-uncased",
               batch_size=32, epochs=30)

Validate a training file without training:

.. code-block:: bash

    cc4q train --task quantum_related --data my_annotations.jsonl \
        --output-dir out/x --dry-run

The train-ready export of the annotation UI already satisfies this
contract: annotate first (see :doc:`annotate`), then train on the exported
``annotations.jsonl`` (add an ``id``/text column mapping via the schema if
your text column is not the task's default).
