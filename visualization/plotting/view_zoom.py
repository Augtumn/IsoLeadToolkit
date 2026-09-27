"""Wheel zoom and middle-drag pan maths.

Pure helpers so the interaction can be unit-tested without Qt: a zoom keeps the point under
the cursor fixed, a pan translates the current window. Ternary views zoom and pan in
component space (t, l, r), Cartesian views in data space (x, y).
"""
from __future__ import annotations

from typing import Any

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


def zoom_ternary(axes: Any, factor: float, t: float, l: float, r: float) -> tuple[float, ...]:
    """Zoom a ternary view about the point ``(t, l, r)``; returns the new six limits."""
    limits: list[float] = []
    for anchor, (low, high) in zip((t, l, r), (axes.get_tlim(), axes.get_llim(), axes.get_rlim())):
        new_low, new_high = zoom_pair(low, high, factor, anchor)
        limits.extend(_clamp_window(new_low, new_high))
    axes.set_ternary_lim(*limits)
    return tuple(limits)


def pan_ternary(axes: Any, shift: float) -> tuple[float, ...]:
    """Shift a ternary view by *shift* component units (uniform, clamped to [0, 1])."""
    limits: list[float] = []
    for low, high in (axes.get_tlim(), axes.get_llim(), axes.get_rlim()):
        limits.extend(_clamp_window(low + shift, high + shift))
    axes.set_ternary_lim(*limits)
    return tuple(limits)


def is_ternary_axes(axes: Any) -> bool:
    """True for mpltern axes, which have their own limit API."""
    return axes is not None and hasattr(axes, "set_ternary_lim")
