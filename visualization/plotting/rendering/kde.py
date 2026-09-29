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


def _draw_ternary_kde(axes, t_values, l_values, r_values, color, levels, fill, alpha) -> bool:
    """Density contours for a ternary plot, drawn in the axes' Cartesian frame.

    An mpltern axes has its own Cartesian data space: the triangle vertices are (0, 1),
    (-1/sqrt(3), 0) and (+1/sqrt(3), 0), so a composition (t, l, r) sits at
    x = (r - l)/sqrt(3), y = t (mpltern's "Cartesian coordinates" example). Estimating the
    density on a rectangular grid in that frame and drawing it with transform=ax.transData
    gives smooth iso-lines.

    Two earlier attempts failed for instructive reasons: handing Cartesian data to
    ax.contour without the transform draws nothing (the axes read the arrays as (t, l, r)),
    and going through tricontour on a simplex grid makes the iso-lines follow triangle edges,
    which looks like concentric hexagons.
    """
    from scipy.stats import gaussian_kde

    t = np.asarray(t_values, dtype=float)
    l = np.asarray(l_values, dtype=float)
    r = np.asarray(r_values, dtype=float)
    points = np.column_stack([(r - l) / np.sqrt(3.0), t])
    if points.shape[0] < 3:
        return False
    try:
        kde = gaussian_kde(points.T, bw_method="scott")
    except Exception as err:
        logger.warning("Ternary KDE estimator failed: %s", err)
        return False

    limit = 1.0 / np.sqrt(3.0)
    step = 0.01
    xs = np.arange(-limit, limit + step, step)
    ys = np.arange(0.0, 1.0 + step, step)
    grid_x, grid_y = np.meshgrid(xs, ys)
    # Outside the simplex the density stays NaN, so the contours stop at the edges.
    inside = np.abs(grid_x) <= (1.0 - grid_y) / np.sqrt(3.0)
    if not np.any(inside):
        return False
    density = np.full(grid_x.shape, np.nan)
    density[inside] = kde(np.vstack([grid_x[inside], grid_y[inside]]))
    peak = float(np.nanmax(density))
    if not np.isfinite(peak) or peak <= 0.0:
        return False
    level_values = peak * np.linspace(0.1, 0.9, max(2, int(levels)))
    # Stated in the log so a running instance can be told apart from a stale one: this line
    # only exists in the Cartesian-frame implementation.
    logger.info(
        "Ternary KDE: Cartesian grid %dx%d, %d levels, fill=%s (transData contours).",
        grid_x.shape[1], grid_x.shape[0], len(level_values), fill,
    )
    try:
        if fill:
            from matplotlib.colors import LinearSegmentedColormap, to_rgb

            base = to_rgb(color)
            gradient = LinearSegmentedColormap.from_list(
                "ternary_kde", [(1.0, 1.0, 1.0, 0.0), (base[0], base[1], base[2], 1.0)]
            )
            axes.contourf(
                grid_x, grid_y, density, levels=np.linspace(0.0, peak, 64), cmap=gradient,
                alpha=alpha, transform=axes.transData, zorder=1,
            )
        axes.contour(
            grid_x, grid_y, density, levels=level_values, colors=[color], linewidths=0.7,
            alpha=min(1.0, alpha + 0.3), transform=axes.transData, zorder=1.1,
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

                kde_style = _resolve_kde_style('kde')
                kde_fill = bool(kde_style.get('fill', True))
                if not _draw_ternary_kde(
                    app_state.ax, t_norm, 1.0 - t_norm - r_norm, r_norm, new_palette[cat],
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
