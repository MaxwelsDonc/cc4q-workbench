API reference
=============

CC4Q Workbench exposes the same corpus-construction and analysis capabilities through
three interfaces:

* the **Web Workbench** (``cc4q serve`` / ``cc4q demo``),
* the **command line** (``cc4q <command>``),
* the **Python library** (``import cc4q``).

The reference is grouped by workflow rather than by file layout. Each page
lists every public function/class with its signature and docstring, and the
module index maps the implementation modules onto those groups.

.. note::

   A name is part of the public API when it appears on one of these pages or
   in a module's ``__all__``. Names starting with ``_`` are implementation
   details and may change without notice. The API-coverage check
   (``docs/check_api_coverage.py``) fails CI when a public name disappears
   from the reference.

API map
-------

.. list-table::
   :header-rows: 1
   :widths: 22 30 48

   * - Interface / area
     - Entry point
     - What it covers
   * - Python, top level
     - :doc:`api/python`
     - Lazy convenience aliases such as ``cc4q.load_models`` and
       ``cc4q.predict_corpus``.
   * - Corpus pipeline
     - :doc:`api/pipeline`
     - LibCST extraction (stage 01), docstring/inline/block segmentation
       (stage 02), SCCU segmentation (stage 03), cleaning, config, metrics.
   * - Models
     - :doc:`api/models`
     - Checkpoint download/verification, device resolution, lazy BERT
       loading.
   * - Inference
     - :doc:`api/inference`
     - Snippet and corpus labeling, confidence scores, unit extraction,
       parser fallback.
   * - Training and evaluation
     - :doc:`api/training`
     - Fine-tuning, schema normalization, agreement/kappa/Wilson metrics.
   * - Sampling and annotation
     - :doc:`api/annotation`
     - Random/stratified/quota sampling, annotation sessions, embedded UI.
   * - Workspace and registry
     - :doc:`api/workspace`
     - Asset persistence, JSONL payloads, user model packages.
   * - Web Workbench HTTP API
     - :doc:`api/web`
     - Starlette routes used by the browser UI, with request/response notes.
   * - Command line
     - :doc:`api/cli`
     - Every ``cc4q`` subcommand and its options.
   * - Module index
     - :doc:`api/modules`
     - All public modules, including the ones that are implementation
       details behind a facade.

API sections
------------

.. toctree::
   :maxdepth: 1

   api/python
   api/pipeline
   api/models
   api/inference
   api/training
   api/annotation
   api/workspace
   api/web
   api/cli
   api/modules
