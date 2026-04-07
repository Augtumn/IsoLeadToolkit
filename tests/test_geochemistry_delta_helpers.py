"""Tests for data.geochemistry.delta helper defaults."""

from __future__ import annotations

import numpy as np

from data.geochemistry.delta import calculate_deltas, calculate_v1v2
from data.geochemistry.engine import (
    E1_DEFAULT,
    E2_DEFAULT,
    REGRESSION_A,
    REGRESSION_B,
    REGRESSION_C,
    GeochemistryEngine,
)


def test_calculate_deltas_uses_named_e_defaults_when_missing() -> None:
    ge_engine = GeochemistryEngine()
    params = ge_engine.get_parameters()
    params.pop("E1", None)
    params.pop("E2", None)

    pb206 = np.array([18.1, 19.3], dtype=float)
    pb207 = np.array([15.5, 15.9], dtype=float)
    pb208 = np.array([38.4, 39.7], dtype=float)
    t_ma = np.array([120.0, 260.0], dtype=float)

    with_defaults = calculate_deltas(pb206, pb207, pb208, t_ma, params=params)
    with_explicit_constants = calculate_deltas(
        pb206,
        pb207,
        pb208,
        t_ma,
        params=params,
        E1=E1_DEFAULT,
        E2=E2_DEFAULT,
    )

    np.testing.assert_allclose(with_defaults[0], with_explicit_constants[0])
    np.testing.assert_allclose(with_defaults[1], with_explicit_constants[1])
    np.testing.assert_allclose(with_defaults[2], with_explicit_constants[2])


def test_calculate_v1v2_uses_named_regression_defaults() -> None:
    d_alpha = np.array([1.0, 2.0], dtype=float)
    d_beta = np.array([0.5, 1.5], dtype=float)
    d_gamma = np.array([3.0, 4.0], dtype=float)

    with_defaults = calculate_v1v2(d_alpha, d_beta, d_gamma)
    with_explicit_constants = calculate_v1v2(
        d_alpha,
        d_beta,
        d_gamma,
        a=REGRESSION_A,
        b=REGRESSION_B,
        c=REGRESSION_C,
    )

    np.testing.assert_allclose(with_defaults[0], with_explicit_constants[0])
    np.testing.assert_allclose(with_defaults[1], with_explicit_constants[1])
