"""CC4Q pipeline: comment-pair extraction and semantic segmentation.

Heavy submodules (libcst/spacy/docutils) are imported lazily so that
``import cc4q`` stays cheap; attribute access pulls in what you use.
"""

import importlib

_LAZY = {
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
    "compute_comment_density": "cc4q.pipeline.metrics",
    "quantum_residence": "cc4q.pipeline.metrics",
}


def __getattr__(name):
    if name in _LAZY:
        module = importlib.import_module(_LAZY[name])
        value = getattr(module, name)
        globals()[name] = value  # cache for subsequent accesses
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(_LAZY)
