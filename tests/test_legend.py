"""Legend display-entry, parent-inline and styling tests."""

import os
from typing import Any

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from core import app_state, state_gateway, translate
from ui.main_window_parts.legend_actions import build_legend_display_entries
from visualization.plotting.rendering.common import legend as legend_common
from visualization.plotting.rendering.raw import plot2d
from visualization.plotting.styling import legend as legend_helpers
from visualization.plotting.styling.legend import (
    _DEFAULT_LEGEND_FRAME_ALPHA,
    _legend_columns_for_layout,
    _legend_layout_config,
    _style_legend,
)


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
def test_remove_nested_parent_from_parent(monkeypatch) -> None:
    """Ejecting a nested parent keeps it as a top-level parent with subtree."""
    from PyQt5.QtWidgets import QApplication, QListWidget

    from core import state_gateway
    from ui.main_window_parts.legend_actions import MainWindowLegendActionsMixin
    from ui.main_window_parts.legend_core import MainWindowLegendCoreMixin

    app = QApplication.instance() or QApplication([])

    class Stub(MainWindowLegendActionsMixin, MainWindowLegendCoreMixin):
        def _refresh_plot(self):
            pass

    stub = Stub()
    lst = QListWidget()
    stub._legend_list = lst

    prev_parents = getattr(app_state, "parent_groups", None)
    prev_ax = getattr(app_state, "ax", None)
    prev_fig = getattr(app_state, "fig", None)
    prev_overlays = getattr(app_state, "overlay_artists", None)
    try:
        monkeypatch.setattr(app_state, "ax", None, raising=False)
        monkeypatch.setattr(app_state, "fig", None, raising=False)
        monkeypatch.setattr(app_state, "overlay_artists", {}, raising=False)
        state_gateway.set_parent_groups({"B": ["A", "y"], "A": ["x"]})

        # A is nested inside B before the eject.
        from visualization.plotting.grouping import parent_of_group

        assert parent_of_group(app_state, "A") == "B"

        stub._remove_group_from_parent("A")

        # A is ejected from B but remains a parent group with its subtree.
        assert app_state.parent_groups == {"B": ["y"], "A": ["x"]}
        assert parent_of_group(app_state, "A") is None
        assert parent_of_group(app_state, "x") == "A"
    finally:
        if prev_parents is not None:
            state_gateway.set_parent_groups(prev_parents)
        if prev_ax is not None:
            monkeypatch.setattr(app_state, "ax", prev_ax, raising=False)
        if prev_fig is not None:
            monkeypatch.setattr(app_state, "fig", prev_fig, raising=False)
        if prev_overlays is not None:
            monkeypatch.setattr(app_state, "overlay_artists", prev_overlays, raising=False)


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


#: Top-level parents covering most groups (34 total in the real dataset).
_PARENT_GROUPS = {
    "铜钱": ["五铢(残)", "开元通宝(残)", "大历元宝(残)"],
    "饰片": ["铜饰片", "铜饰片（残）", "花瓣形饰"],
    "其他": ["铜渣", "铜块", "铜丝", "铜条"],
}


def _restore_parent_state(snapshot: tuple) -> None:
    parents, shape_map = snapshot
    state_gateway.set_parent_groups(parents)
    state_gateway.set_parent_shape_map(shape_map)


def test_merge_parent_groups_collapses_children() -> None:
    original = (
        dict(getattr(app_state, "parent_groups", {}) or {}),
        dict(getattr(app_state, "parent_shape_map", {}) or {}),
    )
    try:
        state_gateway.set_parent_groups(_PARENT_GROUPS)
        labels = ["五铢(残)", "开元通宝(残)", "大历元宝(残)", "铜饰片", "铜渣", "独立组"]
        handles = [object() for _ in labels]  # non-Line2D => group entries

        merged = legend_common._merge_parent_groups_for_inline(handles, labels)
        assert merged is not None
        merged_handles, merged_labels = merged
        parent_prefix = translate("Parent")
        assert merged_labels == [
            f"{parent_prefix}: 铜钱",
            f"{parent_prefix}: 饰片",
            f"{parent_prefix}: 其他",
            "独立组",
        ]
        assert len(merged_handles) == len(merged_labels)
    finally:
        _restore_parent_state(original)


