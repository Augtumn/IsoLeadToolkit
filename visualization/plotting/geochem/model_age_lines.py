"""Model-age line construction helpers for Pb evolution plots."""
from __future__ import annotations

import logging

import numpy as np

from core import app_state
from visualization.line_styles import resolve_line_style
from ..label_layout import position_curve_label
from ..data import _lazy_import_geochemistry
from .overlay_helpers import (
    _format_label_text,
    _label_bbox,
    _register_overlay_artist,
    _register_overlay_curve_label,
    _resolve_label_options,
)
from .plumbotectonics_metadata import get_overlay_default_color

logger = logging.getLogger(__name__)

def _resolve_model_age(pb206, pb207, params):
    """Resolve model age and T1 override from Pb data and model params.

    Returns:
        tuple: (t_model, t1_override) where t_model is age array (Ma)
               and t1_override is T1 in years for calculate_modelcurve.
    """
    geochemistry, _ = _lazy_import_geochemistry()
    t_sk = geochemistry.calculate_two_stage_age(pb206, pb207, params=params)
    t_cdt = geochemistry.calculate_single_stage_age(pb206, pb207, params=params)
    if params.get('Tsec', 0.0) <= 0:
        t_model = t_cdt
        t1_override = params.get('T2', params.get('T1', None))
    else:
        t_model = np.where(np.isfinite(t_sk), t_sk, t_cdt)
        t1_override = params.get('Tsec', None)
    return t_model, t1_override


def _draw_model_age_lines(ax, pb206, pb207, params):
    """Draw model age construction lines for 206/204 vs 207/204."""
    geochemistry, _ = _lazy_import_geochemistry()
    if geochemistry is None:
        return
    try:
        t_model, t1_override = _resolve_model_age(pb206, pb207, params)

        curve = geochemistry.calculate_modelcurve(t_model, params=params, T1=t1_override / 1e6 if t1_override else None)
        x_curve = np.asarray(curve['Pb206_204'])
        y_curve = np.asarray(curve['Pb207_204'])

        max_lines = 200
        idxs = np.arange(len(pb206))
        if len(idxs) > max_lines:
            rng = np.random.RandomState(42)
            idxs = rng.choice(idxs, size=max_lines, replace=False)

        age_style = resolve_line_style(
            app_state,
            'model_age_line',
            {
                'color': None,
                'linewidth': getattr(app_state, 'model_age_line_width', 0.7),
                'linestyle': '-',
                'alpha': 0.7
            }
        )
        line_color = age_style.get('color') or get_overlay_default_color('model_age_line')
        label_opts = _resolve_label_options(
            'model_age_line',
            {
                'label_text': '',
                'label_fontsize': 8,
                'label_background': False,
                'label_bg_color': '#ffffff',
                'label_bg_alpha': 0.85,
                'label_position': 'auto',
            }
        )
        label_text = _format_label_text(label_opts.get('label_text'))
        label_done = False
        for i in idxs:
            if np.isnan(pb206[i]) or np.isnan(pb207[i]) or np.isnan(x_curve[i]) or np.isnan(y_curve[i]):
                continue
            line_kwargs = {
                'linewidth': age_style['linewidth'],
                'linestyle': age_style['linestyle'],
                'alpha': age_style['alpha'],
                'zorder': 1,
                'label': '_nolegend_'
            }
            if line_color is not None:
                line_kwargs['color'] = line_color
            line_artists = ax.plot([x_curve[i], pb206[i]], [y_curve[i], pb207[i]], **line_kwargs)
            for artist in line_artists:
                _register_overlay_artist('model_age_line', artist)
            point_artist = ax.scatter(
                x_curve[i],
                y_curve[i],
                s=10,
                color='#475569',
                alpha=0.6,
                zorder=2,
                label='_nolegend_'
            )
            _register_overlay_artist('model_age_line', point_artist)
            if label_text and not label_done:
                text_artist = ax.text(
                    x_curve[i], y_curve[i],
                    label_text,
                    color=line_color or age_style.get('color') or getattr(app_state, 'label_color', '#1f2937'),
                    fontsize=label_opts['label_fontsize'],
                    va='center',
                    ha='center',
                    alpha=age_style['alpha'],
                    bbox=_label_bbox(label_opts, edgecolor=line_color)
                )
                _register_overlay_curve_label(
                    text_artist,
                    [x_curve[i], pb206[i]],
                    [y_curve[i], pb207[i]],
                    label_text,
                    label_opts.get('label_position', 'auto'),
                    style_key='model_age_line'
                )
                position_curve_label(
                    ax,
                    text_artist,
                    mode='isoage',
                    x_line=[x_curve[i], pb206[i]],
                    y_line=[y_curve[i], pb207[i]],
                    label_text=label_text,
                    position_mode=label_opts.get('label_position', 'auto'),
                )
                label_done = True
    except Exception as err:
        logger.warning("Failed to draw model age lines: %s", err)

