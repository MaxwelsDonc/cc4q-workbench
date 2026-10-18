Module index
============

This page maps every module in the installed package to its role and the
API page that documents its public objects. Facade modules (``cc4q``,
``cc4q.pipeline``, ``cc4q.models``) are intentionally thin: their
attributes are lazy aliases, and the implementation lives in submodules.

.. list-table::
   :header-rows: 1
   :widths: 34 30 36

   * - Module
     - Role
     - Documented in
   * - ``cc4q``
     - Lazy top-level facade (``__all__`` aliases)
     - :doc:`/api/python`
   * - ``cc4q.cli``
     - Typer command-line entry point
     - :doc:`/api/cli`
   * - ``cc4q.pipeline``
     - Lazy pipeline facade
     - :doc:`/api/pipeline`
   * - ``cc4q.pipeline.segment``
     - Lazy segmentation facade
     - :doc:`/api/pipeline`
   * - ``cc4q.pipeline.extract``
     - Stage 01: LibCST extraction
     - :doc:`/api/pipeline`
   * - ``cc4q.pipeline.segment.docstring``
     - Stage 02: Sphinx/reST docstring segmentation
     - :doc:`/api/pipeline`
   * - ``cc4q.pipeline.segment.inline``
     - Stage 02: inline-comment sentence splitting
     - :doc:`/api/pipeline`
   * - ``cc4q.pipeline.segment.block``
     - Stage 02: block-comment segmentation
     - :doc:`/api/pipeline`
   * - ``cc4q.pipeline.segment_pairs``
     - Stage 03: SCCU assembly and JSON I/O
     - :doc:`/api/pipeline`
   * - ``cc4q.pipeline.clean``
     - Code-context cleaning policies
     - :doc:`/api/pipeline`
   * - ``cc4q.pipeline.config``
     - YAML config loading
     - :doc:`/api/pipeline`
   * - ``cc4q.pipeline.download``
     - Repository cloning
     - :doc:`/api/pipeline`
   * - ``cc4q.pipeline.files``
     - Python-file discovery
     - :doc:`/api/pipeline`
   * - ``cc4q.pipeline.ids``
     - Record id generation
     - :doc:`/api/pipeline`
   * - ``cc4q.pipeline.metrics``
     - Comment-density and quantum-residence metrics
     - :doc:`/api/pipeline`
   * - ``cc4q.pipeline.paths``
     - Repository-root/path helpers
     - :doc:`/api/pipeline`
   * - ``cc4q.pipeline.types``
     - :class:`~cc4q.pipeline.types.CommentRecord`
     - :doc:`/api/pipeline`
   * - ``cc4q.pipeline.visitor``
     - Low-level LibCST visitor
     - :doc:`/api/pipeline`
   * - ``cc4q.models``
     - Model-layer re-export facade
     - :doc:`/api/models`
   * - ``cc4q.models.hub``
     - Checkpoints, device resolution, classifier loading
     - :doc:`/api/models`
   * - ``cc4q.predict``
     - Snippet/corpus inference and fallback
     - :doc:`/api/inference`
   * - ``cc4q.train``
     - Fine-tuning and schema normalization
     - :doc:`/api/training`
   * - ``cc4q.evaluate``
     - Agreement, kappa, precision/recall, Wilson CI
     - :doc:`/api/training`
   * - ``cc4q.sample``
     - Random/stratified/quota sampling
     - :doc:`/api/annotation`
   * - ``cc4q.annotate``
     - Session preparation and Streamlit launch
     - :doc:`/api/annotation`
   * - ``cc4q.annotate.ui``
     - Reusable annotation renderer (also embedded in the Workbench)
     - :doc:`/api/annotation`
   * - ``cc4q.annotate.app``
     - Streamlit entrypoint; no importable public API
     - :doc:`/api/annotation`
   * - ``cc4q.workspace``
     - Asset/workspace persistence
     - :doc:`/api/workspace`
   * - ``cc4q.registry``
     - User model package registry
     - :doc:`/api/workspace`
   * - ``cc4q.web``
     - Static/data directory constants for the Workbench
     - :doc:`/api/web`
   * - ``cc4q.web.server``
     - Starlette app, routes, and Uvicorn launcher
     - :doc:`/api/web`

Facades and implementation details
----------------------------------

* ``cc4q.pipeline`` and ``cc4q`` use module-level ``__getattr__`` to import
  heavy dependencies only when a name is first touched. Their ``__all__``
  lists the supported aliases.
* ``cc4q.models`` re-exports the model-hub API for a shorter import path;
  new code can import from ``cc4q.models.hub`` directly.
* Route handlers in ``cc4q.web.server`` and helpers prefixed with ``_`` are
  implementation details. The HTTP surface is the endpoint table in
  :doc:`/api/web`; the Python-callable surface is ``run_server``, ``app``,
  and ``routes``.
* ``cc4q.annotate.app`` executes on import (it is launched by
  ``streamlit run``), so it is deliberately not documented as a library
  module.

API coverage
------------

``docs/check_api_coverage.py`` imports every public module, reads its
``__all__``, and verifies that each name appears as an ``autofunction``,
``autoclass``, or ``autodata`` entry in this documentation tree. The docs
CI workflow runs it before ``sphinx-build -W``. When adding a public
function, add its docstring and its directive on the matching API page; the
checker fails otherwise.
