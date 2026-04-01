"""Scatter group rendering helpers for embedding plots."""
from __future__ import annotations

import logging

import numpy as np

from core import app_state

from ...ternary import prepare_ternary_components

logger = logging.getLogger(__name__)


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
                if {'_emb_tn', '_emb_ln', '_emb_rn'}.issubset(subset.columns):
                    t_norm = subset['_emb_tn'].to_numpy(dtype=float, copy=False)
                    l_norm = subset['_emb_ln'].to_numpy(dtype=float, copy=False)
                    r_norm = subset['_emb_rn'].to_numpy(dtype=float, copy=False)
                else:
                    ts = subset['_emb_t'].to_numpy(dtype=float, copy=False)
                    ls = subset['_emb_l'].to_numpy(dtype=float, copy=False)
                    rs = subset['_emb_r'].to_numpy(dtype=float, copy=False)
                    t_norm, l_norm, r_norm = prepare_ternary_components(ts, ls, rs)

                if len(t_norm) == 0:
                    continue

                marker_size = getattr(app_state, 'plot_marker_size', size)
                marker_alpha = getattr(app_state, 'plot_marker_alpha', 0.88)
                marker_shape = app_state.group_marker_map.get(cat, getattr(app_state, 'plot_marker_shape', 'o'))
                color = app_state.current_palette[cat]

                sc = app_state.ax.scatter(
                    t_norm,
                    l_norm,
                    r_norm,
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
                if offsets is None or len(offsets) < len(indices):
                    x_cart = 0.5 * t_norm + r_norm
                    y_cart = (np.sqrt(3.0) / 2.0) * t_norm
                    offsets = np.column_stack((x_cart, y_cart))

                sc.indices = indices

                for j, idx in enumerate(indices):
                    if j >= len(offsets):
                        continue
                    x_val, y_val = offsets[j]
                    x_val = float(x_val)
                    y_val = float(y_val)
                    key = (round(x_val, 2), round(y_val, 2))
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
            logger.warning('Error plotting category %s: %s', cat, err)

    if not scatters and not is_kde_mode:
        logger.error('No data points plotted')
        return None

    return scatters
