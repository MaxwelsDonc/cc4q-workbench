"""Repository-level metrics shared by the live pipeline and the demo-data
build. No heavy imports (no torch/streamlit) so build_demo_data.py can use it.

Comment density definition (mirrors RQ2 of the companion paper):
``comment lines / code lines`` over the repository checkout, restricted to
the same ``include_dirs`` the corpus pipeline uses. A physical line is a
comment line if it carries a ``#`` comment token (inline or full-line, per
Python's ``tokenize``); code lines are all other non-blank lines. Files that
fail to tokenize fall back to a simple ``lstrip().startswith('#')`` scan.
"""

import io
import os
import tokenize

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules"}


def iter_py_files(root, include_dirs=None):
    """.py files under root, restricted to include_dirs (relative names)."""
    root = os.path.abspath(root)
    if include_dirs:
        bases = [os.path.abspath(os.path.join(root, d)) for d in include_dirs]
    else:
        bases = [root]
    for base in bases:
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in sorted(filenames):
                if fn.endswith(".py"):
                    yield os.path.join(dirpath, fn)


def _fallback_line_scan(source):
    comment = code = 0
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            comment += 1
        else:
            code += 1
    return comment, code


def count_comment_code_lines(path):
    """(comment_lines, code_lines) for one Python file."""
    with open(path, "rb") as f:
        raw = f.read()
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError:
        source = raw.decode("latin-1", errors="replace")
    comment_lines = set()
    try:
        for tok in tokenize.tokenize(io.BytesIO(raw).readline):
            if tok.type == tokenize.COMMENT:
                comment_lines.update(range(tok.start[0], tok.end[0] + 1))
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return _fallback_line_scan(source)
    comment = code = 0
    for lineno, line in enumerate(source.splitlines(), 1):
        if not line.strip():
            continue
        if lineno in comment_lines:
            comment += 1
        else:
            code += 1
    return comment, code


def compute_comment_density(root, include_dirs=None):
    """Aggregate comment density over a repo checkout.

    Returns {"comment_lines": int, "code_lines": int, "value": float}
    where value = comment_lines / code_lines (0.0 if no code lines).
    """
    comment = code = 0
    for path in iter_py_files(root, include_dirs):
        c, k = count_comment_code_lines(path)
        comment += c
        code += k
    return {
        "comment_lines": comment,
        "code_lines": code,
        "value": round(comment / code, 4) if code else 0.0,
    }


def quantum_residence(units):
    """Quantum SCCU counts per (comment_type, entity_level).

    ``units`` are lean unit dicts/DataFrame records with keys comment_type,
    code_entity_type, quantum_related. Returns
    {comment_type: {entity_level: count}} over quantum units only.
    """
    table = {}
    for u in units:
        if not u.get("quantum_related"):
            continue
        ctype = u.get("comment_type", "")
        entity = u.get("code_entity_type", "")
        table.setdefault(ctype, {})
        table[ctype][entity] = table[ctype].get(entity, 0) + 1
    return table
