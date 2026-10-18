Workspace and model registry
============================

The Workbench persists user work as **assets** in a JSON-indexed workspace
and keeps user-trained model packages in a separate **registry**. Both
layers are plain files; there is no database.

Workspace
---------

Directory resolution: ``$CC4Q_WORKSPACE`` > ``.cc4q_workspace/`` next to a
source checkout > ``~/.cache/cc4q/workspace`` for wheel installs.

.. automodule:: cc4q.workspace

Asset types
~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 26 22 52

   * - Type
     - Required fields
     - Purpose
   * - ``corpus``
     - ``name``, ``source``
     - SCCU records (raw or labeled); ``files`` points at the JSONL
       payloads.
   * - ``annotation_session``
     - ``name``, ``schema``, ``mode``
     - One annotation round, with ``total``/``labeled_count`` progress.
   * - ``evaluation``
     - ``name``, ``pair``
     - A model-pair comparison report and metrics.

Assets also carry a short ``id``, ``created_at``, and (after updates) an
``updated_at`` timestamp. The index is written atomically; a corrupt
``index.json`` is backed up to ``index.json.bak`` and rebuilt empty.

Lifecycle helpers
~~~~~~~~~~~~~~~~~

.. autofunction:: cc4q.workspace.workspace_dir

.. autofunction:: cc4q.workspace.create_asset

.. autofunction:: cc4q.workspace.list_assets

.. autofunction:: cc4q.workspace.get_asset

.. autofunction:: cc4q.workspace.update_asset

.. autofunction:: cc4q.workspace.rename_asset

.. autofunction:: cc4q.workspace.delete_asset

.. autofunction:: cc4q.workspace.export_asset

Payload helpers
~~~~~~~~~~~~~~~

.. autofunction:: cc4q.workspace.asset_path

.. autofunction:: cc4q.workspace.write_jsonl

.. autofunction:: cc4q.workspace.read_jsonl

.. autofunction:: cc4q.workspace.list_models

Model registry
--------------

A user model package is a directory with one sub-directory per axis it
provides (``quantum_related`` and/or ``quantum_category``), each a Hugging
Face model directory. Packages may provide a single axis; missing axes fall
back to the released checkpoints at prediction time.

Registry location: ``$CC4Q_USER_MODELS`` > ``user_models/`` next to a
source checkout > ``~/.cache/cc4q/user_models``.

.. automodule:: cc4q.registry

.. autofunction:: cc4q.registry.registry_root

.. autofunction:: cc4q.registry.list_models

.. autofunction:: cc4q.registry.package_dir

.. autofunction:: cc4q.registry.register

.. autofunction:: cc4q.registry.register_uploaded_zip

.. autofunction:: cc4q.registry.set_default

.. autofunction:: cc4q.registry.delete

.. autofunction:: cc4q.registry.zip_package

Example
-------

.. code-block:: python

   from cc4q import workspace as ws

   corpus = ws.create_asset(
       "corpus", name="qiskit-nature", source="url", sdk="qiskit-nature",
       version="0.7.2", sccus=1200, labeled=False,
   )
   path = ws.write_jsonl(corpus["id"], "corpus.jsonl", records)
   ws.update_asset(corpus["id"], files={"corpus": path})
