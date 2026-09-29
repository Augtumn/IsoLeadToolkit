"""Regression: ternary density must be drawn in ternary coordinates."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import mpltern  # noqa: F401,E402  (registers the ternary projection)
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from core import app_state, state_gateway  # noqa: E402
import visualization.plotting.kde as kde_module  # noqa: E402
import visualization.plotting.rendering.kde as kde_render  # noqa: E402


@pytest.fixture()
def ternary_axes():
    figure = plt.figure()
    axes = figure.add_subplot(projection="ternary")
    state_gateway.set_figure_axes(figure, axes)
    state_gateway.set_show_kde(True)
    yield axes
    state_gateway.set_show_kde(False)
    plt.close(figure)


def _frame() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    t = rng.uniform(0.25, 0.55, 60)
    l = rng.uniform(0.25, 0.55, 60)
    r = np.maximum(0.02, 1.0 - t - l)
    return pd.DataFrame({"_emb_t": t, "_emb_l": l, "_emb_r": r,
                         "Province": ["A"] * 30 + ["B"] * 30})


def test_ternary_kde_draws_contours(ternary_axes) -> None:
    before = len(ternary_axes.collections)

    kde_render._render_kde_overlay(
        "TERNARY", _frame(), "Province", ["A", "B"], {"A": "#d62728", "B": "#1f77b4"}
    )

    assert len(ternary_axes.collections) > before, "the ternary density drew nothing"


def test_density_z_order_follows_the_legend_order(ternary_axes) -> None:
    """Later legend entries must sit on top, not at one fixed z-order."""
    kde_render._render_kde_overlay(
        "TERNARY", _frame(), "Province", ["A", "B"], {"A": "#d62728", "B": "#1f77b4"}
    )

    tagged = [c for c in ternary_axes.collections if hasattr(c, "_legend_group")]
    assert tagged, "the density artists carry no legend group tag"
    order = [c.get_zorder() for c in tagged]
    assert order == sorted(order), f"z-order does not increase with the legend: {order}"


def test_a_small_group_is_reported(ternary_axes, caplog) -> None:
    """Three samples cannot support a density: say so instead of drawing silently."""
    frame = _frame().iloc[:3].copy()

    with caplog.at_level("WARNING"):
        kde_render._render_kde_overlay("TERNARY", frame, "Province", ["A"], {"A": "#333333"})

    assert any("sample" in record.getMessage() for record in caplog.records), caplog.records


def test_ternary_kde_is_quiet_when_disabled(ternary_axes) -> None:
    state_gateway.set_show_kde(False)
    before = len(ternary_axes.collections)

    kde_render._render_kde_overlay("TERNARY", _frame(), "Province", ["A"], {"A": "#333333"})

    assert len(ternary_axes.collections) == before


def test_marginal_kde_is_skipped_on_ternary(ternary_axes) -> None:
    """Marginals need rectangular axes; on a simplex the call must be a no-op."""
    state_gateway.set_show_marginal_kde(True)
    try:
        # ax, df_plot, group_col, palette, unique_cats are the five required parameters.
        kde_module.draw_marginal_kde(None, None, None, None, None)
    finally:
        state_gateway.set_show_marginal_kde(False)

    assert app_state.marginal_axes is None


def test_common_norm_shares_the_colour_scale(ternary_axes, monkeypatch) -> None:
    """With common_norm every group is drawn against one shared peak.

    The assertion watches the value handed to the drawer: contourf overwrites the norm's vmax
    with the group's own level maximum, so the colour scale cannot be read back from the
    artists.
    """
    seen: list = []
    original = kde_render._draw_ternary_kde

    def _capture(*args, **kwargs):
        seen.append(kwargs.get("shared_peak"))
        return original(*args, **kwargs)

    monkeypatch.setattr(kde_render, "_draw_ternary_kde", _capture)
    state_gateway.set_kde_compute_options(common_norm=True)
    try:
        kde_render._render_kde_overlay(
            "TERNARY", _frame(), "Province", ["A", "B"], {"A": "#d62728", "B": "#1f77b4"}
        )
    finally:
        state_gateway.set_kde_compute_options(common_norm=False)

    assert seen, "no group reached the drawer"
    assert all(value is not None for value in seen), f"no shared peak was passed: {seen}"
    assert len(set(seen)) == 1, f"groups were scaled differently: {seen}"


def test_without_common_norm_each_group_keeps_its_own_scale(ternary_axes, monkeypatch) -> None:
    seen: list = []
    original = kde_render._draw_ternary_kde

    def _capture(*args, **kwargs):
        seen.append(kwargs.get("shared_peak"))
        return original(*args, **kwargs)

    monkeypatch.setattr(kde_render, "_draw_ternary_kde", _capture)
    state_gateway.set_kde_compute_options(common_norm=False)
    kde_render._render_kde_overlay(
        "TERNARY", _frame(), "Province", ["A", "B"], {"A": "#d62728", "B": "#1f77b4"}
    )

    assert seen and all(value is None for value in seen), f"unexpected shared peak: {seen}"
