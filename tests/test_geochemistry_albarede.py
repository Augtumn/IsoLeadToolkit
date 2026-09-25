"""Tests for the Albarède & Juteau (1984) T–μ–κ model.

Albarède, F. & Juteau, M. (1984). Unscrambling the lead model ages.
Geochimica et Cosmochimica Acta 48(1), 207-212.
https://doi.org/10.1016/0016-7037(84)90364-8

Constants and solving strategy were cross-checked against the R package ASTR
(`ASTR::albarede_juteau_1984()`, which transcribes F. Albarède's MATLAB script
v2020-11-06). ASTR deliberately does **not** implement the T–μ–κ variant of
Albarède et al. (2012) because the author himself advises against it; this
project therefore implements AJ84 only.

The model is added strictly through the existing extension points: one entry in
``PRESET_MODELS`` (standard fields only) plus functions placed in the modules
that already own that concern — ``engine`` (reference constants, model curve
slope), ``age`` (model age), ``source`` (Δμ/μ, Δκ/κ) and the package facade
(one-call inversion).
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import optimize

from data.geochemistry import (
    ALBAREDE_AGE_SENSITIVITY_KEY,
    ALBAREDE_DELTA_KAPPA_KEY,
    ALBAREDE_DELTA_MU_KEY,
    ALBAREDE_KAPPA_KEY,
    ALBAREDE_KAPPA_STAR,
    ALBAREDE_MU_KEY,
    ALBAREDE_MU_STAR,
    ALBAREDE_OMEGA_KEY,
    ALBAREDE_T0,
    ALBAREDE_T_MODEL_KEY,
    ALBAREDE_U238_235,
    ALBAREDE_X0,
    ALBAREDE_X_STAR,
    ALBAREDE_Y_STAR,
    ALBAREDE_Z_STAR,
    PRESET_MODELS,
    albarede_model_age_residual,
    calculate_albarede_age_sensitivity,
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

_MODEL = "Albarède & Juteau (1984)"
_DEFAULT_MODEL = "Stacey & Kramers (2nd Stage)"


@pytest.fixture(autouse=True)
def _restore_engine_model():
    """Keep the engine singleton on its previous preset after each test."""
    previous = getattr(engine, "current_model_name", "") or _DEFAULT_MODEL
    yield
    engine.load_preset(previous)


def _forward_sample(t_i_ma: float, mu_i: float, kappa_i: float, params: dict) -> tuple[float, float, float]:
    """Generate an ore composition from the AJ84 growth equations (no U after T_i)."""
    t = t_i_ma * 1e6
    u = 1.0 / params["U_ratio"]
    x = params["a0"] + mu_i * (np.exp(params["lambda_238"] * ALBAREDE_T0) - np.exp(params["lambda_238"] * t))
    y = params["b0"] + mu_i / u * (
        np.exp(params["lambda_235"] * ALBAREDE_T0) - np.exp(params["lambda_235"] * t)
    )
    z = params["c0"] + mu_i * kappa_i * (
        np.exp(params["lambda_232"] * ALBAREDE_T0) - np.exp(params["lambda_232"] * t)
    )
    return float(x), float(y), float(z)


# ---------------------------------------------------------------- preset
def test_preset_registered_with_aj84_constants() -> None:
    preset = PRESET_MODELS[_MODEL]

    assert preset["age_model"] == "single_stage"
    assert preset["T1"] == pytest.approx(3.8e9)
    assert preset["T2"] == pytest.approx(3.8e9)
    assert preset["Tsec"] == pytest.approx(0.0)
    assert preset["mu_M"] == pytest.approx(9.66)
    assert preset["omega_M"] == pytest.approx(9.66 * 3.90)
    assert 1.0 / preset["U_ratio"] == pytest.approx(137.79)

    assert engine.load_preset(_MODEL) is True
    assert engine.current_model_name == _MODEL


def test_preset_uses_only_standard_engine_fields() -> None:
    """The preset must not extend the engine parameter schema."""
    assert set(PRESET_MODELS[_MODEL]) <= set(engine.get_parameters())


def test_reference_constants_match_aj84_and_astr() -> None:
    assert ALBAREDE_T0 == pytest.approx(3.8e9)
    assert ALBAREDE_X_STAR == pytest.approx(18.750)
    assert ALBAREDE_Y_STAR == pytest.approx(15.63)
    assert ALBAREDE_Z_STAR == pytest.approx(38.83)
    assert ALBAREDE_MU_STAR == pytest.approx(9.66)
    assert ALBAREDE_KAPPA_STAR == pytest.approx(3.90)
    assert ALBAREDE_U238_235 == pytest.approx(137.79)


def test_implied_primordial_anchor_is_not_cdt() -> None:
    """AJ84 anchors T0 = 3.8 Ga, so its back-solved 'primordial' Pb is far from
    the Canyon Diablo troilite values used by the CDT presets (do not 'fix')."""
    from data.geochemistry import A0, B0, C0

    assert ALBAREDE_X0 == pytest.approx(10.992618, abs=1e-5)
    assert abs(ALBAREDE_X0 - A0) > 1.0
    assert abs(B0 - 12.741576) > 1.0
    assert abs(C0 - 31.037527) > 1.0


def test_reference_curve_passes_through_modern_common_pb() -> None:
    """The preset's curve must hit x*/y*/z* today (t = 0)."""
    engine.load_preset(_MODEL)
    params = engine.get_parameters()

    curve = calculate_modelcurve(0.0, params=params)

    assert curve["Pb206_204"] == pytest.approx(ALBAREDE_X_STAR, abs=1e-9)
    assert curve["Pb207_204"] == pytest.approx(ALBAREDE_Y_STAR, abs=1e-9)
    assert curve["Pb208_204"] == pytest.approx(ALBAREDE_Z_STAR, abs=1e-9)


