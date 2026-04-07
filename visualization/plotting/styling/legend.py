"""Legend layout and styling helpers for plotting."""
from __future__ import annotations

from typing import Any, Sequence

from core import app_state


_LEGEND_OFFSET_EPSILON = 1e-12


def _is_zero_offset(value: float, floor: float = _LEGEND_OFFSET_EPSILON) -> bool:
    """Return True when legend offset component is effectively zero."""
    return abs(float(value)) <= float(floor)


def _legend_layout_config(
    ax: Any | None = None,
    show_marginal_kde: bool = False,
    location_key: str | None = None,
) -> tuple[Any, tuple[float, float] | None, None, None]:
    """Resolve in-plot legend location, bbox, and layout options."""
    loc = location_key if location_key else getattr(app_state, 'legend_position', None)
    if not loc:
        return 'best', None, None, None
    if isinstance(loc, str) and loc.startswith('outside_'):
        return 'best', None, None, None
    offsets = getattr(app_state, 'legend_offset', (0.0, 0.0)) or (0.0, 0.0)
    try:
        dx, dy = float(offsets[0]), float(offsets[1])
    except Exception:
        dx, dy = 0.0, 0.0
    if _is_zero_offset(dx) and _is_zero_offset(dy):
        return loc, None, None, None

    anchor_map = {
        'upper left': (0.0, 1.0),
        'upper center': (0.5, 1.0),
        'upper right': (1.0, 1.0),
        'center left': (0.0, 0.5),
        'center': (0.5, 0.5),
        'center right': (1.0, 0.5),
        'lower left': (0.0, 0.0),
        'lower center': (0.5, 0.0),
        'lower right': (1.0, 0.0),
    }
    base = anchor_map.get(loc)
    if base is None:
        return loc, None, None, None
    bbox = (base[0] + dx, base[1] + dy)
    return loc, bbox, None, None


def _legend_columns_for_layout(
    labels: Sequence[Any] | None,
    ax: Any,
    location_key: str | None,
) -> int | None:
    """Compute legend columns for auto layouts."""
    if not labels:
        return 1
    if location_key in {'outside_left', 'outside_right'}:
        return 1
    return None


def _style_legend(
    legend: Any,
    show_marginal_kde: bool = False,
    location_key: str | None = None,
) -> None:
    """Apply legend styling from app_state."""
    if legend is None:
        return
    legend_ax = getattr(app_state, 'legend_ax', None)
    if legend_ax is None or legend.axes is not legend_ax:
        loc, bbox, _mode, _pad = _legend_layout_config(
            show_marginal_kde=show_marginal_kde,
            location_key=location_key,
        )
        try:
            legend.set_loc(loc)
        except Exception:
            pass
        if bbox:
            try:
                legend.set_bbox_to_anchor(bbox, transform=legend.axes.transAxes)
            except Exception:
                pass

    frame_on = bool(getattr(app_state, 'legend_frame_on', True))
    legend.set_frame_on(frame_on)
    frame = legend.get_frame()
    if frame_on:
        try:
            frame.set_facecolor(getattr(app_state, 'legend_frame_facecolor', '#ffffff'))
            frame.set_edgecolor(getattr(app_state, 'legend_frame_edgecolor', '#cbd5f5'))
            frame.set_alpha(float(getattr(app_state, 'legend_frame_alpha', 0.95)))
        except Exception:
            pass

    legend_size = getattr(app_state, 'plot_font_sizes', {}).get('legend', 10)
    text_color = getattr(app_state, 'label_color', '#1f2937')
    for text in legend.get_texts():
        try:
            text.set_fontsize(legend_size)
            text.set_color(text_color)
        except Exception:
            pass
    try:
        title = legend.get_title()
        title.set_fontsize(getattr(app_state, 'plot_font_sizes', {}).get('label', 12))
        title.set_color(text_color)
        title.set_fontweight(getattr(app_state, 'label_weight', 'normal'))
    except Exception:
        pass
