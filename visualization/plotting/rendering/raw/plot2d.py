"""2D raw scatter plotting implementation."""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from core import app_state, state_gateway

from ... import kde as kde_utils
from ...core import _build_group_palette, _ensure_axes
from ...geochem.equation_overlays import _draw_equation_overlays
from ...grouping import resolve_group_marker
from ...style import _apply_axis_text_style, _apply_current_style, _enforce_plot_style
from ..common.legend import _place_inline_legend
from ..common.state_access import _active_subset_indices, _df_global
from ..kde import _resolve_kde_style

logger = logging.getLogger(__name__)


def _validate_2d_inputs(
    data_columns: list[str],
    df_global: pd.DataFrame | None,
) -> tuple[str, str] | None:
    """Validate figure/data prerequisites for a 2D scatter plot.

    Returns the two validated data column names, or ``None`` on failure.
    """
    if app_state.fig is None:
        logger.error('Plot figure not initialized')
        return None

    if not data_columns or len(data_columns) != 2:
        logger.error('Exactly two data columns are required for a 2D scatter plot')
        return None

    if df_global is None or len(df_global) == 0:
        logger.warning('No data available for plotting')
        return None

    missing = [col for col in data_columns if col not in df_global.columns]
    if missing:
        logger.error('Missing columns for 2D plot: %s', missing)
        return None

    return data_columns[0], data_columns[1]


def _capture_prev_axes() -> tuple[Any | None, Any | None, Any | None, list[str] | None]:
    """Snapshot the current axes and its limits before reconfiguring for 2D."""
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
    return prev_ax, prev_xlim, prev_ylim, prev_2d_cols


def _prepare_2d_dataframe(
    group_col: str,
    data_columns: list[str],
    df_global: pd.DataFrame,
) -> tuple[pd.DataFrame, list[str]] | None:
    """Apply subsetting, numeric conversion and group visibility filtering.

    Returns ``(df_plot, all_groups)`` or ``None`` when no plottable rows exist.
    """
    subset_indices = _active_subset_indices()
    if subset_indices is not None:
        indices_to_plot = sorted(list(subset_indices))
        df_plot = df_global.iloc[indices_to_plot].dropna(subset=data_columns).copy()
    else:
        df_plot = df_global.dropna(subset=data_columns).copy()

    if df_plot.empty:
        logger.warning('No complete rows available for the selected 2D columns')
        return None

    if group_col not in df_plot.columns:
        logger.error('Column not found: %s', group_col)
        return None

    try:
        for col in data_columns:
            df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce')

        df_plot = df_plot.dropna(subset=data_columns)

        if df_plot.empty:
            logger.warning('No valid numeric data available for 2D plot.')
            return None
    except Exception as err:
        logger.error('Failed to convert columns to numeric: %s', err)
        return None

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
            logger.info('No 2D data matches the selected legend filter; reverting to all groups.')
            state_gateway.set_visible_groups(None)
        else:
            df_plot = df_plot[mask].copy()
            if df_plot.empty:
                logger.info('Filtered 2D data is empty; reverting to all groups.')
                df_plot = df_global.dropna(subset=data_columns).copy()
                df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)
                state_gateway.set_visible_groups(None)
                all_groups = sorted(df_plot[group_col].unique())
                state_gateway.sync_available_and_visible_groups(all_groups)

    return df_plot, all_groups


def _render_2d_kde(
    df_plot: pd.DataFrame,
    group_col: str,
    data_columns: list[str],
) -> None:
    """Render the seaborn KDE contour overlay onto the current axes."""
    try:
        kde_utils.lazy_import_seaborn()
        kde_style = _resolve_kde_style('kde')
        kde_fill = bool(kde_style.get('fill', True))
        kde_kwargs: dict[str, Any] = {
            'data': df_plot,
            'x': data_columns[0],
            'y': data_columns[1],
            'hue': group_col,
            'palette': app_state.current_palette,
            'ax': app_state.ax,
            'levels': int(kde_style.get('levels', 10)),
            'fill': kde_fill,
            'alpha': float(kde_style.get('alpha', 0.6)),
            'warn_singular': False,
            'legend': False,
            'zorder': 1,
            # Per-group normalization: seaborn's default common_norm=True
            # lets one tight-spike group flatten every other group's KDE.
            'common_norm': False,
        }
        if not kde_fill:
            # seaborn warns when 'linewidth' is passed to filled contours;
            # only pass 'linewidths' for line-only contours.
            kde_kwargs['linewidths'] = float(kde_style.get('linewidth', 1.0))
        kde_utils.sns.kdeplot(**kde_kwargs)
    except Exception as err:
        logger.warning('Failed to render KDE: %s', err)


def _render_2d_scatter_groups(
    df_plot: pd.DataFrame,
    group_col: str,
    data_columns: list[str],
    unique_cats: list[str],
    size: int,
) -> list[Any]:
    """Render per-group 2D scatter collections and register point mappings."""
    show_edge = bool(getattr(app_state, 'scatter_show_edge', True))
    edge_color = getattr(app_state, 'scatter_edgecolor', '#1e293b') if show_edge else 'none'
    edge_width = getattr(app_state, 'scatter_edgewidth', 0.4) if show_edge else 0.0
    scatters = []

    for cat in unique_cats:
        subset = df_plot[df_plot[group_col] == cat]
        if subset.empty:
            continue

        xs = pd.to_numeric(subset[data_columns[0]], errors='coerce').values
        ys = pd.to_numeric(subset[data_columns[1]], errors='coerce').values
        indices = subset.index.tolist()

        color = app_state.current_palette[cat]

        marker_size = getattr(app_state, 'plot_marker_size', size)
        marker_alpha = getattr(app_state, 'plot_marker_alpha', 0.88)
        marker_shape = resolve_group_marker(app_state, cat)
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

    return scatters


