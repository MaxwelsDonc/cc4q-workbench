Corpus pipeline
===============

The pipeline turns a Python repository into sentence-level comment units
(SCCUs) in three stages:

1. **Extraction (stage 01)** walks the LibCST tree and emits one
   :class:`~cc4q.pipeline.types.CommentRecord` per docstring, inline
   comment, or contiguous block comment.
2. **Segmentation (stage 02)** splits each comment into sentence-level
   semantic blocks, with a dedicated path for Sphinx/reST docstrings.
3. **SCCU assembly (stage 03)** joins the segments back to their comment
   type, entity scope, file path, and source context.

.. py:module:: cc4q.pipeline

The package facade is lazy: ``cc4q.pipeline.segment_docstring``-style attributes
are resolved on first access. The canonical functions live in the
submodules below.

Extraction
----------

.. automodule:: cc4q.pipeline.extract

.. autofunction:: cc4q.pipeline.extract.python_extract_comment_pairs

.. autoclass:: cc4q.pipeline.types.CommentRecord
   :members:

.. autoclass:: cc4q.pipeline.visitor.LibCSTVisitor
   :members: get_records

Segmentation
------------

.. automodule:: cc4q.pipeline.segment.docstring

.. autofunction:: cc4q.pipeline.segment.docstring.segment_docstring

.. autofunction:: cc4q.pipeline.segment.docstring.parse_docstring_to_blocks

.. automodule:: cc4q.pipeline.segment.inline

.. autofunction:: cc4q.pipeline.segment.inline.segment_inline_comment

.. autofunction:: cc4q.pipeline.segment.inline.segment_inline_comment_advanced

.. automodule:: cc4q.pipeline.segment.block

.. autofunction:: cc4q.pipeline.segment.block.segment_block_comment

Stage-03 SCCU assembly
----------------------

.. automodule:: cc4q.pipeline.segment_pairs

.. autofunction:: cc4q.pipeline.segment_pairs.fix_rst_definition_lists

.. autofunction:: cc4q.pipeline.segment_pairs.segment_comment_pairs

Cleaning, configuration, and repository helpers
-----------------------------------------------

.. automodule:: cc4q.pipeline.clean

.. autoclass:: cc4q.pipeline.clean.CodeCleanMode
   :members:

.. autofunction:: cc4q.pipeline.clean.clean_code_snippet

.. automodule:: cc4q.pipeline.config

.. autofunction:: cc4q.pipeline.config.read_config

.. automodule:: cc4q.pipeline.download

.. autofunction:: cc4q.pipeline.download.clone_repo

.. automodule:: cc4q.pipeline.files

.. autofunction:: cc4q.pipeline.files.get_files_from_dir

.. automodule:: cc4q.pipeline.ids

.. autofunction:: cc4q.pipeline.ids.id_generator

.. automodule:: cc4q.pipeline.paths

.. autofunction:: cc4q.pipeline.paths.get_project_path

.. autofunction:: cc4q.pipeline.paths.split_path

Repository metrics
------------------

These helpers compute the comment-density and quantum-residence statistics
reported by the Workbench. They intentionally avoid torch/Streamlit imports.

.. automodule:: cc4q.pipeline.metrics

.. autofunction:: cc4q.pipeline.metrics.iter_py_files

.. autofunction:: cc4q.pipeline.metrics.count_comment_code_lines

.. autofunction:: cc4q.pipeline.metrics.compute_comment_density

.. autofunction:: cc4q.pipeline.metrics.quantum_residence
