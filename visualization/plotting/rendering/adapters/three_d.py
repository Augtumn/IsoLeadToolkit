"""The 3D scatter mode, on the shared render sequence.

Only what makes a 3D scatter a 3D scatter lives here; the axes, the style, the plot state, the view and
the error path come from the pipeline. The marker style, the edge style and the palette are read as the
mode's own renderer read them, so the picture does not change with the move.
"""
from __future__ import annotations

import logging
from typing import Any

from ..context import RenderContext
from ..pipeline import Ink
from ..registry import Adapter, register

logger = logging.getLogger(__name__)


class ThreeDAdapter(Adapter):
    """A 3D scatter plot of three selected columns."""

    mode = "3D"

    def validate(self, context: RenderContext) -> None:
        if len(context.columns_3d) != 3:
            raise ValueError("exactly three data columns are required for a 3D scatter plot")

    def token(self, context: RenderContext) -> tuple[Any, ...]:
        return ("3D", tuple(context.columns_3d))

    def axes_dimensions(self, context: RenderContext) -> Any:
        return 3

    def prepare(self, context: RenderContext) -> Any:
        import pandas as pd

        from ..common.state_access import _active_subset_indices, _df_global

        df_global = _df_global()
        if df_global is None or len(df_global) == 0:
            logger.warning("No data available for plotting")
            return False
        columns = list(context.columns_3d)
        missing = [column for column in columns if column not in df_global.columns]
        if missing:
            logger.error("Missing columns for 3D plot: %s", missing)
            return False

        indices = _active_subset_indices()
        if indices is not None:
            frame = df_global.iloc[sorted(list(indices))].dropna(subset=columns).copy()
        else:
            frame = df_global.dropna(subset=columns).copy()
        if frame.empty:
            logger.warning("No complete rows available for the selected 3D columns")
            return False
        if context.group_col not in frame.columns:
            logger.error("Column not found: %s", context.group_col)
            return False
        frame[context.group_col] = frame[context.group_col].fillna("Unknown").astype(str)

        # The legend's visibility filter applies in 3D exactly as it does to the other renders.
        from core import app_state

        visible = app_state.visible_groups
        if visible is not None:
            allowed = {str(group) for group in visible}
            frame = frame[frame[context.group_col].isin(allowed)].copy()
            if frame.empty:
                logger.warning(
                    "No 3D row belongs to a visible group (%s); the plot stays empty until a group is "
                    "ticked in the legend.",
                    ", ".join(sorted(allowed)) or "none",
                )
        # An empty frame is still this mode's frame: it is drawn, not refused.
        return frame

    def groups(self, context: RenderContext, prepared: Any) -> list[Any]:
        return _categories(context, prepared)

    def draw(self, context: RenderContext, prepared: Any) -> Ink:
        import pandas as pd
        from core import app_state

        from ...grouping import resolve_group_marker

        columns = list(context.columns_3d)
        for category in _categories(context, prepared):
            subset = prepared[prepared[context.group_col] == category]
            if subset.empty:
                continue
            xs = pd.to_numeric(subset[columns[0]], errors="coerce").values
            ys = pd.to_numeric(subset[columns[1]], errors="coerce").values
            zs = pd.to_numeric(subset[columns[2]], errors="coerce").values

            marker_size = app_state.plot_marker_size
            marker_alpha = app_state.plot_marker_alpha
            marker_shape = resolve_group_marker(app_state, category)
            show_edge = bool(app_state.scatter_show_edge)
            edge_color = app_state.scatter_edgecolor if show_edge else "none"
            edge_width = app_state.scatter_edgewidth if show_edge else 0.0
            # The collections are registered in the plot state, which is what the legend and the hover
            # linking read.
            app_state.scatter_collections.append(
                context.axes.scatter(
                    xs,
                    ys,
                    zs,
                    label=category,
                    color=app_state.current_palette[category],
                    s=marker_size,
                    marker=marker_shape,
                    alpha=marker_alpha,
                    edgecolors=edge_color,
                    linewidth=edge_width,
                    zorder=2,
                )
            )

        if not app_state.scatter_collections:
            if len(prepared) == 0:
                # Every group the user keeps visible is absent from this projection: keep the 3D frame
                # and the mode instead of reporting a failure, which would send the use case looking
                # for another mode to draw in.
                return Ink.EMPTY
            logger.error("No points were plotted in 3D")
            return Ink.FAILED
        return Ink.DRAWN

    def legend(self, context: RenderContext, prepared: Any) -> None:
        from core import app_state

        from ..common.legend import _place_inline_legend

        try:
            _place_inline_legend(
                context.axes,
                context.group_col,
                list(app_state.scatter_collections),
                _categories(context, prepared),
                show_marginal_kde=False,
            )
        except Exception as err:
            logger.warning("3D legend creation error: %s", err)

    def decorate(self, context: RenderContext, prepared: Any) -> None:
        from ..raw.plot3d import _apply_frame_labels

        _apply_frame_labels(list(context.columns_3d), context.group_col)

    def finish(self, context: RenderContext, prepared: Any) -> None:
        from core import state_gateway

        from ..common.legend import _notify_legend_panel

        if len(prepared) == 0:
            _notify_legend_panel(context.group_col, [], [])
        # A 3D plot has no tooltip annotation to attach; it clears the one another mode left.
        state_gateway.set_annotation(None)


def _categories(context: RenderContext, prepared: Any) -> list[Any]:
    try:
        return sorted(prepared[context.group_col].unique())
    except Exception as err:
        logger.warning("Could not read the 3D categories: %s", err)
        return []


def register_three_d() -> ThreeDAdapter:
    """Put the 3D adapter in the registry."""
    return register(ThreeDAdapter())  # type: ignore[return-value]
