import json
import os
from typing import List
import libcst as cst
from libcst.metadata import MetadataWrapper
from cc4q.pipeline.visitor import LibCSTVisitor
from cc4q.pipeline.types import CommentRecord

def python_extract_comment_pairs(source_code: str, rel_path: str, sdk: str, id_gen: str, version: str, host_language: str='python', clean_mode: str='full') -> List[CommentRecord]:
    source_lines = source_code.splitlines()
    module = cst.parse_module(source_code)
    wrapper = MetadataWrapper(module)
    visitor = LibCSTVisitor(source_lines=source_lines, rel_path=rel_path, sdk=sdk, version=version, id_gen=id_gen, host_language=host_language, clean_mode=clean_mode, wrapper=wrapper)
    wrapper.visit(visitor)
    return visitor.get_records()
if __name__ == '__main__':
    from cc4q.pipeline.ids import id_generator
    id_gen = id_generator()
    test_file_path = 'examples/test_code.py'
    rel_path = os.path.relpath(test_file_path)
    sdk = 'qiskit'
    version = '2.0.1'
    host_language = 'python'
    with open(test_file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    comment_records = python_extract_comment_pairs(source_code=source_code, rel_path=rel_path, sdk=sdk, id_gen=id_gen, version=version, host_language=host_language, clean_mode='current_only')
    with open('output_comment_pairs.json', 'w', encoding='utf-8') as fout:
        json.dump(comment_records, fout, indent=2, ensure_ascii=False)
