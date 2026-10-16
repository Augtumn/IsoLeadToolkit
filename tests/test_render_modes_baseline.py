"""Every render mode draws, and the shared rules hold for all of them.

This is the safety net for unifying the renderers: one case per mode in the mode list, asserting what
the pipeline must guarantee for every plot type - it renders, it draws something, a refresh keeps the
view the user set, and the title names the grouping column the user chose. Behaviour must survive the
move to a single pipeline, and this is what says so.
"""
from __future__ import annotations

import pandas as pd
import pytest
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from core import app_state, state_gateway
from core.render_modes import RENDER_MODE_VALUES

#: Every mode the application offers, from the one list the controls are built from.
MODES = tuple(RENDER_MODE_VALUES)

#: A view inside the data range of each family of plots.
ZOOM = {
    "2D": (2.0, 4.0),
    "3D": (2.0, 4.0),
    "Ternary": (0.2, 0.8),
}
DEFAULT_ZOOM = (17.0, 19.0)
EMBEDDING_ZOOM = (2.0, 4.0)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Site": ["A", "A", "B", "B", "C", "C"],
            "206Pb/204Pb": [18.1, 18.3, 18.5, 18.7, 19.0, 19.2],
            "207Pb/204Pb": [15.5, 15.55, 15.6, 15.62, 15.65, 15.7],
            "208Pb/204Pb": [38.2, 38.3, 38.4, 38.5, 38.6, 38.7],
            "V1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "V2": [6.0, 5.0, 4.0, 3.0, 2.0, 1.0],
            "x1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
            "x2": [2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            "x3": [1.5, 2.5, 3.5, 4.5, 5.5, 6.5],
        }
    )


@pytest.fixture()
def render_ready(qapp):
    """A loaded dataset with every column selection the modes need, and one canvas."""
    frame = _frame()
    state_gateway.set_dataframe_and_source(frame, file_path="baseline.csv", sheet_name="s")
    state_gateway.set_group_data_columns(["Site"], list(frame.columns[1:]))
    state_gateway.set_last_group_col("Site")
    state_gateway.set_visible_groups(None)
    state_gateway.set_selected_2d_columns(["x1", "x2"], confirmed=True)
    state_gateway.set_selected_3d_columns(["x1", "x2", "x3"], confirmed=True)
    state_gateway.set_selected_ternary_columns(
        ["206Pb/204Pb", "207Pb/204Pb", "208Pb/204Pb"], confirmed=True
    )

    figure = Figure()
    canvas = FigureCanvas(figure)
    canvas.resize(600, 450)
    state_gateway.set_figure(figure)
    return frame


def _render(mode: str) -> bool:
    from visualization.plotting.rendering.embedding_plot import plot_embedding
    from visualization.plotting.rendering.raw.plot2d import plot_2d_data
    from visualization.plotting.rendering.raw.plot3d import plot_3d_data

    if mode == "2D":
        return bool(plot_2d_data("Site", ["x1", "x2"]))
    if mode == "3D":
        return bool(plot_3d_data("Site", ["x1", "x2", "x3"]))
    return bool(plot_embedding("Site", mode))


def _zoom_for(mode: str) -> tuple[float, float]:
    if mode in ZOOM:
        return ZOOM[mode]
    if mode in ("UMAP", "tSNE", "PCA", "RobustPCA", "V1V2"):
        return EMBEDDING_ZOOM
    return DEFAULT_ZOOM


def _limits(axes) -> tuple[tuple[float, float], tuple[float, float]]:
    return (
        tuple(round(float(value), 2) for value in axes.get_xlim()),
        tuple(round(float(value), 2) for value in axes.get_ylim()),
    )


@pytest.mark.parametrize("mode", MODES)
def test_every_mode_renders_and_draws_something(render_ready, mode) -> None:
    state_gateway.set_render_mode(mode)

    assert _render(mode) is True, f"{mode} renders"
    assert app_state.ax is not None, f"{mode} has an axes"
    assert app_state.scatter_collections, f"{mode} drew the samples"
    # The title is computed for every mode; whether it is shown on the canvas is the user's switch.
    assert app_state.current_plot_title.strip(), f"{mode} has a title"


def _title_for(mode: str) -> str:
    """The title the renderer computed, and the canvas title when the user asks to see it."""
    if app_state.show_plot_title:
        assert app_state.ax.get_title().strip(), f"{mode} shows its title"
    return str(app_state.current_plot_title)


@pytest.mark.parametrize("mode", MODES)
def test_every_mode_keeps_the_view_on_a_refresh(render_ready, mode) -> None:
    state_gateway.set_render_mode(mode)
    assert _render(mode) is True

    if mode == "Ternary":
        # A ternary plot has no x/y view: its window is three ranges held in the state, and what the
        # user sets by hand is the manual range.
        manual = {
            "tmin": 0.30,
            "tmax": 0.60,
            "lmin": 0.20,
            "lmax": 0.50,
            "rmin": 0.20,
            "rmax": 0.50,
        }
        state_gateway.set_ternary_manual_limits(manual)
        state_gateway.set_ternary_manual_limits_enabled(True)

        assert _render(mode) is True
        assert app_state.ternary_manual_limits_enabled is True, "the manual window stays on"
        for key, value in manual.items():
            assert abs(float(app_state.ternary_manual_limits[key]) - value) < 1e-9, (
                f"Ternary keeps the manual {key}"
            )
        return

    zoom = _zoom_for(mode)
    app_state.ax.set_xlim(*zoom)
    app_state.ax.set_ylim(*zoom)

    assert _render(mode) is True
    xlim, ylim = _limits(app_state.ax)
    assert xlim == tuple(round(value, 2) for value in zoom), f"{mode} keeps the x view"
    assert ylim == tuple(round(value, 2) for value in zoom), f"{mode} keeps the y view"


@pytest.mark.parametrize("mode", MODES)
def test_every_mode_title_names_the_grouping_column(render_ready, mode) -> None:
    from visualization.plotting.decomposition import (
        BASE_DECOMPOSITION_KEY,
        DECOMPOSED_GROUP_COLUMN,
    )

    state_gateway.set_render_mode(mode)
    assert _render(mode) is True
    assert "Site" in _title_for(mode), f"{mode} names the grouping column"

    # The column a decomposition writes is not a name the user can read.
    state_gateway.set_group_decomposition({BASE_DECOMPOSITION_KEY: "Site", "A": "206Pb/204Pb"})
    assert _render(mode) is True
    title = _title_for(mode)
    assert DECOMPOSED_GROUP_COLUMN not in title, f"{mode} does not print the working column: {title}"
