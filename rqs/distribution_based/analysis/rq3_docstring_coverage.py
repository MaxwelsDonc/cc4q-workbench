#!/usr/bin/env python3

import os
import json
from pathlib import Path
from typing import Dict, Any, List
import libcst as cst
from libcst import metadata

class DocstringCoverageVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (metadata.ScopeProvider,)

    def __init__(self):
        self.module_count = 0
        self.module_with_docstring = 0
        self.class_count = 0
        self.class_with_docstring = 0
        self.function_count = 0
        self.function_with_docstring = 0
        self.current_file_has_module_docstring = False

    def visit_Module(self, node: cst.Module) -> None:
        self.module_count += 1
        self.current_file_has_module_docstring = False
        if node.get_docstring() is not None:
            self.module_with_docstring += 1
            self.current_file_has_module_docstring = True

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self.class_count += 1
        if node.get_docstring() is not None:
            self.class_with_docstring += 1

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        self.function_count += 1
        if node.get_docstring() is not None:
            self.function_with_docstring += 1

def analyze_file(file_path: Path) -> DocstringCoverageVisitor:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        tree = cst.parse_module(source_code)
        visitor = DocstringCoverageVisitor()
        wrapper = metadata.MetadataWrapper(tree)
        wrapper.visit(visitor)
        return visitor
    except Exception as e:
        print(f'Error analyzing {file_path}: {e}')
        visitor = DocstringCoverageVisitor()
        visitor.module_count = 1
        return visitor

def find_python_files(directory: Path) -> List[Path]:
    python_files = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    return python_files

def main():
    import sys
    qiskit_source_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('data/input/qiskit/qiskit')
    output_dir = Path('rqs/distribution_based/results')
    output_file = output_dir / 'rq3_docstring_coverage.json'
    output_dir.mkdir(parents=True, exist_ok=True)
    if not qiskit_source_dir.exists():
        print(f'Error: Source directory {qiskit_source_dir} does not exist')
        return
    print(f'Analyzing docstring coverage in {qiskit_source_dir}...')
    python_files = find_python_files(qiskit_source_dir)
    print(f'Found {len(python_files)} Python files')
    total_modules = 0
    total_modules_with_docstring = 0
    total_classes = 0
    total_classes_with_docstring = 0
    total_functions = 0
    total_functions_with_docstring = 0
    for i, file_path in enumerate(python_files, 1):
        if i % 100 == 0:
            print(f'Processed {i}/{len(python_files)} files...')
        visitor = analyze_file(file_path)
        total_modules += visitor.module_count
        total_modules_with_docstring += visitor.module_with_docstring
        total_classes += visitor.class_count
        total_classes_with_docstring += visitor.class_with_docstring
        total_functions += visitor.function_count
        total_functions_with_docstring += visitor.function_with_docstring
    module_coverage = total_modules_with_docstring / total_modules if total_modules > 0 else 0.0
    class_coverage = total_classes_with_docstring / total_classes if total_classes > 0 else 0.0
    function_coverage = total_functions_with_docstring / total_functions if total_functions > 0 else 0.0
    results = {'module': {'docstring_count': total_modules_with_docstring, 'entity_count': total_modules, 'docstring_coverage': round(module_coverage, 4)}, 'class': {'docstring_count': total_classes_with_docstring, 'entity_count': total_classes, 'docstring_coverage': round(class_coverage, 4)}, 'function': {'docstring_count': total_functions_with_docstring, 'entity_count': total_functions, 'docstring_coverage': round(function_coverage, 4)}}
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f'\nDocstring Coverage Analysis Complete!')
    print(f'Results saved to: {output_file}')
    print(f'\nSummary:')
    print(f'Modules: {total_modules_with_docstring}/{total_modules} ({module_coverage:.2%})')
    print(f'Classes: {total_classes_with_docstring}/{total_classes} ({class_coverage:.2%})')
    print(f'Functions: {total_functions_with_docstring}/{total_functions} ({function_coverage:.2%})')
if __name__ == '__main__':
    main()
