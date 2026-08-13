"""Tests for legend display ordering and parent-group z-order stacking."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from typing import Any

import pytest

from core import app_state
from ui.main_window_parts.legend_actions import build_legend_display_entries


# ---------------------------------------------------------------------------
# build_legend_display_entries (pure function)
# ---------------------------------------------------------------------------


def _entry(e_type: str, key: str) -> dict[str, Any]:
    return {"type": e_type, "key": key, "group": key} if e_type == "group" else {"type": e_type, "key": key}


def test_display_entries_block_follows_parent_order_index() -> None:
    entries = [
        _entry("group", "A"),
        _entry("group", "B"),
        _entry("group", "C"),
        _entry("overlay", "iso"),
    ]
    parents = ["P1", "P2"]
    child_parent = {"A": "P1", "B": "P1", "C": "P2"}

    # P2's order index puts it first -> its block must render first.
    order_index = {"parent:P2": 0, "parent:P1": 1, "group:A": 2, "group:B": 3, "group:C": 4, "overlay:iso": 5}
    result = build_legend_display_entries(entries, parents, child_parent, order_index)

    keys = [(e["type"], e["key"]) for e in result]
    assert keys == [
        ("parent", "P2"),
        ("group", "C"),
        ("parent", "P1"),
        ("group", "A"),
        ("group", "B"),
        ("overlay", "iso"),
    ]
    # Children carry their parent marker.
    assert result[1]["in_parent"] == "P2"
    assert result[3]["in_parent"] == "P1"
    assert result[4]["in_parent"] == "P1"


def test_display_entries_without_parents_passthrough() -> None:
    entries = [_entry("group", "A"), _entry("overlay", "iso")]
    result = build_legend_display_entries(entries, [], {}, {})
    assert result == entries


def test_display_entries_children_keep_own_order() -> None:
    entries = [_entry("group", "B"), _entry("group", "A"), _entry("group", "C")]
    parents = ["P1"]
    child_parent = {"A": "P1", "B": "P1"}
    order_index = {"parent:P1": 0, "group:A": 1, "group:B": 2, "group:C": 3}
    result = build_legend_display_entries(entries, parents, child_parent, order_index)
    keys = [(e["type"], e["key"]) for e in result]
    # Children keep their own relative order inside the block.
    assert keys == [("parent", "P1"), ("group", "A"), ("group", "B"), ("group", "C")]


def test_independent_group_can_sort_above_parent_block() -> None:
    """Independent groups are free units: they may be dragged above parents."""
    entries = [_entry("group", "A"), _entry("group", "B"), _entry("group", "C")]
    parents = ["P1"]
    child_parent = {"A": "P1", "B": "P1"}

    # C's order index places it FIRST — above the parent block.
    order_index = {"group:C": 0, "parent:P1": 1, "group:A": 2, "group:B": 3}
    result = build_legend_display_entries(entries, parents, child_parent, order_index)
    keys = [(e["type"], e["key"]) for e in result]
    assert keys == [("group", "C"), ("parent", "P1"), ("group", "A"), ("group", "B")]

    # And back: parent block above the independent group.
    order_index = {"parent:P1": 0, "group:A": 1, "group:B": 2, "group:C": 3}
    result = build_legend_display_entries(entries, parents, child_parent, order_index)
    keys = [(e["type"], e["key"]) for e in result]
    assert keys == [("parent", "P1"), ("group", "A"), ("group", "B"), ("group", "C")]


def test_independent_group_mixed_with_multiple_parent_blocks() -> None:
    entries = [_entry("group", "A"), _entry("group", "B"), _entry("group", "C"), _entry("group", "D")]
    parents = ["P1", "P2"]
    child_parent = {"A": "P1", "C": "P2"}

    # Interleave: P2 block, independent B, P1 block, independent D.
    order_index = {"parent:P2": 0, "group:C": 1, "group:B": 2, "parent:P1": 3, "group:A": 4, "group:D": 5}
    result = build_legend_display_entries(entries, parents, child_parent, order_index)
    keys = [(e["type"], e["key"]) for e in result]
    assert keys == [
        ("parent", "P2"),
        ("group", "C"),
        ("group", "B"),
        ("parent", "P1"),
        ("group", "A"),
        ("group", "D"),
    ]


# ---------------------------------------------------------------------------
# drop ambiguity guard (parent rows must never stack on other rows)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not hasattr(__import__("PyQt5.QtWidgets", fromlist=["QApplication"]), "QApplication"),
    reason="PyQt5 not available",
)
def test_is_parent_related_drop_guards_stacking() -> None:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication, QListWidgetItem

    from ui.main_window_parts.setup import _is_parent_related_drop

    app = QApplication.instance() or QApplication([])

    def item(entry_type: str) -> QListWidgetItem:
        it = QListWidgetItem()
        it.setData(Qt.UserRole, {"type": entry_type, "key": "k"})
        return it

    # Dragging a parent onto anything is parent-related.
    assert _is_parent_related_drop({"type": "parent"}, [item("group")]) is True
    # Dropping anything onto a parent row is parent-related.
    assert _is_parent_related_drop({"type": "group"}, [item("parent")]) is True
    # Group-over-group reorder is plain and must not be intercepted.
    assert _is_parent_related_drop({"type": "group"}, [item("group")]) is False
    assert _is_parent_related_drop({"type": "overlay"}, [item("group")]) is False
    assert _is_parent_related_drop(None, []) is False


# ---------------------------------------------------------------------------
# _apply_legend_z_order parent-block stacking (offscreen Qt)
# ---------------------------------------------------------------------------


class _Artist:
    def __init__(self) -> None:
        self.z = None

    def set_zorder(self, z: float) -> None:
        self.z = z

    def get_zorder(self) -> float:
        return self.z if self.z is not None else 0.0


class _Ax:
    def get_children(self) -> list[Any]:
        return []


@pytest.mark.skipif(
    not hasattr(__import__("PyQt5.QtWidgets", fromlist=["QApplication"]), "QApplication"),
    reason="PyQt5 not available",
)
def test_apply_legend_z_order_parent_block_shares_slot(monkeypatch) -> None:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication, QListWidget, QListWidgetItem

    from core import state_gateway
    from ui.main_window_parts.legend_core import MainWindowLegendCoreMixin

    app = QApplication.instance() or QApplication([])

    lst = QListWidget()
    for e_type, key in [("parent", "P1"), ("group", "A"), ("group", "B"), ("group", "C"), ("overlay", "iso")]:
        item = QListWidgetItem()
        item.setData(Qt.UserRole, {"type": e_type, "key": key})
        lst.addItem(item)

    stub = MainWindowLegendCoreMixin.__new__(MainWindowLegendCoreMixin)
    stub._legend_list = lst

    a, b, c = _Artist(), _Artist(), _Artist()
    prev_g2s = getattr(app_state, "group_to_scatter", None)
    prev_parents = getattr(app_state, "parent_groups", None)
    prev_ax = getattr(app_state, "ax", None)
    prev_fig = getattr(app_state, "fig", None)
    prev_overlays = getattr(app_state, "overlay_artists", None)
    prev_order = getattr(app_state, "legend_item_order", None)
    try:
        monkeypatch.setattr(app_state, "group_to_scatter", {"A": a, "B": b, "C": c}, raising=False)
        # Use the gateway: a direct assignment is rolled back by the next
        # store sync (e.g. the set_legend_item_order dispatch inside
        # _apply_legend_z_order), exactly like production code.
        state_gateway.set_parent_groups({"P1": ["A", "B"]})
        monkeypatch.setattr(app_state, "ax", _Ax(), raising=False)
        monkeypatch.setattr(app_state, "fig", None, raising=False)
        monkeypatch.setattr(app_state, "overlay_artists", {}, raising=False)
        monkeypatch.setattr(app_state, "legend_item_order", [], raising=False)

        stub._apply_legend_z_order()

        # P1 occupies one slot: both children share the same z-order.
        assert a.z == b.z, f"children must share the parent slot, got {a.z} vs {b.z}"
        # Independent group C is one slot lower.
        assert c.z == a.z - 1
        # Order written back includes the parent key.
        order = getattr(app_state, "legend_item_order", [])
        assert "parent:P1" in order
    finally:
        for attr, value in [
            ("group_to_scatter", prev_g2s),
            ("ax", prev_ax),
            ("fig", prev_fig),
            ("overlay_artists", prev_overlays),
            ("legend_item_order", prev_order),
        ]:
            if value is not None:
                monkeypatch.setattr(app_state, attr, value, raising=False)
        state_gateway.set_parent_groups(prev_parents or {})
