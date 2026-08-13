"""Tests for geochemistry source inversion helper utilities."""

from __future__ import annotations

import numpy as np

from data.geochemistry import source as source_module


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
