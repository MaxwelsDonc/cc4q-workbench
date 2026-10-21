Command line
============

The ``cc4q`` console script mirrors the Python API one-to-one. Every
subcommand works standalone; run ``cc4q <command> --help`` for the exact
option list of the installed version.

.. code-block:: bash

   cc4q --help
   cc4q build --help

Commands
--------

.. list-table::
   :header-rows: 1
   :widths: 20 45 35

   * - Command
     - Main options
     - Purpose
   * - ``cc4q download-models``
     - ``--check``, ``--with-base``
     - Download/SHA256-verify/extract the released checkpoints. ``--check``
       only verifies and exits non-zero when incomplete; ``--with-base``
       also fetches ``bert-base-uncased`` so cold-start fine-tuning works
       offline.
   * - ``cc4q build``
     - ``--repo``, ``--output-dir``, ``--ref``, ``--include-dir``,
       ``--clean-mode``
     - Clone/scan a repository and write ``comment_pairs.json`` +
       ``sccus_segmented.json``.
   * - ``cc4q predict``
     - ``--input``, ``--output``, ``--models-dir``, ``--device``,
       ``--batch``
     - Label an SCCU corpus on both quantum axes.
   * - ``cc4q sample``
     - ``--input``, ``--output``, ``--by``, ``--n``, ``--frac``,
       ``--quotas``, ``--seed``
     - Random, stratified, or quota sampling over JSONL.
   * - ``cc4q annotate``
     - ``--data``, ``--output-dir``, ``--schema``, ``--labels``,
       ``--text-column``, ``--id-column``, ``--mode``, ``--predictions``,
       ``--dry-run``
     - Prepare/launch the annotation UI. ``--dry-run`` validates inputs and
       prints the session config path.
   * - ``cc4q train``
     - ``--task``, ``--data``, ``--output-dir``, ``--base-model``,
       ``--batch-size``, ``--epochs``, ``--dry-run``
     - Fine-tune one classifier. ``--dry-run`` validates the data contract.
   * - ``cc4q evaluate``
     - ``--annotations``, ``--key``, ``--id-join``, ``--contaminated``
     - Human-vs-model agreement, kappa, precision/recall, Wilson 95% CI,
       and per-repository breakdown.
   * - ``cc4q demo``
     - ``--host``, ``--port``
     - Launch the Workbench with reviewer quick-start defaults.
   * - ``cc4q serve``
     - ``--host``, ``--port``
     - Serve the Workbench on the given interface/port.

End-to-end example
------------------

.. code-block:: bash

   cc4q download-models
   cc4q build --repo https://github.com/qiskit-community/qiskit-algorithms \
       --include-dir qiskit_algorithms --output-dir out/algorithms
   cc4q predict --input out/algorithms/sccus_segmented.json \
       --output out/algorithms/labeled.jsonl
   cc4q sample --input out/algorithms/labeled.jsonl --by SDK --n 200 \
       --output out/algorithms/sample.jsonl
   cc4q annotate --data out/algorithms/sample.jsonl \
       --labels quantum,non-quantum --mode adjudicate \
       --predictions out/algorithms/labeled.jsonl \
       --output-dir out/algorithms/ann
   cc4q evaluate --annotations exp/spotcheck_annotation.csv \
       --key exp/spotcheck_answer_key.jsonl \
       --contaminated 1,8,16,25,62,132

.. note::

   ``--key`` expects a JSONL whose records carry an id column (matching
   ``--id-join``, default ``no``) and a ``model_label``/``label`` field.
   ``--contaminated`` accepts a comma-separated list of ids to exclude
   from evaluation (for example units that were part of training). The
   equivalent Python option is ``contaminated=...`` in
   :func:`cc4q.evaluate.evaluate_files`.
