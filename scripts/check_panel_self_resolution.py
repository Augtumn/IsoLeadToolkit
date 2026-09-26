"""Guard: every `self.<name>()` call in a panel/window mixin must resolve in the MRO
of the class that composes it.

Regression this prevents: a mixin moved to another panel keeps calling a helper that
only existed in the panel it came from. That failure surfaces only when a user clicks
the widget (offscreen build tests do not run the handler), e.g. the
`DisplayPanel has no _sync_toggle_widgets` and `GeoPanel has no _open_line_style_dialog`
errors found in isotopes_analyse.error.log on 2026-09-26.
"""
from __future__ import annotations

import argparse
import ast
import importlib
from pathlib import Path

from source_scan_guard import print_scan_result, repo_root

EXCLUDED_PARTS = {".venv", "reference", "_viewcheck", "__pycache__", "dialogs", "tests"}

#: Names provided by the Qt base classes the panels/window derive from.
QT_NAMES: set[str] = set(dir(object))
try:  # pragma: no cover - PyQt5 is present in this project
    from PyQt5.QtCore import QObject
    from PyQt5.QtWidgets import QDialog, QMainWindow, QWidget

    for base in (QObject, QWidget, QMainWindow, QDialog):
        QT_NAMES |= set(dir(base))
except Exception:  # pragma: no cover
    pass


def _composing_class(rel: Path):
    """Return the class whose MRO must provide the self.* names of *rel*."""
    parts = rel.parts
    if parts[:2] == ("ui", "main_window_parts"):
        return getattr(importlib.import_module("ui.main_window"), "Qt5MainWindow")
    if parts[:2] != ("ui", "panels"):
        return None
    if len(parts) >= 4 and parts[2] != "__init__.py":
        section = parts[2]
        sections = importlib.import_module("ui.panels").SECTIONS
        for meta, panel_cls in sections:
            if meta["key"] == section:
                return panel_cls
        return None
    if len(parts) == 3:  # ui/panels/<module>.py -> shared BasePanel helpers
        return getattr(importlib.import_module("ui.panels.base_panel"), "BasePanel")
    return None


def _dynamic_attributes(root: Path) -> set[str]:
    """Names ever assigned as ``self.<name> = ...``: runtime attributes, not methods."""
    found: set[str] = set()
    for path in root.rglob("ui/**/*.py"):
        rel = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        found.add(target.attr)
    return found


def scan() -> dict[str, int]:
    root = repo_root()
    dynamic = _dynamic_attributes(root)
    counts: dict[str, int] = {}
    for path in sorted(root.rglob("ui/**/*.py")):
        rel = path.relative_to(root)
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        target = _composing_class(rel)
        if target is None:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            counts[f"{rel}: unparsable"] = 1
            continue
        mro_names = {cls.__name__ for cls in target.__mro__}
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            # only classes that are actually part of the composing MRO; helper widget
            # classes defined in the same module have their own (Qt) method surface
            if cls.name not in mro_names:
                continue
            for node in ast.walk(cls):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (
                    isinstance(func, ast.Attribute)
                    and isinstance(func.value, ast.Name)
                    and func.value.id == "self"
                ):
                    continue
                name = func.attr
                if name.startswith("__") or name in QT_NAMES or name in dynamic:
                    continue
                if not hasattr(target, name):
                    counts[f"{rel}:{node.lineno} self.{name}() missing on {target.__name__}"] = 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fail-on-hits", action="store_true")
    args = parser.parse_args()

    counts = scan()
    print_scan_result(counts)
    if args.fail_on_hits and sum(counts.values()) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
