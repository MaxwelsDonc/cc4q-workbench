Top-level Python API
====================

``import cc4q`` exposes the most common entry points as lazy aliases. The
aliases keep import time low (no torch/transformers/spaCy import until you
touch a model or a segmenter) and mirror the command-line workflow.

.. automodule:: cc4q

Grouped aliases
---------------

Corpus construction
~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 34 44 22

   * - Top-level alias
     - Canonical API
     - Purpose
   * - ``cc4q.python_extract_comment_pairs(...)``
     - :func:`cc4q.pipeline.extract.python_extract_comment_pairs`
     - Source file -> comment/code pairs (stage 01).
   * - ``cc4q.segment_docstring(...)``
     - :func:`cc4q.pipeline.segment.docstring.segment_docstring`
     - reST/Sphinx docstring -> semantic blocks (stage 02).
   * - ``cc4q.segment_inline_comment(...)``
     - :func:`cc4q.pipeline.segment.inline.segment_inline_comment`
     - Inline comment -> sentences (stage 02).
   * - ``cc4q.segment_block_comment(...)``
     - :func:`cc4q.pipeline.segment.block.segment_block_comment`
     - Block comment -> sentences (stage 02).
   * - ``cc4q.clean_code_snippet(...)``
     - :func:`cc4q.pipeline.clean.clean_code_snippet`
     - Apply a code-context cleaning policy.
   * - ``cc4q.get_files_from_dir(...)``
     - :func:`cc4q.pipeline.files.get_files_from_dir`
     - Discover ``.py`` files under a checkout.
   * - ``cc4q.read_config(...)``
     - :func:`cc4q.pipeline.config.read_config`
     - Load a YAML pipeline config.
   * - ``cc4q.clone_repo(...)``
     - :func:`cc4q.pipeline.download.clone_repo`
     - Shallow-clone a repository at a pinned ref.
   * - ``cc4q.id_generator(...)``
     - :func:`cc4q.pipeline.ids.id_generator`
     - Deterministic record ids.
   * - ``cc4q.get_project_path()``
     - :func:`cc4q.pipeline.paths.get_project_path`
     - Repository root of a source checkout.
   * - ``cc4q.split_path(...)``
     - :func:`cc4q.pipeline.paths.split_path`
     - Normalize a path into components.
   * - ``cc4q.CommentRecord``
     - :class:`cc4q.pipeline.types.CommentRecord`
     - Typed record exchanged by the stages.
   * - ``cc4q.LibCSTVisitor``
     - :class:`cc4q.pipeline.visitor.LibCSTVisitor`
     - Low-level LibCST extractor.

Models and inference
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 34 44 22

   * - Top-level alias
     - Canonical API
     - Purpose
   * - ``cc4q.load_models(...)``
     - :func:`cc4q.models.hub.load_models`
     - Load both released classifiers in eval mode.
   * - ``cc4q.resolve_device(...)``
     - :func:`cc4q.models.hub.resolve_device`
     - Resolve ``cuda``/``cpu``/``mps`` from arguments/env.
   * - ``cc4q.ensure_checkpoints(...)``
     - :func:`cc4q.models.hub.ensure_checkpoints`
     - Download, verify, and extract missing checkpoints.
   * - ``cc4q.predict_snippet(...)``
     - :func:`cc4q.predict.predict_snippet`
     - Extract -> segment -> classify one snippet.
   * - ``cc4q.predict_corpus(...)``
     - :func:`cc4q.predict.predict_corpus`
     - Label an SCCU corpus on both quantum axes.
   * - ``cc4q.extract_units(...)``
     - :func:`cc4q.predict.extract_units`
     - Extract and segment a snippet without a model.
   * - ``cc4q.analyze_snippet(...)``
     - :func:`cc4q.predict.analyze_snippet`
     - Full snippet pipeline with parser fallback.

Training, evaluation, sampling, annotation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 34 44 22

   * - Top-level alias
     - Canonical API
     - Purpose
   * - ``cc4q.train(...)``
     - :func:`cc4q.train.train`
     - Fine-tune one quantum classifier.
   * - ``cc4q.evaluate(...)``
     - :func:`cc4q.evaluate.evaluate`
     - Agreement, kappa, precision/recall/F1, Wilson CI.
   * - ``cc4q.evaluate_files(...)``
     - :func:`cc4q.evaluate.evaluate_files`
     - Spot-check evaluation from CSV/JSONL + answer key.
   * - ``cc4q.sample(...)``
     - :func:`cc4q.sample.sample`
     - Random, stratified, or quota sampling.
   * - ``cc4q.annotate(...)``
     - :func:`cc4q.annotate.annotate`
     - Launch the interactive annotation UI.
   * - ``cc4q.workspace``
     - :mod:`cc4q.workspace`
     - Asset/workspace persistence module.

.. note::

   The top-level names are **aliases**, not separate implementations. Use
   the canonical module path when you need module-level helpers, for
   example ``from cc4q.train import normalize_training_records`` or
   ``from cc4q.models.hub import load_models_from``. For new code, importing
   from the canonical module is the most explicit option.

Example
-------

.. code-block:: python

   from cc4q import load_models, predict_corpus, sample

   models = load_models()                       # auto-download once
   labeled = predict_corpus("out/sccus_segmented.json", models=models)
   spot_check = sample(labeled, by=["SDK"], n=200, seed=42)

The same functions are available through the CLI (see :doc:`/api/cli`) and
the Workbench HTTP API (see :doc:`/api/web`).
