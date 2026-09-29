"""Ternary density must be drawn in ternary coordinates.

Regression: the ternary branch handed Cartesian x/y to seaborn's kdeplot on an mpltern
axes, which cannot draw them, so neither the density nor its marginals appeared.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import mpltern  # noqa: F401  (registers the ternary projection)
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
    return pd.DataFrame(
        {
            "_emb_t": t,
            "_emb_l": l,
            "_emb_r": r,
            "Province": ["A"] * 30 + ["B"] * 30,
        }
    )


def test_ternary_kde_draws_contours(ternary_axes) -> None:
    before = len(ternary_axes.collections)

    kde_render._render_kde_overlay(
        "TERNARY", _frame(), "Province", ["A", "B"], {"A": "#d62728", "B": "#1f77b4"}
    )

    assert len(ternary_axes.collections) > before, "the ternary density drew nothing"


def test_ternary_kde_is_quiet_when_disabled(ternary_axes) -> None:
    state_gateway.set_show_kde(False)
    before = len(ternary_axes.collections)

    kde_render._render_kde_overlay(
        "TERNARY", _frame(), "Province", ["A"], {"A": "#333333"}
    )

    assert len(ternary_axes.collections) == before


def test_marginal_kde_is_skipped_on_ternary(ternary_axes) -> None:
    """Marginals need rectangular axes; on a simplex the call must be a no-op."""
    state_gateway.set_show_marginal_kde(True)
    try:
        # ax, df_plot, group_col, palette, unique_cats are the five required parameters
        kde_module.draw_marginal_kde(None, None, None, None, None)
    finally:
        state_gateway.set_show_marginal_kde(False)

    assert app_state.marginal_axes is None
