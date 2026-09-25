"""Ternary plot helpers."""
from __future__ import annotations

import logging
from typing import Any, Iterable

import numpy as np

from core import app_state, state_gateway

logger = logging.getLogger(__name__)
_FULL_TERNARY_LIMITS = (0.0, 1.0, 0.0, 1.0, 0.0, 1.0)
_VALID_LIMIT_MODES = {'min', 'max', 'both'}
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











def configure_ternary_axis(
    ax: Any,
    t_vals: Iterable[float],
    l_vals: Iterable[float],
    r_vals: Iterable[float],
    labels: tuple[str, str, str] | list[str] | None = None,
    *,
    auto_zoom: bool = True,
) -> tuple[float, float, float, float, float, float]:
    """Configure mpltern axis labels and limits using mpltern API."""
    if labels and len(labels) == 3:
        try:
            ax.set_tlabel(str(labels[0]))
            ax.set_llabel(str(labels[1]))
            ax.set_rlabel(str(labels[2]))
        except Exception:
            logger.debug("Failed to set ternary axis labels", exc_info=True)

    mode = resolve_ternary_limit_mode(app_state.ternary_limit_mode)
    state_gateway.set_ternary_limit_mode(mode)

    tmin, tmax, lmin, lmax, rmin, rmax = _FULL_TERNARY_LIMITS

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

    try:
        ax.set_aspect('equal', adjustable='box')
    except Exception:
        logger.debug("Failed to set equal aspect on ternary axis", exc_info=True)

    return tmin, tmax, lmin, lmax, rmin, rmax



