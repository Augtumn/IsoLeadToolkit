"""Tests for the Albarède et al. (2012) T–μ–κ model.

Albarède, F., Desaulty, A.-M. & Blichert-Toft, J. (2012). A geological
perspective on the use of Pb isotopes in archaeometry. Archaeometry 54(5),
853-867.  https://doi.org/10.1111/j.1475-4754.2011.00653.x

The model is added strictly through the existing extension points: one entry in
``PRESET_MODELS`` (standard fields only) plus functions placed in the modules
that already own that concern — ``engine`` (reference constants, model curve
slope), ``age`` (equation 12 model age), ``source`` (equations 11/14 Δμ/μ, Δκ/κ)
and the package facade (one-call inversion).
"""

from __future__ import annotations

import numpy as np
import pytest

from data.geochemistry import (
    ALBAREDE_DELTA_KAPPA_KEY,
    ALBAREDE_DELTA_MU_KEY,
    ALBAREDE_KAPPA_KEY,
    ALBAREDE_KAPPA_STAR,
    ALBAREDE_MU_KEY,
    ALBAREDE_MU_STAR,
    ALBAREDE_OMEGA_KEY,
    ALBAREDE_T0,
    ALBAREDE_T_MODEL_KEY,
    ALBAREDE_X_STAR,
    ALBAREDE_Y_STAR,
    ALBAREDE_Z_STAR,
    PRESET_MODELS,
    albarede_model_age_residual,
    calculate_albarede_delta_kappa,
    calculate_albarede_delta_mu,
    calculate_albarede_kappa,
    calculate_albarede_model_age,
    calculate_albarede_mu,
    calculate_albarede_parameters,
    calculate_model_slope,
    calculate_modelcurve,
    engine,
)

_MODEL = "Albarède et al. (2012)"
_DEFAULT_MODEL = "Stacey & Kramers (2nd Stage)"


@pytest.fixture(autouse=True)
def _restore_engine_model():
    """Keep the engine singleton on its previous preset after each test."""
    previous = getattr(engine, "current_model_name", "") or _DEFAULT_MODEL
    yield
    engine.load_preset(previous)


def _forward_sample(t_i_ma: float, mu_i: float, kappa_i: float, params: dict) -> tuple[float, float, float]:
    """Generate an ore composition from equations (10)/(11)/(13) with μ2 = 0."""
    t = t_i_ma * 1e6
    x = params["a0"] + mu_i * (np.exp(params["lambda_238"] * ALBAREDE_T0) - np.exp(params["lambda_238"] * t))
    y = params["b0"] + mu_i * params["U_ratio"] * (
        np.exp(params["lambda_235"] * ALBAREDE_T0) - np.exp(params["lambda_235"] * t)
    )
    z = params["c0"] + mu_i * kappa_i * (
        np.exp(params["lambda_232"] * ALBAREDE_T0) - np.exp(params["lambda_232"] * t)
    )
    return float(x), float(y), float(z)


# ---------------------------------------------------------------- preset
def test_preset_registered_with_paper_reference_values() -> None:
    preset = PRESET_MODELS[_MODEL]

    assert preset["mu_M"] == pytest.approx(9.66)
    assert preset["omega_M"] == pytest.approx(9.66 * 3.90)
    assert preset["T1"] == pytest.approx(4430e6)
    assert preset["age_model"] == "single_stage"

    assert engine.load_preset(_MODEL) is True
    assert engine.current_model_name == _MODEL


def test_preset_uses_only_standard_engine_fields() -> None:
    """The preset must not extend the engine parameter schema."""
    assert set(PRESET_MODELS[_MODEL]) <= set(engine.get_parameters())


def test_reference_constants_match_the_paper() -> None:
    assert ALBAREDE_T0 == pytest.approx(4430e6)
    assert ALBAREDE_X_STAR == pytest.approx(18.750)
    assert ALBAREDE_Y_STAR == pytest.approx(15.63)
    assert ALBAREDE_Z_STAR == pytest.approx(38.83)
    assert ALBAREDE_MU_STAR == pytest.approx(9.66)
    assert ALBAREDE_KAPPA_STAR == pytest.approx(3.90)


