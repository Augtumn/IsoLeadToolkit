"""Tests for visualization.plotting.geochem.isochron_labels helpers."""

from __future__ import annotations

from core import app_state, state_gateway
from visualization.plotting.geochem.isochron_labels import _build_isochron_label


def test_build_isochron_label_uses_default_age_and_n_points() -> None:
    original_options = dict(getattr(app_state, "isochron_label_options", {}) or {})
    try:
        state_gateway.set_isochron_label_options({})

        label = _build_isochron_label(
            {
                "age": 123.4,
                "n_points": 9,
                "mswd": 1.23,
                "r_squared": 0.98,
            }
        )

        assert label == "123 Ma, n=9"
    finally:
        state_gateway.set_isochron_label_options(original_options)


def test_build_isochron_label_respects_extended_options() -> None:
    original_options = dict(getattr(app_state, "isochron_label_options", {}) or {})
    try:
        state_gateway.set_isochron_label_options(
            {
                "show_age": False,
                "show_n_points": False,
                "show_mswd": True,
                "show_r_squared": True,
                "show_slope": True,
                "show_intercept": True,
            }
        )

        label = _build_isochron_label(
            {
                "age": 500.0,
                "n_points": 12,
                "mswd": 1.234,
                "r_squared": 0.9876,
                "slope": 0.01234,
                "intercept": 15.6789,
            }
        )

        assert label == "MSWD=1.23, R²=0.988, m=0.0123, b=15.6789"
    finally:
        state_gateway.set_isochron_label_options(original_options)
