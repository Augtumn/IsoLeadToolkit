"""Guard: a mixin's dependencies on other classes must be declared.

Cross-class ``self.method()`` calls inside mixin trees are implicit: nothing says which
other mixin has to provide what. Each class declares them in a module-level
``REQUIRES_<ClassName>`` tuple (the explicit interface, UI review item I) and this guard
checks that the declaration matches reality:

  * a cross-class dependency that is missing from the tuple fails the guard,
  * a declared name that no class provides any more fails as stale,
  * Qt base-class methods are not dependencies and are ignored (resolved at runtime).
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASELINE = Path(__file__).resolve().parent / "cross_mixin_calls_baseline.json"
SCANNED = ("ui/main_window_parts", "ui/panels", "ui/app_parts")


def qt_method_names() -> set[str]:
    """Names provided by the Qt base classes (not dependencies of ours)."""
    try:
        from PyQt5.QtCore import QObject
        from PyQt5.QtWidgets import (
            QDialog,
            QDockWidget,
            QGraphicsView,
            QGroupBox,
            QLabel,
            QLineEdit,
            QListWidget,
            QMainWindow,
            QPushButton,
            QScrollArea,
            QSlider,
            QSpinBox,
            QSplitter,
            QTabWidget,
            QTableWidget,
            QTextEdit,
            QToolBar,
            QTreeWidget,
            QWidget,
        )
    except Exception:  # pragma: no cover - PyQt is a hard dependency in practice
        return set()
    bases = (
        QObject, QWidget, QDialog, QMainWindow, QDockWidget, QGraphicsView, QGroupBox, QLabel,
        QLineEdit, QListWidget, QPushButton, QScrollArea, QSlider, QSpinBox, QSplitter,
        QTabWidget, QTableWidget, QTextEdit, QToolBar, QTreeWidget,
    )
    names: set[str] = set()
    for base in bases:
        names |= set(dir(base))
    return names


def duplicate_class_names() -> dict[str, list[str]]:
    """Class names defined in more than one module: one silently shadows the other."""
    seen: dict[str, list[str]] = defaultdict(list)
    for base in SCANNED:
        for path in (ROOT / base).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
                seen[cls.name].append(path.relative_to(ROOT).as_posix())
    return {name: files for name, files in seen.items() if len(files) > 1}


def analyse() -> tuple[dict[str, set[str]], dict[str, set[str]], dict[str, str]]:
    """(class -> external deps), (class -> module path), (class -> declared tuple names)."""
    owned: dict[str, set[str]] = defaultdict(set)  # class -> its own methods
    providers: dict[str, set[str]] = defaultdict(set)  # method -> classes defining it
    calls: dict[str, set[str]] = defaultdict(set)
    module_of: dict[str, str] = {}
    declared: dict[str, set[str]] = {}

    for base in SCANNED:
        for path in (ROOT / base).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for cls in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
                module_of[cls.name] = path.relative_to(ROOT).as_posix()
                own = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
                owned[cls.name] |= own
                for method in own:
                    providers[method].add(cls.name)
                for node in ast.walk(cls):
                    if (
                        isinstance(node, ast.Call)
                        and isinstance(node.func, ast.Attribute)
                        and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "self"
                    ):
                        calls[cls.name].add(node.func.attr)
            # declarations in this module
            for node in tree.body:
                if isinstance(node, ast.Assign) and len(node.targets) == 1:
                    target = node.targets[0]
                    if isinstance(target, ast.Name) and target.id.startswith("REQUIRES_"):
                        names = {
                            element.value
                            for element in getattr(node.value, "elts", [])
                            if isinstance(element, ast.Constant) and isinstance(element.value, str)
                        }
                        declared[target.id[len("REQUIRES_"):]] = names

    qt = qt_method_names()
    external: dict[str, set[str]] = {}
    for cls, called in calls.items():
        deps = {
            name
            for name in called
            if name not in owned.get(cls, set()) and name not in qt and name in providers
        }
        if deps:
            external[cls] = deps
    return external, module_of, declared


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", action="store_true", help="write the current counts as the baseline")
    parser.add_argument("--fail-on-hits", action="store_true")
    args = parser.parse_args()

    external, module_of, declared = analyse()
    if args.update:
        BASELINE.write_text(
            json.dumps({cls: sorted(deps) for cls, deps in sorted(external.items())}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"baseline updated: {sum(len(v) for v in external.values())} dependencies in {len(external)} classes")
        return 0

    problems: list[str] = []
    for name, files in sorted(duplicate_class_names().items()):
        problems.append(f"duplicate class names: {name} in {files}")
    for cls, deps in sorted(external.items()):
        declared_names = declared.get(cls, set())
        undeclared = sorted(deps - declared_names)
        if undeclared:
            problems.append(
                f"{module_of[cls]}: {cls} depends on {undeclared} without declaring REQUIRES_{cls}"
            )
    for cls, names in sorted(declared.items()):
        stale = sorted(name for name in names if name not in {n for deps in external.values() for n in deps} and cls not in external)
        if cls in external:
            stale = sorted(name for name in names if name not in external[cls])
        if stale:
            problems.append(f"{module_of.get(cls, '?')}: REQUIRES_{cls} lists {stale}, which it no longer depends on")

    if problems:
        print(f"TOTAL={len(problems)}")
        for problem in problems:
            print(f"1\t{problem}")
        return 1

    print(f"# cross-mixin dependencies: {sum(len(v) for v in external.values())} in {len(external)} classes, all declared")
    print("TOTAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