def test_reference_curve_passes_through_modern_crust() -> None:
    """The preset's curve must hit x*/y*/z* today (t = 0)."""
    engine.load_preset(_MODEL)
    params = engine.get_parameters()

    curve = calculate_modelcurve(0.0, params=params)

    assert curve["Pb206_204"] == pytest.approx(ALBAREDE_X_STAR, abs=1e-9)
    assert curve["Pb207_204"] == pytest.approx(ALBAREDE_Y_STAR, abs=1e-9)
    assert curve["Pb208_204"] == pytest.approx(ALBAREDE_Z_STAR, abs=1e-9)


# ------------------------------------------------------------- equations
def test_model_slope_matches_equation_4() -> None:
    params = engine.get_parameters()
    t0 = 4430e6
    t = 300e6
    expected = (1.0 / 137.88) * (
        np.exp(params["lambda_235"] * t0) - np.exp(params["lambda_235"] * t)
    ) / (np.exp(params["lambda_238"] * t0) - np.exp(params["lambda_238"] * t))

    assert calculate_model_slope(t0, t, params) == pytest.approx(float(expected))


def test_model_slope_of_identical_ages_returns_tangent_limit() -> None:
    """s(T0, T0) is 0/0; the l'Hôpital tangent limit must be returned."""
    params = engine.get_parameters()
    t0 = 4430e6
    l238 = params["lambda_238"]
    l235 = params["lambda_235"]
    expected = params["U_ratio"] * (l235 / l238) * np.exp((l235 - l238) * t0)

    value = calculate_model_slope(t0, t0, params)

    assert np.isfinite(value)
    assert value == pytest.approx(float(expected), rel=1e-12)


@pytest.mark.parametrize(
    "t_i_ma,mu_i,kappa_i",
    [(50.0, 9.60, 3.85), (300.0, 9.90, 4.05), (900.0, 9.70, 3.90), (1800.0, 10.40, 4.20)],
)
def test_forward_inverse_roundtrip_recovers_all_three_parameters(
    t_i_ma: float, mu_i: float, kappa_i: float
) -> None:
    engine.load_preset(_MODEL)
    params = engine.get_parameters()
    x, y, z = _forward_sample(t_i_ma, mu_i, kappa_i, params)

    age = calculate_albarede_model_age(x, y, params)
    mu = calculate_albarede_mu(x, y, age, params)
    kappa = calculate_albarede_kappa(x, z, age, mu, params)

    assert float(age) == pytest.approx(t_i_ma, abs=1e-4)
    assert float(mu) == pytest.approx(mu_i, rel=1e-9)
    assert float(kappa) == pytest.approx(kappa_i, rel=1e-9)
    # The chronometric residual must vanish at the recovered age.
    assert abs(float(albarede_model_age_residual(age, x, y, params))) < 1e-6


def test_delta_functions_match_mu_minus_star_and_kappa_minus_star() -> None:
    engine.load_preset(_MODEL)
    params = engine.get_parameters()
    x, y, z = _forward_sample(400.0, 9.85, 4.10, params)

    age = calculate_albarede_model_age(x, y, params)
    delta_mu = calculate_albarede_delta_mu(x, y, age, params)
    mu = calculate_albarede_mu(x, y, age, params)
    delta_kappa = calculate_albarede_delta_kappa(x, z, age, mu, params)
    kappa = calculate_albarede_kappa(x, z, age, mu, params)

    assert float(delta_mu) == pytest.approx(9.85 - ALBAREDE_MU_STAR, rel=1e-9)
    assert float(mu) == pytest.approx(9.85, rel=1e-9)
    assert float(delta_kappa) == pytest.approx(4.10 - ALBAREDE_KAPPA_STAR, rel=1e-9)
    assert float(kappa) == pytest.approx(4.10, rel=1e-9)