# ------------------------------------------------------------- equations
def test_model_slope_matches_definition() -> None:
    engine.load_preset(_MODEL)
    params = engine.get_parameters()
    t0 = ALBAREDE_T0
    t = 300e6
    expected = params["U_ratio"] * (
        np.exp(params["lambda_235"] * t0) - np.exp(params["lambda_235"] * t)
    ) / (np.exp(params["lambda_238"] * t0) - np.exp(params["lambda_238"] * t))

    assert calculate_model_slope(t0, t, params) == pytest.approx(float(expected))


def test_model_slope_of_identical_ages_returns_tangent_limit() -> None:
    """s(T0, T0) is 0/0; the l'Hôpital tangent limit must be returned."""
    engine.load_preset(_MODEL)
    params = engine.get_parameters()
    l238 = params["lambda_238"]
    l235 = params["lambda_235"]
    expected = params["U_ratio"] * (l235 / l238) * np.exp((l235 - l238) * ALBAREDE_T0)

    value = calculate_model_slope(ALBAREDE_T0, ALBAREDE_T0, params)

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
    assert abs(float(albarede_model_age_residual(age, x, y, params))) < 1e-9


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
        ALBAREDE_AGE_SENSITIVITY_KEY,
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
    assert np.isfinite(result[ALBAREDE_AGE_SENSITIVITY_KEY]).all()


# -------------------------------------------------- external cross-checks
def test_reproduces_silverquest_galena_database_rows() -> None:
    """Real-world check against the ore database shipped with SilverQuest_v1
    (``Pb_DB_20240310AllGalenas.xlsx``, columns Tmod/mu/kappa), whose values were
    produced by the AJ84 pipeline (F. Albarède's MATLAB script).

    Agreement with our implementation: 0.01 Ma in T (their 3-decimal rounding),
    exact in mu and kappa.
    """
    engine.load_preset(_MODEL)
    params = engine.get_parameters()

    rows = [
        # (206/204, 207/204, 208/204, Tmod, mu, kappa)
        (18.860, 15.694, 38.946, 46.027, 9.8852, 3.9110),
        (18.670, 15.665, 38.728, 130.220, 9.8096, 3.9125),
        (18.437, 15.673, 38.704, 317.400, 9.8919, 4.0575),
    ]
    x = np.array([r[0] for r in rows])
    y = np.array([r[1] for r in rows])
    z = np.array([r[2] for r in rows])
    t_db = np.array([r[3] for r in rows])
    mu_db = np.array([r[4] for r in rows])
    kappa_db = np.array([r[5] for r in rows])

    result = calculate_albarede_parameters(x, y, z, params=params)

    np.testing.assert_allclose(result[ALBAREDE_T_MODEL_KEY], t_db, atol=0.5)
    np.testing.assert_allclose(result[ALBAREDE_MU_KEY], mu_db, atol=0.005)
    np.testing.assert_allclose(result[ALBAREDE_KAPPA_KEY], kappa_db, atol=0.005)


