"""3D raw scatter plotting: the frame labels, and the mode's entry point.

The render sequence itself belongs to the pipeline, and what makes a 3D scatter a 3D scatter belongs to
its adapter; this module keeps the frame's naming and the entry point the rest of the application calls.
"""
from __future__ import annotations

import logging

from core import app_state, state_gateway

from ...style import _apply_axis_text_style
from ..common.state_access import _active_subset_indices

logger = logging.getLogger(__name__)


def _apply_frame_labels(data_columns: list[str], group_col: str) -> None:
    """Title and axis labels of the 3D frame.

    Shared by the drawn and the empty path: a frame with nothing visible still has to say which columns
    it shows, or the canvas looks like a failed render.
    """
    from ..common.title import display_group_col

    subset_info = ' (Subset)' if _active_subset_indices() is not None else ''
    # The grouping column is named the way the user knows it; the column a decomposition writes is not
    # a name to show.
    title = (
        f'3D Scatter Plot{subset_info} ({data_columns[0]}, {data_columns[1]}, {data_columns[2]})\n'
        f'Colored by {display_group_col(group_col)}'
    )
    state_gateway.set_current_plot_title(title)
    if app_state.show_plot_title:
        app_state.ax.set_title(title, pad=app_state.title_pad)
    else:
        app_state.ax.set_title('')
    app_state.ax.set_xlabel(data_columns[0])
    app_state.ax.set_ylabel(data_columns[1])
    app_state.ax.set_zlabel(data_columns[2])
    _apply_axis_text_style(app_state.ax)


def plot_3d_data(group_col: str, data_columns: list[str], size: int = 60) -> bool:
    """Render a 3D scatter plot using selected raw measurement columns."""
    # The sequence every render follows, and the 3D adapter for the parts that are 3D's own.
    from ..adapters import register_adapters
    from ..context import build_context
    from ..pipeline import run
    from ..registry import adapter_for

    register_adapters()
    context = build_context(
        "3D",
        group_col=group_col,
        figure=app_state.fig,
        axes=app_state.ax,
        columns_3d=tuple(data_columns or ()),
        point_size=size,
        subset_indices=_active_subset_indices(),
    )
    return bool(run(adapter_for("3D"), context))
