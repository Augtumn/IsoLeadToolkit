"""Tests for data.geochemistry.engine parameter management helpers."""

from __future__ import annotations

import numpy as np
import pytest

from data.geochemistry.engine import (
    E1_DEFAULT,
    E1_CUMMING_RICHARDS,
    E2_DEFAULT,
    E2_CUMMING_RICHARDS,
    GeochemistryEngine,
    MU_M_DEFAULT,
    OMEGA_M_DEFAULT,
    PRESET_MODELS,
    T_EARTH_1ST,
    T_EARTH_CANON,
    T_SK_STAGE2,
    calculate_modelcurve,
    _exp_evolution_term,
    _is_zero_like,
)


def test_get_available_models_matches_presets() -> None:
    ge_engine = GeochemistryEngine()

    assert ge_engine.get_available_models() == list(PRESET_MODELS.keys())


def test_load_preset_returns_false_for_unknown_model() -> None:
    ge_engine = GeochemistryEngine()
    baseline = ge_engine.get_parameters()

    assert ge_engine.load_preset("__unknown_model__") is False
    assert ge_engine.get_parameters() == baseline
    assert ge_engine.current_model_name == "Stacey & Kramers (2nd Stage)"


def test_update_parameters_ignores_unknown_and_invalid_values() -> None:
    ge_engine = GeochemistryEngine()

    ge_engine.update_parameters(
        {
            "age_model": "single_stage",
            "mu_M": "10.5",
            "T1": "invalid",
            "unknown_key": 123,
        }
    )

    params = ge_engine.get_parameters()
    assert params["age_model"] == "single_stage"
    assert params["mu_M"] == pytest.approx(10.5)
    assert params["T1"] == pytest.approx(T_SK_STAGE2)
    assert "unknown_key" not in params
    assert params["v_M"] == pytest.approx(float(params["mu_M"]) * float(params["U_ratio"]))


def test_load_cumming_richards_preset_uses_named_evolution_constants() -> None:
    ge_engine = GeochemistryEngine()

    assert ge_engine.load_preset("Cumming & Richards (Model III)") is True

    params = ge_engine.get_parameters()
    assert params["E1"] == pytest.approx(E1_CUMMING_RICHARDS)
    assert params["E2"] == pytest.approx(E2_CUMMING_RICHARDS)


def test_geokit_preset_uses_named_time_constants() -> None:
    geokit = PRESET_MODELS["V1V2 (Geokit)"]

    assert geokit["T1"] == pytest.approx(T_EARTH_1ST)
    assert geokit["T2"] == pytest.approx(T_EARTH_CANON)
    assert geokit["Tsec"] == pytest.approx(T_SK_STAGE2)


def test_stacey_kramers_stage2_preset_uses_named_mantle_constants() -> None:
    sk2 = PRESET_MODELS["Stacey & Kramers (2nd Stage)"]

    assert sk2["mu_M"] == pytest.approx(MU_M_DEFAULT)
    assert sk2["omega_M"] == pytest.approx(OMEGA_M_DEFAULT)


def test_is_zero_like_treats_zero_as_zero_like() -> None:
    assert _is_zero_like(0.0) is True


def test_exp_evolution_term_zero_uses_plain_exponential() -> None:
    lmbda = 1.55125e-10
    t_years = np.array([1.0e6, 2.5e6, 4.0e6], dtype=float)

    result = _exp_evolution_term(lmbda, t_years, E=0.0)
    expected = np.exp(lmbda * t_years)

    np.testing.assert_allclose(result, expected)


def test_exp_evolution_term_nonzero_applies_evolution_factor() -> None:
    lmbda = 9.8485e-10
    t_years = np.array([2.0e6, 3.0e6], dtype=float)
    e_value = 0.145

    result = _exp_evolution_term(lmbda, t_years, E=e_value)
    expected = np.exp(lmbda * t_years) * (1.0 - e_value * (t_years - (1.0 / lmbda)))

    np.testing.assert_allclose(result, expected)


def test_update_derived_params_uses_mu_default_when_missing() -> None:
    ge_engine = GeochemistryEngine()
    ge_engine.params.pop("mu_M", None)

    ge_engine._update_derived_params()

    params = ge_engine.get_parameters()
    assert params["v_M"] == pytest.approx(MU_M_DEFAULT * float(params["U_ratio"]))


def test_calculate_modelcurve_uses_named_mu_omega_defaults_when_missing() -> None:
    ge_engine = GeochemistryEngine()
    params = ge_engine.get_parameters()
    params.pop("mu_M", None)
    params.pop("omega_M", None)
    t_vals = np.array([1.0, 5.0], dtype=float)

    with_defaults = calculate_modelcurve(t_vals, params=params)
    with_explicit_constants = calculate_modelcurve(
        t_vals,
        params=params,
        Mu1=MU_M_DEFAULT,
        W1=OMEGA_M_DEFAULT,
    )

    np.testing.assert_allclose(with_defaults["Pb206_204"], with_explicit_constants["Pb206_204"])
    np.testing.assert_allclose(with_defaults["Pb207_204"], with_explicit_constants["Pb207_204"])
    np.testing.assert_allclose(with_defaults["Pb208_204"], with_explicit_constants["Pb208_204"])


def test_calculate_modelcurve_uses_named_e_defaults_when_missing() -> None:
    ge_engine = GeochemistryEngine()
    params = ge_engine.get_parameters()
    params.pop("E1", None)
    params.pop("E2", None)
    t_vals = np.array([1.0, 5.0], dtype=float)

    with_defaults = calculate_modelcurve(t_vals, params=params)
    with_explicit_constants = calculate_modelcurve(
        t_vals,
        params=params,
        E1=E1_DEFAULT,
        E2=E2_DEFAULT,
    )

    np.testing.assert_allclose(with_defaults["Pb206_204"], with_explicit_constants["Pb206_204"])
    np.testing.assert_allclose(with_defaults["Pb207_204"], with_explicit_constants["Pb207_204"])
    np.testing.assert_allclose(with_defaults["Pb208_204"], with_explicit_constants["Pb208_204"])
