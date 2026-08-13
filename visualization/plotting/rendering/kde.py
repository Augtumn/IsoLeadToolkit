"""KDE rendering helpers for embedding plots."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from core import app_state
from visualization.line_styles import ensure_line_style
from .. import kde as kde_utils
from ..ternary import prepare_ternary_components

logger = logging.getLogger(__name__)


def _resolve_kde_style(target: str = 'kde') -> dict[str, Any]:
    legacy_key = 'kde_style' if target == 'kde' else 'marginal_kde_style'
    style_key = 'kde_curve' if target == 'kde' else 'marginal_kde_curve'
    legacy_style = getattr(app_state, legacy_key, {}) or {}
    fallback = {
        'color': None,
        'linewidth': float(legacy_style.get('linewidth', 1.0)),
        'linestyle': '-',
        'alpha': float(legacy_style.get('alpha', 0.6 if target == 'kde' else 0.25)),
        'fill': bool(legacy_style.get('fill', True)),
    }
    if target == 'kde':
        fallback['levels'] = int(legacy_style.get('levels', 10))
    return ensure_line_style(app_state, style_key, fallback)


def _render_kde_overlay(
    actual_algorithm: str,
    df_plot: Any,
    group_col: str,
    unique_cats: list[str],
    new_palette: dict[str, str],
) -> None:
    if not getattr(app_state, 'show_kde', False):
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
                kde_kwargs: dict[str, Any] = {
                    'levels': int(kde_style.get('levels', 10)),
                    'fill': kde_fill,
                    'alpha': float(kde_style.get('alpha', 0.6)),
                    'warn_singular': False,
                    'legend': False,
                    'zorder': 1,
                }
                if not kde_fill:
                    # seaborn warns when 'linewidth' is passed to filled
                    # contours; only pass 'linewidths' for line-only contours.
                    kde_kwargs['linewidths'] = float(kde_style.get('linewidth', 1.0))
                kde_utils.sns.kdeplot(
                    x=x_cart,
                    y=y_cart,
                    color=new_palette[cat],
                    ax=app_state.ax,
                    **kde_kwargs,
                )
        else:
            logger.info("Generating KDE for %s...", actual_algorithm)
            kde_style = _resolve_kde_style('kde')
            kde_fill = bool(kde_style.get('fill', True))
            kde_kwargs = {
                'levels': int(kde_style.get('levels', 10)),
                'fill': kde_fill,
                'alpha': float(kde_style.get('alpha', 0.6)),
                'warn_singular': False,
                'legend': False,
                'zorder': 1,
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
