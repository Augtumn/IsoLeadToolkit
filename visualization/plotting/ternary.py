"""Ternary plot helpers."""
from __future__ import annotations

import logging
from typing import Any, Iterable

import numpy as np

from core import app_state, state_gateway

logger = logging.getLogger(__name__)
_FULL_TERNARY_LIMITS = (0.0, 1.0, 0.0, 1.0, 0.0, 1.0)
_VALID_LIMIT_MODES = {'min', 'max', 'both'}
_TERNARY_SQRT3 = 3.0 ** 0.5
_TERNARY_LIMIT_EPSILON = 1e-9
_TERNARY_RENDER_MARGIN = 0.002


def _coerce_nonnegative(values: Iterable[float]) -> np.ndarray:
    """Convert values to finite, non-negative float arrays."""
    arr = np.asarray(values, dtype=float)
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    return np.maximum(arr, 0.0)


def resolve_ternary_limit_mode(mode: Any = None) -> str:
    """Resolve ternary limit mode from explicit value or app state fallback."""
    candidate = mode
    if candidate is None:
        candidate = app_state.ternary_limit_mode

    token = str(candidate).strip().lower() if candidate is not None else ''
    if token in _VALID_LIMIT_MODES:
        return token

    anchor = str(app_state.ternary_limit_anchor).strip().lower()
    if anchor in ('min', 'max'):
        return anchor
    return 'min'


def _sanitize_limit_value(value: Any, default: float) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = float(default)
    return min(1.0, max(0.0, v))


def _resolve_manual_limits() -> tuple[float, float, float, float, float, float]:
    manual = app_state.ternary_manual_limits or {}

    tmin = _sanitize_limit_value(manual.get('tmin', 0.0), 0.0)
    tmax = _sanitize_limit_value(manual.get('tmax', 1.0), 1.0)
    lmin = _sanitize_limit_value(manual.get('lmin', 0.0), 0.0)
    lmax = _sanitize_limit_value(manual.get('lmax', 1.0), 1.0)
    rmin = _sanitize_limit_value(manual.get('rmin', 0.0), 0.0)
    rmax = _sanitize_limit_value(manual.get('rmax', 1.0), 1.0)

    if tmin > tmax:
        tmin, tmax = tmax, tmin
    if lmin > lmax:
        lmin, lmax = lmax, lmin
    if rmin > rmax:
        rmin, rmax = rmax, rmin

    return tmin, tmax, lmin, lmax, rmin, rmax


