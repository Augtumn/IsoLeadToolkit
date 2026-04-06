"""Tests for geochemistry overlay drawing helpers."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from core import app_state
from visualization.plotting.geochem import (
    isochron_fits,
    model_overlays,
    paleoisochron_overlays,
    plumbotectonics_isoage,
    selected_isochron_overlay,
)


class _FakeModelGeochemistry:
    class engine:
        @staticmethod
        def get_parameters() -> dict[str, float]:
            return {"Tsec": 0.0, "T2": 1_000_000.0}

    @staticmethod
    def calculate_modelcurve(_t_vals, params=None, T1=None):
        _ = params, T1
        return {
            "Pb206_204": np.array([1.0, 2.0, 3.0], dtype=float),
            "Pb207_204": np.array([4.0, 5.0, 6.0], dtype=float),
            "Pb208_204": np.array([7.0, 8.0, 9.0], dtype=float),
        }


class _FakePaleoGeochemistry:
    @staticmethod
    def calculate_paleoisochron_line(_age, params=None, algorithm=None):
        _ = params, algorithm
        return (0.5, 1.0)


def _snapshot_state() -> dict[str, object]:
    keys = [
        "selected_isochron_data",
        "overlay_curve_label_data",
        "paleoisochron_label_data",
        "plumbotectonics_isoage_label_data",
        "line_styles",
    ]
    return {key: getattr(app_state, key, None) for key in keys}


def _restore_state(snapshot: dict[str, object]) -> None:
    for key, value in snapshot.items():
        setattr(app_state, key, value)


def test_draw_isochron_overlays_no_geochemistry_is_noop(monkeypatch) -> None:
    fig, ax = plt.subplots()
    try:
        monkeypatch.setattr(isochron_fits, "_lazy_import_geochemistry", lambda: (None, None))

        isochron_fits._draw_isochron_overlays(ax, "PB_EVOL_76")

        assert len(ax.lines) == 0
    finally:
        plt.close(fig)


def test_draw_model_curves_renders_curve_line(monkeypatch) -> None:
    snapshot = _snapshot_state()
    fig, ax = plt.subplots()
    try:
        setattr(app_state, "overlay_curve_label_data", [])
        monkeypatch.setattr(model_overlays, "_lazy_import_geochemistry", lambda: (_FakeModelGeochemistry(), None))
        monkeypatch.setattr(model_overlays, "position_curve_label", lambda *args, **kwargs: None)

        model_overlays._draw_model_curves(ax, "PB_EVOL_76", [{"Tsec": 0.0, "T2": 1_000_000.0}])

        assert len(ax.lines) >= 1
    finally:
        plt.close(fig)
        _restore_state(snapshot)


def test_draw_mu_kappa_paleoisochrons_ignores_invalid_ages() -> None:
    fig, ax = plt.subplots()
    try:
        model_overlays._draw_mu_kappa_paleoisochrons(ax, [100.0, "invalid", np.nan])

        assert len(ax.lines) == 1
    finally:
        plt.close(fig)


def test_draw_paleoisochrons_draws_line_and_label_data(monkeypatch) -> None:
    snapshot = _snapshot_state()
    fig, ax = plt.subplots()
    try:
        monkeypatch.setattr(paleoisochron_overlays, "_lazy_import_geochemistry", lambda: (_FakePaleoGeochemistry(), None))
        monkeypatch.setattr(paleoisochron_overlays, "position_curve_label", lambda *args, **kwargs: None)

        paleoisochron_overlays._draw_paleoisochrons(ax, "PB_EVOL_76", [100.0], {"Tsec": 0.0})

        assert len(ax.lines) == 1
        assert len(getattr(app_state, "paleoisochron_label_data", [])) == 1
    finally:
        plt.close(fig)
        _restore_state(snapshot)


def test_draw_plumbotectonics_isoage_lines_draws_multiple_lines(monkeypatch) -> None:
    snapshot = _snapshot_state()
    fig, ax = plt.subplots()
    try:
        section = {
            "groups": [
                {"t": [0.1, 0.2], "pb206": [1.0, 2.0], "pb207": [3.0, 4.0]},
                {"t": [0.1, 0.2], "pb206": [1.5, 2.5], "pb207": [3.5, 4.5]},
            ]
        }
        monkeypatch.setattr(plumbotectonics_isoage, "_load_plumbotectonics_data", lambda: {"stub": section})
        monkeypatch.setattr(plumbotectonics_isoage, "_select_plumbotectonics_section", lambda _sections: section)
        monkeypatch.setattr(plumbotectonics_isoage, "position_curve_label", lambda *args, **kwargs: None)

        plumbotectonics_isoage._draw_plumbotectonics_isoage_lines(ax, "PLUMBOTECTONICS_76")

        assert len(ax.lines) == 2
        assert len(getattr(app_state, "plumbotectonics_isoage_label_data", [])) == 2
    finally:
        plt.close(fig)
        _restore_state(snapshot)


def test_draw_selected_isochron_renders_highlight() -> None:
    snapshot = _snapshot_state()
    fig, ax = plt.subplots()
    try:
        setattr(
            app_state,
            "selected_isochron_data",
            {
                "x_range": [1.0, 2.0],
                "y_range": [3.0, 4.0],
                "age_ma": 120.0,
                "age_err_2sigma": 8.0,
                "mswd": 1.1,
            },
        )

        selected_isochron_overlay._draw_selected_isochron(ax)

        assert len(ax.lines) == 1
    finally:
        plt.close(fig)
        _restore_state(snapshot)
