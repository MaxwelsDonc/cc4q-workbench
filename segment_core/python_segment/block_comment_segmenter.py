#!/usr/bin/env python3

import re
import spacy
from typing import List, Dict, Any
try:
    nlp = spacy.load('en_core_web_sm')
except OSError:
    try:
        nlp = spacy.load('en_core_web_md')
    except OSError:
        try:
            nlp = spacy.load('en_core_web_lg')
        except OSError:
            raise ImportError('Please install the spaCy English model: python -m spacy download en_core_web_sm')

def segment_block_comment(comment_text: str) -> List[str]:
    if not comment_text or not comment_text.strip():
        return []
    special_blocks = _detect_special_blocks(comment_text)
    if special_blocks:
        return special_blocks
    return split_comment_into_sentences(comment_text)

def split_comment_into_sentences(text: str) -> List[str]:
    results = []
    paragraphs = re.split('\\n\\s*\\n', text)
    for par in paragraphs:
        sentences = nlp(par)
        for sent in sentences.sents:
            if sent.text.strip():
                results.append(sent.text.strip())
    return results

def _detect_special_blocks(text: str) -> List[str]:
    text_lower = text.lower()
    copyright_patterns = ['copyright\\s+\\(c\\)', '\\(c\\)\\s+copyright', 'copyright\\s+\\d{4}', 'all rights reserved', '©\\s*\\d{4}']
    license_patterns = ['licensed under', 'apache license', 'mit license', 'gpl license', 'bsd license', 'this code is licensed', 'license:']
    for pattern in copyright_patterns + license_patterns:
        if re.search(pattern, text_lower):
            return [text]
    if _is_file_header(text):
        return [text]
    return []

def _is_file_header(text: str) -> bool:
    text_lower = text.lower()
    header_keywords = ['file:', 'filename:', 'author:', 'date:', 'version:', 'description:', 'purpose:', 'module:', 'package:', 'created:', 'modified:', 'last updated:']
    keyword_count = sum((1 for keyword in header_keywords if keyword in text_lower))
    return keyword_count >= 2
if __name__ == '__main__':
    test_comments = ['This module implements quantum error correction codes\n\n        It provides functions for encoding and decoding quantum states \n        The implementation supports various error correction schemes', 'Copyright (c) 2024 Quantum Computing Inc.\n        All rights reserved.\n        Licensed under the MIT License.', 'File: quantum_circuit.py\n        Author: Dr. Smith\n        Date: 2024-01-01\n        Description: Implementation of quantum circuits.', 'Single sentence block comment.', "First sentence with abbreviation like Dr. Smith's work.\n        Second sentence continues here.\n        Visit https://example.com for more info.\n        Contact us at contact@example.com for questions."]
    print('Testing block comment segmentation:')
    for i, comment in enumerate(test_comments, 1):
        sentences = segment_block_comment(comment)
        print(f'\n{i}. original: {comment[:50]}...')
        print(f'   segmentation result ({len(sentences)} sentences):')
        for j, sentence in enumerate(sentences, 1):
            print(f'   {j}. {sentence}')
