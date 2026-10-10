#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sys
import os
import json
from segment_core.python_segment.docstring_segmenter import segment_docstring
from segment_core.python_segment.inline_comment_segmenter import segment_inline_comment
from segment_core.python_segment.block_comment_segmenter import segment_block_comment

def test_segmentation():
    print('=== Testing docstring segmentation ===')
    docstring_text = 'Calculate quantum state.\n    \n    Args:\n        state: Initial state\n        \n    Returns:\n        Final state\n    '
    docstring_result = segment_docstring(docstring_text)
    print(f'Docstring segmentation result: {len(docstring_result)} blocks')
    for i, segment in enumerate(docstring_result, 1):
        print(f"  block {i}: type='{segment['type']}', content='{segment['content'][:50]}...'")
    print('\n=== Testing inline comment segmentation ===')
    inline_text = 'Initialize quantum register. Apply gates sequentially. Measure results.'
    inline_result = segment_inline_comment(inline_text)
    print(f'Inline segmentation result: {len(inline_result)} sentences')
    for i, sentence in enumerate(inline_result, 1):
        print(f"  sentence {i}: '{sentence}'")
    print('\n=== Testing block comment segmentation ===')
    block_text = 'This module implements quantum algorithms.\n    It provides various optimization functions.\n    Performance is O(n²) complexity.'
    block_result = segment_block_comment(block_text)
    print(f'Block segmentation result: {len(block_result)} sentences')
    for i, sentence in enumerate(block_result, 1):
        print(f"  sentence {i}: '{sentence}'")
    print('\n=== Testing simple docstring ===')
    simple_docstring = 'Helper function for converting a circuit to a gate'
    simple_result = segment_docstring(simple_docstring)
    print(f'Simple docstring segmentation result: {len(simple_result)} blocks')
    for i, segment in enumerate(simple_result, 1):
        print(f"  block {i}: type='{segment['type']}', content='{segment['content']}'")
if __name__ == '__main__':
    test_segmentation()