def test_merge_parent_groups_keeps_overlay_entries() -> None:
    original = (
        dict(getattr(app_state, "parent_groups", {}) or {}),
        dict(getattr(app_state, "parent_shape_map", {}) or {}),
    )
    try:
        state_gateway.set_parent_groups({"P": ["A", "B"]})
        from matplotlib.lines import Line2D

        overlay_handle = Line2D([0], [0], color="#111", linestyle="-")
        handles = [object(), object(), overlay_handle]
        labels = ["A", "B", "Model Curves"]

        merged_handles, merged_labels = legend_common._merge_parent_groups_for_inline(handles, labels)
        assert merged_labels == [f"{translate('Parent')}: P", "Model Curves"]
        assert merged_handles[-1] is overlay_handle
    finally:
        _restore_parent_state(original)


def test_merge_parent_groups_returns_none_without_parents() -> None:
    original = (
        dict(getattr(app_state, "parent_groups", {}) or {}),
        dict(getattr(app_state, "parent_shape_map", {}) or {}),
    )
    try:
        state_gateway.set_parent_groups({})
        assert legend_common._merge_parent_groups_for_inline([], []) is None
    finally:
        _restore_parent_state(original)


def test_inline_legend_renders_when_parents_merge_below_cap(monkeypatch) -> None:
    """34 categories + parents => merged entries must draw (regression)."""
    original = (
        dict(getattr(app_state, "parent_groups", {}) or {}),
        dict(getattr(app_state, "parent_shape_map", {}) or {}),
    )
    original_position = getattr(app_state, "legend_position", None)
    try:
        state_gateway.set_parent_groups(_PARENT_GROUPS)
        state_gateway.set_legend_position("upper right")

        cats = [f"G{i:02d}" for i in range(34)]
        slot = 0
        for parent, children in _PARENT_GROUPS.items():
            for child in children:
                cats[slot] = child
                slot += 1

        fig, ax = plt.subplots()
        called: dict = {}

        def _fake_legend(handles, labels, **kwargs):
            called["handles"] = list(handles)
            called["labels"] = list(labels)
            return type("Legend", (), {"set_bbox_to_anchor": lambda *a, **k: None})()

        monkeypatch.setattr(ax, "legend", _fake_legend)
        monkeypatch.setattr(legend_common, "_legend_columns_for_layout", lambda *a, **k: 2)
        monkeypatch.setattr(legend_common, "_legend_layout_config", lambda *a, **k: ("upper right", None, None, None))
        monkeypatch.setattr(legend_common, "_style_legend", lambda *a, **k: None)
        monkeypatch.setattr(legend_common, "state_gateway", type("G", (), {
            "set_legend_snapshot": staticmethod(lambda *a, **k: None),
        })())

        scatters = [object() for _ in cats]
        legend_common._place_inline_legend(
            ax,
            "器物名称",
            list(scatters),
            list(cats),
            inline_handles=[object() for _ in range(4)],
            inline_labels=[f"{translate('Parent')}: {p}" for p in _PARENT_GROUPS] + ["G00"],
        )
        # Drawn with the merged (4) entries, not the raw 34.
        assert len(called["labels"]) == 4
    finally:
        _restore_parent_state(original)
        state_gateway.set_legend_position(original_position)
        try:
            plt.close("all")
        except Exception:
            pass


def test_2d_legend_path_merges_parents(monkeypatch) -> None:
    """plot2d's legend renderer must merge parent groups too."""
    original = (
        dict(getattr(app_state, "parent_groups", {}) or {}),
        dict(getattr(app_state, "parent_shape_map", {}) or {}),
    )
    try:
        state_gateway.set_parent_groups({"P": ["A", "B"]})
        captured: dict = {}

        def _fake_place(ax, group_col, handles, labels, **kwargs):
            captured["inline_labels"] = kwargs.get("inline_labels")

        monkeypatch.setattr(plot2d, "_place_inline_legend", _fake_place)
        monkeypatch.setattr(app_state, "current_palette", {"A": "#ff0000", "B": "#00ff00"})
        ax = type("Ax", (), {})()

        plot2d._render_2d_legend(ax, "g", ["A", "B"], [object(), object()],
                                 show_kde=False, show_marginal_kde=False)
        assert captured["inline_labels"] == [f"{translate('Parent')}: P"]
    finally:
        _restore_parent_state(original)


def test_legend_layout_config_applies_offset_for_inplot_location() -> None:
    original_position = getattr(app_state, "legend_position", None)
    original_offset = tuple(getattr(app_state, "legend_offset", (0.0, 0.0)) or (0.0, 0.0))
    try:
        state_gateway.set_legend_position("upper right")
        state_gateway.set_legend_offset((0.1, -0.2))

        loc, bbox, _mode, _pad = _legend_layout_config()

        assert loc == "upper right"
        assert bbox == pytest.approx((1.1, 0.8), rel=0.0, abs=1e-12)
    finally:
        state_gateway.set_legend_position(original_position)
        state_gateway.set_legend_offset(original_offset)


