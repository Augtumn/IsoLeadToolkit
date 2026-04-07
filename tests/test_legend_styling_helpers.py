"""Tests for visualization.plotting.styling.legend helpers."""

from __future__ import annotations

import pytest

from core import app_state, state_gateway
from visualization.plotting.styling import legend as legend_helpers
from visualization.plotting.styling.legend import (
    _DEFAULT_LEGEND_FRAME_ALPHA,
    _legend_columns_for_layout,
    _legend_layout_config,
    _style_legend,
)


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
