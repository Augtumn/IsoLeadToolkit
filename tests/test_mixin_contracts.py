"""The declared mixin contracts must hold in the composed classes.

Each mixin lists the methods it expects from its siblings (``REQUIRES_<Class>``, the
explicit interface from UI review item I). These tests check that the classes which
actually inherit those mixins provide every declared method, both statically (through the
class registry) and on the real main window.
"""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCANNED = ("ui/main_window_parts", "ui/panels", "ui/app_parts")


def _load_guard():
    spec = importlib.util.spec_from_file_location(
        "check_cross_mixin_calls", ROOT / "scripts/check_cross_mixin_calls.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def registry():
    """class name -> (own methods, base names) for every class in the scanned packages."""
    own_by_name: dict[str, set[str]] = {}
    bases_by_name: dict[str, set[str]] = {}
    for base in SCANNED:
        for path in (ROOT / base).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]:
                own = {n.name for n in node.body if isinstance(n, ast.FunctionDef)}
                bases = {b.id for b in node.bases if isinstance(b, ast.Name)} | {
                    b.attr for b in node.bases if isinstance(b, ast.Attribute)
                }
                # union: the same name may be defined in more than one module
                own_by_name[node.name] = own_by_name.get(node.name, set()) | own
                bases_by_name[node.name] = bases_by_name.get(node.name, set()) | bases

    def closure(name: str) -> set[str]:
        seen: set[str] = set()
        stack = list(bases_by_name.get(name, set()))
        while stack:
            base = stack.pop()
            if base in seen:
                continue
            seen.add(base)
            stack.extend(bases_by_name.get(base, set()))
        return seen

    return {name: (own_by_name[name], closure(name)) for name in own_by_name}


def _declared() -> dict[str, set[str]]:
    return _load_guard().analyse()[2]


def test_every_declaration_belongs_to_a_known_class(registry) -> None:
    declared = _declared()
    assert declared, "expected the mixins to declare their requirements"
    unknown = sorted(name for name in declared if name not in registry)
    assert not unknown, f"REQUIRES_ for unknown classes: {unknown}"


def test_declared_methods_exist_somewhere(registry) -> None:
    provided = {method for own, _bases in registry.values() for method in own}
    declared = _declared()
    missing = {
        f"{cls}.{method}"
        for cls, methods in declared.items()
        for method in methods
        if method not in provided
    }
    assert not missing, f"declared but nobody provides them: {sorted(missing)}"


def _is_composed_class(name: str) -> bool:
    """Composition roots: the classes the application instantiates.

    Intermediate aggregators (``*Mixin``) are not required to satisfy their siblings on
    their own - the composed class is, and that is what this test pins down.
    """
    return name == "Qt5MainWindow" or name.endswith(("Panel", "Dialog"))


def test_composed_classes_satisfy_their_bases_requirements(registry) -> None:
    """A composed class must provide what the mixins it inherits demand."""
    declared = _declared()
    problems: list[str] = []
    checked = 0
    for cls, (own, closure) in registry.items():
        if not _is_composed_class(cls):
            continue
        checked += 1
        available = set(own) | {
            method for base in closure for method in registry.get(base, (set(), set()))[0]
        }
        for base in closure:
            for method in declared.get(base, set()):
                if method not in available:
                    problems.append(f"{cls} inherits {base} but nothing provides {method}")
    assert checked, "expected to check at least one composed class"
    assert not problems, problems


def test_the_real_main_window_provides_every_declared_main_window_method(main_window) -> None:
    declared = _declared()
    main_window_classes = {
        name for name in declared if name.startswith("MainWindow") or name == "LegendListWidget"
    }
    assert main_window_classes, "expected main-window mixins in the declarations"
    missing = sorted(
        f"{cls}.{method}"
        for cls in main_window_classes
        for method in declared[cls]
        if not hasattr(main_window, method)
    )
    assert not missing, f"the composed window lacks: {missing}"
