"""KDE rendering helpers for embedding plots."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from core import app_state
from visualization.line_styles import ensure_line_style
from .. import kde as kde_utils
from ..kde import kde_compute_kwargs
from ..ternary import prepare_ternary_components

logger = logging.getLogger(__name__)



def _resolve_kde_style(target: str = 'kde') -> dict[str, Any]:
    style_key = 'kde_curve' if target == 'kde' else 'marginal_kde_curve'
    fallback: dict[str, Any] = {
        'color': None,
        'linewidth': 1.0,
        'linestyle': '-',
        'alpha': 0.6 if target == 'kde' else 0.25,
        'fill': True,
    }
    if target == 'kde':
        fallback['levels'] = 10
    return ensure_line_style(app_state, style_key, fallback)


def _draw_ternary_kde(axes, x_cart, y_cart, color, levels, fill, alpha) -> bool:
    """Density contours for a ternary plot, in ternary coordinates.

    seaborn's kdeplot cannot be used on an mpltern axes: it builds a Cartesian grid and
    calls contour() with Cartesian data, which is why the ternary density never drew. The
    density is evaluated on a grid that covers the simplex and then handed to mpltern's
    tricontour/tricontourf, which take (t, l, r) coordinates.
    """
    from scipy.stats import gaussian_kde

    points = np.column_stack(
        [np.asarray(x_cart, dtype=float), np.asarray(y_cart, dtype=float)]
    )
    if points.shape[0] < 3:
        return False
    try:
        kde = gaussian_kde(points.T, bw_method="scott")
    except Exception as err:
        logger.warning("Ternary KDE estimator failed: %s", err)
        return False

    step = 0.02
    axis = np.arange(step, 1.0, step)
    grid_t, grid_l = np.meshgrid(axis, axis, indexing="ij")
    inside = (grid_t + grid_l) <= 1.0
    t_grid = grid_t[inside]
    l_grid = grid_l[inside]
    r_grid = 1.0 - t_grid - l_grid
    density = kde(
        np.vstack([0.5 * t_grid + r_grid, (np.sqrt(3.0) / 2.0) * t_grid])
    )
    peak = float(np.max(density)) if density.size else 0.0
    if not np.isfinite(peak) or peak <= 0.0:
        return False
    level_values = peak * np.linspace(0.1, 0.9, max(2, int(levels)))
    try:
        if fill:
            axes.tricontourf(
                t_grid, l_grid, r_grid, density,
                levels=level_values, colors=[color], alpha=alpha, zorder=1,
            )
        axes.tricontour(
            t_grid, l_grid, r_grid, density,
            levels=level_values, colors=[color], linewidths=0.8,
            alpha=min(1.0, alpha + 0.3), zorder=1.1,
        )
    except Exception as err:
        logger.warning("Ternary KDE contours failed: %s", err)
        return False
    return True


def _render_kde_overlay(
    actual_algorithm: str,
    df_plot: Any,
    group_col: str,
    unique_cats: list[str],
    new_palette: dict[str, str],
) -> None:
    if not app_state.show_kde:
        return
    try:
        kde_utils.lazy_import_seaborn()
        if actual_algorithm == 'TERNARY':
            logger.info("Generating KDE for Ternary Plot...")
            for cat in unique_cats:
                subset = df_plot[df_plot[group_col] == cat].copy()
                if subset.empty:
                    continue

                if {'_emb_tn', '_emb_ln', '_emb_rn'}.issubset(subset.columns):
                    t_norm = subset['_emb_tn'].to_numpy(dtype=float)
                    r_norm = subset['_emb_rn'].to_numpy(dtype=float)
                else:
                    ts = subset['_emb_t'].to_numpy(dtype=float)
                    ls = subset['_emb_l'].to_numpy(dtype=float)
                    rs = subset['_emb_r'].to_numpy(dtype=float)
                    t_norm, _, r_norm = prepare_ternary_components(ts, ls, rs)

                x_cart = 0.5 * t_norm + r_norm
                y_cart = (np.sqrt(3.0) / 2.0) * t_norm

                kde_style = _resolve_kde_style('kde')
                kde_fill = bool(kde_style.get('fill', True))
                if not _draw_ternary_kde(
                    app_state.ax, x_cart, y_cart, new_palette[cat],
                    int(kde_style.get('levels', 10)), kde_fill,
                    float(kde_style.get('alpha', 0.6)),
                ):
                    logger.warning(
                        "Ternary KDE skipped for group %s (too few points or bad density).",
                        cat,
                    )
        else:
            logger.info("Generating KDE for %s...", actual_algorithm)
            kde_style = _resolve_kde_style('kde')
            kde_fill = bool(kde_style.get('fill', True))
            kde_kwargs = {
                'levels': int(kde_style.get('levels', 10)),
                'fill': kde_fill,
                'alpha': float(kde_style.get('alpha', 0.6)),
                'legend': False,
                'zorder': 1,
                # Per-group normalisation by default; see _kde_compute_kwargs.
                **kde_compute_kwargs(),
            }
            if not kde_fill:
                kde_kwargs['linewidths'] = float(kde_style.get('linewidth', 1.0))
            kde_utils.sns.kdeplot(
                data=df_plot,
                x='_emb_x',
                y='_emb_y',
                hue=group_col,
                palette=new_palette,
                ax=app_state.ax,
                **kde_kwargs,
            )
    except Exception as kde_err:
        logger.warning("Failed to render KDE: %s", kde_err)
