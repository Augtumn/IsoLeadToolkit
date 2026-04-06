"""Tests for visualization.plotting.styling.legend helpers."""

from __future__ import annotations

import pytest

from core import app_state, state_gateway
from visualization.plotting.styling.legend import (
    _legend_columns_for_layout,
    _legend_layout_config,
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


def test_legend_columns_for_layout_rules() -> None:
    assert _legend_columns_for_layout([], ax=None, location_key=None) == 1
    assert _legend_columns_for_layout(["a", "b"], ax=None, location_key="outside_right") == 1
    assert _legend_columns_for_layout(["a", "b"], ax=None, location_key="upper right") is None