def test_roundtrip_through_the_public_parameter_dict() -> None:
    engine.load_preset(_MODEL)
    params = engine.get_parameters()
    samples = [
        _forward_sample(120.0, 9.80, 4.00, params),
        _forward_sample(750.0, 9.55, 3.80, params),
    ]
    x = np.array([s[0] for s in samples])
    y = np.array([s[1] for s in samples])
    z = np.array([s[2] for s in samples])

    result = calculate_albarede_parameters(x, y, z, params=params)

    assert set(result) == {
        ALBAREDE_T_MODEL_KEY,
        ALBAREDE_MU_KEY,
        ALBAREDE_KAPPA_KEY,
        ALBAREDE_OMEGA_KEY,
        ALBAREDE_DELTA_MU_KEY,
        ALBAREDE_DELTA_KAPPA_KEY,
    }
    np.testing.assert_allclose(result[ALBAREDE_T_MODEL_KEY], [120.0, 750.0], atol=1e-4)
    np.testing.assert_allclose(result[ALBAREDE_MU_KEY], [9.80, 9.55], rtol=1e-9)
    np.testing.assert_allclose(result[ALBAREDE_KAPPA_KEY], [4.00, 3.80], rtol=1e-9)
    np.testing.assert_allclose(
        result[ALBAREDE_OMEGA_KEY], result[ALBAREDE_MU_KEY] * result[ALBAREDE_KAPPA_KEY]
    )
    np.testing.assert_allclose(result[ALBAREDE_DELTA_MU_KEY], result[ALBAREDE_MU_KEY] - ALBAREDE_MU_STAR)
    np.testing.assert_allclose(
        result[ALBAREDE_DELTA_KAPPA_KEY], result[ALBAREDE_KAPPA_KEY] - ALBAREDE_KAPPA_STAR
    )


# -------------------------------------------------------------- robustness
def test_array_input_keeps_nan_for_missing_samples() -> None:
    engine.load_preset(_MODEL)
    params = engine.get_parameters()
    x, y, _z = _forward_sample(300.0, 9.90, 4.05, params)

    ages = calculate_albarede_model_age(
        np.array([x, np.nan]), np.array([y, np.nan]), params
    )

    assert ages.shape == (2,)
    assert ages[0] == pytest.approx(300.0, abs=1e-4)
    assert np.isnan(ages[1])


def test_sample_on_modern_crust_reference_has_no_solution() -> None:
    engine.load_preset(_MODEL)
    params = engine.get_parameters()

    assert calculate_albarede_model_age(ALBAREDE_X_STAR, ALBAREDE_Y_STAR, params) is None

    ages = calculate_albarede_model_age(
        np.array([ALBAREDE_X_STAR]), np.array([ALBAREDE_Y_STAR]), params
    )
    assert np.isnan(ages[0])


def test_scalar_nan_input_does_not_raise() -> None:
    params = engine.get_parameters()

    assert calculate_albarede_model_age(np.nan, np.nan, params) is None


def test_sample_outside_the_model_family_returns_nan_not_a_crash() -> None:
    """A composition with no root in (0, T0) must degrade to NaN."""
    engine.load_preset(_MODEL)
    params = engine.get_parameters()

    # x above modern crust but y far too low: no single-stage growth fits it.
    ages = calculate_albarede_model_age(np.array([19.5]), np.array([15.35]), params)

    assert np.isnan(ages[0])


def test_scalar_input_through_the_public_dict_keeps_shape() -> None:
    """A scalar sample must not crash the one-call inversion."""
    engine.load_preset(_MODEL)
    params = engine.get_parameters()
    x, y, z = _forward_sample(250.0, 9.70, 3.95, params)

    result = calculate_albarede_parameters(x, y, z, params=params)

    assert float(result[ALBAREDE_T_MODEL_KEY]) == pytest.approx(250.0, abs=1e-4)
    assert float(result[ALBAREDE_MU_KEY]) == pytest.approx(9.70, rel=1e-9)