def _draw_model_age_lines_86(ax, pb206, pb207, pb208, params):
    """Draw model age construion lines for 206/204 vs 208/204."""
    geochemistry, _ = _lazy_import_geochemistry()
    if geochemistry is None:
        return
    try:
        t_model, t1_override = _resolve_model_age(pb206, pb207, params)

        curve = geochemistry.calculate_modelcurve(t_model, params=params, T1=t1_override / 1e6 if t1_override else None)
        x_curve = np.asarray(curve['Pb206_204'])
        z_curve = np.asarray(curve['Pb208_204'])

        max_lines = 200
        idxs = np.arange(len(pb206))
        if len(idxs) > max_lines:
            rng = np.random.RandomState(42)
            idxs = rng.choice(idxs, size=max_lines, replace=False)

        age_style = resolve_line_style(
            app_state,
            'model_age_line',
            {
                'color': None,
                'linewidth': getattr(app_state, 'model_age_line_width', 0.7),
                'linestyle': '-',
                'alpha': 0.7
            }
        )
        line_color = age_style.get('color') or get_overlay_default_color('model_age_line')
        label_opts = _resolve_label_options(
            'model_age_line',
            {
                'label_text': '',
                'label_fontsize': 8,
                'label_background': False,
                'label_bg_color': '#ffffff',
                'label_bg_alpha': 0.85,
                'label_position': 'auto',
            }
        )
        label_text = _format_label_text(label_opts.get('label_text'))
        label_done = False
        for i in idxs:
            if np.isnan(pb206[i]) or np.isnan(pb208[i]) or np.isnan(x_curve[i]) or np.isnan(z_curve[i]):
                continue
            line_kwargs = {
                'linewidth': age_style['linewidth'],
                'linestyle': age_style['linestyle'],
                'alpha': age_style['alpha'],
                'zorder': 1,
                'label': '_nolegend_'
            }
            if line_color is not None:
                line_kwargs['color'] = line_color
            line_artists = ax.plot([x_curve[i], pb206[i]], [z_curve[i], pb208[i]], **line_kwargs)
            for artist in line_artists:
                _register_overlay_artist('model_age_line', artist)
            point_artist = ax.scatter(
                x_curve[i],
                z_curve[i],
                s=10,
                color='#475569',
                alpha=0.6,
                zorder=2,
                label='_nolegend_'
            )
            _register_overlay_artist('model_age_line', point_artist)
            if label_text and not label_done:
                text_artist = ax.text(
                    x_curve[i], z_curve[i],
                    label_text,
                    color=line_color or age_style.get('color') or getattr(app_state, 'label_color', '#1f2937'),
                    fontsize=label_opts['label_fontsize'],
                    va='center',
                    ha='center',
                    alpha=age_style['alpha'],
                    bbox=_label_bbox(label_opts, edgecolor=line_color)
                )
                _register_overlay_curve_label(
                    text_artist,
                    [x_curve[i], pb206[i]],
                    [z_curve[i], pb208[i]],
                    label_text,
                    label_opts.get('label_position', 'auto'),
                    style_key='model_age_line'
                )
                position_curve_label(
                    ax,
                    text_artist,
                    mode='isoage',
                    x_line=[x_curve[i], pb206[i]],
                    y_line=[z_curve[i], pb208[i]],
                    label_text=label_text,
                    position_mode=label_opts.get('label_position', 'auto'),
                )
                label_done = True
    except Exception as err:
        logger.warning("Failed to draw model age lines (206-208): %s", err)

