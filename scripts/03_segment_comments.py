import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import os
from loguru import logger

from utils.read_config import read_config
from utils.path_utils import get_project_path
from cc4q.pipeline.segment_pairs import segment_comment_pairs


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
