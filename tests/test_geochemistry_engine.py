"""Geochemistry engine, model-sync and runtime-default tests."""

import numpy as np
import pytest

import data.geochemistry as geochemistry_module
import data.geochemistry.source as geochemistry_source_module
from core import app_state, state_gateway
from data import geochemistry
from data.geochemistry import PRESET_MODELS, engine
from data.geochemistry.delta import calculate_v1v2_coordinates
from data.geochemistry.engine import (
    E1_CUMMING_RICHARDS,
    E1_DEFAULT,
    E2_CUMMING_RICHARDS,
    E2_DEFAULT,
    GeochemistryEngine,
    KAPPA_V1V2_DEFAULT,
    MU_M_DEFAULT,
    MU_V1V2_DEFAULT,
    OMEGA_M_DEFAULT,
    OMEGA_V1V2_DEFAULT,
    PRESET_MODELS,
    T_EARTH_1ST,
    T_EARTH_CANON,
    T_SK_STAGE2,
    _exp_evolution_term,
    _is_zero_like,
    calculate_modelcurve,
)
from ui.panels.data.grouping import DataPanelGroupingMixin


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


def test_v1v2_presets_share_named_mantle_ratio_constants() -> None:
    geokit = PRESET_MODELS["V1V2 (Geokit)"]
    zhu = PRESET_MODELS["V1V2 (Zhu 1993)"]

    assert geokit["mu_M"] == pytest.approx(MU_V1V2_DEFAULT)
    assert zhu["mu_M"] == pytest.approx(MU_V1V2_DEFAULT)
    assert OMEGA_V1V2_DEFAULT == pytest.approx(MU_V1V2_DEFAULT * KAPPA_V1V2_DEFAULT)
    assert geokit["omega_M"] == pytest.approx(OMEGA_V1V2_DEFAULT)
    assert zhu["omega_M"] == pytest.approx(OMEGA_V1V2_DEFAULT)


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


class _DummyGroupingPanel(DataPanelGroupingMixin):
    """Minimal host for DataPanelGroupingMixin behavior tests."""

    def __init__(self) -> None:
        self.geo_panel = None


def _restore_model(model_name: str) -> None:
    if model_name in PRESET_MODELS:
        engine.load_preset(model_name)
        state_gateway.set_geo_model_name(model_name)


def test_sync_geochem_model_for_v1v2_without_geo_panel() -> None:
    previous_model = getattr(engine, "current_model_name", "")
    panel = _DummyGroupingPanel()

    try:
        engine.load_preset("Stacey & Kramers (2nd Stage)")
        state_gateway.set_geo_model_name("Stacey & Kramers (2nd Stage)")

        panel._sync_geochem_model_for_mode("V1V2")

        assert engine.current_model_name == "V1V2 (Zhu 1993)"
        assert app_state.geo_model_name == "V1V2 (Zhu 1993)"
        assert engine.get_parameters().get("v1v2_formula") == "zhu1993"
    finally:
        _restore_model(previous_model)


def test_sync_geochem_model_for_pb_evolution_without_geo_panel() -> None:
    previous_model = getattr(engine, "current_model_name", "")
    panel = _DummyGroupingPanel()

    try:
        engine.load_preset("V1V2 (Zhu 1993)")
        state_gateway.set_geo_model_name("V1V2 (Zhu 1993)")

        panel._sync_geochem_model_for_mode("PB_EVOL_76")

        assert engine.current_model_name == "Stacey & Kramers (2nd Stage)"
        assert app_state.geo_model_name == "Stacey & Kramers (2nd Stage)"
    finally:
        _restore_model(previous_model)


