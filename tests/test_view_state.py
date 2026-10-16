"""One rule for every plot type: the same content on the same axes keeps the user's view."""
from __future__ import annotations

import pandas as pd
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
