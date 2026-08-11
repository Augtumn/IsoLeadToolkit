"""Tests for plotting KDE helper functions."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from core import app_state, state_gateway
from visualization.plotting import kde as kde_helpers
from visualization.plotting.kde import _estimate_density_curve, clear_marginal_axes, draw_marginal_kde


def _snapshot_marginal_axes_state() -> object:
    return getattr(app_state, "marginal_axes", None)


def _restore_marginal_axes_state(snapshot: object) -> None:
    state_gateway.set_marginal_axes(snapshot)


def test_draw_marginal_kde_creates_and_registers_axes() -> None:
    snapshot = _snapshot_marginal_axes_state()
    fig, ax = plt.subplots()
    try:
        state_gateway.set_marginal_axes(None)

        df_plot = pd.DataFrame(
            {
                "group": ["A", "A", "A", "A"],
                "_emb_x": [1.0, 2.0, 3.0, 4.0],
                "_emb_y": [1.5, 2.5, 3.5, 4.5],
            }
        )

        draw_marginal_kde(
            ax=ax,
            df_plot=df_plot,
            group_col="group",
            palette={"A": "#1f77b4"},
            unique_cats=["A"],
        )

        marginal_axes = getattr(app_state, "marginal_axes", None)
        assert marginal_axes is not None
        assert len(marginal_axes) == 2
    finally:
        clear_marginal_axes()
        plt.close(fig)
        _restore_marginal_axes_state(snapshot)


def test_draw_marginal_kde_uses_layout_helper(monkeypatch) -> None:
    snapshot = _snapshot_marginal_axes_state()
    fig, ax = plt.subplots()
    called: dict[str, object | None] = {"fig": None}
    try:
        state_gateway.set_marginal_axes(None)
        monkeypatch.setattr(
            kde_helpers,
            "configure_constrained_layout",
            lambda target_fig: called.__setitem__("fig", target_fig),
        )

        df_plot = pd.DataFrame(
            {
                "group": ["A", "A", "A", "A"],
                "_emb_x": [1.0, 2.0, 3.0, 4.0],
                "_emb_y": [1.5, 2.5, 3.5, 4.5],
            }
        )

        draw_marginal_kde(
            ax=ax,
            df_plot=df_plot,
            group_col="group",
            palette={"A": "#1f77b4"},
            unique_cats=["A"],
        )

        assert called["fig"] is fig
    finally:
        clear_marginal_axes()
        plt.close(fig)
        _restore_marginal_axes_state(snapshot)


def test_clear_marginal_axes_resets_state() -> None:
    snapshot = _snapshot_marginal_axes_state()
    fig, ax = plt.subplots()
    try:
        ax_top = fig.add_axes([0.1, 0.85, 0.8, 0.1])
        ax_right = fig.add_axes([0.85, 0.1, 0.1, 0.8])
        state_gateway.set_marginal_axes((ax_top, ax_right))

        clear_marginal_axes()

        assert getattr(app_state, "marginal_axes", None) is None
    finally:
        plt.close(fig)
        _restore_marginal_axes_state(snapshot)


def test_estimate_density_curve_returns_none_for_near_constant_data() -> None:
    curve = _estimate_density_curve(
        np.array([1.0, 1.0 + 1e-13, 1.0 - 1e-13], dtype=float),
        bw_adjust=1.0,
        bandwidth=0.0,
        kernel="gaussian",
        auto_bandwidth_method="scott",
        gridsize=64,
        cut=1.0,
        log_transform=False,
    )

    assert curve is None


def test_estimate_density_curve_supports_custom_kernel_and_bandwidth() -> None:
    curve = _estimate_density_curve(
        np.array([0.0, 0.8, 1.6, 2.4, 3.2], dtype=float),
        bw_adjust=1.0,
        bandwidth=0.4,
        kernel="cosine",
        auto_bandwidth_method="scott",
        gridsize=64,
        cut=1.0,
        log_transform=False,
    )

    assert curve is not None
    grid, density = curve
    assert grid.shape == density.shape
    assert grid.size >= 32


def test_estimate_density_curve_supports_scott_and_silverman_auto_methods() -> None:
    values = np.array([0.2, 0.8, 1.1, 1.9, 2.2, 2.9, 3.5], dtype=float)

    scott_curve = _estimate_density_curve(
        values,
        bw_adjust=1.0,
        bandwidth=0.0,
        kernel="gaussian",
        auto_bandwidth_method="scott",
        gridsize=64,
        cut=1.0,
        log_transform=False,
    )
    silverman_curve = _estimate_density_curve(
        values,
        bw_adjust=1.0,
        bandwidth=0.0,
        kernel="gaussian",
        auto_bandwidth_method="silverman",
        gridsize=64,
        cut=1.0,
        log_transform=False,
    )

    assert scott_curve is not None
    assert silverman_curve is not None
    _, scott_density = scott_curve
    _, silverman_density = silverman_curve
    assert not np.allclose(scott_density, silverman_density)


def test_lazy_import_seaborn_exposes_sns_attribute() -> None:
    """Regression: rendering/kde.py and plot2d.py call
    ``kde_utils.lazy_import_seaborn()`` then use ``kde_utils.sns``. The
    helper must exist and populate the module-level ``sns`` attribute,
    otherwise KDE overlays fail silently (AttributeError swallowed)."""
    assert callable(kde_helpers.lazy_import_seaborn)

    seaborn_mod = kde_helpers.lazy_import_seaborn()
    assert seaborn_mod is not None
    assert kde_helpers.sns is not None
    assert hasattr(kde_helpers.sns, "kdeplot")
