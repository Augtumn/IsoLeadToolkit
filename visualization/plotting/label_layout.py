"""Reusable curve-label layout helpers powered by adjustText."""
from __future__ import annotations

import logging
from typing import Any, Callable

import numpy as np

from core import app_state, state_gateway

logger = logging.getLogger(__name__)

_SLOPE_EPSILON = 1e-10
_adjust_text_fn = None
_adjust_text_checked = False


def _normalize_position_mode(position_mode: str | None) -> str:
    """Normalize user/session position value to supported internal tokens."""
    value = str(position_mode or 'auto').strip().lower()
    alias_map = {
        'middle': 'center',
        'mid': 'center',
        'centre': 'center',
        'left': 'start',
        'right': 'end',
        'begin': 'start',
        'beginning': 'start',
        'first': 'start',
        'last': 'end',
        '起点': 'start',
        '终点': 'end',
        '居中': 'center',
        '中间': 'center',
        '自动': 'auto',
    }
    value = alias_map.get(value, value)
    if value not in {'auto', 'start', 'center', 'end'}:
        return 'auto'
    return value


def _float_pair(value: Any, fallback: tuple[float, float]) -> tuple[float, float]:
    """Normalize runtime setting to a 2-float tuple."""
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        try:
            return float(value[0]), float(value[1])
        except Exception:
            return fallback
    if isinstance(value, (int, float)):
        scalar = float(value)
        return scalar, scalar
    return fallback


def _resolve_adjust_text_settings() -> tuple[tuple[float, float], tuple[float, float], tuple[float, float], int, float]:
    """Resolve adjustText parameters from app_state with safe defaults."""
    force_text = _float_pair(getattr(app_state, 'adjust_text_force_text', (0.8, 1.0)), (0.8, 1.0))
    force_static = _float_pair(getattr(app_state, 'adjust_text_force_static', (0.4, 0.6)), (0.4, 0.6))
    expand = _float_pair(getattr(app_state, 'adjust_text_expand', (1.08, 1.20)), (1.08, 1.20))

    try:
        iter_lim = int(getattr(app_state, 'adjust_text_iter_lim', 120))
    except Exception:
        iter_lim = 120
    iter_lim = max(10, min(1000, iter_lim))

    try:
        time_lim = float(getattr(app_state, 'adjust_text_time_lim', 0.25))
    except Exception:
        time_lim = 0.25
    time_lim = max(0.05, min(2.0, time_lim))

    return force_text, force_static, expand, iter_lim, time_lim


def _lazy_import_adjust_text() -> Callable[..., Any] | None:
    """Lazy import adjustText.adjust_text."""
    global _adjust_text_fn, _adjust_text_checked
    if _adjust_text_checked:
        return _adjust_text_fn
    _adjust_text_checked = True
    try:
        from adjustText import adjust_text as _adjust_text
        _adjust_text_fn = _adjust_text
        # Keep third-party solver logs from flooding application log files.
        logging.getLogger('adjustText').setLevel(logging.WARNING)
    except Exception as err:
        logger.debug("adjustText import skipped: %s", err)
        _adjust_text_fn = None
    return _adjust_text_fn


def _line_visible_in_axes(ax, x_vals, y_vals) -> bool:
    """Return True when any line sample is inside current axes limits."""
    if x_vals is None or y_vals is None:
        return False
    x_arr = np.asarray(x_vals, dtype=float)
    y_arr = np.asarray(y_vals, dtype=float)
    if x_arr.size == 0 or y_arr.size == 0 or x_arr.size != y_arr.size:
        return False
    valid = np.isfinite(x_arr) & np.isfinite(y_arr)
    if not np.any(valid):
        return False
    x_arr = x_arr[valid]
    y_arr = y_arr[valid]
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    visible = (
        (x_arr >= min(xlim)) & (x_arr <= max(xlim))
        & (y_arr >= min(ylim)) & (y_arr <= max(ylim))
    )
    return bool(np.any(visible))


def _slope_angle_deg(ax: Any, x0: float, y0: float, x1: float, y1: float) -> float:
    """Compute text rotation angle from local line segment in display coords."""
    try:
        p0 = ax.transData.transform((x0, y0))
        p1 = ax.transData.transform((x1, y1))
        return float(np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0])))
    except Exception:
        dx = x1 - x0
        if abs(dx) < _SLOPE_EPSILON:
            return 0.0
        return float(np.degrees(np.arctan((y1 - y0) / dx)))


