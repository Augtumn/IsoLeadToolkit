"""One rule for every plot type: the same content on the same axes keeps the user's view."""
from __future__ import annotations

import pandas as pd
import pytest
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from core import app_state, state_gateway
from visualization.plotting.view_state import (
    capture_view,
    drawn_last,
    mark_drawn,
    restore_view,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Site": ["A", "A", "B", "B"],
            "x1": [1.0, 2.0, 3.0, 4.0],
            "x2": [2.0, 3.0, 4.0, 5.0],
            "x3": [1.5, 2.5, 3.5, 4.5],
        }
    )


def test_the_shared_rule_keeps_a_view_only_for_the_same_content() -> None:
    """The rule three renderers used to implement separately, and disagree about."""
    figure = Figure()
    axes = figure.add_subplot(111)
    axes.scatter([1.0, 2.0], [1.0, 2.0])
    axes.set_xlim(1.2, 1.8)
    axes.set_ylim(1.1, 1.9)
    captured = capture_view(axes)

    assert drawn_last(axes) is None, "nothing has been drawn through this rule yet"
    assert restore_view(axes, captured, ("2D", ("x1", "x2"))) is False, (
        "a view is not restored for content this axes never drew"
    )

    mark_drawn(axes, ("2D", ("x1", "x2")))
    axes.set_xlim(0.0, 1.0)

    assert restore_view(axes, captured, ("2D", ("x1", "x2"))) is True
    assert axes.get_xlim() == (1.2, 1.8), "the same content keeps the user's view"

    axes.set_xlim(0.0, 1.0)
    assert restore_view(axes, captured, ("2D", ("x2", "x1"))) is False, (
        "different content is a new view"
    )
    assert axes.get_xlim() == (0.0, 1.0), "and the ranges are left to the renderer"


def test_a_3d_render_keeps_its_view_and_re_ranges_for_other_columns(qapp) -> None:
    """3D captured nothing at all, so a refresh threw its zoom away."""
    from visualization.plotting.rendering.raw.plot3d import plot_3d_data

    state_gateway.set_dataframe_and_source(_frame(), file_path="x", sheet_name="s")
    state_gateway.set_group_data_columns(["Site"], ["x1", "x2", "x3"])
    state_gateway.set_last_group_col("Site")
    state_gateway.set_visible_groups(None)
    figure = Figure()
    state_gateway.set_figure_axes(figure, figure.add_subplot(111, projection="3d"))
    state_gateway.set_render_mode("3D")

    assert plot_3d_data("Site", ["x1", "x2", "x3"]) is True
    app_state.ax.set_xlim(1.5, 2.5)
    app_state.ax.set_zlim(1.0, 2.0)

    assert plot_3d_data("Site", ["x1", "x2", "x3"]) is True
    assert tuple(round(float(value), 2) for value in app_state.ax.get_xlim()) == (1.5, 2.5)
    assert tuple(round(float(value), 2) for value in app_state.ax.get_zlim()) == (1.0, 2.0)

    assert plot_3d_data("Site", ["x2", "x3", "x1"]) is True
    assert tuple(round(float(value), 2) for value in app_state.ax.get_xlim()) != (1.5, 2.5), (
        "other data columns are a new view, and the ranges are this render's"
    )


#: Every plot type the application can draw, with a window inside each one's data range.
PLOT_TYPES = (
    ("2D", (2.0, 4.0)),
    ("3D", (2.0, 4.0)),
    ("UMAP", (2.0, 4.0)),
    ("tSNE", (2.0, 4.0)),
    ("PCA", (2.0, 4.0)),
    ("RobustPCA", (2.0, 4.0)),
    ("PB_EVOL_86", (17.0, 19.0)),
    ("PB_EVOL_76", (17.0, 19.0)),
    ("PLUMBOTECTONICS_86", (17.0, 19.0)),
    ("PB_MU_AGE", (17.0, 19.0)),
    ("PB_KAPPA_AGE", (17.0, 19.0)),
)


def _wide_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Site": ["A", "A", "B", "B", "C", "C"],
            "206Pb/204Pb": [18.1, 18.3, 18.5, 18.7, 19.0, 19.2],
            "207Pb/204Pb": [15.5, 15.55, 15.6, 15.62, 15.65, 15.7],
            "208Pb/204Pb": [38.2, 38.3, 38.4, 38.5, 38.6, 38.7],
            "x1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "x2": [2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            "x3": [1.5, 2.5, 3.5, 4.5, 5.5, 6.5],
        }
    )


@pytest.mark.parametrize(("mode", "zoom"), PLOT_TYPES)
def test_every_plot_type_keeps_the_view_on_a_refresh(qapp, mode, zoom) -> None:
    """The reported behaviour, for every plot type there is - not only the two that were patched.

    Each renderer used to decide this for itself, and 3D decided not to. The rule they all use now
    lives in visualization.plotting.view_state.
    """
    from visualization.plotting.rendering.embedding_plot import plot_embedding
    from visualization.plotting.rendering.raw.plot2d import plot_2d_data
    from visualization.plotting.rendering.raw.plot3d import plot_3d_data

    frame = _wide_frame()
    state_gateway.set_dataframe_and_source(frame, file_path="x", sheet_name="s")
    state_gateway.set_group_data_columns(["Site"], list(frame.columns[1:]))
    state_gateway.set_last_group_col("Site")
    state_gateway.set_visible_groups(None)
    state_gateway.set_render_mode(mode)

    figure = Figure()
    canvas = FigureCanvas(figure)
    canvas.resize(500, 400)
    state_gateway.set_figure(figure)

    if mode == "2D":
        render = lambda: plot_2d_data("Site", ["x1", "x2"])  # noqa: E731
    elif mode == "3D":
        render = lambda: plot_3d_data("Site", ["x1", "x2", "x3"])  # noqa: E731
    else:
        render = lambda: plot_embedding("Site", mode)  # noqa: E731

    assert render() is True, f"{mode} renders"
    app_state.ax.set_xlim(*zoom)
    app_state.ax.set_ylim(*zoom)

    assert render() is True, f"{mode} renders again"

    assert tuple(round(float(value), 2) for value in app_state.ax.get_xlim()) == tuple(
        round(value, 2) for value in zoom
    ), f"{mode} keeps the view the user set"
    assert tuple(round(float(value), 2) for value in app_state.ax.get_ylim()) == tuple(
        round(value, 2) for value in zoom
    ), f"{mode} keeps the view the user set"

