"""Ternary plot helpers."""
from __future__ import annotations

import logging
from typing import Any, Iterable

import numpy as np
import pandas as pd
from scipy.stats import gmean

from core import app_state, state_gateway

logger = logging.getLogger(__name__)
_FULL_TERNARY_LIMITS = (0.0, 1.0, 0.0, 1.0, 0.0, 1.0)
_VALID_LIMIT_MODES = {'min', 'max', 'both'}
_TERNARY_LIMIT_EPSILON = 1e-9
_TERNARY_FACTORS_FILL_VALUE = 1e-3
_TERNARY_FACTORS_MIN_VALUE = 1e-6


def _data_state() -> Any:
    return getattr(app_state, 'data', app_state)


def _df_global() -> Any:
    return getattr(_data_state(), 'df_global', app_state.df_global)


def _active_subset_indices() -> Any:
    return getattr(_data_state(), 'active_subset_indices', app_state.active_subset_indices)


def _apply_ternary_stretch(
    t_vals: Iterable[float],
    l_vals: Iterable[float],
    r_vals: Iterable[float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Apply ternary stretch transform based on current mode."""
    if not getattr(app_state, 'ternary_stretch', False):
        return t_vals, l_vals, r_vals

    factors = getattr(app_state, 'ternary_factors', [1.0, 1.0, 1.0])
    if not factors or len(factors) != 3:
        factors = [1.0, 1.0, 1.0]

    t_vals = np.asarray(t_vals, dtype=float) * float(factors[0])
    l_vals = np.asarray(l_vals, dtype=float) * float(factors[1])
    r_vals = np.asarray(r_vals, dtype=float) * float(factors[2])

    mode = getattr(app_state, 'ternary_stretch_mode', 'power')
    power = float(getattr(app_state, 'ternary_stretch_power', 0.5))

    def _minmax(vals: np.ndarray) -> np.ndarray:
        vmin = np.nanmin(vals)
        vmax = np.nanmax(vals)
        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax == vmin:
            return vals
        return (vals - vmin) / (vmax - vmin)

    if mode in ('minmax', 'hybrid'):
        t_vals = _minmax(t_vals)
        l_vals = _minmax(l_vals)
        r_vals = _minmax(r_vals)

    if mode in ('power', 'hybrid'):
        t_vals = np.power(np.maximum(t_vals, 0), power)
        l_vals = np.power(np.maximum(l_vals, 0), power)
        r_vals = np.power(np.maximum(r_vals, 0), power)

    return t_vals, l_vals, r_vals


def _coerce_nonnegative(values: Iterable[float]) -> np.ndarray:
    """Convert values to finite, non-negative float arrays."""
    arr = np.asarray(values, dtype=float)
    arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)
    return np.maximum(arr, 0.0)


def _sanitize_boundary_percent(value: Any, default: float = 5.0) -> float:
    try:
        percent = float(value)
    except (TypeError, ValueError):
        percent = float(default)
    return float(min(30.0, max(0.0, percent)))


def resolve_ternary_limit_mode(mode: Any = None) -> str:
    """Resolve ternary limit mode from explicit value or app state fallback."""
    candidate = mode
    if candidate is None:
        candidate = getattr(app_state, 'ternary_limit_mode', None)

    token = str(candidate).strip().lower() if candidate is not None else ''
    if token in _VALID_LIMIT_MODES:
        return token

    anchor = str(getattr(app_state, 'ternary_limit_anchor', 'min')).strip().lower()
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
    manual = getattr(app_state, 'ternary_manual_limits', {}) or {}

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


def _equalized_window(min_val: float, max_val: float, span: float) -> tuple[float, float]:
    center = 0.5 * (min_val + max_val)
    low = center - 0.5 * span
    high = center + 0.5 * span

    if low < 0.0:
        high -= low
        low = 0.0
    if high > 1.0:
        low -= (high - 1.0)
        high = 1.0

    low = max(0.0, low)
    high = min(1.0, high)

    if (high - low) < span:
        if low <= _TERNARY_LIMIT_EPSILON:
            high = min(1.0, low + span)
        elif high >= (1.0 - _TERNARY_LIMIT_EPSILON):
            low = max(0.0, high - span)

    return float(low), float(high)


def _robust_bounds(vals: np.ndarray, trim_ratio: float) -> tuple[float, float]:
    finite = vals[np.isfinite(vals)]
    if finite.size == 0:
        return 0.0, 1.0

    low = float(np.nanmin(finite))
    high = float(np.nanmax(finite))
    if finite.size < 10 or trim_ratio <= _TERNARY_LIMIT_EPSILON:
        return low, high

    q_low = float(np.quantile(finite, trim_ratio))
    q_high = float(np.quantile(finite, 1.0 - trim_ratio))
    if np.isfinite(q_low) and np.isfinite(q_high) and q_high > q_low:
        return q_low, q_high
    return low, high


def _is_tiny_span(value: float, floor: float = _TERNARY_LIMIT_EPSILON) -> bool:
    """Return True when span is non-finite or effectively zero."""
    return (not np.isfinite(value)) or (float(value) <= float(floor))


def infer_ternary_limits(
    t_vals: Iterable[float],
    l_vals: Iterable[float],
    r_vals: Iterable[float],
    *,
    boundary_percent: float = 5.0,
) -> tuple[float, float, float, float, float, float]:
    """Infer ternary limits using data distribution and boundary percentage."""
    t_arr, l_arr, r_arr = normalize_ternary_components(t_vals, l_vals, r_vals)
    if t_arr.size == 0 or l_arr.size == 0 or r_arr.size == 0:
        return _FULL_TERNARY_LIMITS

    boundary_ratio = _sanitize_boundary_percent(boundary_percent) / 100.0
    trim_ratio = min(0.20, boundary_ratio * 0.5)

    tmin_raw, tmax_raw = _robust_bounds(t_arr, trim_ratio)
    lmin_raw, lmax_raw = _robust_bounds(l_arr, trim_ratio)
    rmin_raw, rmax_raw = _robust_bounds(r_arr, trim_ratio)

    mins = np.array([tmin_raw, lmin_raw, rmin_raw], dtype=float)
    maxs = np.array([tmax_raw, lmax_raw, rmax_raw], dtype=float)
    if not np.all(np.isfinite(mins)) or not np.all(np.isfinite(maxs)):
        return _FULL_TERNARY_LIMITS

    spans = np.maximum(maxs - mins, 0.0)
    base_span = float(np.nanmax(spans))
    if _is_tiny_span(base_span):
        base_span = 0.15

    span = min(1.0, base_span * (1.0 + 2.0 * boundary_ratio))
    span = max(span, 0.03)

    tmin, tmax = _equalized_window(mins[0], maxs[0], span)
    lmin, lmax = _equalized_window(mins[1], maxs[1], span)
    rmin, rmax = _equalized_window(mins[2], maxs[2], span)
    return tmin, tmax, lmin, lmax, rmin, rmax


def _apply_mode_limits(
    ax: Any,
    limits: tuple[float, float, float, float, float, float],
    *,
    mode: str,
    auto_zoom: bool,
) -> tuple[float, float, float, float, float, float]:
    tmin, tmax, lmin, lmax, rmin, rmax = limits

    if not auto_zoom:
        ax.set_ternary_lim(*limits)
        return limits

    if mode == 'max':
        ax.set_ternary_max(tmax, lmax, rmax)
        return (
            max(0.0, 1.0 - lmax - rmax), tmax,
            max(0.0, 1.0 - tmax - rmax), lmax,
            max(0.0, 1.0 - tmax - lmax), rmax,
        )

    if mode == 'min':
        ax.set_ternary_min(tmin, lmin, rmin)
        return (
            tmin, min(1.0, 1.0 - lmin - rmin),
            lmin, min(1.0, 1.0 - tmin - rmin),
            rmin, min(1.0, 1.0 - tmin - lmin),
        )

    ax.set_ternary_lim(*limits)
    return limits


def _collect_current_ternary_components() -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    cols = getattr(app_state, 'selected_ternary_cols', [])
    if not cols or len(cols) != 3:
        return None

    df_global = _df_global()
    if df_global is None or df_global.empty:
        return None

    subset_indices = _active_subset_indices()
    if subset_indices is not None:
        if len(subset_indices) == 0:
            return None
        df = df_global.iloc[sorted(list(subset_indices))].copy()
    else:
        df = df_global.copy()

    missing = [col for col in cols if col not in df.columns]
    if missing:
        logger.warning("Missing ternary columns during optimization: %s", missing)
        return None

    data = df[cols].apply(pd.to_numeric, errors='coerce').fillna(0.0).to_numpy(dtype=float)
    if data.size == 0:
        return None
    return data[:, 0], data[:, 1], data[:, 2]


def recommend_boundary_percent_from_components(
    t_vals: Iterable[float],
    l_vals: Iterable[float],
    r_vals: Iterable[float],
    *,
    mode: str,
    current_percent: float,
) -> float:
    """Recommend boundary percent from data spread and selected limit mode."""
    t_arr, l_arr, r_arr = normalize_ternary_components(t_vals, l_vals, r_vals)
    spans = np.array([
        float(np.nanmax(t_arr) - np.nanmin(t_arr)),
        float(np.nanmax(l_arr) - np.nanmin(l_arr)),
        float(np.nanmax(r_arr) - np.nanmin(r_arr)),
    ])
    base_span = float(np.nanmax(np.maximum(spans, 0.0)))

    if _is_tiny_span(base_span):
        computed = 12.0
    else:
        target_span = 0.78 if mode in ('min', 'max') else 0.72
        computed = ((target_span / base_span) - 1.0) * 50.0

    computed = _sanitize_boundary_percent(computed)
    current = _sanitize_boundary_percent(current_percent)
    blended = (0.65 * computed) + (0.35 * current)
    return round(_sanitize_boundary_percent(blended), 1)


def optimize_current_ternary_limits(
    *,
    mode: str | None = None,
    boundary_percent: float | None = None,
) -> dict[str, Any] | None:
    """Auto-optimize ternary limits using the current boundary percent.

    Boundary percent is treated as a user-controlled parameter and is not
    auto-estimated here.
    """
    components = _collect_current_ternary_components()
    if components is None:
        return None

    resolved_mode = resolve_ternary_limit_mode(mode)
    fixed_percent = _sanitize_boundary_percent(
        boundary_percent,
        default=getattr(app_state, 'ternary_boundary_percent', 5.0),
    )

    limits = infer_ternary_limits(*components, boundary_percent=fixed_percent)
    return {
        'mode': resolved_mode,
        'boundary_percent': fixed_percent,
        'limits': limits,
    }


def configure_ternary_axis(
    ax: Any,
    t_vals: Iterable[float],
    l_vals: Iterable[float],
    r_vals: Iterable[float],
    labels: tuple[str, str, str] | list[str] | None = None,
    *,
    auto_zoom: bool = True,
) -> tuple[float, float, float, float, float, float]:
    """Configure mpltern axis labels and limits."""
    if labels and len(labels) == 3:
        try:
            ax.set_tlabel(str(labels[0]))
            ax.set_llabel(str(labels[1]))
            ax.set_rlabel(str(labels[2]))
        except Exception:
            logger.debug("Failed to set ternary axis labels", exc_info=True)

    mode = resolve_ternary_limit_mode(getattr(app_state, 'ternary_limit_mode', None))
    boundary_percent = _sanitize_boundary_percent(getattr(app_state, 'ternary_boundary_percent', 5.0))
    state_gateway.set_ternary_limit_mode(mode)
    state_gateway.set_ternary_boundary_percent(boundary_percent)

    limits = _FULL_TERNARY_LIMITS
    if auto_zoom:
        use_manual = bool(getattr(app_state, 'ternary_manual_limits_enabled', False))
        if use_manual:
            limits = _resolve_manual_limits()
        else:
            limits = infer_ternary_limits(t_vals, l_vals, r_vals, boundary_percent=boundary_percent)

    try:
        limits = _apply_mode_limits(ax, limits, mode=mode, auto_zoom=bool(auto_zoom))
    except Exception:
        logger.warning("Invalid ternary limits %s, using full ternary range.", limits)
        limits = _FULL_TERNARY_LIMITS
        ax.set_ternary_lim(*limits)

    try:
        ax.set_aspect('equal', adjustable='box')
    except Exception:
        logger.debug("Failed to set equal aspect on ternary axis", exc_info=True)

    return limits


def calculate_auto_ternary_factors() -> bool:
    """Calculate optimal scaling factors for the ternary plot using geometric means.

    This effectively centers the data in the ternary diagram (compositional centering).
    """
    try:
        if not hasattr(app_state, 'selected_ternary_cols') or len(app_state.selected_ternary_cols) != 3:
            logger.warning("Factors calc: invalid col selection")
            return False

        cols = app_state.selected_ternary_cols
        df_global = _df_global()
        if df_global is None:
            logger.warning("Factors calc: no source dataframe available")
            return False

        subset_indices = _active_subset_indices()
        if subset_indices is not None:
            df = df_global.iloc[subset_indices].copy()
        else:
            df = df_global.copy()

        data = df[cols].apply(pd.to_numeric, errors='coerce').fillna(_TERNARY_FACTORS_FILL_VALUE).values
        data = np.maximum(data, _TERNARY_FACTORS_MIN_VALUE)

        gmeans = gmean(data, axis=0)

        factors = 1.0 / gmeans
        min_f = np.min(factors)
        if min_f > 0:
            factors = factors / min_f

        factors_list = factors.tolist()
        state_gateway.set_ternary_factors(factors_list)
        logger.info("Auto-Calculated Factors: %s", factors_list)
        return True

    except Exception as e:
        logger.error("Auto factor calculation failed: %s", e)
        return False


