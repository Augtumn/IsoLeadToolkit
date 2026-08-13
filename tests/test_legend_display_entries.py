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


def _build(entries, parents, child_parent, order_index):
    """Call build_legend_display_entries with a derived parent_names set."""
    parent_names = set(parents) | set(child_parent.values())
    return build_legend_display_entries(entries, parents, child_parent, parent_names, order_index)


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
    result = _build(entries, parents, child_parent, order_index)

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
    result = _build(entries, [], {}, {})
    assert result == entries


def test_display_entries_children_keep_own_order() -> None:
    entries = [_entry("group", "B"), _entry("group", "A"), _entry("group", "C")]
    parents = ["P1"]
    child_parent = {"A": "P1", "B": "P1"}
    order_index = {"parent:P1": 0, "group:A": 1, "group:B": 2, "group:C": 3}
    result = _build(entries, parents, child_parent, order_index)
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
    result = _build(entries, parents, child_parent, order_index)
    keys = [(e["type"], e["key"]) for e in result]
    assert keys == [("group", "C"), ("parent", "P1"), ("group", "A"), ("group", "B")]

    # And back: parent block above the independent group.
    order_index = {"parent:P1": 0, "group:A": 1, "group:B": 2, "group:C": 3}
    result = _build(entries, parents, child_parent, order_index)
    keys = [(e["type"], e["key"]) for e in result]
    assert keys == [("parent", "P1"), ("group", "A"), ("group", "B"), ("group", "C")]


def test_independent_group_mixed_with_multiple_parent_blocks() -> None:
    entries = [_entry("group", "A"), _entry("group", "B"), _entry("group", "C"), _entry("group", "D")]
    parents = ["P1", "P2"]
    child_parent = {"A": "P1", "C": "P2"}

    # Interleave: P2 block, independent B, P1 block, independent D.
    order_index = {"parent:P2": 0, "group:C": 1, "group:B": 2, "parent:P1": 3, "group:A": 4, "group:D": 5}
    result = _build(entries, parents, child_parent, order_index)
    keys = [(e["type"], e["key"]) for e in result]
    assert keys == [
        ("parent", "P2"),
        ("group", "C"),
        ("group", "B"),
        ("parent", "P1"),
        ("group", "A"),
        ("group", "D"),
    ]


def test_nested_parent_block_expands_recursively() -> None:
    """A parent nested inside another renders as an indented sub-block."""
    entries = [_entry("group", "A"), _entry("group", "B"), _entry("group", "C")]
    top_parents = ["root"]
    child_parent = {"sub": "root", "A": "sub", "B": "sub", "C": "root"}
    parent_names = {"root", "sub"}
    order_index = {
        "parent:root": 0, "group:sub": 1, "group:A": 2, "group:B": 3, "group:C": 4,
    }
    result = build_legend_display_entries(
        entries, top_parents, child_parent, parent_names, order_index
    )

    # root -> sub(parent row) -> A, B; then C.
    keys = [(e["type"], e["key"], e.get("depth", 0)) for e in result]
    assert keys == [
        ("parent", "root", 0),
        ("parent", "sub", 1),
        ("group", "A", 2),
        ("group", "B", 2),
        ("group", "C", 1),
    ]
    assert result[2]["in_parent"] == "sub"
    assert result[3]["in_parent"] == "sub"
    assert result[4]["in_parent"] == "root"


# ---------------------------------------------------------------------------
# manual reorder (legend_item_order based, no row stacking)
# ---------------------------------------------------------------------------


def test_reorder_legend_keys_moves_before_and_after_target() -> None:
    from ui.main_window_parts.legend_actions import reorder_legend_keys

    order = ["parent:P1", "group:A", "group:B", "overlay:iso"]

    # Move B before P1 (drop above the first row).
    assert reorder_legend_keys(order, "group:B", "parent:P1", below=False) == [
        "group:B", "parent:P1", "group:A", "overlay:iso",
    ]
    # Move A after iso (drop below the last row).
    assert reorder_legend_keys(order, "group:A", "overlay:iso", below=True) == [
        "parent:P1", "group:B", "overlay:iso", "group:A",
    ]
    # No-op cases.
    assert reorder_legend_keys(order, "missing:X", "group:A", below=False) == order
    assert reorder_legend_keys(order, "group:A", "group:A", below=False) == order


