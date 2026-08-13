"""Tests for parent-group marker resolution and state integration."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from core import app_state, state_gateway
from visualization.plotting.grouping import (
    PARENT_SHAPE_CYCLE,
    all_parents,
    descendant_groups,
    is_descendant,
    is_parent,
    parent_children,
    parent_of_group,
    parent_shape,
    resolve_group_marker,
    top_parent_of_group,
)


class _FakeState:
    """Minimal stand-in for app_state with the fields grouping reads."""

    def __init__(self):
        self.parent_groups: dict[str, list[str]] = {}
        self.parent_shape_map: dict[str, str] = {}
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


def test_parent_shape_manual_override_wins() -> None:
    state = _FakeState()
    state.parent_groups = {"first": ["A"]}
    assert parent_shape(state, "first") == PARENT_SHAPE_CYCLE[0]

    state.parent_shape_map = {"first": "^"}
    assert parent_shape(state, "first") == "^"
    # Children inherit the manual parent shape.
    assert resolve_group_marker(state, "A") == "^"

    # Removing the override falls back to automatic assignment.
    state.parent_shape_map = {}
    assert parent_shape(state, "first") == PARENT_SHAPE_CYCLE[0]


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


def test_nested_parents_top_level_and_descendants() -> None:
    state = _FakeState()
    state.parent_groups = {
        "root": ["sub", "leafA"],
        "sub": ["leafB", "leafC"],
    }
    # Only the top-level parent is listed as a root block.
    assert all_parents(state) == ["root"]
    assert is_parent(state, "sub") is True
    assert is_parent(state, "leafA") is False
    # Direct parent of a nested parent is the innermost container.
    assert parent_of_group(state, "sub") == "root"
    assert parent_of_group(state, "leafB") == "sub"
    # Top-level ancestor is resolved by walking up.
    assert top_parent_of_group(state, "leafB") == "root"
    assert top_parent_of_group(state, "leafA") == "root"
    assert top_parent_of_group(state, "sub") == "root"
    # Descendants expand recursively, depth-first.
    assert descendant_groups(state, "root") == ["leafB", "leafC", "leafA"]
    assert descendant_groups(state, "sub") == ["leafB", "leafC"]
    # Cycle detection.
    assert is_descendant(state, "sub", "root") is True
    assert is_descendant(state, "root", "sub") is False


def test_nested_parent_shape_inherits_root() -> None:
    state = _FakeState()
    state.parent_groups = {
        "root": ["sub"],
        "sub": ["A"],
    }
    state.group_marker_map = {"A": "^"}
    # Automatic: root takes cycle[0], nested parents inherit it.
    assert parent_shape(state, "root") == PARENT_SHAPE_CYCLE[0]
    assert parent_shape(state, "sub") == PARENT_SHAPE_CYCLE[0]
    assert resolve_group_marker(state, "A") == PARENT_SHAPE_CYCLE[0]
    # Manual override on the root applies to the whole subtree.
    state.parent_shape_map = {"root": "X"}
    assert resolve_group_marker(state, "A") == "X"


def test_gateway_set_parent_groups_syncs_store_and_state() -> None:
    previous = app_state.parent_groups
    previous_shapes = app_state.parent_shape_map
    try:
        state_gateway.set_parent_groups({"grp": ["x", "y"]})
        assert app_state.parent_groups == {"grp": ["x", "y"]}
        # Snapshot round-trip through the store.
        snapshot = app_state.state_store.snapshot()
        assert snapshot["parent_groups"] == {"grp": ["x", "y"]}

        state_gateway.set_parent_shape_map({"grp": "^"})
        assert app_state.parent_shape_map == {"grp": "^"}
        assert app_state.state_store.snapshot()["parent_shape_map"] == {"grp": "^"}

        state_gateway.set_parent_groups({})
        state_gateway.set_parent_shape_map({})
        assert app_state.parent_groups == {}
        assert app_state.parent_shape_map == {}
    finally:
        state_gateway.set_parent_groups(previous or {})
        state_gateway.set_parent_shape_map(previous_shapes or {})


def test_guard_script_scan_is_clean_for_grouping(monkeypatch) -> None:
    """The grouping module must never mutate app_state directly."""
    import re
    from pathlib import Path

    source = Path("visualization/plotting/grouping.py").read_text(encoding="utf-8")
    pattern = re.compile(r"app_state\.[A-Za-z_][A-Za-z0-9_]*\s*=(?!=)")
    assert not pattern.search(source), "grouping.py must not assign app_state fields"
