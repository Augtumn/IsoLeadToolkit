"""Paleoisochron overlay rendering helpers."""
from __future__ import annotations

import logging

import numpy as np

from core import app_state, state_gateway
from visualization.line_styles import resolve_line_style

from ..data import _lazy_import_geochemistry
from ..label_layout import position_curve_label
from .overlay_helpers import (
    _format_label_text,
    _label_bbox,
    _register_overlay_artist,
    _resolve_label_options,
    get_overlay_default_color,
)

logger = logging.getLogger(__name__)

def _draw_paleoisochrons(ax, actual_algorithm, ages, params):
    """Draw paleoisochron reference lines for given ages."""
    geochemistry, _ = _lazy_import_geochemistry()
    if geochemistry is None:
        return
    try:
        state_gateway.set_attr('paleoisochron_label_data', [])
        xlim = ax.get_xlim()
        x_min = xlim[0]
        x_max = xlim[1]
        x_vals = np.linspace(x_min, x_max, 200)

        for age in ages:
            params_line = geochemistry.calculate_paleoisochron_line(
                age,
                params=params,
                algorithm=actual_algorithm
            )
            if not params_line:
                logger.debug("Paleoisochron returned None for age=%s Ma, algorithm=%s", age, actual_algorithm)
                continue
            slope, intercept = params_line

            y_vals = slope * x_vals + intercept
            paleo_style = resolve_line_style(
                app_state,
                'paleoisochron',
                {
                    'color': None,
                    'linewidth': getattr(app_state, 'paleoisochron_width', 0.9),
                    'linestyle': '--',
                    'alpha': 0.85
                }
            )
            line_color = paleo_style.get('color') or get_overlay_default_color('paleoisochron')
            label_opts = _resolve_label_options(
                'paleoisochron',
                {
                    'label_text': '',
                    'label_fontsize': 8,
                    'label_background': False,
                    'label_bg_color': '#ffffff',
                    'label_bg_alpha': 0.85,
                    'label_position': 'auto',
                }
            )
            line_kwargs = {
                'linestyle': paleo_style['linestyle'],
                'linewidth': paleo_style['linewidth'],
                'alpha': paleo_style['alpha'],
                'zorder': 3,
                'label': '_nolegend_'
            }
            if line_color is not None:
                line_kwargs['color'] = line_color
            line_artists = ax.plot(x_vals, y_vals, **line_kwargs)
            for artist in line_artists:
                _register_overlay_artist('paleoisochron', artist)
            if len(x_vals) > 0:
                label_text = _format_label_text(label_opts.get('label_text'), age)
                if not label_text:
                    label_text = f" {age:.0f} Ma"
                text_artist = ax.text(
                    x_vals[-1], y_vals[-1],
                    label_text,
                    color=line_color or paleo_style.get('color') or getattr(app_state, 'label_color', '#1f2937'),
                    fontsize=label_opts['label_fontsize'],
                    va='center',
                    ha='left',
                    alpha=paleo_style['alpha'],
                    bbox=_label_bbox(label_opts, edgecolor=line_color)
                )
                app_state.paleoisochron_label_data.append({
                    'text': text_artist,
                    'slope': slope,
                    'intercept': intercept,
                    'age': age,
                    'label_text': label_text,
                    'position': label_opts.get('label_position', 'auto'),
                    'style_key': 'paleoisochron',
                })
                position_curve_label(
                    ax,
                    text_artist,
                    mode='paleo',
                    slope=slope,
                    intercept=intercept,
                    age=age,
                    label_text=label_text,
                    position_mode=label_opts.get('label_position', 'auto'),
                )
    except Exception as err:
        logger.warning("Failed to draw paleoisochrons: %s", err)


