"""Plumbotectonics same-age line rendering helpers."""
from __future__ import annotations

import numpy as np

from core import app_state, state_gateway
from visualization.line_styles import resolve_line_style

from ..label_layout import position_curve_label
from .overlay_common import (
    _format_label_text,
    _label_bbox,
    _register_overlay_artist,
    _resolve_label_options,
)
from .plumbotectonics_metadata import (
    _load_plumbotectonics_data,
    _select_plumbotectonics_section,
    get_overlay_default_color,
)


def _draw_plumbotectonics_isoage_lines(ax, actual_algorithm):
    """Draw same-age connection lines (paleoisochrons) for Plumbotectonics."""
    sections = _load_plumbotectonics_data()
    section = _select_plumbotectonics_section(sections)
    if not section:
        return

    y_key = 'pb207' if str(actual_algorithm).endswith('_76') else 'pb208'
    groups = [g for g in section.get('groups', []) if g.get('pb206') and g.get(y_key)]
    if not groups:
        return

    lengths = []
    for group in groups:
        lengths.append(len(group.get('t', [])))
        lengths.append(len(group.get('pb206', [])))
        lengths.append(len(group.get(y_key, [])))
    n_points = min(lengths) if lengths else 0
    if n_points < 2:
        return

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

    state_gateway.set_attr('plumbotectonics_isoage_label_data', [])

    for idx in range(n_points):
        pts = []
        t_val = None
        for group in groups:
            try:
                t_val = float(group.get('t', [])[idx])
                x_val = float(group.get('pb206', [])[idx])
                y_val = float(group.get(y_key, [])[idx])
            except (TypeError, ValueError, IndexError):
                continue
            if not (np.isfinite(t_val) and np.isfinite(x_val) and np.isfinite(y_val)):
                continue
            pts.append((x_val, y_val))

        if len(pts) < 2:
            continue

        pts.sort(key=lambda p: p[0])
        x_line = [p[0] for p in pts]
        y_line = [p[1] for p in pts]
        line_kwargs = {
            'linestyle': paleo_style['linestyle'],
            'linewidth': paleo_style['linewidth'],
            'alpha': paleo_style['alpha'],
            'zorder': 1.05,
            'label': '_nolegend_'
        }
        if line_color is not None:
            line_kwargs['color'] = line_color
        line_artists = ax.plot(x_line, y_line, **line_kwargs)
        for artist in line_artists:
            _register_overlay_artist('paleoisochron', artist)

        if t_val is not None and len(x_line) >= 2:
            label_text = _format_label_text(label_opts.get('label_text'), t_val * 1000.0)
            if not label_text:
                label_text = f" {t_val * 1000.0:.0f} Ma"
            text_artist = ax.text(
                x_line[0], y_line[0],
                label_text,
                color=line_color or paleo_style.get('color') or getattr(app_state, 'label_color', '#1f2937'),
                fontsize=label_opts['label_fontsize'],
                va='center',
                ha='left',
                alpha=paleo_style['alpha'],
                bbox=_label_bbox(label_opts, edgecolor=line_color)
            )
            app_state.plumbotectonics_isoage_label_data.append({
                'text': text_artist,
                'x_line': x_line,
                'y_line': y_line,
                'age': t_val * 1000.0,
                'label_text': label_text,
                'position': label_opts.get('label_position', 'auto'),
                'style_key': 'paleoisochron',
            })
            position_curve_label(
                ax,
                text_artist,
                mode='isoage',
                x_line=x_line,
                y_line=y_line,
                age_ma=t_val * 1000.0,
                label_text=label_text,
                position_mode=label_opts.get('label_position', 'auto'),
            )