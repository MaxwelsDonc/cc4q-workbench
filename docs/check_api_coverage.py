#!/usr/bin/env python3
"""Check that every public CC4Q API name appears in the Sphinx docs.

The checker imports each public module, reads its ``__all__``, and looks for
the corresponding ``autofunction`` / ``autoclass`` / ``autodata`` /
``automodule`` directive (or, for constants, a literal mention) in the RST
sources under ``docs/``. Run it before ``sphinx-build -W`` in docs CI.

Exit status is non-zero when something is missing, so a new public function
cannot silently ship without a reference entry.
"""

from __future__ import annotations

import importlib
import inspect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

# Modules whose __all__ defines the public API. Facades (cc4q,
# cc4q.pipeline, cc4q.models) are included so their aliases stay covered.
PUBLIC_MODULES = [
    "cc4q",
    "cc4q.cli",
    "cc4q.pipeline",
    "cc4q.pipeline.segment",
    "cc4q.pipeline.extract",
    "cc4q.pipeline.segment.docstring",
    "cc4q.pipeline.segment.inline",
    "cc4q.pipeline.segment.block",
    "cc4q.pipeline.segment_pairs",
    "cc4q.pipeline.clean",
    "cc4q.pipeline.config",
    "cc4q.pipeline.download",
    "cc4q.pipeline.files",
    "cc4q.pipeline.ids",
    "cc4q.pipeline.metrics",
    "cc4q.pipeline.paths",
    "cc4q.pipeline.types",
    "cc4q.pipeline.visitor",
    "cc4q.models",
    "cc4q.models.hub",
    "cc4q.predict",
    "cc4q.train",
    "cc4q.evaluate",
    "cc4q.sample",
    "cc4q.annotate",
    "cc4q.annotate.ui",
    "cc4q.workspace",
    "cc4q.registry",
    "cc4q.web",
    "cc4q.web.server",
]

# Objects that are deliberately prose-only (the CLI app object, the ASGI
# application, and the route table are described on their pages).
EXEMPT = {
    ("cc4q.cli", "app"),
    ("cc4q.cli", "main"),
    ("cc4q.web.server", "app"),
    ("cc4q.web.server", "routes"),
}

DIRECTIVE_RE = re.compile(
    r"^\s*\.\.\s+"
    r"(automodule|autofunction|autoclass|autodata|py:module)::\s*"
    r"([A-Za-z_][\w.]*)",
    re.MULTILINE,
)


def documented_names() -> set[str]:
    names: set[str] = set()
    for path in sorted(DOCS.rglob("*.rst")):
        if any(part in {"_build", "_redirects"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8")
        for match in DIRECTIVE_RE.finditer(text):
            names.add(match.group(2).strip().rstrip("."))
    return names


def canonical_name(module_name: str, public_name: str):
    """Resolve a facade alias to its defining module/object."""
    obj = getattr(importlib.import_module(module_name), public_name)
    if inspect.ismodule(obj):
        return obj.__name__, None
    if inspect.isfunction(obj) or inspect.isclass(obj):
        qualname = getattr(obj, "__qualname__", obj.__name__)
        return f"{obj.__module__}.{qualname}", obj
    return None, obj  # constant / other data


def main() -> int:
    documented = documented_names()
    docs_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(DOCS.rglob("*.rst"))
        if not any(part in {"_build", "_redirects"} for part in path.parts)
    )
    missing: list[str] = []
    checked = 0

    for module_name in PUBLIC_MODULES:
        module = importlib.import_module(module_name)
        public = getattr(module, "__all__", None)
        if public is None:
            missing.append(f"{module_name}: no __all__ (cannot audit public API)")
            continue
        for name in public:
            if (module_name, name) in EXEMPT:
                continue
            canonical, obj = canonical_name(module_name, name)
            checked += 1
            if canonical is not None:
                if canonical not in documented:
                    missing.append(
                        f"{module_name}.{name}: expected a directive for "
                        f"{canonical}"
                    )
            elif name not in docs_text:
                missing.append(
                    f"{module_name}.{name}: constant/object is not mentioned "
                    f"in the docs"
                )

    if missing:
        print("API coverage check failed:\n", file=sys.stderr)
        for item in missing:
            print(f"  - {item}", file=sys.stderr)
        print(
            f"\n{len(missing)} missing item(s); checked {checked} public names.",
            file=sys.stderr,
        )
        return 1

    print(f"API coverage OK ({checked} public names checked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
