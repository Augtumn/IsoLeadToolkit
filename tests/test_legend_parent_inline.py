"""In-plot legend parent-group merging tests.

Regression: with >30 categories the in-plot legend was skipped entirely
('Too many categories'), even when parent groups collapsed the visible
entries well below the cap — the cap used the raw group count.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from core import app_state, state_gateway, translate
from visualization.plotting.rendering.common import legend as legend_common
from visualization.plotting.rendering.raw import plot2d

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
