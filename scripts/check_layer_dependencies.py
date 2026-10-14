"""Guard: imports may only point down the layer stack.

Layers (docs/dev_conventions.md §18.1), mapped onto this repository:

  presentation    ui/, visualization/
  application     application/
  domain          data/ - the geochemistry calculations, the metadata registry, the
                  plumbotectonics tables.  Nothing else lives here, and nothing here may
                  touch pandas/openpyxl/Qt or any other layer.
  infrastructure  core/, utils/, adapters/ (file IO: dataset reading, the galena workbook)

Allowed edges: presentation -> application | domain | infrastructure; application -> domain |
infrastructure; infrastructure -> domain.  Everything else is a hit:

  * ``ui/`` importing ``data/`` - the UI must reach the domain through a use case, not by
    calling loaders and cleaners itself (rule 1, the one the conventions state explicitly);
  * ``application/`` importing ``ui/`` or ``visualization/`` - a use case that opens dialogs
    or reads matplotlib axes;
  * ``visualization/`` importing ``ui/`` - a cycle inside the presentation layer;
  * ``core/``, ``utils/`` or ``adapters/`` importing an outer layer or the application;
  * a domain module importing anything outside the domain (``adapters/`` included) or a
    windowing/plotting/dataframe library (PyQt5, matplotlib, pandas, openpyxl).

There is no allow-list: an exception here means the code is in the wrong layer, and the fix is
to move the code or invert the call, not to declare it accepted.
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PACKAGES = (
    "adapters", "application", "core", "data", "locales", "plugins",
    "scripts", "tests", "ui", "utils", "visualization",
)
SKIPPED_DIRS = {
    ".venv", "__pycache__", "reference", "build", "dist", ".git",
    "_viewcheck", "scripts", "tests",
}

PRESENTATION = {"ui", "visualization"}
APPLICATION = {"application"}
INFRASTRUCTURE = {"core", "utils", "adapters"}
DOMAIN = {"data"}
OUTER = PRESENTATION | APPLICATION | INFRASTRUCTURE

DOMAIN_BANNED_THIRD_PARTY = {
    "PyQt5", "PyQt6", "PySide2", "PySide6",
    "matplotlib", "pandas", "openpyxl",
}
#: A domain module may use stdlib and numerics, but nothing that points outward.
DOMAIN_FORBIDDEN = OUTER | {"plugins"} | DOMAIN_BANNED_THIRD_PARTY


def package_of(path: Path) -> str | None:
    try:
        parts = path.relative_to(ROOT).parts
    except ValueError:
        return None
    return parts[0] if parts and parts[0] in PACKAGES else None


def imported_modules(tree: ast.AST) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((alias.name, node.lineno) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level or not node.module:
                continue
            found.append((node.module, node.lineno))
    return found


def violations() -> list[str]:
    hits: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        parts = path.relative_to(ROOT).parts
        if any(part in SKIPPED_DIRS for part in parts):
            continue
        package = package_of(path)
        if package is None:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            # A file deleted while the scan walks the tree (a test probe, an editor swap).
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError as err:
            rel = path.relative_to(ROOT).as_posix()
            hits.append(f"{rel}:{err.lineno}  syntax error: {err.msg}")
            continue
        rel = path.relative_to(ROOT).as_posix()

        for module, line in imported_modules(tree):
            top = module.split(".")[0]
            same_package = top == package
            reason = None
            if package in DOMAIN:
                if top in DOMAIN_BANNED_THIRD_PARTY:
                    reason = f"domain imports {top}"
                elif top in DOMAIN_FORBIDDEN and not same_package:
                    reason = f"domain imports outside layer {top}"
            elif same_package:
                reason = None
            elif package == "ui" and top == "data":
                reason = "ui imports data (use a use case)"
            elif package == "application" and top in PRESENTATION:
                reason = f"application imports {top}"
            elif package == "visualization" and top == "ui":
                reason = "visualization imports ui"
            elif package in INFRASTRUCTURE and top in PRESENTATION | APPLICATION:
                reason = f"{package} imports {top}"
            if reason:
                hits.append(f"{rel}:{line}  import {module}  ({reason})")
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fail-on-hits", action="store_true")
    args = parser.parse_args()

    hits = violations()
    print(f"TOTAL={len(hits)}")
    for hit in hits:
        print(f"1\t{hit}")
    if hits and args.fail_on_hits:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
