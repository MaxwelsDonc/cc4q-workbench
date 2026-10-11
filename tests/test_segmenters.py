"""Comment-segmentation unit tests.

The cases come from scripts/test_segment.py (kept as a runnable usage
example); here they are real assertions. The demo smoke suite exercises the
same segmenters end-to-end through the full pipeline.

Imports are skipped (not failed) when the spaCy English model is missing,
so data-only tests still run on lean checkouts.
"""

import pytest

_SPACY_HINT = ("spaCy English model not available "
               "(python -m spacy download en_core_web_sm)")

_docstring_segmenter = pytest.importorskip(
    "segment_core.python_segment.docstring_segmenter", reason=_SPACY_HINT)
_inline_segmenter = pytest.importorskip(
    "segment_core.python_segment.inline_comment_segmenter", reason=_SPACY_HINT)
_block_segmenter = pytest.importorskip(
    "segment_core.python_segment.block_comment_segmenter", reason=_SPACY_HINT)

segment_docstring = _docstring_segmenter.segment_docstring
segment_inline_comment = _inline_segmenter.segment_inline_comment
segment_block_comment = _block_segmenter.segment_block_comment

DOCSTRING_TEXT = (
    "Calculate quantum state.\n    \n    Args:\n        state: Initial state"
    "\n        \n    Returns:\n        Final state\n    "
)
INLINE_TEXT = "Initialize quantum register. Apply gates sequentially. Measure results."
BLOCK_TEXT = (
    "This module implements quantum algorithms.\n"
    "    It provides various optimization functions.\n"
    "    Performance is O(n²) complexity."
)
SIMPLE_DOCSTRING = "Helper function for converting a circuit to a gate"


def test_docstring_segmentation():
    blocks = segment_docstring(DOCSTRING_TEXT)
    assert len(blocks) == 2
    assert blocks[0]["type"] == "paragraph"
    assert blocks[0]["content"].startswith("Calculate quantum state.")
    assert blocks[1]["type"] == "block_quote"
    assert "Args:" in blocks[1]["content"]


def test_inline_comment_segmentation():
    sentences = segment_inline_comment(INLINE_TEXT)
    assert sentences == [
        "Initialize quantum register.",
        "Apply gates sequentially.",
        "Measure results.",
    ]


def test_block_comment_segmentation():
    sentences = segment_block_comment(BLOCK_TEXT)
    assert sentences == [
        "This module implements quantum algorithms.",
        "It provides various optimization functions.",
        "Performance is O(n²) complexity.",
    ]


def test_simple_docstring_single_paragraph():
    blocks = segment_docstring(SIMPLE_DOCSTRING)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "paragraph"
    assert blocks[0]["content"] == SIMPLE_DOCSTRING
