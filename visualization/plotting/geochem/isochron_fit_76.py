"""ISOCHRON1 (PB_EVOL_76) group rendering helpers."""
from __future__ import annotations

import logging

import numpy as np

from core import app_state, state_gateway
from visualization.line_styles import resolve_line_style

from ..label_layout import position_curve_label
from .isochron_labels import _build_isochron_label
from .overlay_helpers import (
    _format_label_text,
    _label_bbox,
    _register_overlay_artist,
    _register_overlay_curve_label,
    _resolve_label_options,
)

logger = logging.getLogger(__name__)


def render_isochron1_group(
    *,
    ax: Any,
    geochemistry: Any,
    params: dict[str, Any],
    grp: str,
    slope: float,
    intercept: float,
    slope_err: float | None,
    x_line: np.ndarray,
    y_line: np.ndarray,
    color: str,
    show_fits: bool,
    show_growth: bool,
) -> None:
    """Render fitted line labels and optional growth curve for ISOCHRON1."""
    age_ma = None
    try:
        age_ma, _ = geochemistry.calculate_pbpb_age_from_ratio(slope, slope_err, params)
        if age_ma is not None and age_ma >= 0:
            # Copy-then-submit: an in-place write here would be rolled back
            # by the next StateStore sync, leaving export/UI without the age.
            results = dict(getattr(app_state, 'isochron_results', {}) or {})
            entry = dict(results.get(grp, {}) or {})
            entry['age_ma'] = age_ma
            results[grp] = entry
            state_gateway.set_isochron_results(results)
    except Exception as age_err:
        logger.warning('Failed to calculate isochron age for slope %.6f: %s', slope, age_err)

    label_opts = _resolve_label_options(
        'isochron',
        {
            'label_text': '',
            'label_fontsize': 9,
            'label_background': False,
            'label_bg_color': '#ffffff',
            'label_bg_alpha': 0.85,
            'label_position': 'auto',
        },
    )
    label_text = _build_isochron_label(app_state.isochron_results[grp])
    age_val = app_state.isochron_results[grp].get('age')
    if age_val is None:
        age_val = app_state.isochron_results[grp].get('age_ma')
    label_override = _format_label_text(label_opts.get('label_text'), age_val)
    if label_override:
        label_text = label_override

    if show_fits and label_text:
        final_label = f' {label_text}'
        text_artist = ax.text(
            x_line[0],
            y_line[0],
            final_label,
            color=color,
            fontsize=label_opts['label_fontsize'],
            va='center',
            ha='center',
            fontweight='bold',
            bbox=_label_bbox(label_opts, edgecolor=color),
        )
        _register_overlay_curve_label(
            text_artist,
            x_line,
            y_line,
            final_label,
            label_opts.get('label_position', 'auto'),
            style_key='isochron',
        )
        position_curve_label(
            ax,
            text_artist,
            mode='isoage',
            x_line=x_line,
            y_line=y_line,
            label_text=final_label,
            position_mode=label_opts.get('label_position', 'auto'),
        )

    if show_growth and age_ma is not None and age_ma > 0:
        growth = geochemistry.calculate_isochron1_growth_curve(
            slope,
            intercept,
            age_ma,
            params=params,
            steps=100,
        )
        if not growth:
            return

        x_growth = growth['x']
        y_growth = growth['y']
        mu_source = growth['mu_source']
        annot_text = f' μ={mu_source:.1f}'

        growth_style = resolve_line_style(
            app_state,
            'growth_curve',
            {
                'color': None,
                'linewidth': getattr(app_state, 'model_curve_width', 1.2),
                'linestyle': ':',
                'alpha': 0.6,
            },
        )
        line_artists = ax.plot(
            x_growth,
            y_growth,
            linestyle=growth_style['linestyle'],
            color=growth_style['color'] or color,
            alpha=growth_style['alpha'],
            linewidth=growth_style['linewidth'],
            zorder=1.5,
        )
        for artist in line_artists:
            _register_overlay_artist('growth_curve', artist)

        label_opts = _resolve_label_options(
            'growth_curve',
            {
                'label_text': '',
                'label_fontsize': 8,
                'label_background': False,
                'label_bg_color': '#ffffff',
                'label_bg_alpha': 0.85,
                'label_position': 'auto',
            },
        )
        growth_label = _format_label_text(label_opts.get('label_text'))
        if not growth_label:
            growth_label = annot_text
        if not growth_label:
            return

        text_artist = ax.text(
            x_growth[0],
            y_growth[0],
            growth_label,
            fontsize=label_opts['label_fontsize'],
            color=color,
            va='bottom',
            ha='right',
            alpha=0.8,
            bbox=_label_bbox(label_opts, edgecolor=color),
        )
        _register_overlay_curve_label(
            text_artist,
            x_growth,
            y_growth,
            growth_label,
            label_opts.get('label_position', 'auto'),
            style_key='growth_curve',
        )
        position_curve_label(
            ax,
            text_artist,
            mode='isoage',
            x_line=x_growth,
            y_line=y_growth,
            label_text=growth_label,
            position_mode=label_opts.get('label_position', 'auto'),
        )