def normalize_ternary_components(
    t_vals: Iterable[float],
    l_vals: Iterable[float],
    r_vals: Iterable[float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Normalize ternary components so each triplet sums to 1."""
    t_arr = _coerce_nonnegative(t_vals)
    l_arr = _coerce_nonnegative(l_vals)
    r_arr = _coerce_nonnegative(r_vals)

    sums = t_arr + l_arr + r_arr
    valid = np.isfinite(sums) & (sums > 0)
    safe_sums = np.where(valid, sums, 1.0)

    t_norm = t_arr / safe_sums
    l_norm = l_arr / safe_sums
    r_norm = r_arr / safe_sums

    if np.any(~valid):
        t_norm[~valid] = 1.0 / 3.0
        l_norm[~valid] = 1.0 / 3.0
        r_norm[~valid] = 1.0 / 3.0

    return t_norm, l_norm, r_norm


def prepare_ternary_components(
    t_vals: Iterable[float],
    l_vals: Iterable[float],
    r_vals: Iterable[float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Normalize ternary components by sum only (no stretch)."""
    return normalize_ternary_components(t_vals, l_vals, r_vals)


def infer_ternary_limits(
    t_vals: Iterable[float],
    l_vals: Iterable[float],
    r_vals: Iterable[float],
) -> tuple[float, float, float, float, float, float]:
    """Infer ternary data limits from component ranges."""
    t_arr, l_arr, r_arr = normalize_ternary_components(t_vals, l_vals, r_vals)
    if t_arr.size == 0 or l_arr.size == 0 or r_arr.size == 0:
        return _FULL_TERNARY_LIMITS

    tmin = float(np.nanmin(t_arr))
    tmax = float(np.nanmax(t_arr))
    lmin = float(np.nanmin(l_arr))
    lmax = float(np.nanmax(l_arr))
    rmin = float(np.nanmin(r_arr))
    rmax = float(np.nanmax(r_arr))

    return tmin, tmax, lmin, lmax, rmin, rmax


#: mpltern's Cartesian positions of the three vertices (measured from mpltern).
_TERNARY_APEX_XY = (0.0, 1.0)
_TERNARY_LEFT_XY = (-1.0 / _TERNARY_SQRT3, 0.0)
_TERNARY_RIGHT_XY = (1.0 / _TERNARY_SQRT3, 0.0)


def cartesian_to_ternary(x: float, y: float) -> tuple[float, float, float]:
    """Convert mpltern Cartesian data coordinates to (top, left, right) components."""
    t = float(y)
    r = ((1.0 - t) + _TERNARY_SQRT3 * float(x)) / 2.0
    l = (1.0 - t) - r
    return t, l, r


def ternary_to_cartesian(t: float, l: float, r: float) -> tuple[float, float]:
    """Inverse of :func:`cartesian_to_ternary`: mpltern Cartesian coordinates for a composition."""
    return _TERNARY_SQRT3 * (float(r) - float(l)) / 3.0, float(t)


def _ray_exit_scale(anchor_x: float, anchor_y: float, dir_x: float, dir_y: float) -> float:
    """How far (in units of the direction vector) the ray stays inside the triangle."""
    candidates: list[float] = []
    if dir_y < 0.0:
        candidates.append(-anchor_y / dir_y)                     # y >= 0
    if dir_y > 0.0:
        candidates.append((1.0 - anchor_y) / dir_y)              # y <= 1
    upper = _TERNARY_SQRT3 * dir_x + dir_y
    if upper > 0.0:
        candidates.append(
            (1.0 - (_TERNARY_SQRT3 * anchor_x + anchor_y)) / upper  # sqrt3 x + y <= 1
        )
    lower = -_TERNARY_SQRT3 * dir_x + dir_y
    if lower > 0.0:
        candidates.append(
            (1.0 - (-_TERNARY_SQRT3 * anchor_x + anchor_y)) / lower  # -sqrt3 x + y <= 1
        )
    positive = [value for value in candidates if value > 0.0]
    if not positive:
        return float("inf")
    return min(positive)


def similar_subtriangle_limits(
    anchor_x: float, anchor_y: float, drag_x: float, drag_y: float
) -> tuple[float, float, float, float, float, float]:
    """Ternary limits for the sub-triangle similar to the full one.

    The press point is the homothety centre; the release point ends up on the
    boundary of the resulting triangle. Dragging beyond the triangle (or not at
    all) returns the full-view limits, which callers treat as a zoom reset.
    """
    dir_x = float(drag_x) - float(anchor_x)
    dir_y = float(drag_y) - float(anchor_y)
    if abs(dir_x) < _TERNARY_LIMIT_EPSILON and abs(dir_y) < _TERNARY_LIMIT_EPSILON:
        return _FULL_TERNARY_LIMITS

    exit_scale = _ray_exit_scale(float(anchor_x), float(anchor_y), dir_x, dir_y)
    if not (exit_scale > 1.0):
        # The drag leaves the parent triangle: nothing to zoom into.
        return _FULL_TERNARY_LIMITS

    ratio = 1.0 / exit_scale
    corners = (_TERNARY_APEX_XY, _TERNARY_LEFT_XY, _TERNARY_RIGHT_XY)
    components = [
        cartesian_to_ternary(
            float(anchor_x) + ratio * (corner[0] - float(anchor_x)),
            float(anchor_y) + ratio * (corner[1] - float(anchor_y)),
        )
        for corner in corners
    ]
    limits: list[float] = []
    for values in zip(*components):
        low = max(0.0, min(1.0, min(values)))
        high = max(0.0, min(1.0, max(values)))
        if high - low < _TERNARY_LIMIT_EPSILON:
            high = min(1.0, low + _TERNARY_LIMIT_EPSILON)
            low = max(0.0, high - _TERNARY_LIMIT_EPSILON)
        limits.extend((low, high))
    return tuple(limits)  # type: ignore[return-value]


def ternary_limits_cover_full_view(
    limits: tuple[float, float, float, float, float, float], tolerance: float = 0.02
) -> bool:
    """True when *limits* are (nearly) the whole triangle - i.e. a zoom reset."""
    tmin, tmax, lmin, lmax, rmin, rmax = limits
    return (
        tmin <= tolerance
        and lmin <= tolerance
        and rmin <= tolerance
        and tmax >= 1.0 - tolerance
        and lmax >= 1.0 - tolerance
        and rmax >= 1.0 - tolerance
    )


#: A magnifier drag shorter than this fraction of the view is a click, not a zoom gesture.
_TERNARY_DRAG_MIN_FRACTION = 0.02


def _unfold_point(window, x: float, y: float) -> tuple[float, float]:
    """A Cartesian point expressed inside *window*: the window's own region becomes the triangle.

    The magnification a zoom asks for has to be measured against what the reader sees, not against
    the whole triangle, so the current window is undone first.  For the similar sub-triangle a drag
    produces, this is exact: the sub-triangle's three component spans are equal, so ``t + l + r``
    stays 1 and the unfolded point is a real composition again.
    """
    t, l, r = cartesian_to_ternary(x, y)
    tmin, tmax, lmin, lmax, rmin, rmax = (float(value) for value in window)
    t_span, l_span, r_span = tmax - tmin, lmax - lmin, rmax - rmin
    if min(t_span, l_span, r_span) <= 0.0:
        return float(x), float(y)
    return ternary_to_cartesian(
        (t - tmin) / t_span, (l - lmin) / l_span, (r - rmin) / r_span
    )


def _collapse_window(window, limits) -> tuple[float, ...]:
    """Map limits measured inside *window* back onto the components."""
    tmin, _, lmin, _, rmin, _ = (float(value) for value in window)
    spans = (
        float(window[1]) - float(window[0]),
        float(window[3]) - float(window[2]),
        float(window[5]) - float(window[4]),
    )
    lows = (tmin, lmin, rmin)
    collapsed: list[float] = []
    for index, (low, high) in enumerate(zip(limits[0::2], limits[1::2])):
        collapsed.extend(
            (
                lows[index] + float(low) * spans[index],
                lows[index] + float(high) * spans[index],
            )
        )
    return tuple(collapsed)


def drag_ternary_window(
    window,
    anchor_xy: tuple[float, float],
    drag_xy: tuple[float, float],
    min_fraction: float = _TERNARY_DRAG_MIN_FRACTION,
) -> tuple[float, ...] | None:
    """The window a magnifier drag asks for, measured inside *window*; None for a click.

    The drag is a sub-triangle of what the reader sees rather than of the whole triangle: the press
    and the release are mapped into *window* first, so a second drag composes with the first
    instead of jumping back to a region of the full triangle.  A drag that leaves the window asks
    for all of it again and the *full* limits come back, which the callers read as the reset
    gesture - still reachable while zoomed, because the drawn window fills the axes and the canvas
    margin around it maps outside.  A drag too short to be a gesture returns None, so a plain click
    never discards the current zoom.
    """
    start = _unfold_point(window, *anchor_xy)
    end = _unfold_point(window, *drag_xy)
    if float(np.hypot(end[0] - start[0], end[1] - start[1])) < float(min_fraction):
        return None
    limits = similar_subtriangle_limits(start[0], start[1], end[0], end[1])
    if ternary_limits_cover_full_view(limits):
        return _FULL_TERNARY_LIMITS
    return _collapse_window(window, limits)


def use_ternary_layout(fig: Any) -> None:
    """Let the ternary axes lay itself out.

    mpltern draws the triangle itself and reports a degenerate box to the layout
    engine, which is what makes constrained_layout warn that the axes collapsed to
    zero. Ternary figures therefore run without a layout engine; the 2D render path
    restores it when it takes over the figure again.
    """
    if fig is None:
        return
    if fig.get_layout_engine() is not None:
        fig.set_layout_engine("none")


def effective_ternary_limits(limits, mode: str | None = None) -> tuple:
    """The range actually drawn, given the limit mode.

    mpltern's modes matter here: with 'min' only set_ternary_min is called, so the axes keep their
    upper bound at 1 - ticks placed across the inferred range then covered a sliver of each edge
    instead of the edge itself, which is what "the ticks should span the axis" was about.
    """
    if limits is None or len(limits) != 6:
        return limits
    resolved = resolve_ternary_limit_mode(mode)
    tmin, tmax, lmin, lmax, rmin, rmax = (float(v) for v in limits)
    if resolved == "min":
        return (tmin, 1.0, lmin, 1.0, rmin, 1.0)
    if resolved == "max":
        return (0.0, tmax, 0.0, lmax, 0.0, rmax)
    return (tmin, tmax, lmin, lmax, rmin, rmax)


def _with_render_margin(limits) -> tuple[float, float, float, float, float, float]:
    """Grow a range by the render margin, so the labels do not stop just short of the data."""
    margin = float(app_state.ternary_render_margin)
    tmin, tmax, lmin, lmax, rmin, rmax = (float(value) for value in limits)
    return (
        max(0.0, tmin - margin), min(1.0, tmax + margin),
        max(0.0, lmin - margin), min(1.0, lmax + margin),
        max(0.0, rmin - margin), min(1.0, rmax + margin),
    )


def manual_ternary_label_range(mode: str | None = None) -> tuple[float, ...]:
    """The user's manual window, as the range the tick labels report."""
    return effective_ternary_limits(_with_render_margin(_resolve_manual_limits()), mode)


def infer_ternary_label_range(t_vals, l_vals, r_vals, mode: str | None = None) -> tuple[float, ...]:
    """The window the data implies, as the range the tick labels report."""
    return effective_ternary_limits(
        _with_render_margin(infer_ternary_limits(t_vals, l_vals, r_vals)), mode
    )


#: Where the label window is kept: the axes' own limits are the full triangle on purpose, so the
#: window a zoom moves has to live beside them.
_TERNARY_LABEL_RANGE_ATTR = "_ternary_label_range"


def set_ternary_label_range(ax: Any, limits) -> tuple[float, ...] | None:
    """Record *limits* as the window the tick labels report; returns the stored window.

    Nothing here touches the drawing. The axes draw the whole triangle unless a window is handed to
    them, so a window that is only meant to label has to live beside them: a range restricted per
    component is the intersection of the triangle with a box - a hexagon - and no setting of
    mpltern's makes that both equilateral and undistorted (see
    tests/test_ternary_rendered_geometry.py).  Use :func:`apply_ternary_label_window` to relabel the
    ticks as well, or :func:`apply_ternary_zoom_window` to magnify the view too.
    """
    if ax is None or limits is None or len(limits) != 6:
        return None
    window = tuple(float(value) for value in limits)
    try:
        setattr(ax, _TERNARY_LABEL_RANGE_ATTR, window)
    except Exception as err:
        logger.warning("Could not store the ternary label range: %s", err)
        return None
    return window


def get_ternary_label_range(ax: Any) -> tuple[float, ...] | None:
    """The label window stored on *ax*, or None while the labels follow the axes' own limits."""
    window = getattr(ax, _TERNARY_LABEL_RANGE_ATTR, None)
    if window is None:
        return None
    try:
        values = tuple(float(value) for value in window)
    except (TypeError, ValueError):
        return None
    return values if len(values) == 6 else None


#: Where the window an explicit zoom asked for is kept: every later render draws it again, and only
#: an explicit reset drops it.  It lives on the axes rather than in app_state.ternary_manual_limits
#: because that field is persisted - a window loaded from the last session must not clip a fresh
#: plot, which is the flattened trapezoid tests/test_ternary_rendered_geometry.py is about.
_TERNARY_VIEW_WINDOW_ATTR = "_ternary_view_window"
#: Where the range the data implies is kept, so a reset can go back to the numbers a fresh plot has.
_TERNARY_DATA_RANGE_ATTR = "_ternary_data_range"


def _coerce_ternary_window(limits) -> tuple[float, ...] | None:
    """A six-value window as floats, or None when *limits* is not one."""
    try:
        if limits is None or len(limits) != 6:
            return None
        return tuple(float(value) for value in limits)
    except (TypeError, ValueError):
        return None


def store_ternary_view_window(ax: Any, limits) -> tuple[float, ...] | None:
    """Record *limits* as the window every later render draws; an unusable or full one clears it.

    This is what makes a zoom persist: :func:`configure_ternary_axis` draws the stored window on
    every render, so a data-point change, a KDE toggle, a style change or a panel change cannot
    throw it away, and only :func:`reset_ternary_view` drops it.  A window that covers the whole
    triangle is not a zoom - zooming out fully is a reset in all but the name - so it clears the
    record instead of storing it.
    """
    window = _coerce_ternary_window(limits)
    if window is None or ternary_limits_cover_full_view(window):
        clear_ternary_view_window(ax)
        return None
    try:
        setattr(ax, _TERNARY_VIEW_WINDOW_ATTR, window)
    except Exception as err:
        logger.warning("Could not store the ternary view window: %s", err)
        return None
    return window


def stored_ternary_view_window(ax: Any) -> tuple[float, ...] | None:
    """The window an explicit zoom asked for, or None while nothing is zoomed."""
    return _coerce_ternary_window(getattr(ax, _TERNARY_VIEW_WINDOW_ATTR, None))


def clear_ternary_view_window(ax: Any) -> None:
    """Drop the stored window: the next render draws the whole triangle again."""
    try:
        setattr(ax, _TERNARY_VIEW_WINDOW_ATTR, None)
    except Exception as err:
        logger.warning("Could not clear the ternary view window: %s", err)


def set_ternary_data_range(ax: Any, limits) -> tuple[float, ...] | None:
    """Record the range the data implies, for :func:`reset_ternary_view` to come back to."""
    window = _coerce_ternary_window(limits)
    if window is None:
        return None
    try:
        setattr(ax, _TERNARY_DATA_RANGE_ATTR, window)
    except Exception as err:
        logger.warning("Could not store the ternary data range: %s", err)
        return None
    return window


def get_ternary_data_range(ax: Any) -> tuple[float, ...] | None:
    """The range the last render inferred from the data, or None when it recorded none."""
    return _coerce_ternary_window(getattr(ax, _TERNARY_DATA_RANGE_ATTR, None))


def ternary_axes_limits(ax: Any) -> tuple[float, ...] | None:
    """The axes' own limits as one six-tuple, or None when they cannot be read."""
    try:
        pairs = (ax.get_tlim(), ax.get_llim(), ax.get_rlim())
        return tuple(float(value) for pair in pairs for value in pair)
    except Exception:
        return None


def ternary_label_window(ax: Any) -> tuple[float, ...]:
    """The window the labels currently report: the stored one, else the axes' own limits."""
    return get_ternary_label_range(ax) or ternary_axes_limits(ax) or _FULL_TERNARY_LIMITS


def apply_ternary_label_window(ax: Any, limits) -> tuple[float, ...] | None:
    """Move the label window to *limits* and redraw the ticks; the drawing is untouched.

    This is the label-only path: the range the data implies (the automatic window) and the range a
    reset labels the axes with use it, so the axes keep whatever they are drawing and only the
    numbers change.  A zoom that is meant to magnify goes through
    :func:`apply_ternary_zoom_window` instead.
    """
    window = set_ternary_label_range(ax, limits)
    if window is None:
        return None
    relabel_ternary_ticks(ax, window)
    return window


def apply_ternary_zoom_window(ax: Any, limits, *, store: bool = True) -> tuple[float, ...] | None:
    """Draw *limits* as the view and label the axes with it - the explicit zoom.

    Unlike :func:`apply_ternary_label_window` this really magnifies: mpltern is handed the window,
    so the points grow on screen and the tick labels move with the drawing, which is what keeps the
    readings on screen matching the picture.  The outline then has the window's shape - a hexagon,
    flatter than the full triangle - and that is the accepted trade-off of zooming, no longer
    imposed on the default view (see tests/test_ternary_rendered_geometry.py).

    mpltern does not take every box as given - it clips one that reaches past the triangle, so
    ``1 - lmin - rmin`` caps ``tmax`` and the same for the other components.  The drawn limits are
    therefore read back and *they* become the label window and the return value, so the numbers on
    screen describe the region that is really there.

    The window that comes out is recorded (:func:`store_ternary_view_window`), so every later render
    of these axes draws it again; only :func:`reset_ternary_view` clears it.  With ``store=False``
    the drawing moves and nothing is recorded: that is the shape an *imposed* view needs - the
    axis-scale lock draws its recorded window on every render without becoming the zoom the
    renderer keeps, so a window the user zoomed to before the lock is still there when it is
    switched off again.
    """
    window = set_ternary_label_range(ax, limits)
    if window is None:
        return None
    try:
        ax.set_ternary_lim(*window)
    except Exception as err:
        logger.warning("Could not draw the ternary zoom window: %s", err)
        return None
    drawn = ternary_axes_limits(ax)
    if drawn is not None and drawn != window:
        logger.info(
            "Ternary window %s was drawn as %s; the labels follow the drawing.",
            tuple(round(float(value), 4) for value in window),
            tuple(round(float(value), 4) for value in drawn),
        )
        window = set_ternary_label_range(ax, drawn) or window
    # What is really drawn is what every later render has to draw again: this record is what an
    # explicit zoom leaves behind, and only an explicit reset clears it. An imposed view
    # (store=False) leaves the record alone.
    if store:
        store_ternary_view_window(ax, window)
    relabel_ternary_ticks(ax, window)
    return window


def _last_ternary_components():
    """The components of the last ternary embedding, or None when there is none."""
    embedding = getattr(app_state, "last_embedding", None)
    if embedding is None:
        return None
    if str(getattr(app_state, "last_embedding_type", "") or "").upper() != "TERNARY":
        return None
    try:
        arr = np.asarray(embedding, dtype=float)
    except (TypeError, ValueError):
        return None
    if arr.ndim != 2 or arr.shape[1] != 3 or arr.shape[0] == 0:
        return None
    return arr[:, 0], arr[:, 1], arr[:, 2]


def _stored_ternary_label_range() -> tuple[float, ...] | None:
    """The window the last render reported, from app_state.ternary_ranges."""
    ranges = getattr(app_state, "ternary_ranges", None) or {}
    window: list[float] = []
    try:
        for key in ("t", "l", "r"):
            low, high = ranges[key]
            window.extend((float(low), float(high)))
    except (KeyError, TypeError, ValueError):
        return None
    return tuple(window)


def reset_ternary_label_window() -> tuple[float, ...]:
    """The window a zoom reset falls back to when the axes recorded no data range: the data range.

    ``app_state.ternary_ranges`` holds the window the last render reported, which is the inferred
    range unless that render drew a stored window, the checkbox's or a zoom's.  A reset therefore
    prefers the data range the render recorded on the axes (:func:`get_ternary_data_range`) and
    comes here only for axes that never rendered; the range is then inferred from the data of the
    last ternary embedding when that is known, and the stored window is the last resort.
    """
    if not bool(app_state.ternary_manual_limits_enabled):
        window = _stored_ternary_label_range()
        if window is not None:
            return window
    components = _last_ternary_components()
    if components is not None:
        return infer_ternary_label_range(*components, mode=resolve_ternary_limit_mode())
    return _stored_ternary_label_range() or _FULL_TERNARY_LIMITS


def reset_ternary_view(ax: Any) -> tuple[float, ...]:
    """Put the view back to the default: the whole triangle, labelled with the data range.

    The counterpart of :func:`apply_ternary_zoom_window`, and the only thing that clears the window
    that function stored: the explicit zoom is dropped here and the axes are handed the full
    triangle again - the drawing really goes back, it is not just relabelled - while the ticks go
    back to the range the data implies, which is the window a fresh render labels with.  Returns
    that window.
    """
    window = get_ternary_data_range(ax) or reset_ternary_label_window()
    clear_ternary_view_window(ax)
    set_ternary_label_range(ax, window)
    try:
        ax.set_ternary_lim(*_FULL_TERNARY_LIMITS)
    except Exception as err:
        logger.warning("Could not reset the ternary view: %s", err)
    relabel_ternary_ticks(ax, window)
    return window


TERNARY_AXIS_STYLE_KEY = "ternary_axis"

# The ternary axes had no style entry at all: the tick format was written into the code twice, and
# everything else was mpltern's defaults. Registering the key here puts the ternary plot under the
# style manager like the other overlays, so the same panel that edits a curve edits these too.
TERNARY_AXIS_STYLE_DEFAULTS = {
    "tick_format": "%.2f",
    "tick_labelsize": 10.0,
    "tick_length": 4.0,
    "tick_width": 1.0,
    "label_size": 11.0,
    "edge_color": "black",
    "edge_width": 1.0,
    "grid": False,
    "grid_color": "#cbd5e1",
    "grid_width": 0.6,
}


def ternary_axis_style() -> dict:
    """The resolved ternary axis style (registered on first use)."""
    try:
        from visualization.line_styles import ensure_line_style

        return ensure_line_style(app_state, TERNARY_AXIS_STYLE_KEY, dict(TERNARY_AXIS_STYLE_DEFAULTS))
    except Exception as err:
        logger.warning("Could not resolve the ternary axis style: %s", err)
        return dict(TERNARY_AXIS_STYLE_DEFAULTS)


def format_ternary_tick(value: float, style: dict | None = None) -> str:
    """One formatter for every ternary tick, driven by the style."""
    style = style or ternary_axis_style()
    template = str(style.get("tick_format", "%.2f"))
    try:
        return template % float(value)
    except Exception:
        return f"{float(value):.2f}"


def apply_ternary_axis_style(ax: Any, style: dict | None = None) -> None:
    """Push the cosmetic parts of the style onto the axes (never the geometry)."""
    style = style or ternary_axis_style()
    for name in ("t", "l", "r"):
        axis = getattr(ax, f"{name}axis", None)
        if axis is None:
            continue
        try:
            axis.set_tick_params(
                labelsize=float(style.get("tick_labelsize", 10.0)),
                length=float(style.get("tick_length", 4.0)),
                width=float(style.get("tick_width", 1.0)),
            )
        except Exception as err:
            logger.warning("Could not apply the ternary tick parameters: %s", err)
        try:
            label = getattr(ax, f"set_{name}label")
            label(getattr(ax, f"get_{name}label")(), fontsize=float(style.get("label_size", 11.0)))
        except Exception as err:
            logger.warning("Could not apply the ternary axis label style: %s", err)


def resolve_ternary_value_display(mode: Any = None) -> str:
    """'raw' labels the axes with the original ratios, 'normalized' with the fractions."""
    if mode is None:
        mode = getattr(app_state, "ternary_value_display", "raw")
    name = str(mode or "raw").strip().lower()
    return name if name in ("raw", "normalized") else "raw"


def _raw_scale(normalized, raw) -> float | None:
    """The factor that turns this axis's fractions back into its own ratios.

    Each axis is independent by design: normalising divided every component by its own sample sum,
    so the factor that undoes it for one axis is the mean of that axis's ratios over the mean of
    that axis's fractions. Using one shared factor would show a number that belongs to no axis.
    """
    import numpy as _np

    norm = _np.asarray(normalized, dtype=float)
    values = _np.asarray(raw, dtype=float)
    mask = _np.isfinite(norm) & _np.isfinite(values)
    if not _np.any(mask):
        return None
    denominator = float(_np.mean(norm[mask]))
    if denominator <= 0.0:
        return None
    return float(_np.mean(values[mask])) / denominator


def _nice_tick_step(target: float) -> float:
    """A readable step (1, 2, 2.5 or 5 times a power of ten) close to *target*."""
    import math as _math

    if not _math.isfinite(target) or target <= 0.0:
        return 1.0
    exponent = _math.floor(_math.log10(target))
    base = target / (10.0 ** exponent)
    for candidate in (1.0, 2.0, 2.5, 5.0, 10.0):
        if base <= candidate:
            return candidate * (10.0 ** exponent)
    return 10.0 ** (exponent + 1)


def _raw_tick_values(low_raw: float, high_raw: float, target_count: int = 6):
    """Tick values at a constant density along the axis, on readable numbers.

    The count is what has to stay steady: placing a fixed number of ticks across whatever range
    is visible makes them sparse when zoomed out and crowded when zoomed in, because the range
    changes by orders of magnitude between plots.
    """
    import math as _math

    span = high_raw - low_raw
    if not _math.isfinite(span) or span <= 0.0:
        return []
    step = _nice_tick_step(span / max(1, target_count))
    start = _math.ceil(low_raw / step) * step
    # Indexed rather than accumulated: adding the step repeatedly drifts (18.599999999999998),
    # and the labels are meant to read as round values.
    count = int((high_raw - start) // step) + 1 if start <= high_raw else 0
    return [start + index * step for index in range(max(0, min(count, 40)))]


def _ternary_tick_positions(ax: Any, name: str, values, scale: float, low: float, high: float):
    """Where the labelled values sit along the edge the reader sees.

    The values come from the label window, the positions from the axes' own limits, so the ticks
    always span the edge that is drawn.  The two coincide whenever a window is drawn - a zoom, or
    the manual-limits box - and the readings are then exact.  While the whole triangle is drawn
    instead, an automatic (never-clipping) window is laid out across that edge rather than at its
    absolute composition: placing its ticks absolutely would bunch the real dataset's 7% window
    into a sliver of the edge, which is the defect "the ticks should span the axis" was about.
    """
    drawn_low, drawn_high = 0.0, 1.0
    try:
        pair = getattr(ax, f"get_{name}lim")()
        drawn_low, drawn_high = float(pair[0]), float(pair[1])
    except Exception:
        # mpltern-free stand-ins in unit tests: fall back to the whole edge.
        drawn_low, drawn_high = 0.0, 1.0
    span = float(high) - float(low)
    if span <= 0.0 or drawn_high <= drawn_low:
        return []
    return [
        drawn_low + (float(value) / scale - float(low)) / span * (drawn_high - drawn_low)
        for value in values
    ]


def _set_ternary_tick_labels(ax: Any, limits, scales: dict) -> int:
    """Set the three axes' ticks and labels for the label window *limits*.

    One body for the render path and the zoom path, so a fresh plot, a zoom and a reset cannot
    drift apart.  mpltern's axis objects expose setters only (no get_ticks), so both the positions
    and the labels are written here; the values span the window at a constant density, whichever
    window is current.
    """
    style = ternary_axis_style()
    changed = 0
    for name, low, high in zip(("t", "l", "r"), limits[0::2], limits[1::2]):
        axis = getattr(ax, f"{name}axis", None)
        scale = scales.get(name)
        if axis is None or not scale or not np.isfinite(scale):
            continue
        low, high = float(low), float(high)
        if high <= low:
            continue
        values = _raw_tick_values(low * scale, high * scale)
        if len(values) < 2:
            continue
        positions = _ternary_tick_positions(ax, name, values, scale, low, high)
        if len(positions) != len(values):
            continue
        try:
            axis.set_ticks(positions)
            axis.set_ticklabels([format_ternary_tick(value, style) for value in values])
            changed += 1
        except Exception as err:
            logger.warning("Could not relabel the %s axis in raw units: %s", name, err)
    return changed


def apply_ternary_tick_display(ax: Any, limits, normalized, raw_values, display: str) -> int:
    """Relabel the three axes in raw ratio units; returns how many axes were relabelled.

    *limits* is the label window, never the drawn region: the ticks are laid out across the axes'
    own limits and carry the values of the window.  The per-axis factors are cached on the axes,
    because they depend on the data alone - that is what lets a later zoom relabel without
    reaching for the data again.
    """
    if ax is None or raw_values is None or resolve_ternary_value_display(display) != "raw":
        return 0
    if limits is None or len(limits) != 6:
        return 0

    scales: dict = {}
    for name, norm, raw in zip(("t", "l", "r"), normalized, raw_values):
        scale = _raw_scale(norm, raw)
        if scale and np.isfinite(scale):
            scales[name] = scale
    changed = _set_ternary_tick_labels(ax, limits, scales)
    if scales:
        setattr(ax, "_ternary_raw_scales", scales)
    return changed


def enforce_ternary_aspect(ax: Any) -> bool:
    """Re-assert the physical constraint: a ternary triangle is equilateral.

    mpltern draws the triangle to fill its axes box, so the equal aspect is what keeps the three
    edges the same length. Anything global can take it away - plt.style.use resets rcParams while a
    window is assembled, a theme can carry a different image.aspect, and any future geometry control
    in the style panel would do the same - and the triangle then comes out stretched like a
    trapezoid, which is meaningless as a composition diagram. This is called after every draw, so the
    constraint holds no matter what was applied, and a drift is logged rather than corrected in
    silence.
    """
    if ax is None:
        return False
    try:
        before = str(ax.get_aspect())
        drifted = before not in ("equal", "1", "1.0")
        if drifted:
            logger.warning(
                "Ternary aspect was %s (a style or theme changed it); restoring equal.", before
            )
        ax.set_aspect("equal", adjustable="box")
        return drifted
    except Exception as err:
        logger.warning("Could not enforce the ternary aspect: %s", err)
        return False


def install_ternary_tick_refresh(ax: Any) -> bool:
    """Keep the raw labels applied after every draw.

    Something clears them between configure_ternary_axis and the first paint - the reported symptom
    is no labels on a fresh plot, appearing only once the view is zoomed. Rather than chase every
    site that touches the limits, the labels are reapplied after each draw from the label window
    kept on the axes (a zoom moves that window, not the drawing) and the cached factors: that
    covers the first paint, later zooms, resizes and plain redraws alike.
    """
    if ax is None:
        return False
    figure = getattr(ax, "figure", None)
    canvas = getattr(figure, "canvas", None)
    if canvas is None or getattr(ax, "_ternary_tick_refresh_installed", False):
        return False

    state = {"running": False}

    def _on_draw(_event) -> None:
        if state["running"]:
            return
        state["running"] = True
        try:
            relabel_ternary_ticks(ax, ternary_label_window(ax))
            if enforce_ternary_aspect(ax):
                # draw_event fires after the layout, so the correction would only show on the next
                # paint; ask for it, once, and only when something had actually drifted.
                canvas.draw_idle()
        except Exception as err:  # pragma: no cover - cosmetic, never break a draw
            logger.warning("Could not refresh ternary tick labels after a draw: %s", err)
        finally:
            state["running"] = False

    try:
        canvas.mpl_connect("draw_event", _on_draw)
        setattr(ax, "_ternary_tick_refresh_installed", True)
        return True
    except Exception as err:
        logger.warning("Could not install the ternary tick refresh: %s", err)
        return False


def relabel_ternary_ticks(ax: Any, limits, mode: str | None = None) -> int:
    """Redraw the raw tick labels for a new label window.

    A zoom moves the label window and never the drawing (``set_ternary_lim`` is not called here),
    so the labels have to follow the window: the per-axis factors cached at render time supply the
    mapping, and the ticks are laid out across the edge again at the same density.  *limits* is the
    label window, not the region that is drawn.
    """
    if ax is None or limits is None or len(limits) != 6:
        return 0
    scales = getattr(ax, "_ternary_raw_scales", None)
    if not scales or resolve_ternary_value_display(mode) != "raw":
        return 0
    return _set_ternary_tick_labels(ax, limits, scales)


def configure_ternary_axis(
    ax: Any,
    t_vals: Iterable[float],
    l_vals: Iterable[float],
    r_vals: Iterable[float],
    labels: tuple[str, str, str] | list[str] | None = None,
    *,
    auto_zoom: bool = True,
    raw_values: tuple | list | None = None,
    value_display: str | None = None,
) -> tuple[float, float, float, float, float, float]:
    """Configure mpltern axis labels and limits using mpltern API.

    By default the axes draw the full triangle: a range restricted per component is the intersection
    of the triangle with a box, i.e. a hexagon, and no setting of mpltern's makes that both
    equilateral and undistorted (21 configurations measured - see
    tests/test_ternary_rendered_geometry.py).  The automatic range inferred from the data therefore
    only *labels* the axes - it is what the tick labels report and what the callers store as
    app_state.ternary_ranges - and it never clips the drawing.

    A window an explicit zoom asked for is the exception, and it is drawn here on *every* render: the
    gesture records it on the axes (:func:`store_ternary_view_window`) and only an explicit reset
    (:func:`reset_ternary_view`) drops it, so a data-point change, a KDE toggle, a style change or a
    panel change cannot throw the zoom away - and the ticks follow what is drawn.

    The manual-limits checkbox keeps its meaning - "use my stored window" - and is effectively
    always true while such a window exists: ticked, the window from
    ``app_state.ternary_manual_limits`` is drawn as well, which is what keeps the manual spin boxes
    live; it no longer decides whether a zoom survives a render.
    """
    if labels and len(labels) == 3:
        try:
            ax.set_tlabel(str(labels[0]))
            ax.set_llabel(str(labels[1]))
            ax.set_rlabel(str(labels[2]))
        except Exception as err:
            logger.warning("configure_ternary_axis failed: %s", err)

    mode = resolve_ternary_limit_mode(app_state.ternary_limit_mode)
    state_gateway.set_ternary_limit_mode(mode)

    tmin, tmax, lmin, lmax, rmin, rmax = _FULL_TERNARY_LIMITS
    drawn = _FULL_TERNARY_LIMITS
    manual_window = False
    data_range = _FULL_TERNARY_LIMITS

    use_ternary_layout(getattr(ax, "figure", None))

    try:
        # The range the data implies: it labels a plot that is not zoomed, and it is what a reset
        # comes back to, so it is recorded on the axes on every render.
        data_range = infer_ternary_label_range(t_vals, l_vals, r_vals, mode)
        if auto_zoom:
            # The window to draw: the one an explicit zoom stored, or the user's manual window.
            # Either is drawn, not merely labelled - and the labels describe what was drawn.
            window = stored_ternary_view_window(ax)
            if bool(app_state.ternary_manual_limits_enabled):
                # The checkbox means "use my stored window" - and its spin boxes are the editor for
                # the manual copy of it, so that copy wins while the box asks for it.
                window = manual_ternary_label_range(mode)
            if window is None:
                # Automatic: the inferred range labels the axes and never narrows the drawing.
                tmin, tmax, lmin, lmax, rmin, rmax = data_range
            else:
                tmin, tmax, lmin, lmax, rmin, rmax = window
                drawn = (tmin, tmax, lmin, lmax, rmin, rmax)
                manual_window = True

        ax.set_ternary_lim(*drawn)
        if manual_window:
            read_back = ternary_axes_limits(ax)
            if read_back is not None:
                # mpltern clips a box that reaches past the triangle - tmax cannot exceed
                # 1 - lmin - rmin, and so on - so the window that is really drawn is the one the
                # labels have to describe.
                tmin, tmax, lmin, lmax, rmin, rmax = read_back
    except Exception as e:
        logger.warning("Failed to configure ternary limits: %s", e)
        ax.set_ternary_lim(*_FULL_TERNARY_LIMITS)
        tmin, tmax, lmin, lmax, rmin, rmax = _FULL_TERNARY_LIMITS

    label_range = (tmin, tmax, lmin, lmax, rmin, rmax)
    set_ternary_label_range(ax, label_range)
    set_ternary_data_range(ax, data_range)
    apply_ternary_axis_style(ax)
    install_ternary_tick_refresh(ax)
    apply_ternary_tick_display(
        ax,
        label_range,
        (t_vals, l_vals, r_vals),
        raw_values,
        resolve_ternary_value_display(value_display),
    )

    try:
        ax.set_aspect('equal', adjustable='box')
    except Exception as err:
        logger.warning("configure_ternary_axis failed: %s", err)

    return tmin, tmax, lmin, lmax, rmin, rmax


