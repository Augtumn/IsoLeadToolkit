"""Regression tests for geochemistry age and isochron helpers."""

from __future__ import annotations

import numpy as np
import pytest

from data.geochemistry import age as age_module
from data.geochemistry import engine
from data.geochemistry.isochron import (
    calculate_isochron1_growth_curve,
    calculate_isochron_age_from_slope,
    calculate_pbpb_age_from_ratio,
    calculate_source_kappa_from_slope,
    calculate_source_mu_from_isochron,
    york_regression,
)


def _ratio_from_age_years(t_years: float) -> float:
    params = engine.get_parameters()
    l238 = float(params["lambda_238"])
    l235 = float(params["lambda_235"])
    u_ratio = float(params["U_ratio"])
    return u_ratio * (np.exp(l235 * t_years) - 1.0) / (np.exp(l238 * t_years) - 1.0)


def test_calculate_pbpb_age_from_ratio_recovers_input_age() -> None:
    expected_age_ma = 1250.0
    ratio = _ratio_from_age_years(expected_age_ma * 1e6)

    age_ma, age_err_ma = calculate_pbpb_age_from_ratio(ratio, sr76=1e-5)

    assert age_ma == pytest.approx(expected_age_ma, rel=0.0, abs=1e-6)
    assert age_err_ma is not None
    assert age_err_ma > 0.0


def test_calculate_pbpb_age_from_ratio_non_positive_short_circuit() -> None:
    age_ma, age_err_ma = calculate_pbpb_age_from_ratio(0.0)

    assert age_ma == 0.0
    assert age_err_ma is None


def test_calculate_isochron_age_from_slope_matches_pbpb_solver() -> None:
    expected_age_ma = 880.0
    ratio = _ratio_from_age_years(expected_age_ma * 1e6)

    age_ma = calculate_isochron_age_from_slope(ratio)

    assert age_ma == pytest.approx(expected_age_ma, rel=0.0, abs=1e-6)


def test_calculate_source_mu_from_isochron_returns_zero_on_degenerate_denominator() -> None:
    params = {
        **engine.get_parameters(),
        "T1": 1_000_000.0,
        "a1": 11.0,
        "b1": 12.0,
    }

    mu = calculate_source_mu_from_isochron(
        slope=0.3,
        intercept=11.5,
        age_ma=1.0,
        params=params,
    )

    assert mu == 0.0


def test_calculate_source_kappa_from_slope_returns_zero_on_degenerate_denominator() -> None:
    params = {
        **engine.get_parameters(),
        "T1": 1_000_000.0,
    }

    kappa = calculate_source_kappa_from_slope(
        slope_208_206=0.25,
        age_ma=1.0,
        params=params,
    )

    assert kappa == 0.0


def test_calculate_isochron1_growth_curve_returns_none_on_degenerate_denominator() -> None:
    params = {
        **engine.get_parameters(),
        "T1": 1_000_000.0,
        "a1": 11.0,
        "b1": 12.0,
        "age_model": "two_stage",
    }

    curve = calculate_isochron1_growth_curve(
        slope=0.3,
        intercept=11.5,
        age_ma=1.0,
        params=params,
    )

    assert curve is None


def test_calculate_isochron1_growth_curve_returns_data_on_regular_input() -> None:
    params = {
        **engine.get_parameters(),
        "T1": 2_000_000.0,
        "a1": 11.0,
        "b1": 12.0,
        "age_model": "two_stage",
    }

    curve = calculate_isochron1_growth_curve(
        slope=0.0,
        intercept=12.0,
        age_ma=1.0,
        params=params,
        steps=16,
    )

    assert curve is not None
    assert len(curve["x"]) == 16
    assert len(curve["y"]) == 16


def test_single_stage_age_guard_short_circuits_ratio_singularity(monkeypatch) -> None:
    params = {
        **engine.get_parameters(),
        "a0": 10.0,
        "b0": 11.0,
    }

    def _fake_solver(func, bounds, search_points=200):
        _ = bounds, search_points
        val = func(0.0)
        return None if val >= 1e9 else 0.0

    monkeypatch.setattr(age_module, "_solve_age_scipy", _fake_solver)

    age = age_module.calculate_single_stage_age(
        Pb206_204_S=10.0,
        Pb207_204_S=12.0,
        params=params,
    )

    assert age is None


def test_two_stage_age_guard_produces_nan_for_array_element(monkeypatch) -> None:
    params = {
        **engine.get_parameters(),
        "a1": 12.0,
        "b1": 13.0,
    }

    def _fake_solver(func, bounds, search_points=200):
        _ = bounds, search_points
        val = func(0.0)
        return None if val >= 1e9 else 1_000_000.0

    monkeypatch.setattr(age_module, "_solve_age_scipy", _fake_solver)

    ages = age_module.calculate_two_stage_age(
        Pb206_204_S=np.array([12.0, 12.5], dtype=float),
        Pb207_204_S=np.array([13.2, 13.4], dtype=float),
        params=params,
    )

    assert isinstance(ages, np.ndarray)
    assert np.isnan(ages[0])
    assert ages[1] == pytest.approx(1.0, rel=0.0, abs=1e-12)


def test_york_regression_recovers_simple_linear_trend() -> None:
    x = np.array([1.0, 2.0, 3.0, 4.0], dtype=float)
    y = (2.0 * x) + 1.0
    sx = np.full_like(x, 0.1)
    sy = np.full_like(x, 0.1)

    result = york_regression(x, sx, y, sy)

    assert result["b"] == pytest.approx(2.0, rel=0.0, abs=1e-6)
    assert result["a"] == pytest.approx(1.0, rel=0.0, abs=1e-6)


def test_york_regression_rejects_non_positive_uncertainties() -> None:
    x = np.array([1.0, 2.0], dtype=float)
    y = np.array([3.0, 5.0], dtype=float)
    sx = np.array([0.0, 0.1], dtype=float)
    sy = np.array([0.1, 0.1], dtype=float)

    with pytest.raises(ValueError):
        york_regression(x, sx, y, sy)


def test_solve_age_scipy_uses_named_xtol_on_endpoint_sign_change(monkeypatch) -> None:
    calls: list[float] = []

    def _fake_brentq(func, left, right, xtol):
        _ = func, left, right
        calls.append(float(xtol))
        return 12.34

    monkeypatch.setattr(age_module.optimize, "brentq", _fake_brentq)

    result = age_module._solve_age_scipy(lambda t: t, bounds=(-10.0, 10.0))

    assert result == pytest.approx(12.34, rel=0.0, abs=1e-12)
    assert calls == [age_module._AGE_SOLVER_XTOL]


def test_solve_age_scipy_uses_named_xtol_on_scanned_sign_change(monkeypatch) -> None:
    calls: list[tuple[float, float, float]] = []

    def _fake_brentq(func, left, right, xtol):
        _ = func
        calls.append((float(left), float(right), float(xtol)))
        return 2.5

    monkeypatch.setattr(age_module.optimize, "brentq", _fake_brentq)

    result = age_module._solve_age_scipy(
        lambda t: (t - 2.5) * (t - 7.3),
        bounds=(0.0, 10.0),
    )

    assert result == pytest.approx(2.5, rel=0.0, abs=1e-12)
    assert len(calls) == 1
    _left, _right, xtol = calls[0]
    assert xtol == age_module._AGE_SOLVER_XTOL
