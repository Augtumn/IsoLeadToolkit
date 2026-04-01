"""3D raw scatter plotting implementation."""
from __future__ import annotations

import logging
import traceback

import pandas as pd

from core import app_state, state_gateway
from ..style import _apply_axis_text_style, _apply_current_style, _enforce_plot_style
from ..core import _build_group_palette, _ensure_axes
from .helpers import _active_subset_indices, _df_global, _place_inline_legend

logger = logging.getLogger(__name__)


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
            logger.error(f'Missing columns for 3D plot: {missing}')
            return False

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
            logger.error(f'Column not found: {group_col}')
            return False

        df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)

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

            marker_size = getattr(app_state, 'plot_marker_size', size)
            marker_alpha = getattr(app_state, 'plot_marker_alpha', 0.85)
            marker_shape = app_state.group_marker_map.get(
                cat,
                getattr(app_state, 'plot_marker_shape', 'o'),
            )
            show_edge = bool(getattr(app_state, 'scatter_show_edge', True))
            edge_color = getattr(app_state, 'scatter_edgecolor', '#1e293b') if show_edge else 'none'
            edge_width = getattr(app_state, 'scatter_edgewidth', 0.4) if show_edge else 0.0
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
            logger.error('No points were plotted in 3D')
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
            logger.warning(f'3D legend creation error: {legend_err}')

        subset_info = ' (Subset)' if _active_subset_indices() is not None else ''
        title = (
            f'3D Scatter Plot{subset_info} ({data_columns[0]}, {data_columns[1]}, {data_columns[2]})\n'
            f'Colored by {group_col}'
        )
        state_gateway.set_attr('current_plot_title', title)
        if getattr(app_state, 'show_plot_title', True):
            app_state.ax.set_title(title, pad=getattr(app_state, 'title_pad', 20.0))
        else:
            app_state.ax.set_title('')
        app_state.ax.set_xlabel(data_columns[0])
        app_state.ax.set_ylabel(data_columns[1])
        app_state.ax.set_zlabel(data_columns[2])
        _apply_axis_text_style(app_state.ax)

        state_gateway.set_attr('annotation', None)
        return True

    except Exception as err:
        logger.error(f'3D plot failed: {err}')
        traceback.print_exc()
        return False
