"""3D raw scatter plotting implementation."""
from __future__ import annotations

import logging

import pandas as pd

from core import app_state, state_gateway

from ...core import _build_group_palette, _ensure_axes
from ...grouping import resolve_group_marker
from ...style import _apply_axis_text_style, _apply_current_style, _enforce_plot_style
from ..common.legend import _notify_legend_panel, _place_inline_legend
from ..common.state_access import _active_subset_indices, _df_global

logger = logging.getLogger(__name__)


def _apply_frame_labels(data_columns: list[str], group_col: str) -> None:
    """Title and axis labels of the 3D frame.

    Shared by the drawn and the empty path: a frame with nothing visible still has to say
    which columns it shows, or the canvas looks like a failed render.
    """
    subset_info = ' (Subset)' if _active_subset_indices() is not None else ''
    title = (
        f'3D Scatter Plot{subset_info} ({data_columns[0]}, {data_columns[1]}, {data_columns[2]})\n'
        f'Colored by {group_col}'
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
    try:
        if app_state.fig is None:
            logger.error('Plot figure not initialized')
            return False

        if not data_columns or len(data_columns) != 3:
            logger.error('Exactly three data columns are required for a 3D scatter plot')
            return False

        df_global = _df_global()
        if df_global is None or len(df_global) == 0:
            logger.warning('No data available for plotting')
            return False

        missing = [col for col in data_columns if col not in df_global.columns]
        if missing:
            logger.error('Missing columns for 3D plot: %s', missing)
            return False

        # The view belongs to the user, and this renderer clears the axes before drawing again, so
        # it is captured first and put back afterwards - the same rule every plot type follows, from
        # visualization.plotting.view_state.
        from visualization.plotting.view_state import capture_view, mark_drawn, restore_view

        view_token = ("3D", tuple(data_columns))
        captured_view = capture_view(app_state.ax)

        _ensure_axes(dimensions=3)

        if app_state.ax is None:
            logger.error('Failed to configure 3D axes')
            return False

        subset_indices = _active_subset_indices()
        if subset_indices is not None:
            indices_to_plot = sorted(list(subset_indices))
            df_plot = df_global.iloc[indices_to_plot].dropna(subset=data_columns).copy()
        else:
            df_plot = df_global.dropna(subset=data_columns).copy()

        if df_plot.empty:
            logger.warning('No complete rows available for the selected 3D columns')
            return False

        if group_col not in df_plot.columns:
            logger.error('Column not found: %s', group_col)
            return False

        df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)

        # The legend's visibility filter applies in 3D exactly as it does to the 2D and
        # embedding renders: switching render mode must neither drop the user's selection
        # nor ignore it (a group hidden in the legend used to come back on the 3D canvas).
        visible_groups = app_state.visible_groups
        if visible_groups is not None:
            allowed = {str(group) for group in visible_groups}
            df_plot = df_plot[df_plot[group_col].isin(allowed)].copy()
            if df_plot.empty:
                logger.warning(
                    'No 3D row belongs to a visible group (%s); the plot stays empty until '
                    'a group is ticked in the legend.',
                    ', '.join(sorted(allowed)) or 'none',
                )

        _apply_current_style()

        app_state.ax.clear()
        _enforce_plot_style(app_state.ax)
        app_state.clear_plot_state()

        unique_cats = sorted(df_plot[group_col].unique())

        _build_group_palette(unique_cats)

        for cat in unique_cats:
            subset = df_plot[df_plot[group_col] == cat]
            if subset.empty:
                continue

            xs = pd.to_numeric(subset[data_columns[0]], errors='coerce').values
            ys = pd.to_numeric(subset[data_columns[1]], errors='coerce').values
            zs = pd.to_numeric(subset[data_columns[2]], errors='coerce').values

            marker_size = app_state.plot_marker_size
            marker_alpha = app_state.plot_marker_alpha
            marker_shape = resolve_group_marker(app_state, cat)
            show_edge = bool(app_state.scatter_show_edge)
            edge_color = app_state.scatter_edgecolor if show_edge else 'none'
            edge_width = app_state.scatter_edgewidth if show_edge else 0.0
            sc = app_state.ax.scatter(
                xs,
                ys,
                zs,
                label=cat,
                color=app_state.current_palette[cat],
                s=marker_size,
                marker=marker_shape,
                alpha=marker_alpha,
                edgecolors=edge_color,
                linewidth=edge_width,
                zorder=2,
            )
            app_state.scatter_collections.append(sc)

        legend_handles = list(app_state.scatter_collections)
        legend_labels = list(unique_cats)

        if not app_state.scatter_collections:
            if df_plot.empty:
                # Every group the user keeps visible is absent from this projection: keep
                # the 3D frame and the render mode instead of reporting a failure, which
                # would send the use case looking for another mode to draw in.  The legend
                # panel is still told, so its checkboxes match the selection that produced
                # this empty frame (an empty selection must not leave them all ticked).
                _apply_frame_labels(data_columns, group_col)
                _notify_legend_panel(group_col, [], [])
                mark_drawn(app_state.ax, view_token)
                state_gateway.set_annotation(None)
                return True
            logger.error('No points were plotted in 3D')
            try:
                app_state.fig.canvas.draw_idle()
            except Exception as err:
                logger.warning("plot_3d_data failed: %s", err)
            return False

        try:
            _place_inline_legend(
                app_state.ax,
                group_col,
                legend_handles,
                legend_labels,
                show_marginal_kde=False,
            )
        except Exception as legend_err:
            logger.warning('3D legend creation error: %s', legend_err)

        _apply_frame_labels(data_columns, group_col)

        # Same content on the same axes: the view the user set comes back. A different column set is
        # a new view, and the ranges stay as this render set them.
        restore_view(app_state.ax, captured_view, view_token)
        mark_drawn(app_state.ax, view_token)
        state_gateway.set_annotation(None)
        return True

    except Exception as err:
        logger.exception('3D plot failed: %s', err)
        try:
            if app_state.fig is not None and app_state.fig.canvas is not None:
                app_state.fig.canvas.draw_idle()
        except Exception as err:
            logger.warning("plot_3d_data failed: %s", err)
        return False
