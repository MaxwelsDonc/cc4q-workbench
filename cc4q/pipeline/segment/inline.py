#!/usr/bin/env python3

import spacy
from typing import List
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

def segment_inline_comment(comment_text: str) -> List[str]:
    if not comment_text or not comment_text.strip():
        return []
    return split_comment_into_sentences(comment_text)

def split_comment_into_sentences(text: str) -> List[str]:
    doc = nlp(text)
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]

def segment_inline_comment_advanced(comment_text: str, min_length: int=5) -> List[str]:
    sentences = segment_inline_comment(comment_text)
    filtered_sentences = [s for s in sentences if len(s.strip()) >= min_length]
    if not filtered_sentences and comment_text.strip():
        return [comment_text.strip()]
    return filtered_sentences
if __name__ == '__main__':
    test_comments = ['Initialize the quantum register. Set default parameters.', 'This is a single sentence comment.', 'First sentence! Second sentence? Third sentence.', "Check if Dr. Smith's algorithm works. It should be fine.", 'Short.', '# Remove comment symbols and split properly.', '// Multiple comment styles supported here.', '* Bullet point style comment with multiple sentences. This is the second one.']
    print('Testing inline comment segmentation:')
    for i, comment in enumerate(test_comments, 1):
        sentences = segment_inline_comment(comment)
        print(f'\n{i}. original: {comment}')
        print(f'   segmentation result ({len(sentences)} sentences):')
        for j, sentence in enumerate(sentences, 1):
            print(f'   {j}. {sentence}')
