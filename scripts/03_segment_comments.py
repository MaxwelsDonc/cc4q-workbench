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

def segment_comment_pairs(input_file: str, output_file: str=None) -> None:
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f'错误: 找不到文件 {input_file}')
        return
    except json.JSONDecodeError as e:
        logger.error(f'错误: JSON解析失败 - {e}')
        return
    if output_file is None:
        base_name = os.path.splitext(input_file)[0]
        output_file = f'{base_name}_segmented.json'
    segmented_data = []
    logger.info(f'开始处理 {len(data)} 个注释对...')
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
                logger.warning(f"未知的comment_type '{comment_type}' for id {original_id}")
                segmented_data.append(item)
        except Exception as e:
            logger.error(f'错误: 处理id {original_id} 时出错 - {e}')
            segmented_data.append(item)
    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(segmented_data, f, ensure_ascii=False, indent=2)
        logger.info(f'分割完成!')
        logger.info(f'原始数据: {len(data)} 个注释对')
        logger.info(f'分割后数据: {len(segmented_data)} 个注释段')
        logger.info(f'输出文件: {output_file}')
    except Exception as e:
        logger.error(f'错误: 保存文件失败 - {e}')

def analyze_comment_types(input_file: str) -> None:
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f'错误: 找不到文件 {input_file}')
        return
    except json.JSONDecodeError as e:
        logger.error(f'错误: JSON解析失败 - {e}')
        return
    type_counts = {}
    for item in data:
        comment_type = item.get('comment_type', 'unknown')
        type_counts[comment_type] = type_counts.get(comment_type, 0) + 1
    logger.info('注释类型分布:')
    for comment_type, count in sorted(type_counts.items()):
        logger.info(f'  {comment_type}: {count}')
    logger.info(f'总计: {len(data)}')
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = 'config/config_qiskit-ibm-runtime.yaml'
    config = read_config(config_path)
    clean_mode = config.get('clean_mode', 'current_only')
    input_file_path = os.path.join(config['output_dir'], f'comment_pairs_{clean_mode}.json')
    out_file_path = os.path.join(config['output_dir'], f'segmented/comment_pairs_{clean_mode}_segmented.json')
    logger.add('scripts/log/03_segment_comments.log', rotation='1 day', retention='7 days', compression='zip')
    if config.get('pipeline', {}).get('analyze', True):
        logger.info('🔍 分析注释类型分布...')
        analyze_comment_types(input_file_path)
    if config.get('pipeline', {}).get('segment', True):
        logger.info('✂️  开始注释语义分割...')
        segment_comment_pairs(input_file_path, out_file_path)
        logger.info('✅ 注释语义分割完成！')
    else:
        logger.warning('⚠️  已跳过语义分割阶段。')
