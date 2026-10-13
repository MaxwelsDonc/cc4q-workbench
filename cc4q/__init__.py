"""CC4Q — build, inspect, and profile labeled comment corpora for
Python-based quantum SDKs.

Public API (imported lazily):

Pipeline:
    python_extract_comment_pairs, segment_docstring,
    segment_inline_comment, segment_block_comment, get_files_from_dir,
    read_config, id_generator

Models / inference (WP1):
    load_models, resolve_device, ensure_checkpoints

Prediction (WP1):
    predict_snippet, predict_corpus, extract_units, analyze_snippet

Training / evaluation (WP1):
    train, evaluate, evaluate_files
"""

import importlib

__version__ = "0.1.0"

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
    if name in _LAZY:
        module = importlib.import_module(_LAZY[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(_LAZY))
