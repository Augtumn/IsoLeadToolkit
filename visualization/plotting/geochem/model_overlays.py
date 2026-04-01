"""Model curve and Mu/Kappa overlay rendering helpers."""
from __future__ import annotations

import logging

import numpy as np

from core import app_state
from visualization.line_styles import resolve_line_style
from ..data import _lazy_import_geochemistry
from ..label_layout import position_curve_label
from .overlay_common import (
    _format_label_text,
    _label_bbox,
    _register_overlay_artist,
    _register_overlay_curve_label,
    _resolve_label_options,
)
from .plumbotectonics_metadata import get_overlay_default_color

logger = logging.getLogger(__name__)

def _draw_model_curves(ax, actual_algorithm, params_list):
    """Draw model curves for Pb evolution plots."""
    geochemistry, _ = _lazy_import_geochemistry()
    if geochemistry is None:
        return

    if not params_list:
        params_list = [geochemistry.engine.get_parameters()]

    for params in params_list:
        try:
            tsec = float(params.get('Tsec', 0.0))
            if tsec > 0:
                t_max = tsec / 1e6
                t1_override = tsec
            else:
                t_max = float(params.get('T2', params.get('T1', 0.0))) / 1e6
                t1_override = params.get('T2', params.get('T1', None))
            t_vals = np.linspace(0, max(t_max, 1.0), 300)
            curve = geochemistry.calculate_modelcurve(
                t_vals,
                params=params,
                T1=t1_override / 1e6 if t1_override else None
            )
            x_vals = np.asarray(curve['Pb206_204'])
            if actual_algorithm == 'PB_EVOL_76':
                y_vals = np.asarray(curve['Pb207_204'])
            else:
                y_vals = np.asarray(curve['Pb208_204'])

            style = resolve_line_style(
                app_state,
                'model_curve',
                {
                    'color': None,
                    'linewidth': getattr(app_state, 'model_curve_width', 1.2),
                    'linestyle': '-',
                    'alpha': 0.8
                }
            )
            line_color = style.get('color') or get_overlay_default_color('model_curve')
            label_opts = _resolve_label_options(
                'model_curve',
                {
                    'label_text': '',
                    'label_fontsize': 9,
                    'label_background': False,
                    'label_bg_color': '#ffffff',
                    'label_bg_alpha': 0.85,
                    'label_position': 'auto',
                }
            )
            line_kwargs = {
                'linewidth': style['linewidth'],
                'linestyle': style['linestyle'],
                'alpha': style['alpha'],
                'zorder': 1,
                'label': '_nolegend_'
            }
            if line_color is not None:
                line_kwargs['color'] = line_color
            line_artists = ax.plot(x_vals, y_vals, **line_kwargs)
            for artist in line_artists:
                _register_overlay_artist('model_curve', artist)

            label_text = _format_label_text(
                label_opts.get('label_text'),
                index=len(getattr(app_state, 'overlay_curve_label_data', [])) + 1
            )
            if label_text:
                text_artist = ax.text(
                    x_vals[0], y_vals[0],
                    label_text,
                    color=line_color or style.get('color') or getattr(app_state, 'label_color', '#1f2937'),
                    fontsize=label_opts['label_fontsize'],
                    va='center',
                    ha='center',
                    alpha=style['alpha'],
                    bbox=_label_bbox(label_opts, edgecolor=line_color)
                )
                _register_overlay_curve_label(
                    text_artist,
                    x_vals,
                    y_vals,
                    label_text,
                    label_opts.get('label_position', 'auto'),
                    style_key='model_curve'
                )
                position_curve_label(
                    ax,
                    text_artist,
                    mode='isoage',
                    x_line=x_vals,
                    y_line=y_vals,
                    label_text=label_text,
                    position_mode=label_opts.get('label_position', 'auto'),
                )
        except Exception as err:
            logger.warning("Failed to draw model curve: %s", err)


def _draw_mu_kappa_paleoisochrons(ax, ages):
    """Draw paleoisochron ages as vertical guides for Mu/Kappa plots."""
    if not ages:
        return
    try:
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
        # Place labels in axes coordinates so zoom/pan preserves their position.
        position_mode = label_opts.get('label_position', 'auto')
        if position_mode == 'start':
            label_y = 0.02
        elif position_mode == 'center':
            label_y = 0.5
        else:
            label_y = 0.98
        label_transform = ax.get_xaxis_transform()
        for age in ages:
            try:
                age_val = float(age)
            except (TypeError, ValueError):
                continue
            if not np.isfinite(age_val):
                continue
            line_kwargs = {
                'linewidth': paleo_style['linewidth'],
                'linestyle': paleo_style['linestyle'],
                'alpha': paleo_style['alpha'],
                'zorder': 2,
                'clip_on': True,
            }
            if line_color is not None:
                line_kwargs['color'] = line_color
            line_artist = ax.axvline(age_val, **line_kwargs)
            _register_overlay_artist('paleoisochron', line_artist)
            ax.text(
                age_val,
                label_y,
                _format_label_text(label_opts.get('label_text'), age_val) or f" {age_val:.0f} Ma",
                color=line_color or paleo_style.get('color') or getattr(app_state, 'label_color', '#1f2937'),
                fontsize=label_opts['label_fontsize'],
                rotation=90,
                va='top',
                ha='right',
                alpha=paleo_style['alpha'],
                transform=label_transform,
                clip_on=True,
                bbox=_label_bbox(label_opts, edgecolor=line_color)
            )
    except Exception as err:
        logger.warning("Failed to draw Mu/Kappa paleoisochrons: %s", err)