@pytest.mark.skipif(
    not hasattr(__import__("PyQt5.QtWidgets", fromlist=["QApplication"]), "QApplication"),
    reason="PyQt5 not available",
)
def test_reorder_handler_updates_order_state(monkeypatch) -> None:
    """Drag flow: startDrag records the row, dropEvent reorders the state."""
    from PyQt5.QtCore import QMimeData, QPoint, Qt
    from PyQt5.QtGui import QDropEvent
    from PyQt5.QtWidgets import QApplication, QListWidgetItem

    from core import state_gateway
    from ui.main_window_parts.legend_actions import MainWindowLegendActionsMixin
    from ui.main_window_parts.legend_core import MainWindowLegendCoreMixin
    from ui.main_window_parts.setup import LegendListWidget

    app = QApplication.instance() or QApplication([])

    class Stub(MainWindowLegendActionsMixin, MainWindowLegendCoreMixin):
        pass

    stub = Stub()
    lst = LegendListWidget()
    lst.resize(200, 300)
    for key in ["A", "B", "C"]:
        item = QListWidgetItem(key)
        item.setData(Qt.UserRole, {"type": "group", "key": key})
        lst.addItem(item)
    lst._legend_reorder_handler = stub._handle_legend_reorder
    stub._legend_list = lst
    app.processEvents()

    prev_order = getattr(app_state, "legend_item_order", None)
    prev_ax = getattr(app_state, "ax", None)
    try:
        monkeypatch.setattr(app_state, "ax", None, raising=False)
        monkeypatch.setattr(app_state, "legend_item_order", [], raising=False)

        # Simulate dragging row B (index 1) onto row A (index 0).
        lst._dragging_items = [lst.item(1)]
        event = QDropEvent(
            QPoint(5, 5), Qt.MoveAction, QMimeData(), Qt.LeftButton, Qt.NoModifier
        )
        assert stub._handle_legend_reorder(lst, event) is True
        # The order state now reflects B above A; a panel rebuild driven by
        # this state renders the new order.
        assert getattr(app_state, "legend_item_order", None) == [
            "group:B", "group:A", "group:C",
        ]
    finally:
        if prev_order is not None:
            state_gateway.set_legend_item_order(prev_order)
        if prev_ax is not None:
            monkeypatch.setattr(app_state, "ax", prev_ax, raising=False)


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
def test_apply_legend_z_order_nested_subtree_shares_root_slot(monkeypatch) -> None:
    """A nested parent's groups share the TOP-LEVEL parent's z-slot."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication, QListWidget, QListWidgetItem

    from core import state_gateway
    from ui.main_window_parts.legend_core import MainWindowLegendCoreMixin

    app = QApplication.instance() or QApplication([])

    lst = QListWidget()
    for e_type, key in [("parent", "root"), ("parent", "sub"), ("group", "A"), ("group", "B"), ("group", "C")]:
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
        state_gateway.set_parent_groups({"root": ["sub"], "sub": ["A", "B"]})
        monkeypatch.setattr(app_state, "ax", _Ax(), raising=False)
        monkeypatch.setattr(app_state, "fig", None, raising=False)
        monkeypatch.setattr(app_state, "overlay_artists", {}, raising=False)
        monkeypatch.setattr(app_state, "legend_item_order", [], raising=False)

        stub._apply_legend_z_order()

        # A and B (nested under sub under root) share root's single slot.
        assert a.z == b.z, f"nested children must share the root slot, got {a.z} vs {b.z}"
        # Independent C sits one slot lower.
        assert c.z == a.z - 1
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
