"""Geochemistry source/delta inversion helper tests."""

import numpy as np

from data.geochemistry import source as source_module
from data.geochemistry.delta import calculate_deltas, calculate_v1v2_coordinates
from data.geochemistry.engine import (
    E1_DEFAULT,
    E2_DEFAULT,
    GeochemistryEngine,
    REGRESSION_A,
    REGRESSION_B,
    REGRESSION_C,
)


def test_safe_denominator_applies_epsilon_floor() -> None:
    values = np.array([0.0, source_module.EPSILON * 0.5, -source_module.EPSILON * 0.5, source_module.EPSILON * 2.0])

    safe = source_module._safe_denominator(values)

    # Floor preserves the sign of tiny values: flipping small negative
    # denominators to +EPSILON would invert the quotient's sign near
    # singularities and manufacture spurious μ/ω values.
    np.testing.assert_allclose(
        safe,
        np.array([source_module.EPSILON, source_module.EPSILON, -source_module.EPSILON, source_module.EPSILON * 2.0]),
        rtol=0.0,
        atol=0.0,
    )


def test_invert_mu_remains_finite_on_degenerate_time_terms() -> None:
    params = {
        **source_module.engine.get_parameters(),
        "lambda_238": 1.55125e-10,
        "lambda_235": 9.8485e-10,
        "U_ratio": 1.0 / 137.88,
    }

    result = source_module._invert_mu(
        x=np.array([10.0], dtype=float),
        y=np.array([11.0], dtype=float),
        t_Ma=np.array([0.0], dtype=float),
        X_ref=9.0,
        Y_ref=10.0,
        T_ref=0.0,
        params=params,
    )

    assert np.isfinite(result).all()


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

    with_defaults = calculate_v1v2_coordinates(d_alpha, d_beta, d_gamma)
    with_explicit_constants = calculate_v1v2_coordinates(
        d_alpha,
        d_beta,
        d_gamma,
        params={'a': REGRESSION_A, 'b': REGRESSION_B, 'c': REGRESSION_C},
    )

    np.testing.assert_allclose(with_defaults[0], with_explicit_constants[0])
    np.testing.assert_allclose(with_defaults[1], with_explicit_constants[1])
