"""Tests for plotting.core axes helper behavior."""

from __future__ import annotations

import matplotlib.pyplot as plt

from core import app_state
from visualization.plotting.core import _ensure_axes


def _snapshot_axes_state() -> dict[str, object]:
    return {
        "fig": getattr(app_state, "fig", None),
        "ax": getattr(app_state, "ax", None),
        "legend_ax": getattr(app_state, "legend_ax", None),
    }


def _restore_axes_state(snapshot: dict[str, object]) -> None:
    setattr(app_state, "fig", snapshot.get("fig"))
    setattr(app_state, "ax", snapshot.get("ax"))
    setattr(app_state, "legend_ax", snapshot.get("legend_ax"))


def test_ensure_axes_returns_none_when_figure_missing() -> None:
    snapshot = _snapshot_axes_state()
    try:
        setattr(app_state, "fig", None)
        setattr(app_state, "ax", None)

        result = _ensure_axes()

        assert result is None
    finally:
        _restore_axes_state(snapshot)


def test_ensure_axes_switches_between_2d_and_3d() -> None:
    snapshot = _snapshot_axes_state()
    fig = plt.figure()
    try:
        setattr(app_state, "fig", fig)
        setattr(app_state, "ax", None)
        setattr(app_state, "legend_ax", object())

        ax2d = _ensure_axes(2)
        assert ax2d is not None
        assert getattr(ax2d, "name", "") != "3d"
        assert getattr(app_state, "legend_ax", None) is None

        ax3d = _ensure_axes(3)
        assert ax3d is not None
        assert getattr(ax3d, "name", "") == "3d"
        assert getattr(app_state, "legend_ax", None) is None

        ax2d_again = _ensure_axes(2)
        assert ax2d_again is not None
        assert getattr(ax2d_again, "name", "") != "3d"
    finally:
        plt.close(fig)
        _restore_axes_state(snapshot)