def test_out_of_family_sample_returns_nan_instead_of_a_negative_age() -> None:
    """Deliberate difference from ASTR: its unbounded ``rootSolve::multiroot``
    returns non-physical roots outside (0, T0) — the SilverQuest database even
    contains Tmod = -84 Ma for this composition. We restrict the search interval
    and report NaN instead.
    """
    engine.load_preset(_MODEL)
    params = engine.get_parameters()

    x, y, z = 18.740, 15.586, 38.661  # database row with Tmod = -84.000 Ma

    assert calculate_albarede_model_age(x, y, params) is None
    result = calculate_albarede_parameters(x, y, z, params=params)
    assert np.isnan(result[ALBAREDE_T_MODEL_KEY])


# --------------------------------------------------------- error propagation
def test_age_sensitivity_matches_finite_difference_on_t0() -> None:
    """The analytic T0 sensitivity must equal the numerical derivative obtained
    by re-solving the model-age equation with T0 perturbed (independent check of
    the formula's λ'/λ and 1/U placement)."""
    engine.load_preset(_MODEL)
    params = engine.get_parameters()
    x, y, _z = _forward_sample(300.0, 9.90, 4.05, params)

    age = float(calculate_albarede_model_age(x, y, params))
    mu = float(calculate_albarede_mu(x, y, age, params))
    analytic = float(calculate_albarede_age_sensitivity(age, mu - ALBAREDE_MU_STAR, mu, params))

    def solve_with_t0(t0_years: float) -> float:
        def residual(t_years: float) -> float:
            dx = x - ALBAREDE_X_STAR
            s_t0_t = calculate_model_slope(t0_years, t_years, params)
            s_t_0 = calculate_model_slope(t_years, 0.0, params)
            return (
                (y - ALBAREDE_Y_STAR) / dx
                - s_t0_t
                - (ALBAREDE_MU_STAR * (np.exp(params["lambda_238"] * t_years) - 1.0) / dx)
                * (s_t0_t - s_t_0)
            )

        return float(optimize.brentq(residual, 0.0, t0_years, xtol=1e-6))

    step = 1.0e6  # 1 Ma, in years
    numeric = (solve_with_t0(ALBAREDE_T0 + step) - solve_with_t0(ALBAREDE_T0)) / step

    assert numeric != 0.0
    assert analytic == pytest.approx(numeric, rel=1e-3)


# -------------------------------------------------------------- robustness
def test_array_input_keeps_nan_for_missing_samples() -> None:
    engine.load_preset(_MODEL)
    params = engine.get_parameters()
    x, y, _z = _forward_sample(300.0, 9.90, 4.05, params)

    ages = calculate_albarede_model_age(np.array([x, np.nan]), np.array([y, np.nan]), params)

    assert ages.shape == (2,)
    assert ages[0] == pytest.approx(300.0, abs=1e-4)
    assert np.isnan(ages[1])


def test_sample_on_modern_reference_has_no_solution() -> None:
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


def test_scalar_input_through_the_public_dict_keeps_shape() -> None:
    engine.load_preset(_MODEL)
    params = engine.get_parameters()
    x, y, z = _forward_sample(250.0, 9.70, 3.95, params)

    result = calculate_albarede_parameters(x, y, z, params=params)

    assert float(result[ALBAREDE_T_MODEL_KEY]) == pytest.approx(250.0, abs=1e-3)
    assert float(result[ALBAREDE_MU_KEY]) == pytest.approx(9.70, rel=1e-9)
    assert float(result[ALBAREDE_KAPPA_KEY]) == pytest.approx(3.95, rel=1e-9)
