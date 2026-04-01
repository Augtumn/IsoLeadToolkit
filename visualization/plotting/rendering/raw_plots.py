"""Raw 2D/3D plotting routines extracted from render facade."""
from __future__ import annotations

import logging
import traceback

import pandas as pd

from core import app_state, state_gateway
from .. import kde as kde_utils
from ..style import _apply_current_style, _enforce_plot_style, _apply_axis_text_style
from ..core import _ensure_axes, _build_group_palette
from ..geochem.equation_overlays import _draw_equation_overlays
from .helpers import (
    _active_subset_indices,
    _df_global,
    _place_inline_legend,
    _resolve_kde_style,
)

logger = logging.getLogger(__name__)

def plot_2d_data(group_col: str, data_columns: list[str], size: int = 60, show_kde: bool = False) -> bool:
    """Render a 2D scatter plot using selected raw measurement columns."""
    try:
        if app_state.fig is None:
            logger.error("Plot figure not initialized")
            return False

        if not data_columns or len(data_columns) != 2:
            logger.error("Exactly two data columns are required for a 2D scatter plot")
            return False

        df_global = _df_global()
        if df_global is None or len(df_global) == 0:
            logger.warning("No data available for plotting")
            return False

        missing = [col for col in data_columns if col not in df_global.columns]
        if missing:
            logger.error(f"Missing columns for 2D plot: {missing}")
            return False

        prev_ax = app_state.ax
        prev_2d_cols = getattr(app_state, 'last_2d_cols', None)
        prev_xlim = None
        prev_ylim = None
        if prev_ax is not None and getattr(prev_ax, 'name', '') != '3d':
            try:
                prev_xlim = prev_ax.get_xlim()
                prev_ylim = prev_ax.get_ylim()
            except Exception:
                prev_xlim = None
                prev_ylim = None

        _ensure_axes(dimensions=2)

        if app_state.ax is None:
            logger.error("Failed to configure 2D axes")
            return False

        subset_indices = _active_subset_indices()
        if subset_indices is not None:
            indices_to_plot = sorted(list(subset_indices))
            df_plot = df_global.iloc[indices_to_plot].dropna(subset=data_columns).copy()
        else:
            df_plot = df_global.dropna(subset=data_columns).copy()

        if df_plot.empty:
            logger.warning("No complete rows available for the selected 2D columns")
            return False

        if group_col not in df_plot.columns:
            logger.error(f"Column not found: {group_col}")
            return False

        try:
            for col in data_columns:
                df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce')

            df_plot = df_plot.dropna(subset=data_columns)

            if df_plot.empty:
                logger.warning("No valid numeric data available for 2D plot.")
                return False
        except Exception as e:
            logger.error(f"Failed to convert columns to numeric: {e}")
            return False

        df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)

        all_groups = sorted(df_plot[group_col].unique())
        state_gateway.sync_available_and_visible_groups(all_groups)

        visible_groups = app_state.visible_groups
        if visible_groups is not None:
            allowed = set(visible_groups)
            mask = df_plot[group_col].isin(allowed)
            if not allowed:
                df_plot = df_plot[mask].copy()
            elif not mask.any():
                logger.info("No 2D data matches the selected legend filter; reverting to all groups.")
                state_gateway.set_visible_groups(None)
            else:
                df_plot = df_plot[mask].copy()
                if df_plot.empty:
                    logger.info("Filtered 2D data is empty; reverting to all groups.")
                    df_plot = df_global.dropna(subset=data_columns).copy()
                    df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)
                    state_gateway.set_visible_groups(None)
                    all_groups = sorted(df_plot[group_col].unique())
                    state_gateway.sync_available_and_visible_groups(all_groups)

        _apply_current_style()

        app_state.ax.clear()
        try:
            app_state.ax.set_aspect('auto')
            app_state.ax.set_autoscale_on(True)
        except Exception:
            pass
        _enforce_plot_style(app_state.ax)
        app_state.clear_plot_state()

        unique_cats = sorted(df_plot[group_col].unique())

        new_palette = _build_group_palette(unique_cats)

        show_marginal_kde = getattr(app_state, 'show_marginal_kde', False)

        if show_kde:
            try:
                kde_utils.lazy_import_seaborn()
                kde_style = _resolve_kde_style('kde')
                kde_utils.sns.kdeplot(
                    data=df_plot,
                    x=data_columns[0],
                    y=data_columns[1],
                    hue=group_col,
                    palette=new_palette,
                    ax=app_state.ax,
                    levels=int(kde_style.get('levels', 10)),
                    fill=bool(kde_style.get('fill', True)),
                    alpha=float(kde_style.get('alpha', 0.6)),
                    linewidth=float(kde_style.get('linewidth', 1.0)),
                    warn_singular=False,
                    legend=False,
                    zorder=1,
                )
            except Exception as e:
                logger.warning(f"Failed to render KDE: {e}")

        scatters = []

        if not show_kde:
            show_edge = bool(getattr(app_state, 'scatter_show_edge', True))
            edge_color = getattr(app_state, 'scatter_edgecolor', '#1e293b') if show_edge else 'none'
            edge_width = getattr(app_state, 'scatter_edgewidth', 0.4) if show_edge else 0.0
            for i, cat in enumerate(unique_cats):
                subset = df_plot[df_plot[group_col] == cat]
                if subset.empty:
                    continue

                xs = pd.to_numeric(subset[data_columns[0]], errors='coerce').values
                ys = pd.to_numeric(subset[data_columns[1]], errors='coerce').values
                indices = subset.index.tolist()

                color = app_state.current_palette[cat]

                marker_size = getattr(app_state, 'plot_marker_size', size)
                marker_alpha = getattr(app_state, 'plot_marker_alpha', 0.88)
                marker_shape = app_state.group_marker_map.get(
                    cat,
                    getattr(app_state, 'plot_marker_shape', 'o')
                )
                sc = app_state.ax.scatter(
                    xs,
                    ys,
                    label=cat,
                    color=color,
                    s=marker_size,
                    marker=marker_shape,
                    alpha=marker_alpha,
                    edgecolors=edge_color,
                    linewidth=edge_width,
                    zorder=2,
                )
                app_state.scatter_collections.append(sc)
                scatters.append(sc)
                app_state.group_to_scatter[cat] = sc

                for j, idx in enumerate(indices):
                    key = (round(float(xs[j]), 3), round(float(ys[j]), 3))
                    app_state.sample_index_map[key] = idx
                    app_state.sample_coordinates[idx] = (float(xs[j]), float(ys[j]))
                    app_state.artist_to_sample[(id(sc), j)] = idx

        if not scatters and not show_kde:
            logger.error("No points were plotted in 2D")
            return False

        kde_utils.clear_marginal_axes()
        if show_marginal_kde:
            try:
                kde_utils.draw_marginal_kde(
                    app_state.ax,
                    df_plot,
                    group_col,
                    app_state.current_palette,
                    unique_cats,
                    x_col=data_columns[0],
                    y_col=data_columns[1],
                )
            except Exception as kde_err:
                logger.warning(f"Failed to render marginal KDE: {kde_err}")

        try:
            handles = []
            labels = []

            if show_kde:
                from matplotlib.patches import Patch
                for cat in unique_cats:
                    if cat not in app_state.current_palette:
                        continue
                    color = app_state.current_palette[cat]
                    patch = Patch(facecolor=color, edgecolor='none', label=cat, alpha=0.6)
                    handles.append(patch)
                    labels.append(cat)

            legend_handles = handles if handles else list(scatters)
            legend_labels = labels if labels else list(unique_cats)

            _place_inline_legend(
                app_state.ax, group_col, legend_handles, legend_labels,
                show_marginal_kde=show_marginal_kde,
                scatters=scatters, is_kde_mode=show_kde,
            )

        except Exception as legend_err:
            logger.warning(f"2D legend creation error: {legend_err}")

        subset_info = " (Subset)" if _active_subset_indices() is not None else ""
        title = (
            f"2D Scatter Plot{subset_info} ({data_columns[0]} vs {data_columns[1]})\n"
            f"Colored by {group_col}"
        )
        if app_state.ax is prev_ax and prev_xlim and prev_ylim:
            try:
                if prev_2d_cols and list(prev_2d_cols) == list(data_columns):
                    app_state.ax.set_xlim(prev_xlim)
                    app_state.ax.set_ylim(prev_ylim)
            except Exception:
                pass

        state_gateway.set_attr('current_plot_title', title)
        if getattr(app_state, 'show_plot_title', True):
            app_state.ax.set_title(title, pad=getattr(app_state, 'title_pad', 20.0))
        else:
            app_state.ax.set_title("")
        state_gateway.set_attr('last_2d_cols', list(data_columns))
        app_state.ax.set_xlabel(data_columns[0])
        app_state.ax.set_ylabel(data_columns[1])
        _apply_axis_text_style(app_state.ax)
        try:
            app_state.ax.autoscale(enable=True, axis='both')
        except Exception:
            pass

        _draw_equation_overlays(app_state.ax)

        state_gateway.set_attr(
            'annotation',
            app_state.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#cbd5e1", alpha=0.95),
            arrowprops=dict(arrowstyle="->", color="#475569"),
            zorder=15,
            ),
        )
        app_state.annotation.set_visible(False)
        try:
            if app_state.annotation.arrow_patch is not None:
                app_state.annotation.arrow_patch.set_zorder(14)
        except Exception:
            pass

        return True

    except Exception as err:
        logger.error(f"2D plot failed: {err}")
        traceback.print_exc()
        return False

