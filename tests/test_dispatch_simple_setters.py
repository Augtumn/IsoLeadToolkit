"""The single-field dispatch actions are a declarative table, not one branch each.

Stage three of the state model work, first step: 141 of the 180 branches in dispatch_action were the same shape -
`store._snapshot["field"] = <expression>` - and the expression is the setter. They are _SIMPLE_SETTERS now, with one
lookup before the chain; the 39 branches that remain are the multi-statement ones and the five that read the current
snapshot as their default.
"""
from __future__ import annotations

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

