"""Helper routines for embedding/scatter rendering."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from core import CONFIG, app_state, state_gateway, translate
from visualization.line_styles import resolve_line_style
from ..legend_model import group_legend_items, overlay_legend_items
from .geo_layers import _render_geo_overlays
from .kde import _render_kde_overlay, _resolve_kde_style
from ..style import (
    _apply_axis_text_style,
    _legend_columns_for_layout,
    _legend_layout_config,
    _style_legend,
)
from ..ternary import _apply_ternary_stretch

logger = logging.getLogger(__name__)


def _data_state() -> Any:
    return getattr(app_state, 'data', app_state)


def _df_global() -> Any:
    return getattr(_data_state(), 'df_global', app_state.df_global)


def _data_cols() -> list[str]:
    return getattr(_data_state(), 'data_cols', app_state.data_cols)


def _active_subset_indices() -> Any:
    return getattr(_data_state(), 'active_subset_indices', app_state.active_subset_indices)


def _notify_legend_panel(title, handles, labels):
    callback = getattr(app_state, 'legend_update_callback', None)
    if callable(callback):
        try:
            callback(title, handles, labels)
        except Exception:
            pass

def _build_legend_proxies(handles, labels):
    """Build proxy legend handles from group_legend_items data."""
    items = group_legend_items(all_groups=list(labels))
    use_patch = any(isinstance(h, Patch) for h in handles)
    proxies = []
    for item in items:
        color = item['color']
        if use_patch:
            proxies.append(Patch(facecolor=color, edgecolor='none'))
        else:
            proxies.append(
                Line2D(
                    [0],
                    [0],
                    marker=item['marker'],
                    linestyle='None',
                    markerfacecolor=color,
                    markeredgecolor=getattr(app_state, 'scatter_edgecolor', '#1e293b'),
                    markeredgewidth=getattr(app_state, 'scatter_edgewidth', 0.4),
                    markersize=8,
                )
            )
    return proxies

def _build_overlay_legend_entries(actual_algorithm):
    """Build legend entries for geochemistry overlay curves."""
    entries = []
    for item in overlay_legend_items(actual_algorithm=actual_algorithm):
        style = resolve_line_style(app_state, item['style_key'], item['fallback'])
        color = style.get('color') or item['default_color']
        handle = Line2D(
            [0], [0],
            color=color,
            linewidth=style['linewidth'],
            linestyle=style['linestyle'],
            alpha=style['alpha'],
        )
        entries.append((handle, translate(item['label_key'])))
    return entries


def _place_inline_legend(
    ax, group_col, legend_handles, legend_labels,
    *, show_marginal_kde=False, scatters=None, is_kde_mode=False,
):
    """Place in-plot legend and notify the outside legend panel.

    Shared by plot_embedding, plot_2d_data, and plot_3d_data.
    """
    state_gateway.set_attrs(
        {
            'legend_last_title': group_col,
            'legend_last_handles': legend_handles,
            'legend_last_labels': legend_labels,
        }
    )
    _notify_legend_panel(group_col, legend_handles, legend_labels)

    n_cats = len(legend_labels)
    if n_cats > 30:
        logger.info("Too many categories for standard legend. Use Control Panel legend.")
        return

    inside_location = getattr(app_state, 'legend_position', None)
    if not inside_location or str(inside_location).startswith('outside_'):
        return

    location_key = inside_location
    auto_ncol = _legend_columns_for_layout(legend_labels, ax, location_key)
    if auto_ncol is None:
        ncol = app_state.legend_columns if getattr(app_state, 'legend_columns', 0) > 0 else (2 if n_cats > 15 else 1)
    else:
        ncol = auto_ncol

    legend_kwargs = {
        'title': group_col,
        'frameon': True,
        'fancybox': True,
        'ncol': ncol,
    }

    loc, bbox, mode, borderaxespad = _legend_layout_config(
        ax, show_marginal_kde=show_marginal_kde, location_key=location_key,
    )
    legend_kwargs['loc'] = loc
    legend_kwargs['bbox_to_anchor'] = bbox if bbox else None
    if mode:
        legend_kwargs['mode'] = mode
    if borderaxespad is not None:
        legend_kwargs['borderaxespad'] = borderaxespad

    legend = ax.legend(handles=legend_handles, labels=legend_labels, **legend_kwargs)

    if legend is not None and bbox:
        try:
            legend.set_bbox_to_anchor(bbox, transform=ax.transAxes)
        except Exception:
            pass

    _style_legend(legend, show_marginal_kde=show_marginal_kde, location_key=location_key)

    if legend is not None and scatters and not is_kde_mode:
        try:
            for leg_patch, sc in zip(legend.get_patches(), scatters):
                app_state.legend_to_scatter[leg_patch] = sc
        except Exception:
            pass


def _render_scatter_groups(actual_algorithm, df_plot, group_col, unique_cats, size):
    scatters = []
    is_kde_mode = getattr(app_state, 'show_kde', False)
    show_edge = bool(getattr(app_state, 'scatter_show_edge', True))
    edge_color = getattr(app_state, 'scatter_edgecolor', '#1e293b') if show_edge else 'none'
    edge_width = getattr(app_state, 'scatter_edgewidth', 0.4) if show_edge else 0.0

    for cat in unique_cats:
        if is_kde_mode:
            continue

        try:
            subset = df_plot[df_plot[group_col] == cat]
            if subset.empty:
                continue
            indices = subset.index.tolist()

            if actual_algorithm == 'TERNARY':
                ts = subset['_emb_t'].to_numpy(dtype=float, copy=False)
                ls = subset['_emb_l'].to_numpy(dtype=float, copy=False)
                rs = subset['_emb_r'].to_numpy(dtype=float, copy=False)

                if len(ts) == 0:
                    continue

                t_vals, l_vals, r_vals = _apply_ternary_stretch(ts, ls, rs)

                sums = t_vals + l_vals + r_vals
                with np.errstate(divide='ignore', invalid='ignore'):
                    sums[sums == 0] = 1.0
                    t_norm = t_vals / sums
                    r_norm = r_vals / sums

                h = np.sqrt(3) / 2
                x_cart = 0.5 * t_norm + 1.0 * r_norm
                y_cart = h * t_norm

                marker_size = getattr(app_state, 'plot_marker_size', size)
                marker_alpha = getattr(app_state, 'plot_marker_alpha', 0.88)
                marker_shape = app_state.group_marker_map.get(cat, getattr(app_state, 'plot_marker_shape', 'o'))
                color = app_state.current_palette[cat]

                sc = app_state.ax.scatter(
                    x_cart,
                    y_cart,
                    label=cat,
                    color=color,
                    s=marker_size,
                    marker=marker_shape,
                    alpha=marker_alpha,
                    edgecolors=edge_color,
                    linewidth=edge_width,
                    zorder=2,
                    picker=5,
                )

                offsets = sc.get_offsets()
                sc.indices = indices
                scatters.append(sc)

                for j, idx in enumerate(indices):
                    if j < len(offsets):
                        x_val, y_val = offsets[j]
                        key = (round(float(x_val), 2), round(float(y_val), 2))
                        app_state.sample_index_map[key] = idx
                        app_state.sample_coordinates[idx] = (x_val, y_val)
                        app_state.artist_to_sample[(id(sc), j)] = idx

            else:
                xs = subset['_emb_x'].to_numpy(dtype=float, copy=False)
                ys = subset['_emb_y'].to_numpy(dtype=float, copy=False)

                if len(xs) == 0:
                    continue

                marker_size = getattr(app_state, 'plot_marker_size', size)
                marker_alpha = getattr(app_state, 'plot_marker_alpha', 0.88)
                marker_shape = app_state.group_marker_map.get(cat, getattr(app_state, 'plot_marker_shape', 'o'))

                color = app_state.current_palette[cat]
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
                    picker=5,
                )

                for j, idx in enumerate(indices):
                    x_val = float(xs[j])
                    y_val = float(ys[j])
                    key = (round(x_val, 2), round(y_val, 2))
                    app_state.sample_index_map[key] = idx
                    app_state.sample_coordinates[idx] = (x_val, y_val)
                    app_state.artist_to_sample[(id(sc), j)] = idx

            scatters.append(sc)
            app_state.scatter_collections.append(sc)
            app_state.group_to_scatter[cat] = sc

        except Exception as err:
            logger.warning("Error plotting category %s: %s", cat, err)

    if not scatters and not is_kde_mode:
        logger.error("No data points plotted")
        return None

    return scatters


def _render_legend(actual_algorithm, group_col, unique_cats, scatters):
    try:
        handles = []
        labels = []
        is_kde_mode = getattr(app_state, 'show_kde', False)
        show_marginal_kde = getattr(app_state, 'show_marginal_kde', False)

        if is_kde_mode:
            for cat in unique_cats:
                color = app_state.current_palette[cat]
                patch = Patch(facecolor=color, edgecolor='none', label=cat, alpha=0.6)
                handles.append(patch)
                labels.append(cat)

        legend_handles = handles if handles else list(scatters)
        legend_labels = labels if labels else list(unique_cats)
        for handle, label in _build_overlay_legend_entries(actual_algorithm):
            if label in legend_labels:
                continue
            legend_handles.append(handle)
            legend_labels.append(label)

        _place_inline_legend(
            app_state.ax,
            group_col,
            legend_handles,
            legend_labels,
            show_marginal_kde=show_marginal_kde,
            scatters=scatters,
            is_kde_mode=is_kde_mode,
        )
    except Exception as err:
        logger.warning("Legend creation error: %s", err)


def _render_title_labels(actual_algorithm, group_col, umap_params, tsne_params, pca_params, robust_pca_params):
    subset_info = " (Subset)" if _active_subset_indices() is not None else ""

    if actual_algorithm == 'UMAP':
        title = (
            f'Embedding - UMAP{subset_info} (n_neighbors={umap_params["n_neighbors"]}, min_dist={umap_params["min_dist"]})\n'
            f'Colored by {group_col}'
        )
    elif actual_algorithm == 'TSNE':
        title = (
            f'Embedding - t-SNE{subset_info} (perplexity={tsne_params["perplexity"]}, lr={tsne_params["learning_rate"]})\n'
            f'Colored by {group_col}'
        )
    elif actual_algorithm == 'PCA':
        title = f'Embedding - PCA{subset_info} (n_components={pca_params["n_components"]})\nColored by {group_col}'
    elif actual_algorithm == 'RobustPCA':
        title = (
            f'Embedding - Robust PCA{subset_info} (n_components={robust_pca_params["n_components"]})\n'
            f'Colored by {group_col}'
        )
    elif actual_algorithm == 'V1V2':
        title = f'Geochem - V1-V2 Diagram{subset_info}\nColored by {group_col}'
    elif actual_algorithm == 'TERNARY':
        title = f'Raw - Ternary Plot{subset_info}\nColored by {group_col}'
    elif actual_algorithm == 'PB_EVOL_76':
        title = f'Geochem - Pb Evolution / Model Curves (206-207){subset_info}\nColored by {group_col}'
    elif actual_algorithm == 'PB_EVOL_86':
        title = f'Geochem - Pb Evolution / Model Curves (206-208){subset_info}\nColored by {group_col}'
    elif actual_algorithm == 'PLUMBOTECTONICS_76':
        title = f'Geochem - Plumbotectonics (206-207){subset_info}\nColored by {group_col}'
    elif actual_algorithm == 'PLUMBOTECTONICS_86':
        title = f'Geochem - Plumbotectonics (206-208){subset_info}\nColored by {group_col}'
    elif actual_algorithm == 'PB_MU_AGE':
        title = f'Geochem - Mu vs Age{subset_info}\nColored by {group_col}'
    elif actual_algorithm == 'PB_KAPPA_AGE':
        title = f'Geochem - Kappa vs Age{subset_info}\nColored by {group_col}'
    else:
        title = f'{actual_algorithm}{subset_info}\nColored by {group_col}'

    title_font_dict = {}
    has_cjk = any('\u4e00' <= char <= '\u9fff' for char in title)
    if has_cjk:
        cjk_font = getattr(app_state, 'custom_cjk_font', '')
        if cjk_font:
            title_font_dict['fontname'] = cjk_font
        else:
            try:
                available = {f.name for f in font_manager.fontManager.ttflist}
                for font_name in CONFIG.get('preferred_plot_fonts', []):
                    if font_name in available:
                        title_font_dict['fontname'] = font_name
                        break
            except Exception:
                pass

    state_gateway.set_attr('current_plot_title', title)
    if getattr(app_state, 'show_plot_title', True):
        app_state.ax.set_title(title, pad=getattr(app_state, 'title_pad', 20.0), **title_font_dict)
    else:
        app_state.ax.set_title("")

    if actual_algorithm == 'V1V2':
        app_state.ax.set_xlabel("V1")
        app_state.ax.set_ylabel("V2")
    elif actual_algorithm in ('PB_EVOL_76', 'PLUMBOTECTONICS_76'):
        app_state.ax.set_xlabel("206Pb/204Pb")
        app_state.ax.set_ylabel("207Pb/204Pb")
    elif actual_algorithm in ('PB_EVOL_86', 'PLUMBOTECTONICS_86'):
        app_state.ax.set_xlabel("206Pb/204Pb")
        app_state.ax.set_ylabel("208Pb/204Pb")
    elif actual_algorithm == 'PB_MU_AGE':
        app_state.ax.set_xlabel("Age (Ma)")
        app_state.ax.set_ylabel("Mu (238U/204Pb)")
    elif actual_algorithm == 'PB_KAPPA_AGE':
        app_state.ax.set_xlabel("Age (Ma)")
        app_state.ax.set_ylabel("Kappa (232Th/238U)")
    elif actual_algorithm == 'TERNARY':
        app_state.ax.set_aspect('equal')
    elif actual_algorithm in ('PCA', 'RobustPCA') and hasattr(app_state, 'pca_component_indices'):
        idx_x = app_state.pca_component_indices[0] + 1
        idx_y = app_state.pca_component_indices[1] + 1
        app_state.ax.set_xlabel(f"PC{idx_x}")
        app_state.ax.set_ylabel(f"PC{idx_y}")
    else:
        app_state.ax.set_xlabel(f"{actual_algorithm} Dimension 1")
        app_state.ax.set_ylabel(f"{actual_algorithm} Dimension 2")

    _apply_axis_text_style(app_state.ax)



