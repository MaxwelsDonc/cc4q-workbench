"""Stage-01 extraction: Python source -> comment/code pairs (CCPs).

The extractor walks the LibCST tree once and emits one record for every
module/class/function docstring, every inline comment, and every contiguous
block comment. Code context is attached to each record so later stages and
the annotation UI can show where a comment lives.
"""

import json
import os
from typing import Iterator, List

import libcst as cst
from libcst.metadata import MetadataWrapper

from cc4q.pipeline.types import CommentRecord
from cc4q.pipeline.visitor import LibCSTVisitor

__all__ = ["python_extract_comment_pairs"]


def python_extract_comment_pairs(
    source_code: str,
    rel_path: str,
    sdk: str,
    id_gen: Iterator[str],
    version: str,
    host_language: str = "python",
    clean_mode: str = "full",
) -> List[CommentRecord]:
    """Extract comment/code pairs from one Python source file.

    Args:
        source_code: Complete source text of the file.
        rel_path: File path relative to the repository root. Stored in the
            record as ``dirPath`` (split on the platform separator).
        sdk: SDK name used for provenance, e.g. ``"qiskit-nature"``.
        id_gen: Iterator that yields unique record ids. Pass
            :func:`cc4q.pipeline.ids.id_generator` for a fresh sequence.
        version: SDK release / git ref used for provenance.
        host_language: Source language label; only ``"python"`` is parsed
            by LibCST today.
        clean_mode: How much code context to keep in ``code_snippet``.
            One of ``"current_only"``, ``"full"``, or ``"none"`` (see
            :class:`cc4q.pipeline.clean.CodeCleanMode`).

    Returns:
        One :class:`~cc4q.pipeline.types.CommentRecord` per docstring,
        inline comment, or contiguous block comment.

    Raises:
        libcst.ParserSyntaxError: If ``source_code`` is not valid Python.
    """
    source_lines = source_code.splitlines()
    module = cst.parse_module(source_code)
    wrapper = MetadataWrapper(module)
    visitor = LibCSTVisitor(
        source_lines=source_lines,
        rel_path=rel_path,
        sdk=sdk,
        version=version,
        id_gen=id_gen,
        host_language=host_language,
        clean_mode=clean_mode,
        wrapper=wrapper,
    )
    wrapper.visit(visitor)
    return visitor.get_records()


if __name__ == "__main__":
    from cc4q.pipeline.ids import id_generator

    id_gen = id_generator()
    test_file_path = "examples/test_code.py"
    rel_path = os.path.relpath(test_file_path)
    sdk = "qiskit"
    version = "2.0.1"
    host_language = "python"
    with open(test_file_path, "r", encoding="utf-8") as f:
        source_code = f.read()
    comment_records = python_extract_comment_pairs(
        source_code=source_code,
        rel_path=rel_path,
        sdk=sdk,
        id_gen=id_gen,
        version=version,
        host_language=host_language,
        clean_mode="current_only",
    )
    with open("output_comment_pairs.json", "w", encoding="utf-8") as fout:
        json.dump(comment_records, fout, indent=2, ensure_ascii=False)
