"""CC4Q — build, inspect, and profile labeled comment corpora for
Python-based quantum SDKs.

The package conveniences are imported lazily so ``import cc4q`` stays cheap.
Canonical module APIs live in the submodules listed below; the top-level
names are aliases for the most common entry points.

Pipeline:
    :func:`cc4q.pipeline.extract.python_extract_comment_pairs`, :func:`cc4q.pipeline.segment.docstring.segment_docstring`,
    :func:`cc4q.pipeline.segment.inline.segment_inline_comment`, :func:`cc4q.pipeline.segment.block.segment_block_comment`,
    :func:`cc4q.pipeline.files.get_files_from_dir`, :func:`cc4q.pipeline.config.read_config`, :func:`cc4q.pipeline.ids.id_generator`

Models / inference:
    :func:`cc4q.models.hub.load_models`, :func:`cc4q.models.hub.resolve_device`, :func:`cc4q.models.hub.ensure_checkpoints`

Prediction:
    :func:`cc4q.predict.predict_snippet`, :func:`cc4q.predict.predict_corpus`, :func:`cc4q.predict.extract_units`,
    :func:`cc4q.predict.analyze_snippet`

Training / evaluation:
    :func:`cc4q.train.train`, :func:`cc4q.evaluate.evaluate`, :func:`cc4q.evaluate.evaluate_files`

Sampling / annotation:
    :func:`cc4q.sample.sample`, :func:`cc4q.annotate.annotate`

Persistence:
    :mod:`cc4q.workspace`, :mod:`cc4q.registry`

See :doc:`/api/python` for the grouped top-level API and
:doc:`/api/modules` for the module map.
"""

import importlib

__version__ = "0.2.0"

_LAZY = {
    # pipeline
    "python_extract_comment_pairs": "cc4q.pipeline.extract",
    "CommentRecord": "cc4q.pipeline.types",
    "LibCSTVisitor": "cc4q.pipeline.visitor",
    "clean_code_snippet": "cc4q.pipeline.clean",
    "segment_docstring": "cc4q.pipeline.segment.docstring",
    "segment_inline_comment": "cc4q.pipeline.segment.inline",
    "segment_block_comment": "cc4q.pipeline.segment.block",
    "get_files_from_dir": "cc4q.pipeline.files",
    "get_project_path": "cc4q.pipeline.paths",
    "split_path": "cc4q.pipeline.paths",
    "id_generator": "cc4q.pipeline.ids",
    "read_config": "cc4q.pipeline.config",
    "clone_repo": "cc4q.pipeline.download",
    # models + prediction (WP1)
    "load_models": "cc4q.models.hub",
    "resolve_device": "cc4q.models.hub",
    "ensure_checkpoints": "cc4q.models.hub",
    "predict_snippet": "cc4q.predict",
    "predict_corpus": "cc4q.predict",
    "extract_units": "cc4q.predict",
    "analyze_snippet": "cc4q.predict",
    # training + evaluation (WP1)
    "train": "cc4q.train",
    "evaluate": "cc4q.evaluate",
    "evaluate_files": "cc4q.evaluate",
    # sampling + annotation (WP3)
    "sample": "cc4q.sample",
    "annotate": "cc4q.annotate",
    # workspace persistence (WP4)
    "workspace": "cc4q.workspace",
}

__all__ = sorted(_LAZY)


def __getattr__(name):
    if name not in _LAZY:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(_LAZY[name])
    # ``workspace`` is a public module, not a function re-export.
    value = module if name == "workspace" else getattr(module, name)
    globals()[name] = value
    return value


def __dir__():
    return sorted(set(globals()) | set(_LAZY))
