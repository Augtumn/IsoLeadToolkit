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


def apply_ternary_tick_display(ax: Any, limits, normalized, raw_values, display: str) -> int:
    """Relabel the three axes in raw ratio units; returns how many axes were relabelled.

    The tick positions are set here as well: mpltern's axis objects expose setters only (no
    get_ticks), so the positions are derived from the limits the caller already computed, evenly
    spaced inside whatever range is currently shown.
    """
    if ax is None or raw_values is None or resolve_ternary_value_display(display) != "raw":
        return 0
    if limits is None or len(limits) != 6:
        return 0

    changed = 0
    scales: dict = {}
    for name, norm, raw, low, high in zip(
        ("t", "l", "r"), normalized, raw_values, limits[0::2], limits[1::2]
    ):
        axis = getattr(ax, f"{name}axis", None)
        if axis is None:
            continue
        scale = _raw_scale(norm, raw)
        if not scale or not np.isfinite(scale):
            continue
        low, high = float(low), float(high)
        if high <= low:
            continue
        values = _raw_tick_values(low * scale, high * scale)
        if len(values) < 2:
            continue
        try:
            axis.set_ticks([value / scale for value in values])
            axis.set_ticklabels([f"{value:.2f}" for value in values])
            scales[name] = scale
            changed += 1
        except Exception as err:
            logger.warning("Could not relabel the %s axis in raw units: %s", name, err)
        except Exception as err:
            logger.warning("Could not relabel the %s axis in raw units: %s", name, err)
    if scales:
        # Cached because the factors depend on the data alone, never on the zoom: the wheel and
        # magnifier paths relabel from this instead of reaching for the data again.
        setattr(ax, "_ternary_raw_scales", scales)
    return changed


def relabel_ternary_ticks(ax: Any, limits, mode: str | None = None) -> int:
    """Redraw the raw tick labels for a new view range.

    Zooming changes set_ternary_lim without going through configure_ternary_axis, so the labels
    used to keep the numbers of the previous view - the axis length is fixed, the labels have to
    follow the zoom. The per-axis factors cached at render time supply the mapping.
    """
    if ax is None or limits is None or len(limits) != 6:
        return 0
    scales = getattr(ax, "_ternary_raw_scales", None)
    if not scales or resolve_ternary_value_display(mode) != "raw":
        return 0
    changed = 0
    for name, low, high in zip(("t", "l", "r"), limits[0::2], limits[1::2]):
        axis = getattr(ax, f"{name}axis", None)
        scale = scales.get(name)
        if axis is None or not scale:
            continue
        low, high = float(low), float(high)
        if high <= low:
            continue
        values = _raw_tick_values(low * scale, high * scale)
        if len(values) < 2:
            continue
        try:
            axis.set_ticks([value / scale for value in values])
            axis.set_ticklabels([f"{value:.2f}" for value in values])
            changed += 1
        except Exception as err:
            logger.warning("Could not relabel the %s axis after a zoom: %s", name, err)
    return changed


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
    """Configure mpltern axis labels and limits using mpltern API."""
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

    use_ternary_layout(getattr(ax, "figure", None))

    try:
        if auto_zoom:
            use_manual = bool(app_state.ternary_manual_limits_enabled)
            if use_manual:
                tmin, tmax, lmin, lmax, rmin, rmax = _resolve_manual_limits()
            else:
                tmin, tmax, lmin, lmax, rmin, rmax = infer_ternary_limits(t_vals, l_vals, r_vals)

            # Expand limits by a small margin to prevent edge data from being
            # clipped when the figure is enlarged. mpltern's clip path can
            # exclude points exactly at the boundary due to floating-point
            # precision in the data-to-display coordinate transform chain.
            m = float(app_state.ternary_render_margin)
            tmin = max(0.0, tmin - m)
            tmax = min(1.0, tmax + m)
            lmin = max(0.0, lmin - m)
            lmax = min(1.0, lmax + m)
            rmin = max(0.0, rmin - m)
            rmax = min(1.0, rmax + m)

        # Apply via mpltern API based on mode
        if mode == 'max':
            ax.set_ternary_max(tmax, lmax, rmax)
        elif mode == 'min':
            ax.set_ternary_min(tmin, lmin, rmin)
        else:  # 'both' or default
            ax.set_ternary_lim(tmin, tmax, lmin, lmax, rmin, rmax)
    except Exception as e:
        logger.warning("Failed to configure ternary limits: %s", e)
        ax.set_ternary_lim(*_FULL_TERNARY_LIMITS)
        tmin, tmax, lmin, lmax, rmin, rmax = _FULL_TERNARY_LIMITS

    apply_ternary_tick_display(
        ax,
        effective_ternary_limits((tmin, tmax, lmin, lmax, rmin, rmax), mode),
        (t_vals, l_vals, r_vals),
        raw_values,
        resolve_ternary_value_display(value_display),
    )

    try:
        ax.set_aspect('equal', adjustable='box')
    except Exception as err:
        logger.warning("configure_ternary_axis failed: %s", err)

    return tmin, tmax, lmin, lmax, rmin, rmax


