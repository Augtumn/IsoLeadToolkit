"""Tests for plumbotectonics curve fitting helpers."""

from __future__ import annotations

import numpy as np

from visualization.plotting.geochem.plumbotectonics_curves import _fit_plumbotectonics_curve


def test_fit_plumbotectonics_curve_handles_duplicates_and_invalid_values() -> None:
    x_vals = [1.0, 2.0, 2.0, np.nan, 4.0]
    y_vals = [10.0, 20.0, 22.0, 30.0, np.inf]

    x_fit, y_fit = _fit_plumbotectonics_curve(x_vals, y_vals, n_points=50)

    assert len(x_fit) == 50
    assert len(y_fit) == 50
    assert np.isfinite(x_fit).all()
    assert np.isfinite(y_fit).all()
    assert np.all(np.diff(x_fit) >= 0)


def test_fit_plumbotectonics_curve_returns_raw_when_insufficient_points() -> None:
    x_fit, y_fit = _fit_plumbotectonics_curve([1.0, np.nan], [2.0, 3.0])

    np.testing.assert_allclose(x_fit, np.array([1.0], dtype=float), rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(y_fit, np.array([2.0], dtype=float), rtol=0.0, atol=1e-12)
