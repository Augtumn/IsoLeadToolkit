"""Tests for geochemistry model auto-sync in Data panel."""

from __future__ import annotations

import numpy as np
import pytest

import data.geochemistry as geochemistry_module
import data.geochemistry.source as geochemistry_source_module
from core import app_state, state_gateway
from data.geochemistry import PRESET_MODELS, engine
from data.geochemistry.delta import calculate_v1v2_coordinates
from ui.panels.data.grouping import DataPanelGroupingMixin


class _DummyGroupingPanel(DataPanelGroupingMixin):
    """Minimal host for DataPanelGroupingMixin behavior tests."""

    def __init__(self) -> None:
        self.geo_panel = None


def _restore_model(model_name: str) -> None:
    if model_name in PRESET_MODELS:
        engine.load_preset(model_name)
        state_gateway.set_attr("geo_model_name", model_name)


def test_sync_geochem_model_for_v1v2_without_geo_panel() -> None:
    previous_model = getattr(engine, "current_model_name", "")
    panel = _DummyGroupingPanel()

    try:
        engine.load_preset("Stacey & Kramers (2nd Stage)")
        state_gateway.set_attr("geo_model_name", "Stacey & Kramers (2nd Stage)")

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
        state_gateway.set_attr("geo_model_name", "V1V2 (Zhu 1993)")

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
    captured: dict[str, np.ndarray] = {}

    class _StopAfterDeltas(Exception):
        pass

    def fake_single_stage_age(*_args, **_kwargs):
        return np.array([-5.0, 3.0], dtype=float)

    def fake_two_stage_age(*_args, **_kwargs):
        return np.array([100.0, 200.0], dtype=float)

    def fake_calculate_deltas(_pb206, _pb207, _pb208, t_ma, **_kwargs):
        captured["t_ma"] = np.asarray(t_ma, dtype=float)
        raise _StopAfterDeltas()

    try:
        engine.load_preset("V1V2 (Geokit)")
        state_gateway.set_attr("geo_model_name", "V1V2 (Geokit)")

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
