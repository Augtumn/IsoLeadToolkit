"""Tests for geochemistry model auto-sync in Data panel."""

from __future__ import annotations

import numpy as np

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
