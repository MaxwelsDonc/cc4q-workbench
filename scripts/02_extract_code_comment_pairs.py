import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import os
from typing import Callable, Dict, List
from loguru import logger
from parser_core.python_parser.python_extractor import python_extract_comment_pairs
from utils.get_files_from_dir import get_files_from_dir
from utils.path_utils import get_project_path
from utils.read_config import read_config
from utils.id_utils import id_generator

class CommentPairExtractor:

    def __init__(self, base_dir: str, output_dir: str, project: str, version: str='latest', clean_mode: str='none', host_language: str='python', include_dirs: List[str]=None, id_gen: str=id_generator()):
        self.base_dir = base_dir
        self.output_dir = output_dir
        self.project = project
        self.version = version
        self.clean_mode = clean_mode
        self.host_language = host_language
        self.include_dirs = include_dirs or []
        self.id_gen = id_gen
        self.parsers: Dict[str, Callable] = {'python': python_extract_comment_pairs}
        if host_language not in self.parsers:
            raise ValueError(f'Unsupported host language: {host_language}')
        self.extract_func = self.parsers[host_language]
        logger.add('scripts/log/02_extract_code_comment_pairs.log', rotation='1 day', retention='7 days', compression='zip')

    @classmethod
    def from_config(cls, config_path: str):
        config = read_config(config_path)
        project_root = get_project_path()
        base_dir = os.path.join(project_root, config['input_dir'])
        output_dir = os.path.join(project_root, config['output_dir'])
        project = config['project']
        host_language = config['language']
        include_dirs = config.get('include_dirs', [])
        clean_mode = config.get('clean_mode', 'current_only')
        version = config.get('version', 'latest')
        os.makedirs(output_dir, exist_ok=True)
        return cls(base_dir=base_dir, output_dir=output_dir, project=project, version=version, clean_mode=clean_mode, host_language=host_language, include_dirs=include_dirs)

    def get_target_files(self) -> List[str]:
        return get_files_from_dir(self.base_dir, self.include_dirs)

    def process_file(self, file_path: str) -> List[Dict]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            rel_path = os.path.relpath(file_path, self.base_dir)
            records = self.extract_func(source_code=source_code, rel_path=rel_path, sdk=self.project, id_gen=self.id_gen, version=self.version, host_language=self.host_language, clean_mode=self.clean_mode)
            logger.info(f'Processed: {rel_path} - Found {len(records)} comment pairs')
            return records
        except Exception as e:
            logger.error(f'Error processing {file_path}: {str(e)}')
            return []

    def process_all(self) -> List[Dict]:
        files = self.get_target_files()
        logger.info(f'Found {len(files)} {self.host_language} files to process')
        all_records = []
        for file_path in files:
            all_records.extend(self.process_file(file_path))
        return all_records

    def save_to_json(self, records: List[Dict], filename: str='comment_pairs.json', indent: int=2):
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=indent)
        logger.info(f'Saved {len(records)} records to {output_path}')
if __name__ == '__main__':
    import sys
    project_path = get_project_path()
    rel_config = sys.argv[1] if len(sys.argv) > 1 else 'config/config_qiskit-aer.yaml'
    config_path = os.path.join(project_path, rel_config)
    extractor = CommentPairExtractor.from_config(config_path)
    logger.info('Starting comment pair extraction process.')
    logger.info(f'the extractor mode is {extractor.clean_mode}')
    records = extractor.process_all()
    extractor.save_to_json(records, filename=f'comment_pairs_{extractor.clean_mode}.json')
    logger.info('Extraction and saving completed.')
