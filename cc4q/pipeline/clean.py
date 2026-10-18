"""Code-context cleaning policies for extracted comment/code pairs.

A record's ``code_snippet`` should show enough surrounding code to judge
the comment without leaking unrelated comments into the training text.
Three policies are available via :class:`CodeCleanMode`:

``current_only``
    Keep the comment under study and remove other comments/docstrings.
``full``
    Keep all code and remove comments/docstrings.
``none``
    Keep the snippet verbatim (stripped of leading/trailing whitespace).
"""

from enum import Enum
from typing import List, Optional

__all__ = ["CodeCleanMode", "clean_code_snippet"]


class CodeCleanMode(str, Enum):
    """Supported code-context cleaning policies.

    Attributes:
        FULL: Keep all code, remove comments and docstrings.
        NONE: Keep the snippet verbatim.
        CURRENT_ONLY: Keep the comment under study, remove all other
            comments and docstrings.
    """

    FULL = "full"
    NONE = "none"
    CURRENT_ONLY = "current_only"


def clean_code_snippet(
    code_lines: List[int],
    comment_line: List[int],
    mode: str,
    code_snippet: str,
    docstring_lines: Optional[List[int]] = None,
) -> str:
    """Clean a code context according to ``mode``.

    Args:
        code_lines: Inclusive ``[start, end]`` absolute line range covered
            by ``code_snippet``.
        comment_line: Inclusive ``[start, end]`` absolute line range of the
            comment under study. Required by ``current_only``.
        mode: Cleaning policy, as a :class:`CodeCleanMode` value or the
            equivalent string (``"full"``, ``"none"``, ``"current_only"``).
        code_snippet: Raw code context, one source line per line.
        docstring_lines: Optional inclusive line range of the docstring to
            keep in ``full`` mode.

    Returns:
        The cleaned snippet with blank lines and leading/trailing whitespace
        removed.

    Raises:
        ValueError: If ``mode`` is unknown, or if ``current_only`` is used
            without ``comment_line``.
    """
    snippet_lines = code_snippet.splitlines()
    snippet_start = code_lines[0]
    if mode == CodeCleanMode.NONE:
        return code_snippet.strip()
    if mode == CodeCleanMode.CURRENT_ONLY:
        if comment_line:
            return _remove_other_comments(
                snippet_lines, snippet_start, comment_line
            )
        raise ValueError(
            "current_only mode requires either comment_line or "
            "docstring_lines"
        )
    if mode == CodeCleanMode.FULL:
        return _remove_all_comments(
            snippet_lines, snippet_start, docstring_lines
        )
    raise ValueError(f"Unknown clean mode: {mode}")


def _remove_all_comments(
    snippet_lines: List[str],
    snippet_start_lineno: int,
    docstring_lines: Optional[List[int]] = None,
) -> str:
    cleaned = []
    for i, line in enumerate(snippet_lines):
        lineno = snippet_start_lineno + i
        if (
            docstring_lines
            and docstring_lines[0] <= lineno <= docstring_lines[1]
        ):
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].rstrip()
        if line.strip():
            cleaned.append(line)
    return "\n".join(cleaned).strip()


def _remove_other_comments(
    snippet_lines: List[str],
    snippet_start_lineno: int,
    comment_line: List[int],
) -> str:
    start_comment, end_comment = comment_line
    snippet_end_lineno = snippet_start_lineno + len(snippet_lines) - 1
    head = _clean_comment_lines(
        snippet_lines,
        snippet_start_lineno,
        start_lineno=snippet_start_lineno,
        end_lineno=start_comment - 1,
    )
    keep = snippet_lines[
        start_comment - snippet_start_lineno :
        end_comment - snippet_start_lineno + 1
    ]
    tail = _clean_comment_lines(
        snippet_lines,
        snippet_start_lineno,
        start_lineno=end_comment + 1,
        end_lineno=snippet_end_lineno,
    )
    return "\n".join(head + keep + tail).strip()


def _clean_comment_lines(
    snippet_lines: List[str],
    snippet_start_lineno: int,
    start_lineno: int,
    end_lineno: int,
) -> List[str]:
    cleaned = []
    in_docstring = False
    for lineno in range(start_lineno, end_lineno + 1):
        idx = lineno - snippet_start_lineno
        if idx < 0 or idx >= len(snippet_lines):
            continue
        line = snippet_lines[idx]
        stripped = line.strip()
        if (
            stripped.startswith('"""')
            or stripped.startswith("'''")
            or stripped.startswith('r"""')
            or stripped.startswith("r'''")
        ):
            if not in_docstring:
                in_docstring = True
                if stripped.endswith('"""') or (
                    stripped.endswith("'''") and len(stripped) > 3
                ):
                    in_docstring = False
                continue
            in_docstring = False
            continue
        if in_docstring:
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].rstrip()
        if line.strip():
            cleaned.append(line)
    return cleaned


def _preserve_docstring_only(
    snippet_lines: List[str],
    snippet_start_lineno: int,
    docstring_lines: List[int],
) -> str:
    start_docstring, end_docstring = docstring_lines
    snippet_end_lineno = snippet_start_lineno + len(snippet_lines) - 1
    head = _clean_comment_lines(
        snippet_lines,
        snippet_start_lineno,
        start_lineno=snippet_start_lineno,
        end_lineno=start_docstring - 1,
    )
    keep = snippet_lines[
        start_docstring - snippet_start_lineno :
        end_docstring - snippet_start_lineno + 1
    ]
    tail = _clean_comment_lines(
        snippet_lines,
        snippet_start_lineno,
        start_lineno=end_docstring + 1,
        end_lineno=snippet_end_lineno,
    )
    return "\n".join(head + keep + tail).strip()