def _pick_anchor_on_line(
    ax: Any,
    x_vals: Any,
    y_vals: Any,
    position_mode: str,
) -> tuple[float, float, float] | None:
    """Pick initial anchor and orientation from a visible part of a polyline."""
    x_arr = np.asarray(x_vals, dtype=float)
    y_arr = np.asarray(y_vals, dtype=float)
    valid = np.isfinite(x_arr) & np.isfinite(y_arr)
    x_arr = x_arr[valid]
    y_arr = y_arr[valid]
    if x_arr.size < 2:
        return None

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    visible = (
        (x_arr >= min(xlim)) & (x_arr <= max(xlim))
        & (y_arr >= min(ylim)) & (y_arr <= max(ylim))
    )
    vis_idx = np.where(visible)[0]
    if vis_idx.size == 0:
        return None

    mode = _normalize_position_mode(position_mode)

    if mode == 'start':
        idx = int(vis_idx[0])
    elif mode == 'end':
        idx = int(vis_idx[-1])
    else:
        idx = int(vis_idx[len(vis_idx) // 2])

    i0 = max(0, idx - 1)
    i1 = min(len(x_arr) - 1, idx + 1)
    if i0 == i1:
        i1 = min(len(x_arr) - 1, idx + 1)
        i0 = max(0, idx - 1)
    angle = _slope_angle_deg(ax, x_arr[i0], y_arr[i0], x_arr[i1], y_arr[i1])
    return float(x_arr[idx]), float(y_arr[idx]), angle


def position_curve_label(
    ax,
    text_artist,
    *,
    mode=None,
    slope=None,
    intercept=None,
    x_vals=None,
    y_vals=None,
    x_line=None,
    y_line=None,
    age=None,
    age_ma=None,
    label_text=None,
    position_mode='auto',
):
    """Set a visible initial anchor for curve labels; adjustText refines overlap later."""
    if ax is None or text_artist is None:
        return

    line_x = None
    line_y = None
    if mode == 'paleo' or (slope is not None and intercept is not None):
        xlim = ax.get_xlim()
        line_x = np.asarray([xlim[0], xlim[1]], dtype=float)
        line_y = np.asarray([slope * xlim[0] + intercept, slope * xlim[1] + intercept], dtype=float)
    elif mode == 'curve_left':
        line_x = np.asarray(x_vals if x_vals is not None else [], dtype=float)
        line_y = np.asarray(y_vals if y_vals is not None else [], dtype=float)
    else:
        line_x = np.asarray(x_line if x_line is not None else [], dtype=float)
        line_y = np.asarray(y_line if y_line is not None else [], dtype=float)

    if not _line_visible_in_axes(ax, line_x, line_y):
        text_artist.set_visible(False)
        return

    normalized_mode = _normalize_position_mode(position_mode)
    anchor = _pick_anchor_on_line(ax, line_x, line_y, normalized_mode)
    if anchor is None:
        text_artist.set_visible(False)
        return

    x_anchor, y_anchor, angle = anchor
    text_artist.set_visible(True)
    text_artist.set_position((x_anchor, y_anchor))
    text_artist.set_rotation(angle)
    text_artist.set_rotation_mode('anchor')
    text_artist.set_ha('center')
    text_artist.set_va('center')
    text_artist.set_clip_on(True)
    # Keep mode on artist so adjustText can preserve explicit placement choices.
    text_artist._curve_label_position_mode = normalized_mode

    if label_text is not None:
        text_artist.set_text(label_text)
    elif age_ma is not None:
        text_artist.set_text(f" {age_ma:.0f} Ma")
    elif age is not None:
        text_artist.set_text(f" {age:.0f} Ma")


def apply_adjust_text_to_labels(ax: Any, text_artists: list[Any] | None) -> None:
    """Apply adjustText globally for all visible overlay labels."""
    adjust_text = _lazy_import_adjust_text()
    if adjust_text is None or ax is None:
        return

    texts = []
    anchored_texts = []
    for txt in text_artists or []:
        if txt is None:
            continue
        try:
            if not bool(txt.get_visible()):
                continue
        except Exception:
            continue
        mode = _normalize_position_mode(getattr(txt, '_curve_label_position_mode', 'auto'))
        if mode == 'auto':
            texts.append(txt)
        else:
            anchored_texts.append(txt)

    # Explicit start/center/end labels are user-anchored and should not be auto-repositioned.
    if not texts and anchored_texts:
        return

    if len(texts) < 2:
        return

    if bool(getattr(app_state, 'adjust_text_in_progress', False)):
        return

    static_points = []
    sample_coords = getattr(app_state, 'sample_coordinates', {}) or {}
    if isinstance(sample_coords, dict):
        static_points.extend(sample_coords.values())

    if len(static_points) > 800:
        idx = np.linspace(0, len(static_points) - 1, 800, dtype=int)
        static_points = [static_points[i] for i in idx]

    x_static = None
    y_static = None
    if static_points:
        arr = np.asarray(static_points, dtype=float)
        if arr.ndim == 2 and arr.shape[1] == 2:
            finite = np.isfinite(arr[:, 0]) & np.isfinite(arr[:, 1])
            arr = arr[finite]
            if arr.size:
                x_static = arr[:, 0]
                y_static = arr[:, 1]

    force_text, force_static, expand, iter_lim, time_lim = _resolve_adjust_text_settings()

    target_x = []
    target_y = []
    for txt in texts:
        try:
            x0, y0 = txt.get_position()
            target_x.append(float(x0))
            target_y.append(float(y0))
        except Exception:
            target_x = []
            target_y = []
            break

    try:
        state_gateway.set_adjust_text_in_progress(True)
        adjust_text(
            texts,
            ax=ax,
            x=x_static,
            y=y_static,
            target_x=target_x or None,
            target_y=target_y or None,
            only_move={'text': 'xy', 'static': 'xy', 'explode': 'xy', 'pull': 'xy'},
            ensure_inside_axes=True,
            force_text=force_text,
            force_static=force_static,
            force_pull=(0.04, 0.06),
            expand=expand,
            expand_axes=False,
            avoid_self=True,
            prevent_crossings=True,
            iter_lim=iter_lim,
            time_lim=time_lim,
            arrowprops=None,
        )
    except Exception as err:
        logger.debug("adjustText layout skipped: %s", err)
    finally:
        state_gateway.set_adjust_text_in_progress(False)
