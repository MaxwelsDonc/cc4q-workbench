Web Workbench HTTP API
======================

``cc4q serve`` starts a Starlette/Uvicorn server that serves the single-page
Workbench UI and a JSON API. The browser UI uses the same routes documented
here; they are also usable from scripts and notebooks.

.. automodule:: cc4q.web.server

.. autofunction:: cc4q.web.server.run_server

The ASGI application is available as ``cc4q.web.server.app``, and the route
list as ``cc4q.web.server.routes``, for embedding in another ASGI server.
The ``cc4q.web`` package also exposes ``WEB_DIR`` (package directory),
``STATIC_DIR`` (single-page UI assets), and ``DATA_DIR`` (precomputed demo
corpora).

Endpoints
---------

.. list-table::
   :header-rows: 1
   :widths: 8 32 60

   * - Method
     - Path
     - Purpose
   * - ``GET``
     - ``/``
     - Workbench single-page UI.
   * - ``GET``
     - ``/api/overview``
     - Manifest, corpora, model status, code presets, taxonomy, annotation
       count.
   * - ``GET``
     - ``/api/corpora/{corpus_id}/units``
     - Paginated/filterable SCCU units. Query parameters: ``quantum``
       (``all``/``quantum``/``non-quantum``), ``category``,
       ``comment_type``, ``entity_type``, ``q``, ``offset``, ``limit``.
   * - ``GET``
     - ``/api/corpora/{corpus_id}/download``
     - Download the corpus as JSONL.
   * - ``DELETE``
     - ``/api/corpora/{corpus_id}``
     - Delete a non-built-in corpus asset.
   * - ``POST``
     - ``/api/inspect``
     - Analyze a code snippet. Body: ``{"code": str, "model_id": str}``.
       Returns units, an automated documentation audit, parse error, and
       fallback flag.
   * - ``POST``
     - ``/api/pipeline/build``
     - Start a repository build job. Body: ``{"source_type":
       "url"|"dir", "target": str, "ref": str?, "name": str?,
       "run_predict": bool, "model_id": str}``.
   * - ``GET``
     - ``/api/pipeline/jobs/{job_id}``
     - Poll build progress (stage, progress, status, error).
   * - ``GET``
     - ``/api/annotations``
     - List annotation sessions.
   * - ``POST``
     - ``/api/annotations``
     - Create a session. Body: ``{"name": str?, "corpus_id": str?,
       "sample_size": int?, "stratify_by": [str]?, "mode": str?,
       "seed": int?, "records": [dict]?}``.
   * - ``GET``
     - ``/api/annotations/{session_id}``
     - Session metadata, items, and live agreement metrics.
   * - ``POST``
     - ``/api/annotations/{session_id}/label``
     - Store one human label. Body: ``{"item_id": str? | "index": int?,
       "human_quantum_related": bool, "human_quantum_category": str?,
       "notes": str?}``.
   * - ``GET``
     - ``/api/annotations/{session_id}/export``
     - Export annotations. Query parameter ``task`` is ``full`` (default),
       ``quantum_related``, or ``quantum_category`` (training-ready JSONL).
   * - ``DELETE``
     - ``/api/annotations/{session_id}``
     - Delete a session.
   * - ``GET``
     - ``/api/models``
     - Registered user models, training sources, and training jobs.
   * - ``POST``
     - ``/api/models/default``
     - Set the active model. Body: ``{"model_id": str}``; use ``released``
       for the released checkpoints.
   * - ``POST``
     - ``/api/models/train``
     - Start fine-tuning. Body: ``{"task": str, "source_type":
       "gold"|"session"|"upload", "session_id": str?, "records": [dict]?,
       "base_model": str, "epochs": int, "batch_size": int,
       "learning_rate": float, "max_samples": int?, "model_name": str?}``.
   * - ``GET``
     - ``/api/models/train/{job_id}``
     - Poll training progress (stage, step, history, test results).
   * - ``DELETE``
     - ``/api/models/{model_id}``
     - Delete a user model package.
   * - ``GET``
     - ``/api/models/{model_id}/download``
     - Download a user model package as a zip.
   * - ``POST``
     - ``/api/evaluations/run``
     - Compare two models on a corpus. Body: ``{"model_a": str,
       "model_b": str, "corpus_id": str, "max_units": int}``.

Examples
--------

Start the server and inspect the overview:

.. code-block:: bash

   cc4q serve --host 127.0.0.1 --port 8501
   curl -s http://127.0.0.1:8501/api/overview | python -m json.tool

Analyze a snippet:

.. code-block:: bash

   curl -s -X POST http://127.0.0.1:8501/api/inspect \
     -H 'Content-Type: application/json' \
     -d '{"code": "def f(qc):\n    # Apply a Hadamard gate\n    qc.h(0)\n"}'

.. note::

   Pipeline and training jobs run in background threads and are polled
   through their ``/jobs/{job_id}`` endpoints. The server keeps jobs in
   memory, so a restart clears completed/running job history.
