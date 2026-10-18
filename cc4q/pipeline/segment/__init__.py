"""Comment segmentation (lazy re-exports; importing a segmenter loads the
spaCy English model)."""

import importlib

_LAZY = {
    "segment_docstring": "cc4q.pipeline.segment.docstring",
    "segment_inline_comment": "cc4q.pipeline.segment.inline",
    "segment_block_comment": "cc4q.pipeline.segment.block",
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
    return sorted(_LAZY)