def test_zhu1993_uses_same_regression_plane_projection_as_default() -> None:
    d_alpha = np.array([1.2, -0.3, 0.0, 2.1], dtype=float)
    d_beta = np.array([0.4, 1.1, -0.9, 0.2], dtype=float)
    d_gamma = np.array([-0.7, 0.8, 0.5, -1.2], dtype=float)

    base_params = {'a': 0.0, 'b': 2.0367, 'c': -6.143}
    zhu_params = {**base_params, 'v1v2_formula': 'zhu1993'}
    default_params = {**base_params, 'v1v2_formula': 'default'}

    v1_zhu, v2_zhu = calculate_v1v2_coordinates(d_alpha, d_beta, d_gamma, params=zhu_params)
    v1_def, v2_def = calculate_v1v2_coordinates(d_alpha, d_beta, d_gamma, params=default_params)

    np.testing.assert_allclose(v1_zhu, v1_def, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(v2_zhu, v2_def, rtol=0.0, atol=1e-12)


def test_geokit_clamps_negative_single_stage_age_for_delta(monkeypatch) -> None:
    previous_model = getattr(engine, "current_model_name", "")
    captured: dict[str, np.ndarray | float | None] = {}

    class _StopAfterDeltas(Exception):
        pass

    def fake_single_stage_age(*_args, **_kwargs):
        return np.array([-5.0, 3.0], dtype=float)

    def fake_two_stage_age(*_args, **_kwargs):
        return np.array([100.0, 200.0], dtype=float)

    def fake_calculate_deltas(_pb206, _pb207, _pb208, t_ma, **kwargs):
        captured["t_ma"] = np.asarray(t_ma, dtype=float)
        captured["t_mantle"] = kwargs.get("T_mantle")
        raise _StopAfterDeltas()

    try:
        engine.load_preset("V1V2 (Geokit)")
        state_gateway.set_geo_model_name("V1V2 (Geokit)")

        monkeypatch.setattr(geochemistry_module, "calculate_single_stage_age", fake_single_stage_age)
        monkeypatch.setattr(geochemistry_module, "calculate_two_stage_age", fake_two_stage_age)
        monkeypatch.setattr(geochemistry_module, "calculate_deltas", fake_calculate_deltas)

        with pytest.raises(_StopAfterDeltas):
            geochemistry_module.calculate_all_parameters(
                np.array([10.0, 11.0], dtype=float),
                np.array([10.5, 11.5], dtype=float),
                np.array([30.0, 31.0], dtype=float),
            )

        np.testing.assert_allclose(captured["t_ma"], np.array([0.0, 3.0], dtype=float), rtol=0.0, atol=1e-12)
        assert float(captured["t_mantle"]) == engine.get_parameters().get("T2")
    finally:
        _restore_model(previous_model)


def test_single_stage_model_mu_uses_a0_b0_t2(monkeypatch) -> None:
    captured: dict[str, float] = {}

    def fake_invert_mu(_x, _y, _t, x_ref, y_ref, t_ref, _params):
        captured["x_ref"] = float(x_ref)
        captured["y_ref"] = float(y_ref)
        captured["t_ref"] = float(t_ref)
        return np.array([1.0], dtype=float)

    params = {
        "age_model": "single_stage",
        "a0": 9.307,
        "b0": 10.294,
        "a1": 11.152,
        "b1": 12.998,
        "T1": 4_430e6,
        "T2": 4_570e6,
    }

    monkeypatch.setattr(geochemistry_source_module, "_invert_mu", fake_invert_mu)
    result = geochemistry_source_module.calculate_model_mu(
        np.array([18.0], dtype=float),
        np.array([15.0], dtype=float),
        np.array([1200.0], dtype=float),
        params=params,
    )

    np.testing.assert_allclose(result, np.array([1.0], dtype=float), rtol=0.0, atol=1e-12)
    assert captured["x_ref"] == params["a0"]
    assert captured["y_ref"] == params["b0"]
    assert captured["t_ref"] == params["T2"]


def test_single_stage_initial_ratio_64_uses_a0_t2(monkeypatch) -> None:
    params = {
        "age_model": "single_stage",
        "a0": 9.307,
        "a1": 11.152,
        "T1": 4_430e6,
        "T2": 4_570e6,
        "lambda_238": 1.55125e-10,
        "lambda_235": 9.8485e-10,
        "lambda_232": 4.94752e-11,
        "U_ratio": 1.0 / 137.88,
    }

    monkeypatch.setattr(
        geochemistry_source_module,
        "calculate_model_mu",
        lambda *_args, **_kwargs: np.array([0.0], dtype=float),
    )

    ratio = geochemistry_source_module.calculate_initial_ratio_64(
        np.array([1000.0], dtype=float),
        np.array([18.0], dtype=float),
        np.array([15.0], dtype=float),
        params=params,
    )

    np.testing.assert_allclose(ratio, np.array([params["a0"]], dtype=float), rtol=0.0, atol=1e-12)


def test_resolve_age_model_prefers_explicit_flag() -> None:
    params = {"age_model": "2-stage"}

    assert geochemistry.resolve_age_model(params=params, model_name="Custom Model") == "two_stage"


def test_resolve_age_model_uses_param_delta_floor_for_single_stage() -> None:
    params = {
        "Tsec": 100.0,
        "a0": 9.307,
        "b0": 10.294,
        "c0": 29.476,
        "a1": 9.307 + 5e-7,
        "b1": 10.294 - 5e-7,
        "c1": 29.476 + 5e-7,
    }

    assert geochemistry.resolve_age_model(params=params, model_name="Custom Model") == "single_stage"


def test_resolve_age_model_returns_two_stage_when_delta_exceeds_floor() -> None:
    params = {
        "Tsec": 100.0,
        "a0": 9.307,
        "b0": 10.294,
        "c0": 29.476,
        "a1": 9.307 + 2e-6,
        "b1": 10.294,
        "c1": 29.476,
    }

    assert geochemistry.resolve_age_model(params=params, model_name="Custom Model") == "two_stage"
