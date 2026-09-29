"""Wheel zoom and middle-drag pan maths.

Pure helpers so the interaction can be unit-tested without Qt: a zoom keeps the point under
the cursor fixed, a pan translates the current window. Cartesian views zoom and pan in data
space (x, y); a ternary view zooms and pans its *view window* - the region that is drawn and the
range the tick labels report together, because the magnifier is meant to make the points grow on
screen. The outline then takes the window's shape, which is the accepted trade-off of zooming; the
untouched default view still draws the full equilateral triangle (see visualization/plotting/ternary.py).
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: One wheel notch changes the visible span by this factor.
WHEEL_STEP = 0.85
#: A window never collapses below this span, so the view cannot become degenerate.
MIN_SPAN = 1e-3


def zoom_pair(low: float, high: float, factor: float, anchor: float) -> tuple[float, float]:
    """Scale ``(low, high)`` by *factor* while keeping *anchor* in place."""
    return anchor - (anchor - low) * factor, anchor + (high - anchor) * factor


def wheel_factor(delta: int, step: float = WHEEL_STEP) -> float:
    """Zoom factor for a wheel notch: up zooms in, down zooms out."""
    if delta == 0:
        return 1.0
    return step if delta > 0 else 1.0 / step


def zoom_cartesian(axes: Any, factor: float, x: float, y: float) -> None:
    """Zoom *axes* about the data point ``(x, y)``."""
    x0, x1 = axes.get_xlim()
    y0, y1 = axes.get_ylim()
    axes.set_xlim(*zoom_pair(x0, x1, factor, x))
    axes.set_ylim(*zoom_pair(y0, y1, factor, y))


def pan_cartesian(axes: Any, dx: float, dy: float) -> None:
    """Translate *axes* by ``(dx, dy)`` in data units."""
    x0, x1 = axes.get_xlim()
    y0, y1 = axes.get_ylim()
    axes.set_xlim(x0 + dx, x1 + dx)
    axes.set_ylim(y0 + dy, y1 + dy)


def _clamp_window(low: float, high: float) -> tuple[float, float]:
    """Keep a window inside [0, 1] with at least MIN_SPAN width."""
    span = max(high - low, MIN_SPAN)
    span = min(span, 1.0)
    low = min(max(low, 0.0), 1.0 - span)
    return low, low + span


def _window_pairs(window) -> tuple[tuple[float, float], ...]:
    """The three (low, high) spans of a six-value window."""
    values = [float(value) for value in window]
    return tuple((values[index], values[index + 1]) for index in range(0, 6, 2))


def zoom_ternary(axes: Any, factor: float, t: float, l: float, r: float) -> tuple[float, ...]:
    """Zoom a ternary view about the point ``(t, l, r)``; returns the new six limits.

    The window is measured on what is currently drawn and then applied to the drawing as well as to
    the labels, so an explicit zoom really magnifies: the points grow on screen and the numbers
    follow the picture.  Repeated notches compose, because the next call reads the drawn window
    back.
    """
    limits: list[float] = []
    for anchor, (low, high) in zip((t, l, r), _window_pairs(_view_window(axes))):
        new_low, new_high = zoom_pair(low, high, factor, anchor)
        limits.extend(_clamp_window(new_low, new_high))
    return _apply_view_window(axes, limits) or tuple(limits)


def pan_ternary(axes: Any, shift: float) -> tuple[float, ...]:
    """Shift a ternary view by *shift* component units (uniform, clamped to [0, 1]).

    Like the zoom this moves the region that is drawn, and the labels move with it; the window that
    was applied is returned so the callers can persist it.
    """
    limits: list[float] = []
    for low, high in _window_pairs(_view_window(axes)):
        limits.extend(_clamp_window(low + shift, high + shift))
    return _apply_view_window(axes, limits) or tuple(limits)


def _view_window(axes: Any) -> tuple[float, ...]:
    """The window the ternary view currently shows: what is drawn, else what the labels report."""
    try:
        from visualization.plotting.ternary import ternary_axes_limits, ternary_label_window

        window = ternary_axes_limits(axes)
        if window is not None:
            return window
        return ternary_label_window(axes)
    except Exception as err:  # pragma: no cover - import or attribute trouble only
        logger.warning("Could not read the ternary view window: %s", err)
        return (0.0, 1.0, 0.0, 1.0, 0.0, 1.0)


def _apply_view_window(axes: Any, window) -> tuple[float, ...] | None:
    """Draw the ternary window and relabel the ticks; the drawing and the labels move together."""
    try:
        from visualization.plotting.ternary import apply_ternary_zoom_window

        return apply_ternary_zoom_window(axes, window)
    except Exception as err:  # pragma: no cover - cosmetic, never break the zoom
        logger.warning("Could not apply the ternary zoom window: %s", err)
        return None


def is_ternary_axes(axes: Any) -> bool:
    """True for mpltern axes, which have their own limit API."""
    return axes is not None and hasattr(axes, "set_ternary_lim")