def plot_3d_data(group_col: str, data_columns: list[str], size: int = 60) -> bool:
    """Render a 3D scatter plot using selected raw measurement columns."""
    try:
        if app_state.fig is None:
            logger.error("Plot figure not initialized")
            return False

        if not data_columns or len(data_columns) != 3:
            logger.error("Exactly three data columns are required for a 3D scatter plot")
            return False

        df_global = _df_global()
        if df_global is None or len(df_global) == 0:
            logger.warning("No data available for plotting")
            return False

        missing = [col for col in data_columns if col not in df_global.columns]
        if missing:
            logger.error(f"Missing columns for 3D plot: {missing}")
            return False

        _ensure_axes(dimensions=3)

        if app_state.ax is None:
            logger.error("Failed to configure 3D axes")
            return False

        subset_indices = _active_subset_indices()
        if subset_indices is not None:
            indices_to_plot = sorted(list(subset_indices))
            df_plot = df_global.iloc[indices_to_plot].dropna(subset=data_columns).copy()
        else:
            df_plot = df_global.dropna(subset=data_columns).copy()

        if df_plot.empty:
            logger.warning("No complete rows available for the selected 3D columns")
            return False

        if group_col not in df_plot.columns:
            logger.error(f"Column not found: {group_col}")
            return False

        df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)

        _apply_current_style()

        app_state.ax.clear()
        _enforce_plot_style(app_state.ax)
        app_state.clear_plot_state()

        unique_cats = sorted(df_plot[group_col].unique())

        new_palette = _build_group_palette(unique_cats)

        for i, cat in enumerate(unique_cats):
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
                getattr(app_state, 'plot_marker_shape', 'o')
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
            logger.error("No points were plotted in 3D")
            return False

        try:
            _place_inline_legend(
                app_state.ax, group_col, legend_handles, legend_labels,
                show_marginal_kde=False,
            )
        except Exception as legend_err:
            logger.warning(f"3D legend creation error: {legend_err}")

        subset_info = " (Subset)" if _active_subset_indices() is not None else ""
        title = (
            f"3D Scatter Plot{subset_info} ({data_columns[0]}, {data_columns[1]}, {data_columns[2]})\n"
            f"Colored by {group_col}"
        )
        state_gateway.set_attr('current_plot_title', title)
        if getattr(app_state, 'show_plot_title', True):
            app_state.ax.set_title(title, pad=getattr(app_state, 'title_pad', 20.0))
        else:
            app_state.ax.set_title("")
        app_state.ax.set_xlabel(data_columns[0])
        app_state.ax.set_ylabel(data_columns[1])
        app_state.ax.set_zlabel(data_columns[2])
        _apply_axis_text_style(app_state.ax)

        state_gateway.set_attr('annotation', None)
        return True

    except Exception as err:
        logger.error(f"3D plot failed: {err}")
        traceback.print_exc()
        return False

