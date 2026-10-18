"""LibCST visitor that turns one Python module into comment/code records.

The visitor tracks module/class/function scopes so each extracted comment
is attached to the smallest enclosing entity and carries the right source
line ranges. It is normally used through
:func:`cc4q.pipeline.extract.python_extract_comment_pairs`.
"""

import difflib
import re
import textwrap
from typing import Dict, Iterator, List, Tuple
import libcst as cst
from libcst.metadata import PositionProvider
from libcst.metadata import MetadataWrapper
from cc4q.pipeline.clean import clean_code_snippet
from cc4q.pipeline.paths import split_path

DEBUG_INCONSISTENT_LINENO = False

__all__ = ["LibCSTVisitor"]


class LibCSTVisitor(cst.CSTVisitor):
    """Collect comment/code records while walking a LibCST module.

    Args:
        source_lines: Source file split into physical lines.
        rel_path: Path relative to the repository root.
        sdk: SDK name used for provenance.
        version: SDK release or git ref.
        id_gen: Iterator yielding unique record ids.
        host_language: Source language label.
        clean_mode: Code-context cleaning policy (``current_only``,
            ``full``, or ``none``).
        wrapper: Optional :class:`libcst.metadata.MetadataWrapper` for the
            parsed module; used by the line-number diagnostic.

    Attributes:
        records: Extracted :class:`~cc4q.pipeline.types.CommentRecord`
            dictionaries, in source order.
        scope_ranges: Stack of active module/class/function scopes.
    """
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, source_lines: List[str], rel_path: str, sdk: str, version: str, id_gen: Iterator[str], host_language: str='python', clean_mode: str='full', wrapper=None):
        super().__init__()
        self.source_lines = source_lines
        self.rel_path = split_path(rel_path)
        self.sdk = sdk
        self.version = version
        self.id_gen = id_gen
        self.host_language = host_language
        self.clean_mode = clean_mode
        self.records: List[Dict] = []
        self.scope_ranges: List[Dict] = []
        self._pending_block: List[Tuple[cst.Comment, int]] = []
        self._last_comment_line: int = -10
        self.wrapper = wrapper

    def visit_Module(self, node: cst.Module) -> None:
        self.scope_ranges.append({'type': 'module', 'start': 1, 'end': len(self.source_lines), 'node': node})
        self.debug_inconsistent_lineno(node, label='FunctionDef')
        docstring, doc_start_line, doc_end_line = self._extract_docstring(node.body)
        if docstring:
            raw_code = '\n'.join(self.source_lines[:])
            cleaned_code = clean_code_snippet(code_lines=[1, len(self.source_lines)], comment_line=[doc_start_line, doc_end_line] if docstring else None, mode=self.clean_mode, code_snippet=raw_code)
            self.records.append(self._build_comment_record(comment_text=docstring, comment_type='docstring', code_snippet=cleaned_code, code_entity_type='module', comment_line=[doc_start_line, doc_end_line], code_line=[1, len(self.source_lines)]))

    def leave_Module(self, original_node: cst.Module) -> None:
        self._flush_pending_comment_block()

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        start_line = self.get_metadata(PositionProvider, node).start.line
        end_line = self.get_metadata(PositionProvider, node).end.line
        self.scope_ranges.append({'type': 'class', 'start': start_line, 'end': end_line, 'node': node})
        docstring, doc_start, doc_end = self._extract_docstring(node.body.body)
        if docstring:
            raw_code = '\n'.join(self.source_lines[start_line - 1:end_line])
            cleaned_code = clean_code_snippet(code_lines=[start_line, end_line], comment_line=[doc_start, doc_end] if docstring else None, mode=self.clean_mode, code_snippet=raw_code)
            self.records.append(self._build_comment_record(comment_text=docstring, comment_type='docstring', code_snippet=cleaned_code, code_entity_type='class', comment_line=[doc_start, doc_end], code_line=[start_line, end_line]))

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        self._flush_pending_comment_block()

    def visit_FunctionDef(self, node: cst.FunctionDef) -> None:
        start_line = self.get_metadata(PositionProvider, node).start.line
        end_line = self.get_metadata(PositionProvider, node).end.line
        self.scope_ranges.append({'type': 'function', 'start': start_line, 'end': end_line, 'node': node})
        docstring, doc_start, doc_end = self._extract_docstring(node.body.body)
        if docstring:
            raw_code = '\n'.join(self.source_lines[start_line - 1:end_line])
            cleaned_code = clean_code_snippet(code_lines=[start_line, end_line], comment_line=[doc_start, doc_end] if docstring else None, mode=self.clean_mode, code_snippet=raw_code)
            self.records.append(self._build_comment_record(comment_text=docstring, comment_type='docstring', code_snippet=cleaned_code, code_entity_type='function', comment_line=[doc_start, doc_end], code_line=[start_line, end_line]))

    def leave_FunctionDef(self, original_node: cst.FunctionDef) -> None:
        self._flush_pending_comment_block()

    def visit_Comment(self, node: cst.Comment) -> None:
        start_line = self.get_metadata(PositionProvider, node).start.line
        end_line = self.get_metadata(PositionProvider, node).end.line
        line_text = self.source_lines[start_line - 1]
        is_inline = self._is_inline_comment(line_text)
        if is_inline:
            comment_text = node.value.lstrip('#').strip()
            scope_type, scope_start, scope_end = self._get_scope_for_line(start_line)
            raw_code = '\n'.join(self.source_lines[scope_start - 1:scope_end])
            cleaned_code = clean_code_snippet(code_lines=[scope_start, scope_end], comment_line=[start_line, end_line], mode=self.clean_mode, code_snippet=raw_code)
            self.records.append(self._build_comment_record(comment_text=comment_text, comment_type='inline', code_snippet=cleaned_code, code_entity_type=scope_type, comment_line=[start_line, end_line], code_line=[scope_start, scope_end]))
            self._flush_pending_comment_block()
            self._pending_block = []
            self._last_comment_line = -10
        else:
            if start_line == self._last_comment_line + 1:
                self._pending_block.append((node, start_line))
            else:
                self._flush_pending_comment_block()
                self._pending_block = [(node, start_line)]
            self._last_comment_line = start_line

    def _is_inline_comment(self, line: str) -> bool:
        parts = line.split('#', 1)
        if len(parts) < 2:
            return False
        code_part = parts[0]
        return bool(code_part.strip())

    def _extract_docstring(self, body) -> Tuple[str, int, int]:
        if not body:
            return ('', 0, 0)
        first_stmt = body[0]
        if isinstance(first_stmt, cst.SimpleStatementLine):
            if first_stmt.body and isinstance(first_stmt.body[0], cst.Expr):
                expr = first_stmt.body[0]
                if isinstance(expr.value, cst.SimpleString):
                    start_line = self.get_metadata(PositionProvider, expr).start.line
                    end_line = self.get_metadata(PositionProvider, expr).end.line
                    docstring = expr.value.value
                    if docstring.startswith('"""') or docstring.startswith("'''"):
                        docstring = docstring[3:-3]
                    elif docstring.startswith('r"""') or docstring.startswith("r'''"):
                        docstring = docstring[4:-3]
                    cleaned_docstring = self._format_docstring(docstring)
                    cleaned_docstring = cleaned_docstring.strip() + '\n\n'
                    return (cleaned_docstring, start_line, end_line)
        return ('', 0, 0)

    def _get_scope_for_line(self, line_num: int) -> Tuple[str, int, int]:
        for scope in reversed(self.scope_ranges):
            if scope['start'] <= line_num <= scope['end']:
                return (scope['type'], scope['start'], scope['end'])
        return ('file', 1, len(self.source_lines))

    def _flush_pending_comment_block(self):
        if not self._pending_block:
            return
        comments = self._pending_block
        start_line = comments[0][1]
        end_line = comments[-1][1]
        full_text = '\n'.join((node.value.lstrip('#').strip() for node, _ in comments))
        scope_type, scope_start, scope_end = self._get_scope_for_line(start_line)
        raw_code = '\n'.join(self.source_lines[scope_start - 1:scope_end])
        cleaned_code = clean_code_snippet(code_lines=[scope_start, scope_end], comment_line=[start_line, end_line], mode=self.clean_mode, code_snippet=raw_code)
        self.records.append(self._build_comment_record(comment_text=full_text, comment_type='block', code_snippet=cleaned_code, code_entity_type=scope_type, comment_line=[start_line, end_line], code_line=[scope_start, scope_end]))
        self._pending_block = []

    def _build_comment_record(self, comment_text: str, comment_type: str, code_snippet: str, code_entity_type: str, comment_line: List[int], code_line: List[int], extra: List=None) -> Dict:
        if extra is None:
            extra = []
        return {'id': next(self.id_gen), 'SDK': self.sdk, 'version': self.version, 'hostLanguage': self.host_language, 'dirPath': self.rel_path, 'comment_type': comment_type, 'comment_text': comment_text, 'code_snippet': code_snippet, 'code_entity_type': code_entity_type, 'comment_line': comment_line, 'code_line': code_line, 'extra': extra}

    def _format_docstring(self, docstring: str) -> str:
        lines = docstring.splitlines()
        if not lines:
            return ''
        first_line = lines[0]
        rest_lines = lines[1:]
        indent_lengths = [len(re.match('^[ \\t]*', line).group()) for line in rest_lines if line.strip()]
        common_indent = min(indent_lengths) if indent_lengths else 0
        indent_spaces = ' ' * common_indent
        lines[0] = indent_spaces + first_line
        result = textwrap.dedent('\n'.join(lines))
        return result

    def get_records(self) -> List[Dict]:
        """Return the extracted records in source order."""
        return self.records

    def debug_inconsistent_lineno(self, node: cst.CSTNode, label: str='') -> None:
        """Diagnostic for PositionProvider vs code_for_node drift.

        Silent by default; set DEBUG_INCONSISTENT_LINENO = True to print
        diffs while investigating extraction issues.
        """
        if not DEBUG_INCONSISTENT_LINENO:
            return
        try:
            pos = self.get_metadata(PositionProvider, node)
            start_line = pos.start.line
            end_line = pos.end.line
            source_lines = self.source_lines[start_line - 1:end_line]
            code_by_position = '\n'.join(source_lines)
            code_by_wrapper = self.wrapper.module.code_for_node(node)
            if code_by_position.strip() != code_by_wrapper.strip():
                print(f"\n=== ⚠️ {label or 'Node'}: inconsistent code content ===")
                print(f'PositionProvider line range: {start_line} ~ {end_line}')
                diff = difflib.unified_diff(code_by_position.splitlines(), code_by_wrapper.splitlines(), fromfile='source_lines', tofile='wrapper.code_for_node', lineterm='')
                print('\n'.join(diff))
        except Exception as e:
            print(f'[debug_inconsistent_lineno] failed: {e}')
