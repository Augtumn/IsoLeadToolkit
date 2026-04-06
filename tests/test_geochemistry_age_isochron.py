"""Regression tests for geochemistry age and isochron helpers."""

from __future__ import annotations

import numpy as np
import pytest

from data.geochemistry import engine
from data.geochemistry.isochron import (
    calculate_isochron_age_from_slope,
    calculate_pbpb_age_from_ratio,
    calculate_source_kappa_from_slope,
    calculate_source_mu_from_isochron,
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
