"""Tests for ternary plotting helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from core import app_state
from visualization.plotting import ternary


class _FakeTernaryAxis:
    def __init__(self) -> None:
        self.limits: tuple[float, float, float, float, float, float] | None = None
        self.aspect: tuple[str, str] | None = None

    def set_ternary_lim(self, *limits: float) -> None:
        self.limits = tuple(float(v) for v in limits)

    def set_aspect(self, aspect: str, adjustable: str = "box") -> None:
        self.aspect = (aspect, adjustable)


def test_normalize_ternary_components_falls_back_to_equal_for_invalid_rows() -> None:
    t_norm, l_norm, r_norm = ternary.normalize_ternary_components(
        np.array([0.0, 1.0, -3.0], dtype=float),
        np.array([0.0, 2.0, 1.0], dtype=float),
        np.array([0.0, 3.0, 2.0], dtype=float),
    )

    np.testing.assert_allclose(
        np.column_stack([t_norm, l_norm, r_norm]),
        np.array(
            [
                [1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0],
                [1.0 / 6.0, 2.0 / 6.0, 3.0 / 6.0],
                [0.0, 1.0 / 3.0, 2.0 / 3.0],
            ],
            dtype=float,
        ),
        rtol=0.0,
        atol=1e-12,
    )


def test_configure_ternary_axis_uses_gateway_writes(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    axis = _FakeTernaryAxis()

    monkeypatch.setattr(ternary.state_gateway, "set_ternary_limit_mode", lambda value: calls.append(("mode", value)))
    monkeypatch.setattr(ternary.state_gateway, "set_ternary_boundary_percent", lambda value: calls.append(("percent", value)))

    setattr(app_state, "ternary_limit_mode", "max")
    setattr(app_state, "ternary_boundary_percent", "12.5")

    limits = ternary.configure_ternary_axis(
        axis,
        np.array([0.2, 0.4], dtype=float),
        np.array([0.3, 0.4], dtype=float),
        np.array([0.5, 0.2], dtype=float),
        auto_zoom=False,
    )

    assert calls == [("mode", "max"), ("percent", 12.5)]
    assert axis.limits == limits
    assert axis.aspect == ("equal", "box")


def test_calculate_auto_ternary_factors_writes_via_gateway(monkeypatch) -> None:
    snapshot_cols = list(getattr(app_state, "selected_ternary_cols", []) or [])
    calls: list[list[float]] = []
    try:
        setattr(app_state, "selected_ternary_cols", ["top", "left", "right"])
        monkeypatch.setattr(
            ternary,
            "_df_global",
            lambda: pd.DataFrame(
                {
                    "top": [1.0, 2.0, 3.0],
                    "left": [2.0, 3.0, 4.0],
                    "right": [3.0, 4.0, 5.0],
                }
            ),
        )
        monkeypatch.setattr(ternary, "_active_subset_indices", lambda: None)
        monkeypatch.setattr(ternary.state_gateway, "set_ternary_factors", lambda factors: calls.append(list(factors)))

        ok = ternary.calculate_auto_ternary_factors()

        assert ok is True
        assert len(calls) == 1
        assert len(calls[0]) == 3
        assert all(np.isfinite(calls[0]))
        assert all(value > 0 for value in calls[0])
    finally:
        setattr(app_state, "selected_ternary_cols", snapshot_cols)


def test_calculate_auto_ternary_factors_returns_false_without_dataframe(monkeypatch) -> None:
    snapshot_cols = list(getattr(app_state, "selected_ternary_cols", []) or [])
    try:
        setattr(app_state, "selected_ternary_cols", ["top", "left", "right"])
        monkeypatch.setattr(ternary, "_df_global", lambda: None)

        assert ternary.calculate_auto_ternary_factors() is False
    finally:
        setattr(app_state, "selected_ternary_cols", snapshot_cols)


def test_recommend_boundary_percent_uses_low_span_fallback() -> None:
    recommended = ternary.recommend_boundary_percent_from_components(
        np.array([1.0, 1.0], dtype=float),
        np.array([1.0, 1.0], dtype=float),
        np.array([1.0, 1.0], dtype=float),
        mode="min",
        current_percent=5.0,
    )

    assert recommended == 9.6


def test_calculate_auto_ternary_factors_sanitizes_nonpositive_inputs(monkeypatch) -> None:
    snapshot_cols = list(getattr(app_state, "selected_ternary_cols", []) or [])
    calls: list[list[float]] = []
    try:
        setattr(app_state, "selected_ternary_cols", ["top", "left", "right"])
        monkeypatch.setattr(
            ternary,
            "_df_global",
            lambda: pd.DataFrame(
                {
                    "top": [0.0, -1.0, np.nan],
                    "left": [0.0, np.nan, -2.0],
                    "right": [np.nan, 0.0, -3.0],
                }
            ),
        )
        monkeypatch.setattr(ternary, "_active_subset_indices", lambda: None)
        monkeypatch.setattr(ternary.state_gateway, "set_ternary_factors", lambda factors: calls.append(list(factors)))

        ok = ternary.calculate_auto_ternary_factors()

        assert ok is True
        assert len(calls) == 1
        assert all(np.isfinite(calls[0]))
        assert all(value > 0.0 for value in calls[0])
    finally:
        setattr(app_state, "selected_ternary_cols", snapshot_cols)


def test_robust_bounds_treats_tiny_trim_ratio_as_no_trim() -> None:
    vals = np.array([0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10], dtype=float)

    low, high = ternary._robust_bounds(vals, trim_ratio=1e-12)

    assert low == np.nanmin(vals)
    assert high == np.nanmax(vals)


def test_infer_ternary_limits_uses_fallback_span_for_tiny_base_span() -> None:
    t_vals = np.array([0.333333333333, 0.333333333334], dtype=float)
    l_vals = np.array([0.333333333333, 0.333333333332], dtype=float)
    r_vals = np.array([0.333333333334, 0.333333333334], dtype=float)

    tmin, tmax, *_ = ternary.infer_ternary_limits(t_vals, l_vals, r_vals, boundary_percent=5.0)

    assert np.isfinite(tmin)
    assert np.isfinite(tmax)
    assert (tmax - tmin) > 0.1


def test_is_tiny_span_for_nonfinite_and_small_values() -> None:
    assert ternary._is_tiny_span(float("nan")) is True
    assert ternary._is_tiny_span(1e-12) is True
    assert ternary._is_tiny_span(1e-3) is False
