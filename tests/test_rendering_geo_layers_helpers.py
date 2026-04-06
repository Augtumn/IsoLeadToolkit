"""Tests for rendering geo overlay dispatcher helper."""

from __future__ import annotations

import matplotlib.pyplot as plt

from core import app_state
from visualization.plotting.rendering import geo_layers


class _FakeGeochemistry:
    class engine:
        @staticmethod
        def get_parameters():
            return {"x": 1}


def _snapshot_geo_state() -> dict[str, object]:
    keys = [
        "ax",
        "show_model_curves",
        "show_isochrons",
        "selected_isochron_data",
        "show_paleoisochrons",
        "paleoisochron_ages",
        "show_model_age_lines",
        "show_plumbotectonics_curves",
    ]
    return {key: getattr(app_state, key, None) for key in keys}


def _restore_geo_state(snapshot: dict[str, object]) -> None:
    for key, value in snapshot.items():
        setattr(app_state, key, value)


def test_render_geo_overlays_plumbotectonics_dispatch(monkeypatch) -> None:
    snapshot = _snapshot_geo_state()
    fig, ax = plt.subplots()
    calls: list[str] = []
    try:
        setattr(app_state, "ax", ax)
        setattr(app_state, "show_paleoisochrons", True)
        setattr(app_state, "show_plumbotectonics_curves", True)

        monkeypatch.setattr(geo_layers, "_draw_plumbotectonics_isoage_lines", lambda _ax, _alg: calls.append("isoage"))
        monkeypatch.setattr(geo_layers, "_draw_plumbotectonics_curves", lambda _ax, _alg: calls.append("curves"))
        monkeypatch.setattr(geo_layers, "_draw_equation_overlays", lambda _ax: calls.append("equation"))

        geo_layers._render_geo_overlays(
            actual_algorithm="PLUMBOTECTONICS_76",
            prev_ax=ax,
            prev_embedding_type="PLUMBOTECTONICS_76",
            prev_xlim=ax.get_xlim(),
            prev_ylim=ax.get_ylim(),
        )

        assert calls == ["isoage", "curves", "equation"]
    finally:
        plt.close(fig)
        _restore_geo_state(snapshot)


def test_render_geo_overlays_pb_mu_age_dispatch(monkeypatch) -> None:
    snapshot = _snapshot_geo_state()
    fig, ax = plt.subplots()
    calls: list[str] = []
    try:
        setattr(app_state, "ax", ax)
        setattr(app_state, "show_paleoisochrons", True)
        setattr(app_state, "paleoisochron_ages", [100, 200])

        monkeypatch.setattr(geo_layers, "_lazy_import_geochemistry", lambda: (_FakeGeochemistry(), None))
        monkeypatch.setattr(geo_layers, "_draw_mu_kappa_paleoisochrons", lambda _ax, ages: calls.append(f"mu_kappa:{ages}"))
        monkeypatch.setattr(geo_layers, "_draw_equation_overlays", lambda _ax: calls.append("equation"))

        geo_layers._render_geo_overlays(
            actual_algorithm="PB_MU_AGE",
            prev_ax=ax,
            prev_embedding_type="PB_MU_AGE",
            prev_xlim=ax.get_xlim(),
            prev_ylim=ax.get_ylim(),
        )

        assert calls == ["mu_kappa:[100, 200]", "equation"]
    finally:
        plt.close(fig)
        _restore_geo_state(snapshot)
