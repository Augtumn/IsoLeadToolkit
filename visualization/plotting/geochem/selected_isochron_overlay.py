"""Selected isochron highlight rendering helpers."""
from __future__ import annotations

import logging
from typing import Any

from visualization.line_styles import resolve_line_style

from core import app_state
from .isochron_labels import _build_isochron_label
from .overlay_helpers import (
    _format_label_text,
    _label_bbox,
    _register_overlay_artist,
    _resolve_label_options,
)

logger = logging.getLogger(__name__)

def _draw_selected_isochron(ax: Any) -> None:
    """Draw isochron line for box-selected data points."""
    try:
        # Check if we have selected isochron data
        if app_state.selected_isochron_data is None:
            return

        data = app_state.selected_isochron_data
        x_range = data['x_range']
        y_range = data['y_range']

        # 统一使用 isochron 样式
        fallback_style = {
            'color': '#ef4444',
            'linewidth': 2.0,
            'linestyle': '-',
            'alpha': 0.9
        }
        line_style = resolve_line_style(app_state, 'selected_isochron', fallback_style)
        # 选中等时线用稍粗的线
        draw_width = line_style['linewidth'] * 1.3

        line_artists = ax.plot(
            x_range,
            y_range,
            color=line_style['color'] or '#ef4444',
            linewidth=draw_width,
            linestyle=line_style['linestyle'],
            alpha=line_style['alpha'],
            zorder=100,
            label='_nolegend_'
        )
        for artist in line_artists:
            _register_overlay_artist('selected_isochron', artist)

        label_opts = _resolve_label_options(
            'isochron',
            {
                'label_text': '',
                'label_fontsize': 10,
                'label_background': True,
                'label_bg_color': '#ffffff',
                'label_bg_alpha': 0.9,
                'label_position': 'auto',
            }
        )
        label_text = _build_isochron_label(data)
        age_val = data.get('age')
        if age_val is None:
            age_val = data.get('age_ma')
        label_override = _format_label_text(label_opts.get('label_text'), age_val)
        if label_override:
            label_text = label_override
        if label_text:
            x_mid = (x_range[0] + x_range[1]) / 2
            y_mid = (y_range[0] + y_range[1]) / 2
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            y_offset = (ylim[1] - ylim[0]) * 0.02

            ax.text(
                x_mid,
                y_mid + y_offset,
                label_text,
                color=line_style['color'] or '#ef4444',
                fontsize=label_opts['label_fontsize'],
                fontweight='bold',
                ha='center',
                va='bottom',
                bbox=_label_bbox(label_opts, edgecolor=line_style['color'] or '#ef4444')
                or dict(
                    boxstyle='round,pad=0.4',
                    facecolor='white',
                    edgecolor=line_style['color'] or '#ef4444',
                    alpha=0.9,
                    linewidth=1.5
                ),
                zorder=101
            )

    except Exception as err:
        logger.warning("Failed to draw selected isochron: %s", err)