def _render_2d_marginal_kde(
    df_plot: pd.DataFrame,
    group_col: str,
    unique_cats: list[str],
    data_columns: list[str],
) -> None:
    """Draw marginal KDE distributions alongside the 2D scatter."""
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
        logger.warning('Failed to render marginal KDE: %s', kde_err)


def _render_2d_legend(
    app_state_ax: Any,
    group_col: str,
    unique_cats: list[str],
    scatters: list[Any],
    show_kde: bool,
    show_marginal_kde: bool,
) -> None:
    """Build the 2D legend, using Patch handles for KDE mode."""
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
            app_state_ax,
            group_col,
            legend_handles,
            legend_labels,
            show_marginal_kde=show_marginal_kde,
            scatters=scatters,
            is_kde_mode=show_kde,
        )

    except Exception as legend_err:
        logger.warning('2D legend creation error: %s', legend_err)


def _render_2d_title_and_axes(
    group_col: str,
    data_columns: list[str],
    prev_ax: Any | None,
    prev_xlim: Any | None,
    prev_ylim: Any | None,
    prev_2d_cols: list[str] | None,
    subset_info: str,
) -> None:
    """Build the 2D title, axis labels and restore prior axis limits."""
    title = (
        f'2D Scatter Plot{subset_info} ({data_columns[0]} vs {data_columns[1]})\n'
        f'Colored by {group_col}'
    )
    if app_state.ax is prev_ax and prev_xlim and prev_ylim:
        try:
            if prev_2d_cols and list(prev_2d_cols) == list(data_columns):
                app_state.ax.set_xlim(prev_xlim)
                app_state.ax.set_ylim(prev_ylim)
        except Exception:
            pass

    state_gateway.set_current_plot_title(title)
    if getattr(app_state, 'show_plot_title', True):
        app_state.ax.set_title(title, pad=getattr(app_state, 'title_pad', 20.0))
    else:
        app_state.ax.set_title('')
    state_gateway.set_last_2d_cols(list(data_columns))
    app_state.ax.set_xlabel(data_columns[0])
    app_state.ax.set_ylabel(data_columns[1])
    _apply_axis_text_style(app_state.ax)
    try:
        app_state.ax.autoscale(enable=True, axis='both')
    except Exception:
        pass

    _draw_equation_overlays(app_state.ax)


def _attach_annotation() -> None:
    """Attach the reusable hover annotation and hide it initially."""
    state_gateway.set_annotation(
        app_state.ax.annotate(
            '',
            xy=(0, 0),
            xytext=(20, 20),
            textcoords='offset points',
            bbox=dict(boxstyle='round,pad=0.5', fc='white', ec='#cbd5e1', alpha=0.95),
            arrowprops=dict(arrowstyle='->', color='#475569'),
            zorder=15,
        )
    )
    app_state.annotation.set_visible(False)
    try:
        if app_state.annotation.arrow_patch is not None:
            app_state.annotation.arrow_patch.set_zorder(14)
    except Exception:
        pass


def plot_2d_data(group_col: str, data_columns: list[str], size: int = 60, show_kde: bool = False) -> bool:
    """Render a 2D scatter plot using selected raw measurement columns."""
    try:
        df_global = _df_global()
        if _validate_2d_inputs(data_columns, df_global) is None:
            return False

        prev_ax, prev_xlim, prev_ylim, prev_2d_cols = _capture_prev_axes()

        _ensure_axes(dimensions=2)

        if app_state.ax is None:
            logger.error('Failed to configure 2D axes')
            return False

        prepared = _prepare_2d_dataframe(group_col, data_columns, df_global)
        if prepared is None:
            return False
        df_plot, _ = prepared

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

        _build_group_palette(unique_cats)

        show_marginal_kde = getattr(app_state, 'show_marginal_kde', False)

        if show_kde:
            _render_2d_kde(df_plot, group_col, data_columns)

        scatters = [] if show_kde else _render_2d_scatter_groups(df_plot, group_col, data_columns, unique_cats, size)

        if not scatters and not show_kde:
            logger.error('No points were plotted in 2D')
            try:
                app_state.fig.canvas.draw_idle()
            except Exception:
                pass
            return False

        kde_utils.clear_marginal_axes()
        if show_marginal_kde:
            _render_2d_marginal_kde(df_plot, group_col, unique_cats, data_columns)

        _render_2d_legend(app_state.ax, group_col, unique_cats, scatters, show_kde, show_marginal_kde)

        subset_info = ' (Subset)' if _active_subset_indices() is not None else ''
        _render_2d_title_and_axes(
            group_col,
            data_columns,
            prev_ax,
            prev_xlim,
            prev_ylim,
            prev_2d_cols,
            subset_info,
        )

        _attach_annotation()

        return True

    except Exception as err:
        logger.exception('2D plot failed: %s', err)
        try:
            if app_state.fig is not None and app_state.fig.canvas is not None:
                app_state.fig.canvas.draw_idle()
        except Exception:
            pass
        return False
