"""Windows console compatibility checks.

Windows PowerShell/cmd consoles often expose cp1252 instead of UTF-8.
Printing a glyph such as ``→`` or ``⚛`` then raises UnicodeEncodeError and
aborts an otherwise valid CLI command. Keep console-facing literals ASCII
and verify the launch path under a cp1252 stdout.
"""

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

CONSOLE_MODULES = [
    REPO / "cc4q" / "cli.py",
    REPO / "cc4q" / "pipeline" / "download.py",
    REPO / "cc4q" / "models" / "hub.py",
    REPO / "cc4q" / "pipeline" / "visitor.py",
]


def _console_arguments(node):
    if not isinstance(node, ast.Call):
        return []
    func = node.func
    is_print = isinstance(func, ast.Name) and func.id == "print"
    is_echo = (
        isinstance(func, ast.Attribute)
        and func.attr == "echo"
        and isinstance(func.value, ast.Name)
        and func.value.id == "typer"
    )
    if not (is_print or is_echo):
        return []
    return list(node.args) + [kw.value for kw in node.keywords]


@pytest.mark.parametrize("path", CONSOLE_MODULES, ids=lambda p: p.name)
def test_console_literals_are_ascii(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = []
    for node in ast.walk(tree):
        for arg in _console_arguments(node):
            for child in ast.walk(arg):
                if (
                    isinstance(child, ast.Constant)
                    and isinstance(child.value, str)
                    and not child.value.isascii()
                ):
                    offenders.append(child.value)
    assert not offenders, f"non-ASCII console output in {path}: {offenders}"


def test_demo_output_survives_cp1252_console():
    code = (
        "import cc4q.web.server\n"
        "cc4q.web.server.run_server = lambda **kwargs: None\n"
        "from cc4q.cli import demo\n"
        "demo(host='127.0.0.1', port=8501)\n"
    )
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        encoding="cp1252",
    )
    assert result.returncode == 0, result.stderr
    assert "[cc4q]" in result.stdout
