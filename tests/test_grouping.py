"""Tests for parent-group marker resolution and state integration."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from core import app_state, state_gateway
from visualization.plotting.grouping import (
    PARENT_SHAPE_CYCLE,
    all_parents,
    parent_children,
    parent_of_group,
    parent_shape,
    resolve_group_marker,
)


class _FakeState:
    """Minimal stand-in for app_state with the fields grouping reads."""

    def __init__(self):
        self.parent_groups: dict[str, list[str]] = {}
        self.group_marker_map: dict[str, str] = {}
        self.plot_marker_shape = "o"


def test_parent_of_group_returns_parent() -> None:
    state = _FakeState()
    state.parent_groups = {"coins": ["A", "B"], "silver": ["C"]}
    assert parent_of_group(state, "A") == "coins"
    assert parent_of_group(state, "C") == "silver"
    assert parent_of_group(state, "D") is None


def test_parent_shape_follows_creation_order() -> None:
    state = _FakeState()
    state.parent_groups = {"first": [], "second": [], "third": []}
    assert parent_shape(state, "first") == PARENT_SHAPE_CYCLE[0]
    assert parent_shape(state, "second") == PARENT_SHAPE_CYCLE[1]
    assert parent_shape(state, "third") == PARENT_SHAPE_CYCLE[2]
    # Unknown parent falls back to the first shape.
    assert parent_shape(state, "missing") == PARENT_SHAPE_CYCLE[0]


def test_resolve_group_marker_prefers_parent_shape() -> None:
    state = _FakeState()
    state.group_marker_map = {"A": "^", "B": "^", "C": "s"}
    state.parent_groups = {"first": ["A", "B"]}

    assert resolve_group_marker(state, "A") == PARENT_SHAPE_CYCLE[0]
    assert resolve_group_marker(state, "B") == PARENT_SHAPE_CYCLE[0]
    # Independent groups keep their per-group marker.
    assert resolve_group_marker(state, "C") == "s"
    # Unknown group falls back to the global default.
    assert resolve_group_marker(state, "D") == "o"


def test_parent_children_and_all_parents() -> None:
    state = _FakeState()
    state.parent_groups = {"first": ["A"], "second": ["B", "C"]}
    assert parent_children(state, "second") == ["B", "C"]
    assert all_parents(state) == ["first", "second"]
    assert parent_children(state, "missing") == []


def test_gateway_set_parent_groups_syncs_store_and_state() -> None:
    previous = app_state.parent_groups
    try:
        state_gateway.set_parent_groups({"grp": ["x", "y"]})
        assert app_state.parent_groups == {"grp": ["x", "y"]}
        # Snapshot round-trip through the store.
        snapshot = app_state.state_store.snapshot()
        assert snapshot["parent_groups"] == {"grp": ["x", "y"]}

        state_gateway.set_parent_groups({})
        assert app_state.parent_groups == {}
        assert app_state.state_store.snapshot()["parent_groups"] == {}
    finally:
        state_gateway.set_parent_groups(previous or {})


def test_guard_script_scan_is_clean_for_grouping(monkeypatch) -> None:
    """The grouping module must never mutate app_state directly."""
    import re
    from pathlib import Path

    source = Path("visualization/plotting/grouping.py").read_text(encoding="utf-8")
    pattern = re.compile(r"app_state\.[A-Za-z_][A-Za-z0-9_]*\s*=(?!=)")
    assert not pattern.search(source), "grouping.py must not assign app_state fields"
