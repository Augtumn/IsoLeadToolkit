"""The single-field dispatch actions are a declarative table, not one branch each.

Stage three of the state model work, first step: 141 of the 180 branches in dispatch_action were the same shape -
`store._snapshot["field"] = <expression>` - and the expression is the setter. They are _SIMPLE_SETTERS now, with one
lookup before the chain; the 39 branches that remain are the multi-statement ones and the five that read the current
snapshot as their default.
"""
from __future__ import annotations

import pathlib

import pytest

from core import app_state
from core.state._dispatch_handlers import _SIMPLE_SETTERS, dispatch_action


def test_every_setter_writes_a_field_the_snapshot_has() -> None:
    """The table writes into the store's snapshot, so the field has to be one it carries.

    Not every field is registry-driven: the runtime ones - the selected subset, the embedding task flags, the plot
    title - are among the forty the coverage guard documents as explicit. What none of them may be is invented.
    """
    available = set(app_state.state_store.snapshot())
    unknown = sorted(action for action, (field, _setter) in _SIMPLE_SETTERS.items() if field not in available)
    assert unknown == [], unknown


def test_every_setter_is_callable_and_names_its_field() -> None:
    for action, (field, setter) in _SIMPLE_SETTERS.items():
        assert isinstance(field, str) and field, action
        assert callable(setter), action


def test_the_table_is_what_keeps_the_chain_short() -> None:
    """A count, pinned: without the table this file grows again by a branch per action."""
    assert len(_SIMPLE_SETTERS) == 141


def test_a_simple_setter_still_reaches_the_snapshot() -> None:
    action = "SET_PLOT_STYLE_GRID"
    field, _setter = _SIMPLE_SETTERS[action]
    store = app_state.state_store
    original = store.snapshot()[field]
    try:
        dispatch_action(store, {"type": action, "enabled": not original})
        assert store.snapshot()[field] == (not original)
    finally:
        dispatch_action(store, {"type": action, "enabled": original})

def test_no_action_is_handled_in_both_places() -> None:
    """The table runs first, so a table action that still had a branch would be handled twice."""
    import ast

    import core.state._dispatch_handlers as handlers

    source = pathlib.Path(handlers.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "dispatch_action")
    chain_actions = set()
    for node in ast.walk(function):
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare):
            test = node.test
            if isinstance(test.left, ast.Name) and test.left.id == "action_type":
                chain_actions.add(test.comparators[0].value)
    assert chain_actions & set(_SIMPLE_SETTERS) == set()


def test_the_shared_normalizers_are_the_registry_ones() -> None:
    """Measured: 69 of the 141 setters coerce with the same function the registry uses for that field.

    The other 86 are payload-specific - a colour default, a tuple shape, a clamped range - so the registry cannot spell
    them. This test pins the overlap so a setter that stops matching the registry is noticed; it does not require the
    table to be generated from it.
    """
    import ast

    import core.state._dispatch_handlers as handlers
    from core.state.fields import SIMPLE_FIELDS

    registry = {field.name: field for field in SIMPLE_FIELDS}
    source = pathlib.Path(handlers.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    table = next(n for n in ast.walk(tree) if isinstance(n, ast.Dict) and len(n.keys) > 50)
    shared = 0
    for _key, value in zip(table.keys, table.values):
        field = value.elts[0].value
        setter = value.elts[1]
        if not isinstance(setter, ast.Lambda) or field not in registry:
            continue
        expression = setter.body
        if (isinstance(expression, ast.Call) and isinstance(expression.func, ast.Name)
                and getattr(registry[field].normalize, "__name__", None) == expression.func.id):
            shared += 1
    assert shared == 69, shared
