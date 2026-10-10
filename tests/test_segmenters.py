"""Comment-segmentation unit tests.

The cases come from scripts/test_segment.py (kept as a runnable usage
example); here they are real assertions. The demo smoke suite exercises the
same segmenters end-to-end through the full pipeline.
"""

from segment_core.python_segment.block_comment_segmenter import segment_block_comment
from segment_core.python_segment.docstring_segmenter import segment_docstring
from segment_core.python_segment.inline_comment_segmenter import segment_inline_comment

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