def test_legend_layout_config_ignores_outside_locations() -> None:
    original_position = getattr(app_state, "legend_position", None)
    original_offset = tuple(getattr(app_state, "legend_offset", (0.0, 0.0)) or (0.0, 0.0))
    try:
        state_gateway.set_legend_position("outside_left")
        state_gateway.set_legend_offset((0.3, 0.3))

        loc, bbox, _mode, _pad = _legend_layout_config()

        assert loc == "best"
        assert bbox is None
    finally:
        state_gateway.set_legend_position(original_position)
        state_gateway.set_legend_offset(original_offset)


def test_legend_layout_config_treats_near_zero_offset_as_zero() -> None:
    original_position = getattr(app_state, "legend_position", None)
    original_offset = tuple(getattr(app_state, "legend_offset", (0.0, 0.0)) or (0.0, 0.0))
    try:
        state_gateway.set_legend_position("upper right")
        state_gateway.set_legend_offset((1e-16, -1e-16))

        loc, bbox, _mode, _pad = _legend_layout_config()

        assert loc == "upper right"
        assert bbox is None
    finally:
        state_gateway.set_legend_position(original_position)
        state_gateway.set_legend_offset(original_offset)


def test_legend_columns_for_layout_rules() -> None:
    assert _legend_columns_for_layout([], ax=None, location_key=None) == 1
    assert _legend_columns_for_layout(["a", "b"], ax=None, location_key="outside_right") == 1
    assert _legend_columns_for_layout(["a", "b"], ax=None, location_key="upper right") is None


def test_style_legend_uses_named_default_alpha_when_state_missing(monkeypatch) -> None:
    class _FakeFrame:
        def __init__(self) -> None:
            self.alpha = None

        def set_facecolor(self, _value) -> None:
            pass

        def set_edgecolor(self, _value) -> None:
            pass

        def set_alpha(self, value) -> None:
            self.alpha = float(value)

    class _FakeText:
        def set_fontsize(self, _size) -> None:
            pass

        def set_color(self, _color) -> None:
            pass

    class _FakeTitle(_FakeText):
        def set_fontweight(self, _weight) -> None:
            pass

    class _FakeAxes:
        transAxes = object()

    class _FakeLegend:
        def __init__(self) -> None:
            self.axes = _FakeAxes()
            self._frame = _FakeFrame()
            self._title = _FakeTitle()

        def set_loc(self, _loc) -> None:
            pass

        def set_bbox_to_anchor(self, _bbox, transform=None) -> None:
            _ = transform

        def set_frame_on(self, _enabled) -> None:
            pass

        def get_frame(self):
            return self._frame

        def get_texts(self):
            return [_FakeText()]

        def get_title(self):
            return self._title

    class _FakeState:
        legend_ax = None
        legend_position = None
        legend_offset = (0.0, 0.0)
        legend_frame_on = True
        legend_frame_facecolor = "#ffffff"
        legend_frame_edgecolor = "#cbd5f5"
        plot_font_sizes = {"legend": 10, "label": 12}
        label_color = "#1f2937"
        label_weight = "normal"

    monkeypatch.setattr(legend_helpers, "app_state", _FakeState())
    legend = _FakeLegend()

    _style_legend(legend)

    assert legend.get_frame().alpha == _DEFAULT_LEGEND_FRAME_ALPHA


def test_legend_toggle_uses_available_groups() -> None:
    """Hide/show must operate on the rendered group universe, not current_groups."""
    from core import app_state, state_gateway
    from application.use_cases import selection_interaction

    original_visible = getattr(app_state, "visible_groups", None)
    original_available = list(getattr(app_state, "available_groups", []) or [])
    try:
        state_gateway.sync_available_and_visible_groups(["A", "B", "C"])
        # Hiding A from the full universe keeps B and C visible.
        next_groups = selection_interaction.SelectionInteractionUseCase().next_visible_groups(
            current_visible_groups=None,
            all_groups=list(app_state.available_groups),
            target_group="A",
            target_visible=False,
        )
        assert next_groups == ["B", "C"]
    finally:
        state_gateway.set_visible_groups(original_visible)
        state_gateway.sync_available_and_visible_groups(original_available)
