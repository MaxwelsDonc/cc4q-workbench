"""SCCU segmentation of comment-pair JSON files (stage 03).

Moved from scripts/03_segment_comments.py; the script is now a thin CLI
over this module.
"""

import json
import os
import re

from loguru import logger
from tqdm import tqdm

from cc4q.pipeline.segment.block import segment_block_comment
from cc4q.pipeline.segment.docstring import segment_docstring
from cc4q.pipeline.segment.inline import segment_inline_comment


def fix_rst_definition_lists(docstring: str) -> str:
    lines = docstring.splitlines()
    fixed_lines = []
    pattern = re.compile('^\\s*(Args|Returns?|Raises?|Attributes|Examples|Notes?):\\s*$')
    def_item_pattern = re.compile('^\\s{4,}\\w[\\w\\-]*\\s*\\([^)]*\\):\\s+')
    i = 0
    while i < len(lines):
        line = lines[i]
        fixed_lines.append(line)
        if pattern.match(line):
            if i + 1 < len(lines) and lines[i + 1].strip() != '':
                fixed_lines.append('')
        elif def_item_pattern.match(line):
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if def_item_pattern.match(next_line):
                    fixed_lines.append('')
        i += 1
    return '\n'.join(fixed_lines)

def segment_comment_pairs(input_file: str, output_file: str = None) -> int:
    """Segment comment pairs; returns the number of output records, or -1
    when the input could not be read."""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f'Error: file not found {input_file}')
        return -1
    except json.JSONDecodeError as e:
        logger.error(f'Error: JSON parse failed - {e}')
        return -1
    if output_file is None:
        base_name = os.path.splitext(input_file)[0]
        output_file = f'{base_name}_segmented.json'
    segmented_data = []
    logger.info(f'Starting to process {len(data)} comment pairs...')
    for item in tqdm(data):
        original_id = item.get('id', '')
        comment_type = item.get('comment_type', '')
        comment_text = item.get('comment_text', '')
        if not comment_text.strip():
            continue
        try:
            if comment_type == 'docstring':
                comment_text = fix_rst_definition_lists(comment_text)
                segments = segment_docstring(comment_text)
                for i, segment in enumerate(segments, 1):
                    new_item = item.copy()
                    new_item['id'] = f'{original_id}-{i}'
                    new_item['comment_text'] = segment['content']
                    if 'extra' not in new_item or not isinstance(new_item['extra'], dict):
                        new_item['extra'] = {}
                    new_item['extra']['segment_type'] = segment['type']
                    segmented_data.append(new_item)
            elif comment_type == 'inline':
                segments = segment_inline_comment(comment_text)
                for i, segment in enumerate(segments, 1):
                    new_item = item.copy()
                    new_item['id'] = f'{original_id}-{i}'
                    new_item['comment_text'] = segment
                    segmented_data.append(new_item)
            elif comment_type == 'block':
                segments = segment_block_comment(comment_text)
                for i, segment in enumerate(segments, 1):
                    new_item = item.copy()
                    new_item['id'] = f'{original_id}-{i}'
                    new_item['comment_text'] = segment
                    segmented_data.append(new_item)
            else:
                logger.warning(f"Unknown comment_type '{comment_type}' for id {original_id}")
                segmented_data.append(item)
        except Exception as e:
            logger.error(f'Error processing id {original_id} - {e}')
            segmented_data.append(item)
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(segmented_data, f, ensure_ascii=False, indent=2)
        logger.info(f'Segmentation finished!')
        logger.info(f'Input records: {len(data)} comment pairs')
        logger.info(f'Segmented records: {len(segmented_data)} comment segments')
        logger.info(f'Output file: {output_file}')
        return len(segmented_data)
    except Exception as e:
        logger.error(f'Error: failed to save file - {e}')
        return -1

