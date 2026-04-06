"""Plumbotectonics model curve rendering helpers."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from core import app_state
from visualization.line_styles import ensure_line_style, resolve_line_style

from ..label_layout import position_curve_label
from .overlay_common import (
    _format_label_text,
    _label_bbox,
    _register_overlay_artist,
    _register_overlay_curve_label,
    _resolve_label_options,
)
from .plumbotectonics_metadata import (
    _load_plumbotectonics_data,
    _plumbotectonics_group_visible,
    _plumbotectonics_marker,
    _select_plumbotectonics_section,
    get_plumbotectonics_group_entries,
    get_plumbotectonics_group_palette,
)

logger = logging.getLogger(__name__)


def _fit_plumbotectonics_curve(
    x_vals: Any,
    y_vals: Any,
    n_points: int = 200,
) -> tuple[np.ndarray, np.ndarray]:
    x_arr = np.asarray(x_vals, dtype=float)
    y_arr = np.asarray(y_vals, dtype=float)
    valid = np.isfinite(x_arr) & np.isfinite(y_arr)
    x_arr = x_arr[valid]
    y_arr = y_arr[valid]
    if x_arr.size < 2:
        return x_arr, y_arr

    order = np.argsort(x_arr)
    x_sorted = x_arr[order]
    y_sorted = y_arr[order]

    unique_x, inv = np.unique(x_sorted, return_inverse=True)
    if unique_x.size < 2:
        return unique_x, y_sorted[:unique_x.size]
    y_accum = np.zeros_like(unique_x, dtype=float)
    counts = np.zeros_like(unique_x, dtype=float)
    for idx, group_idx in enumerate(inv):
        y_accum[group_idx] += y_sorted[idx]
        counts[group_idx] += 1
    y_unique = np.divide(y_accum, counts, out=np.zeros_like(y_accum), where=counts > 0)

    x_min = float(unique_x.min())
    x_max = float(unique_x.max())
    if not np.isfinite(x_min) or not np.isfinite(x_max) or x_min == x_max:
        return unique_x, y_unique

    x_fit = np.linspace(x_min, x_max, int(n_points))
    try:
        from scipy.interpolate import PchipInterpolator
        y_fit = PchipInterpolator(unique_x, y_unique)(x_fit)
    except Exception:
        y_fit = np.interp(x_fit, unique_x, y_unique)
    return x_fit, y_fit


def _draw_plumbotectonics_curves(ax: Any, actual_algorithm: str) -> None:
    """Draw Plumbotectonics model curves using fitted data points."""
    sections = _load_plumbotectonics_data()
    section = _select_plumbotectonics_section(sections)
    if not section:
        return

    y_key = 'pb207' if str(actual_algorithm).endswith('_76') else 'pb208'

    base_style = resolve_line_style(
        app_state,
        'plumbotectonics_curve',
        {
            'color': None,
            'linewidth': getattr(app_state, 'plumbotectonics_curve_width', 1.2),
            'linestyle': '-',
            'alpha': 0.85
        }
    )
    base_label_opts = _resolve_label_options(
        'plumbotectonics_curve',
        {
            'label_text': '',
            'label_fontsize': 9,
            'label_background': False,
            'label_bg_color': '#ffffff',
            'label_bg_alpha': 0.85,
            'label_position': 'auto',
        }
    )

    variant_label = section.get('label')
    if variant_label:
        logger.info("Plumbotectonics model variant: %s", variant_label)

    group_entries = get_plumbotectonics_group_entries(section=section)
    group_palette = get_plumbotectonics_group_palette(section=section)
    for group, meta in zip(section.get('groups', []), group_entries):
        name = meta['name']
        x_vals = group.get('pb206', [])
        y_vals = group.get(y_key, [])
        x_fit, y_fit = _fit_plumbotectonics_curve(x_vals, y_vals)
        if len(x_fit) < 2:
            continue
        style_key = meta['style_key']
        style = ensure_line_style(app_state, style_key, dict(base_style))
        color = style.get('color') or base_style.get('color') or group_palette.get(style_key)
        marker = _plumbotectonics_marker(name)
        label_opts = _resolve_label_options(style_key, dict(base_label_opts))
        line_kwargs = {
            'linewidth': style['linewidth'],
            'linestyle': style['linestyle'],
            'alpha': style['alpha'],
            'zorder': 1.2,
            'label': '_nolegend_',
        }
        if color is not None:
            line_kwargs['color'] = color
        line_artists = ax.plot(x_fit, y_fit, **line_kwargs)
        line_color = color
        if line_color is None and line_artists:
            try:
                line_color = line_artists[0].get_color()
            except Exception:
                line_color = None
        is_visible = _plumbotectonics_group_visible(style_key)
        for artist in line_artists:
            _register_overlay_artist(style_key, artist)
            if not is_visible:
                try:
                    artist.set_visible(False)
                except Exception:
                    pass
        point_kwargs = {
            'linestyle': 'None',
            'marker': marker,
            'markersize': 4.5,
            'alpha': min(style['alpha'] + 0.1, 1.0),
            'zorder': 1.3,
            'label': '_nolegend_',
        }
        if line_color is not None:
            point_kwargs['color'] = line_color
        point_artists = ax.plot(x_vals, y_vals, **point_kwargs)
        for artist in point_artists:
            _register_overlay_artist(style_key, artist)
            if not is_visible:
                try:
                    artist.set_visible(False)
                except Exception:
                    pass

        label_text = _format_label_text(label_opts.get('label_text'), name=name)
        if label_text:
            text_artist = ax.text(
                x_fit[0], y_fit[0],
                label_text,
                color=line_color or color or getattr(app_state, 'label_color', '#1f2937'),
                fontsize=label_opts['label_fontsize'],
                va='center',
                ha='center',
                alpha=style['alpha'],
                bbox=_label_bbox(label_opts, edgecolor=line_color or color)
            )
            _register_overlay_curve_label(
                text_artist,
                x_fit,
                y_fit,
                label_text,
                label_opts.get('label_position', 'auto'),
                style_key=style_key
            )
            if not is_visible:
                try:
                    text_artist.set_visible(False)
                except Exception:
                    pass
            position_curve_label(
                ax,
                text_artist,
                mode='isoage',
                x_line=x_fit,
                y_line=y_fit,
                label_text=label_text,
                position_mode=label_opts.get('label_position', 'auto'),
            )