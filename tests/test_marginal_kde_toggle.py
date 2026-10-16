"""Turning the marginal KDE off takes effect.

Reported: the checkbox could turn the marginal KDE on but never off. The embedding family's adapter had
the clear inside the same condition as the draw, so a render with the setting off skipped both and left
the axes the previous render had attached on the figure. The 2D adapter never had the problem because its
clear sits outside the condition - which is what the embedding family does now.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from core import app_state, state_gateway  # noqa: E402


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Site": ["A", "A", "B", "B", "C", "C"],
            "x1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "x2": [2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            "x3": [1.5, 2.5, 3.5, 4.5, 5.5, 6.5],
        }
    )


@pytest.fixture()
def render_ready(qapp):
    frame = _frame()
    state_gateway.set_dataframe_and_source(frame, file_path="marginal.csv", sheet_name="s")
    state_gateway.set_group_data_columns(["Site"], list(frame.columns[1:]))
    state_gateway.set_last_group_col("Site")
    state_gateway.set_visible_groups(None)
    state_gateway.set_selected_2d_columns(["x1", "x2"], confirmed=True)
    canvas = FigureCanvas(Figure())
    canvas.resize(600, 450)
    state_gateway.set_figure(canvas.figure)
    return frame


def _render(mode: str) -> bool:
    from visualization.plotting.rendering.embedding_plot import plot_embedding
    from visualization.plotting.rendering.raw.plot2d import plot_2d_data

    if mode == "2D":
        return bool(plot_2d_data("Site", ["x1", "x2"]))
    return bool(plot_embedding("Site", mode))


def _axes_count() -> int:
    """How many axes the figure that was actually rendered into holds.

    The pipeline owns the axes, and may replace them, so the figure is read from the axes in force after
    each render rather than from the one the fixture installed.
    """
    return len(app_state.ax.figure.axes)


@pytest.mark.parametrize("mode", ["UMAP", "PCA", "2D"])
def test_turning_the_marginal_kde_off_removes_the_axes(render_ready, mode: str) -> None:
    """The figure holds the data axes plus a top and a right marginal, and loses the two when turned off."""
    state_gateway.set_show_marginal_kde(True)
    assert _render(mode), f"{mode} rendered"
    assert _axes_count() == 3, f"{mode}: data axes plus the two marginals"

    state_gateway.set_show_marginal_kde(False)
    assert _render(mode), f"{mode} rendered again"
    assert _axes_count() == 1, f"{mode}: the marginals are gone, not left behind"


def test_turning_it_on_again_reattaches_them(render_ready) -> None:
    state_gateway.set_show_marginal_kde(False)
    assert _render("UMAP")
    assert _axes_count() == 1

    state_gateway.set_show_marginal_kde(True)
    assert _render("UMAP")
    assert _axes_count() == 3, "switching it back on draws the marginals again"

    state_gateway.set_show_marginal_kde(False)
    assert _render("UMAP")
    assert _axes_count() == 1, "and switching it off again removes them"
