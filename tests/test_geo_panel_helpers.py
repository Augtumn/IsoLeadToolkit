"""Tests for GeoPanel helper methods and constants."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("PyQt5")

from data.geochemistry import LAMBDA_232, LAMBDA_235, LAMBDA_238
from ui.panels import geo_panel as geo_panel_module


class _FakeLabel:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeSpinBox:
    def __init__(self) -> None:
        self.value = None
        self.single_step = None
        self.decimals = None
        self.range = None

    def setRange(self, min_val: float, max_val: float) -> None:
        self.range = (min_val, max_val)

    def setDecimals(self, value: int) -> None:
        self.decimals = value

    def setSingleStep(self, value: float) -> None:
        self.single_step = value

    def setValue(self, value: float) -> None:
        self.value = value


class _FakeGrid:
    def __init__(self) -> None:
        self.items: list[tuple[object, int, int]] = []

    def addWidget(self, widget: object, row: int, col: int) -> None:
        self.items.append((widget, row, col))


def test_geo_panel_decay_defaults_match_engine_constants() -> None:
    assert geo_panel_module._GEO_DECAY_LAMBDA_238_DEFAULT == pytest.approx(LAMBDA_238)
    assert geo_panel_module._GEO_DECAY_LAMBDA_235_DEFAULT == pytest.approx(LAMBDA_235)
    assert geo_panel_module._GEO_DECAY_LAMBDA_232_DEFAULT == pytest.approx(LAMBDA_232)


def test_add_geo_param_uses_scientific_step_constant(monkeypatch) -> None:
    monkeypatch.setattr(geo_panel_module, "QLabel", _FakeLabel)
    monkeypatch.setattr(geo_panel_module, "QDoubleSpinBox", _FakeSpinBox)

    panel = SimpleNamespace(geo_params={}, geo_param_labels={})
    grid = _FakeGrid()

    geo_panel_module.GeoPanel._add_geo_param(
        panel,
        grid,
        "lambda_238",
        "lambda label",
        0,
        0,
        0.0,
        1.0,
        geo_panel_module._GEO_DECAY_LAMBDA_238_DEFAULT,
        scientific=True,
    )

    spinbox = panel.geo_params["lambda_238"]
    assert spinbox.single_step == geo_panel_module._GEO_PARAM_SCIENTIFIC_STEP
    assert spinbox.decimals == geo_panel_module._GEO_PARAM_SCIENTIFIC_DECIMALS
    assert spinbox.value == geo_panel_module._GEO_DECAY_LAMBDA_238_DEFAULT


def test_add_geo_param_uses_default_step_and_decimals_when_not_scientific(monkeypatch) -> None:
    monkeypatch.setattr(geo_panel_module, "QLabel", _FakeLabel)
    monkeypatch.setattr(geo_panel_module, "QDoubleSpinBox", _FakeSpinBox)

    panel = SimpleNamespace(geo_params={}, geo_param_labels={})
    grid = _FakeGrid()

    geo_panel_module.GeoPanel._add_geo_param(
        panel,
        grid,
        "T1",
        "time label",
        0,
        0,
        0.0,
        10000.0,
        4430.0,
        scientific=False,
    )

    spinbox = panel.geo_params["T1"]
    assert spinbox.single_step == geo_panel_module._GEO_PARAM_DEFAULT_STEP
    assert spinbox.decimals == geo_panel_module._GEO_PARAM_DEFAULT_DECIMALS
    assert spinbox.value == 4430.0
