import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import os
from typing import List, Dict, Any
import os
from utils.read_config import read_config
from tqdm import tqdm
from loguru import logger
from segment_core.python_segment.docstring_segmenter import segment_docstring
from segment_core.python_segment.inline_comment_segmenter import segment_inline_comment
from segment_core.python_segment.block_comment_segmenter import segment_block_comment
import re

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

def segment_comment_pairs(input_file: str, output_file: str=None) -> int:
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

def analyze_comment_types(input_file: str) -> None:
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f'Error: file not found {input_file}')
        return
    except json.JSONDecodeError as e:
        logger.error(f'Error: JSON parse failed - {e}')
        return
    type_counts = {}
    for item in data:
        comment_type = item.get('comment_type', 'unknown')
        type_counts[comment_type] = type_counts.get(comment_type, 0) + 1
    logger.info('Comment type distribution:')
    for comment_type, count in sorted(type_counts.items()):
        logger.info(f'  {comment_type}: {count}')
    logger.info(f'Total: {len(data)}')
if __name__ == '__main__':
    import sys
    from utils.path_utils import get_project_path
    project_path = get_project_path()
    rel_config = sys.argv[1] if len(sys.argv) > 1 else 'config/examples.yaml'
    config_path = os.path.join(project_path, rel_config)
    if not os.path.isfile(config_path):
        print(f'[✗] Config not found: {config_path}', file=sys.stderr)
        sys.exit(1)
    config = read_config(config_path)
    clean_mode = config.get('clean_mode', 'current_only')
    output_dir = config['output_dir']
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(project_path, output_dir)
    input_file_path = os.path.join(output_dir, f'comment_pairs_{clean_mode}.json')
    out_file_path = os.path.join(output_dir, f'segmented/comment_pairs_{clean_mode}_segmented.json')
    logger.add(os.path.join(project_path, 'scripts/log/03_segment_comments.log'),
               rotation='1 day', retention='7 days', compression='zip')
    if not os.path.isfile(input_file_path):
        print(f'[✗] Input file not found: {input_file_path} '
              f'(run scripts/02_extract_code_comment_pairs.py first)',
              file=sys.stderr)
        sys.exit(1)
    if config.get('pipeline', {}).get('analyze', True):
        logger.info('🔍 Analyzing comment type distribution...')
        analyze_comment_types(input_file_path)
    status = 0
    if config.get('pipeline', {}).get('segment', True):
        logger.info('✂️  Starting comment segmentation...')
        n_out = segment_comment_pairs(input_file_path, out_file_path)
        if n_out < 0:
            status = 1
        elif n_out == 0:
            print(f'[✗] Segmentation produced 0 records from {input_file_path}',
                  file=sys.stderr)
            status = 1
        else:
            logger.info('✅ Comment segmentation finished!')
    else:
        logger.warning('⚠️  Segmentation stage skipped.')
    sys.exit(status)
