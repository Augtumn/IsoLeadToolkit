"""Tests for the new KDE parameters: compute kwargs, clipping and cumulative mode."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from core import app_state, state_gateway
from visualization.plotting import kde as plotting_kde
from visualization.plotting.kde import _estimate_density_curve, kde_compute_kwargs
from visualization.plotting.rendering import kde as rendering_kde
from visualization.plotting.rendering.raw import plot2d


@pytest.fixture(autouse=True)
def _restore_kde_options():
    snapshot = {
        "bw_adjust": app_state.kde_bw_adjust,
        "bw_method": app_state.kde_bw_method,
        "gridsize": app_state.kde_gridsize,
        "thresh": app_state.kde_thresh,
        "clip_min": app_state.kde_clip_min,
        "clip_max": app_state.kde_clip_max,
        "common_norm": app_state.kde_common_norm,
        "warn_singular": app_state.kde_warn_singular,
        "marginal_clip_min": app_state.marginal_kde_clip_min,
        "marginal_clip_max": app_state.marginal_kde_clip_max,
        "marginal_cumulative": app_state.marginal_kde_cumulative,
        "styles": dict(app_state.line_styles or {}),
    }
    yield
    state_gateway.set_kde_compute_options(
        bw_adjust=snapshot["bw_adjust"], bw_method=snapshot["bw_method"],
        gridsize=snapshot["gridsize"], thresh=snapshot["thresh"],
        common_norm=snapshot["common_norm"], warn_singular=snapshot["warn_singular"],
    )
    if snapshot["clip_min"] is None and snapshot["clip_max"] is None:
        state_gateway.set_kde_compute_options(clear_clip=True)
    else:
        state_gateway.set_kde_compute_options(
            clip_min=snapshot["clip_min"], clip_max=snapshot["clip_max"]
        )
    state_gateway.set_marginal_kde_compute_options(cumulative=snapshot["marginal_cumulative"])
    if snapshot["marginal_clip_min"] is None and snapshot["marginal_clip_max"] is None:
        state_gateway.set_marginal_kde_compute_options(clear_clip=True)
    else:
        state_gateway.set_marginal_kde_compute_options(
            clip_min=snapshot["marginal_clip_min"], clip_max=snapshot["marginal_clip_max"]
        )
    state_gateway.set_line_styles(snapshot["styles"])


def test_kde_compute_kwargs_defaults_and_clamping() -> None:
    state_gateway.set_kde_compute_options(
        bw_adjust=1.0, bw_method="scott", gridsize=200, thresh=0.05,
        common_norm=False, warn_singular=False, clear_clip=True,
    )
    assert kde_compute_kwargs() == {
        "bw_adjust": 1.0,
        "bw_method": "scott",
        "gridsize": 200,
        "thresh": 0.05,
        "common_norm": False,
        "warn_singular": False,
    }

    state_gateway.set_kde_compute_options(
        bw_adjust=99.0, bw_method="bogus", gridsize=1, thresh=3.0
    )
    clamped = kde_compute_kwargs()
    assert clamped["bw_adjust"] == 5.0
    assert clamped["bw_method"] == "scott"
    assert clamped["gridsize"] == 32
    assert clamped["thresh"] == 1.0


def test_kde_compute_kwargs_clip_range() -> None:
    state_gateway.set_kde_compute_options(clear_clip=True)
    assert "clip" not in kde_compute_kwargs()

    state_gateway.set_kde_compute_options(clip_min=-2.0, clip_max=8.0)
    assert kde_compute_kwargs()["clip"] == (-2.0, 8.0)

    state_gateway.set_kde_compute_options(clip_min=5.0, clip_max=1.0)  # inverted
    assert "clip" not in kde_compute_kwargs(), "an inverted range must be ignored"


def test_estimate_density_curve_clips_data_and_grid() -> None:
    values = np.array([10.0, 11.0, 12.0, 500.0])  # one far outlier

    unclipped = _estimate_density_curve(
        values, bw_adjust=1.0, bandwidth=0.0, kernel="gaussian",
        auto_bandwidth_method="scott", gridsize=128, cut=1.0, log_transform=False,
    )
    assert unclipped is not None
    assert unclipped[0].max() > 100.0

    clipped = _estimate_density_curve(
        values, bw_adjust=1.0, bandwidth=0.0, kernel="gaussian",
        auto_bandwidth_method="scott", gridsize=128, cut=1.0, log_transform=False,
        clip_min=9.0, clip_max=13.0,
    )
    assert clipped is not None
    grid = clipped[0]
    assert grid.min() >= 9.0 and grid.max() <= 13.0
    assert clipped[1].max() > 0.0


def test_estimate_density_curve_rejects_degenerate_clip() -> None:
    values = np.array([1.0, 2.0, 3.0, 4.0])
    assert _estimate_density_curve(
        values, bw_adjust=1.0, bandwidth=0.0, kernel="gaussian",
        auto_bandwidth_method="scott", gridsize=64, cut=1.0, log_transform=False,
        clip_min=5.0, clip_max=1.0,
    ) is None
    assert _estimate_density_curve(
        values, bw_adjust=1.0, bandwidth=0.0, kernel="gaussian",
        auto_bandwidth_method="scott", gridsize=64, cut=1.0, log_transform=False,
        clip_min=100.0, clip_max=200.0,
    ) is None


def test_estimate_density_curve_cumulative_is_normalised() -> None:
    values = np.linspace(0.0, 10.0, 200)
    result = _estimate_density_curve(
        values, bw_adjust=1.0, bandwidth=0.0, kernel="gaussian",
        auto_bandwidth_method="scott", gridsize=256, cut=1.0, log_transform=False,
        cumulative=True,
    )
    assert result is not None
    grid, curve = result
    assert np.all(np.diff(curve) >= -1e-9), "a cumulative curve must not decrease"
    assert curve[0] >= 0.0
    assert curve[-1] == pytest.approx(1.0, abs=1e-6)
    assert grid.size == curve.size


def test_2d_kde_forwards_compute_options(monkeypatch) -> None:
    captured: dict = {}

    def _fake_kdeplot(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(plotting_kde, "sns", type("SNS", (), {"kdeplot": staticmethod(_fake_kdeplot)})())
    monkeypatch.setattr(plotting_kde, "lazy_import_seaborn", lambda: None)
    monkeypatch.setattr(plot2d.kde_utils, "sns", type("SNS", (), {"kdeplot": staticmethod(_fake_kdeplot)})())
    monkeypatch.setattr(plot2d.kde_utils, "lazy_import_seaborn", lambda: None)
    monkeypatch.setattr(plot2d, "_resolve_kde_style", lambda target="kde": {
        "color": None, "linewidth": 1.0, "linestyle": "-",
        "alpha": 0.6, "fill": False, "levels": 8,
    })
    monkeypatch.setattr(app_state, "current_palette", {"A": "#ff0000"})
    monkeypatch.setattr(app_state, "ax", type("Ax", (), {})())

    state_gateway.set_kde_compute_options(
        bw_adjust=2.0, bw_method="silverman", gridsize=64, thresh=0.25,
        common_norm=True, warn_singular=True, clip_min=-3.0, clip_max=3.0,
    )

    from types import SimpleNamespace

    plot2d._render_2d_kde(SimpleNamespace(), "g", ["Pb206", "Pb207"])

    assert captured.get("bw_adjust") == 2.0
    assert captured.get("bw_method") == "silverman"
    assert captured.get("gridsize") == 64
    assert captured.get("thresh") == 0.25
    assert captured.get("common_norm") is True
    assert captured.get("warn_singular") is True
    assert captured.get("clip") == (-3.0, 3.0)


def test_marginal_kde_forwards_clip_and_cumulative(monkeypatch) -> None:
    captured: dict = {}

    def _fake_estimate(values, **kwargs):
        captured.update(kwargs)
        grid = np.linspace(float(np.min(values)), float(np.max(values)), 64)
        return grid, np.exp(-((grid - grid.mean()) ** 2))

    monkeypatch.setattr(plotting_kde, "_estimate_density_curve", _fake_estimate)
    monkeypatch.setattr(plotting_kde, "ensure_line_style", lambda _s, _k, fb: fb)

    state_gateway.set_marginal_kde_compute_options(
        clip_min=1.0, clip_max=9.0, cumulative=True
    )

    fig, ax = plt.subplots()
    try:
        df_plot = pd.DataFrame({
            "group": ["A"] * 6,
            "_emb_x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "_emb_y": [2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
        })
        plotting_kde.draw_marginal_kde(
            ax=ax, df_plot=df_plot, group_col="group",
            palette={"A": "#1f77b4"}, unique_cats=["A"],
        )
    finally:
        plotting_kde.clear_marginal_axes()
        plt.close(fig)

    assert captured.get("clip_min") == 1.0
    assert captured.get("clip_max") == 9.0
    assert captured.get("cumulative") is True


def test_rendering_kde_uses_shared_compute_helper() -> None:
    """Both 2D paths must read the options from the shared helper."""
    assert not hasattr(rendering_kde, "_kde_compute_kwargs")
    source = (rendering_kde.__file__ or "")
    assert source
    text = open(source, encoding="utf-8").read()
    assert "kde_compute_kwargs()" in text
