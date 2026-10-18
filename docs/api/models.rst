Model hub
=========

The model layer downloads, verifies, and loads the two fine-tuned
quantum-specific BERT classifiers:

* **Task 1 — quantum relatedness** (binary): is this SCCU
  quantum-specific?
* **Task 2 — quantum category** (six classes): Mathematics, Algorithms,
  Circuit model, Hardware, Software framework, Others.

.. py:module:: cc4q.models

``cc4q.models`` is a thin re-export facade. The canonical implementation
(and the only module with the full helper set) is
:mod:`cc4q.models.hub`.

Checkpoint layout
-----------------

Checkpoints are stored under a single root (``models_checkpoints/`` in a
source checkout, ``~/.cache/cc4q/models_checkpoints`` for wheel installs):

.. code-block:: text

   models_checkpoints/
   ├── quantum_related/
   │   ├── config.json
   │   ├── model.safetensors
   │   └── tokenizer_config.json
   └── quantum_category/
       ├── config.json
       ├── model.safetensors
       └── tokenizer_config.json

Released assets are downloaded from GitHub Releases and checked against
the SHA256 digests in ``CHECKPOINTS``.

.. automodule:: cc4q.models.hub

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Constant
     - Value / meaning
   * - ``RELEASE``
     - Release tag of the published checkpoints.
   * - ``RELEASE_REPO``
     - GitHub repository that hosts the release assets.
   * - ``BASE_URL``
     - Download prefix for release assets.
   * - ``CHECKPOINTS``
     - Mapping of archive name -> ``(axis_dir, sha256)`` for the two
       quantum classifiers.
   * - ``BASE_MODEL``
     - Optional ``bert-base-uncased`` archive used for from-scratch
       fine-tuning.
   * - ``REQUIRED_FILES``
     - Files that must exist for a checkpoint directory to be usable.

Device and checkpoint helpers
-----------------------------

.. autofunction:: cc4q.models.hub.default_model_dir

.. autofunction:: cc4q.models.hub.resolve_device

.. autofunction:: cc4q.models.hub.checkpoint_complete

.. autofunction:: cc4q.models.hub.missing_checkpoints

.. autofunction:: cc4q.models.hub.ensure_checkpoints

Loading classifiers
-------------------

.. autoclass:: cc4q.models.hub.ModelHandle
   :members:

.. autofunction:: cc4q.models.hub.load_models

.. autofunction:: cc4q.models.hub.load_models_from

Example
-------

.. code-block:: python

   from cc4q.models.hub import load_models, load_models_from

   # released checkpoints (downloaded on first use)
   models = load_models(device="cuda")

   # mix a user-trained Task-2 classifier with the released Task-1 model
   mixed = load_models_from(
       {"quantum_related": None,
        "quantum_category": "outputs/my_category_model"},
       device="cpu",
   )
