"""Source parameter inversion and initial ratios."""
from __future__ import annotations

from typing import Any

import numpy as np

from .engine import (
    engine,
    ALBAREDE_KAPPA_STAR,
    ALBAREDE_MU_STAR,
    ALBAREDE_T0,
    ALBAREDE_X_STAR,
    ALBAREDE_Z_STAR,
    EPSILON,
)


# =============================================================================
# Internal core functions - unified inversion algorithms
# =============================================================================


def _safe_denominator(values: np.ndarray | float) -> np.ndarray:
    """Apply shared denominator floor for scalar/array-like values.

    Preserves the sign of tiny values so small negative denominators do not
    flip the sign of the quotient near singularities.
    """
    arr = np.asarray(values, dtype=float)
    return np.where(np.abs(arr) < EPSILON, np.copysign(EPSILON, arr), arr)


def _prepare_age(t_Ma: np.ndarray | float | None) -> np.ndarray:
    """Age preprocessing: Ma -> years; None -> NaN and negative values clamp to 0."""
    if t_Ma is None:
        return np.array(np.nan)
    try:
        t = np.asarray(t_Ma, dtype=float)
    except (ValueError, TypeError):
        t_arr = np.asarray(t_Ma)
        if t_arr.ndim == 0:
            return np.array(np.nan)
        t_flat = []
        for x in t_arr.ravel():
            try:
                t_flat.append(float(x))
            except (ValueError, TypeError):
                t_flat.append(np.nan)
        t = np.array(t_flat).reshape(t_arr.shape)
    return np.maximum(t, 0) * 1e6


def _prepare_age_signed(t_Ma: np.ndarray | float | None) -> np.ndarray:
    """Age preprocessing: Ma -> years, handling None/bad values but preserving sign.

    Negative AJ84 model ages are physically meaningful (source μ below the
    reference μ*; the Pb is less radiogenic than modern common Pb), so they
    must not be clamped to 0 the way the PbIso convention does.
    """
    if t_Ma is None:
        return np.array(np.nan)
    try:
        t = np.asarray(t_Ma, dtype=float)
    except (ValueError, TypeError):
        return np.array(np.nan)
    return t * 1e6


def _is_two_stage_model(params: dict[str, Any]) -> bool:
    """Return True when params indicate two-stage mode."""
    mode = str(params.get('age_model', '')).strip().lower().replace('_', '-')
    return mode in ('two-stage', 'two stage', '2-stage', '2nd', 'second')


def _model_reference_params(params: dict[str, Any]) -> tuple[float, float, float, float]:
    """Resolve reference (X, Y, Z, T) by model stage type.

    Single-stage models use primordial reference (a0/b0/c0, T2).
    Two-stage models use second-stage reference (a1/b1/c1, T1).
    """
    if _is_two_stage_model(params):
        return (
            params.get('a1', params.get('a0')),
            params.get('b1', params.get('b0')),
            params.get('c1', params.get('c0')),
            params.get('T1', params.get('T2')),
        )
    return (
        params.get('a0', params.get('a1')),
        params.get('b0', params.get('b1')),
        params.get('c0', params.get('c1')),
        params.get('T2', params.get('T1')),
    )


def _invert_mu(
    x: np.ndarray | float,
    y: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    X_ref: float,
    Y_ref: float,
    T_ref: float,
    params: dict[str, Any],
) -> np.ndarray:
    """Unified μ (238U/204Pb) inversion core.

    Projects through today's isochron slope and combines the 206Pb and 207Pb
    constraints to solve for the source μ.

    Args:
        x: sample 206Pb/204Pb
        y: sample 207Pb/204Pb
        t_Ma: sample age (Ma)
        X_ref: reference 206Pb/204Pb (a0 or a1)
        Y_ref: reference 207Pb/204Pb (b0 or b1)
        T_ref: reference start time (T2 or T1), in years
        params: parameter dict

    Returns:
        np.ndarray: source μ
    """
    l238 = params['lambda_238']
    l235 = params['lambda_235']
    u_ratio = params['U_ratio']

    x = np.asarray(x)
    y = np.asarray(y)
    t = _prepare_age(t_Ma)

    # Today's isochron slope
    e5t = np.exp(l235 * t)
    e8t = np.exp(l238 * t)
    den_slope = e8t - 1
    den_slope = _safe_denominator(den_slope)
    slope_t = u_ratio * (e5t - 1) / den_slope

    # Radiogenic increments
    rad207 = u_ratio * (np.exp(l235 * T_ref) - e5t)
    rad206 = np.exp(l238 * T_ref) - e8t

    # Solve for μ
    numerator = (y - Y_ref) - slope_t * (x - X_ref)
    denominator = rad207 - slope_t * rad206
    denominator = _safe_denominator(denominator)

    return numerator / denominator


def _invert_omega(
    z: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    Z_ref: float,
    T_ref: float,
    params: dict[str, Any],
) -> np.ndarray:
    """Unified ω (232Th/204Pb) inversion core.

    Solved directly from the 208Pb growth equation:
    ω = (z − Z_ref) / [exp(λ232·T) − exp(λ232·t)]

    Args:
        z: sample 208Pb/204Pb
        t_Ma: sample age (Ma)
        Z_ref: reference 208Pb/204Pb (c0 or c1)
        T_ref: reference start time, in years
        params: parameter dict

    Returns:
        np.ndarray: source ω
    """
    l232 = params['lambda_232']

    z = np.asarray(z)
    t = _prepare_age(t_Ma)

    denom = np.exp(l232 * T_ref) - np.exp(l232 * t)
    denom = _safe_denominator(denom)

    return (z - Z_ref) / denom


def _invert_kappa(
    x: np.ndarray | float,
    z: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    X_ref: float,
    Z_ref: float,
    T_ref: float,
    params: dict[str, Any],
) -> np.ndarray:
    """Unified κ (232Th/238U) inversion core.

    Eliminates μ from the ratio of the 206Pb and 208Pb growth equations:
    κ = [(z−Z_ref)/(x−X_ref)] × [exp(λ238·T)−exp(λ238·t)] / [exp(λ232·T)−exp(λ232·t)]

    Args:
        x: sample 206Pb/204Pb
        z: sample 208Pb/204Pb
        t_Ma: sample age (Ma)
        X_ref: reference 206Pb/204Pb (a0 or a1)
        Z_ref: reference 208Pb/204Pb (c0 or c1)
        T_ref: reference start time, in years
        params: parameter dict

    Returns:
        np.ndarray: source κ
    """
    l238 = params['lambda_238']
    l232 = params['lambda_232']

    x = np.asarray(x)
    z = np.asarray(z)
    t = _prepare_age(t_Ma)

    num_time = np.exp(l238 * T_ref) - np.exp(l238 * t)
    den_time = np.exp(l232 * T_ref) - np.exp(l232 * t)
    den_time = _safe_denominator(den_time)

    dx = x - X_ref
    dx = _safe_denominator(dx)

    return ((z - Z_ref) / dx) * (num_time / den_time)


# =============================================================================
# Public API - single-stage reference (CDT: a0/b0/c0, T2)
# =============================================================================

def calculate_source_mu(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """Source Mu (238U/204Pb) using the primordial-lead (single-stage) reference.

    Uses the CDT primordial-lead reference (a0, b0) and Earth age T2.

    Returns:
        np.ndarray: source Mu
    """
    if params is None:
        params = engine.params
    return _invert_mu(Pb206_204_S, Pb207_204_S, t_Ma,
                      params['a0'], params['b0'], params['T2'], params)


def calculate_source_omega(
    Pb208_204_S: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """Source Omega (232Th/204Pb) using the primordial-lead (single-stage) reference.

    Uses the CDT primordial-lead reference (c0) and Earth age T2.
    """
    if params is None:
        params = engine.params
    return _invert_omega(Pb208_204_S, t_Ma,
                         params['c0'], params['T2'], params)


def calculate_source_nu(
    mu: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray | float:
    """Source Nu (235U/204Pb): nu = mu * (235U/238U)."""
    if params is None:
        params = engine.params
    return mu * params['U_ratio']


# =============================================================================
# Public API - model reference (selected from age_model)
# =============================================================================

def calculate_model_mu(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """Model source Mu (PbIso's CalcMu equivalent) with the model reference.

    Picks the reference parameters from age_model:
    - two_stage: (T1, a1, b1)
    - single_stage: (T2, a0, b0)
    Works for any configured geochemistry model (SK, CR, MM, ...).

    Args:
        Pb206_204_S, Pb207_204_S: sample isotope ratios
        t_Ma: sample age (Ma)

    Returns:
        np.ndarray: source Mu, the 238U/204Pb ratio of the T1 -> t stage.
    """
    if params is None:
        params = engine.params
    x_ref, y_ref, _, t_ref = _model_reference_params(params)
    return _invert_mu(Pb206_204_S, Pb207_204_S, t_Ma,
                      x_ref, y_ref, t_ref, params)


def calculate_model_kappa(
    Pb206_204_S: np.ndarray | float,
    Pb208_204_S: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """Model source Kappa (Th/U) (PbIso's CalcKa equivalent) with the model reference.

    Picks the reference parameters from age_model:
    - two_stage: (T1, a1, c1)
    - single_stage: (T2, a0, c0)
    Works for any configured geochemistry model.

    Args:
        Pb206_204_S: sample 206Pb/204Pb ratio
        Pb208_204_S: sample 208Pb/204Pb ratio
        t_Ma: sample age (Ma)

    Returns:
        np.ndarray: source Kappa (232Th/238U)
    """
    if params is None:
        params = engine.params
    x_ref, _, z_ref, t_ref = _model_reference_params(params)
    return _invert_kappa(Pb206_204_S, Pb208_204_S, t_Ma,
                         x_ref, z_ref, t_ref, params)


# =============================================================================
# Initial-ratio inversion (reuses calculate_model_mu / calculate_model_kappa)
# =============================================================================

def calculate_initial_ratio_64(
    t_Ma: np.ndarray | float,
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """Initial 206Pb/204Pb at sample formation (PbIso's Calc64in)."""
    if params is None:
        params = engine.params
    mu = calculate_model_mu(Pb206_204_S, Pb207_204_S, t_Ma, params)
    x_ref, _, _, t_ref = _model_reference_params(params)
    # Use the same age handling as the μ/κ inversion (None -> NaN, clamp >= 0);
    # otherwise the age would differ from the one used for μ.
    t = _prepare_age(t_Ma)
    e8T = np.exp(params['lambda_238'] * t_ref)
    e8t = np.exp(params['lambda_238'] * t)
    return x_ref + mu * (e8T - e8t)


def calculate_initial_ratio_74(
    t_Ma: np.ndarray | float,
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """Initial 207Pb/204Pb at sample formation (PbIso's Calc74in)."""
    if params is None:
        params = engine.params
    mu = calculate_model_mu(Pb206_204_S, Pb207_204_S, t_Ma, params)
    _, y_ref, _, t_ref = _model_reference_params(params)
    t = _prepare_age(t_Ma)
    U8U5 = 1.0 / params['U_ratio']
    e5T = np.exp(params['lambda_235'] * t_ref)
    e5t = np.exp(params['lambda_235'] * t)
    return y_ref + (mu / U8U5) * (e5T - e5t)


def calculate_initial_ratio_84(
    t_Ma: np.ndarray | float,
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    Pb208_204_S: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """Initial 208Pb/204Pb at sample formation (PbIso's Calc84in)."""
    if params is None:
        params = engine.params
    mu = calculate_model_mu(Pb206_204_S, Pb207_204_S, t_Ma, params)
    kappa = calculate_model_kappa(Pb206_204_S, Pb208_204_S, t_Ma, params)
    omega = kappa * mu
    _, _, z_ref, t_ref = _model_reference_params(params)
    t = _prepare_age(t_Ma)
    e2T = np.exp(params['lambda_232'] * t_ref)
    e2t = np.exp(params['lambda_232'] * t)
    return z_ref + omega * (e2T - e2t)


# =============================================================================
# Albarède & Juteau (1984) T–μ–κ model - source parameters
# =============================================================================
# Reference: Albarède, F. & Juteau, M. (1984). GCA 48(1), 207-212.
#       doi:10.1016/0016-7037(84)90364-8
# Constants in engine.py §1.9. AJ84 gives absolute values directly from the
# x/z growth equations:
#     μ_i = (x_i − x0) / (e^{λT0} − e^{λT_i})
#     κ_i = (z_i − z0) / [(e^{λ''T0} − e^{λ''T_i}) · μ_i]
# The Δμ/Δκ notation relative to the modern common-Pb reference (from the
# 2012 edition) is also provided: μ_i = μ* + Δμ_i, κ_i = κ* + Δκ_i.
# T_i may be negative (negative model ages are physical, see age.py), hence
# _prepare_age_signed() instead of the clamping _prepare_age().


def calculate_albarede_delta_mu(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """Albarède & Juteau (1984) source Δμ_i = μ_i − μ*.

    From the x growth equation (x0 = x* − μ*(e^{λT0} − 1)):
    Δμ_i = [x_i − x* + μ*(e^{λT_i} − 1)] / (e^{λT0} − e^{λT_i}).

    Args:
        Pb206_204_S, Pb207_204_S: sample 206Pb/204Pb and 207Pb/204Pb
        t_Ma: model age T_i (Ma), from calculate_albarede_model_age
        params: parameter dict (optional)

    Returns:
        np.ndarray: Δμ_i
    """
    if params is None:
        params = engine.params
    l238 = params['lambda_238']

    x = np.asarray(Pb206_204_S, dtype=float)
    t = _prepare_age_signed(t_Ma)

    numerator = x - ALBAREDE_X_STAR + ALBAREDE_MU_STAR * (np.exp(l238 * t) - 1.0)
    denominator = np.exp(l238 * ALBAREDE_T0) - np.exp(l238 * t)
    denominator = _safe_denominator(denominator)
    return numerator / denominator


def calculate_albarede_mu(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """Albarède & Juteau (1984) source μ_i = ²³⁸U/²⁰⁴Pb = μ* + Δμ_i.

    Returns:
        np.ndarray: μ_i
    """
    if params is None:
        params = engine.params
    return calculate_albarede_delta_mu(Pb206_204_S, Pb207_204_S, t_Ma, params) + ALBAREDE_MU_STAR


def calculate_albarede_delta_kappa(
    Pb206_204_S: np.ndarray | float,
    Pb208_204_S: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    mu_value: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """Albarède & Juteau (1984) source Δκ_i = κ_i − κ*.

    From the z growth equation (z0 = z* − μ*κ*(e^{λ''T0} − 1)):
        Δκ_i = { [z_i − z* + μ*κ*(e^{λ''T_i} − 1)] / (e^{λ''T0} − e^{λ''T_i})
                 − κ* Δμ_i } / μ_i

    (The printed form of eq. (15) in the 2012 edition makes Δκ_i cancel itself
    and generally have no fixed-point solution, so it is not used; see
    docs/geochemistry.md §16.5.)

    Args:
        Pb206_204_S, Pb208_204_S: sample 206Pb/204Pb and 208Pb/204Pb
        t_Ma: model age T_i (Ma)
        mu_value: μ_i of the same sample (from calculate_albarede_mu)
        params: parameter dict (optional)

    Returns:
        np.ndarray: Δκ_i
    """
    if params is None:
        params = engine.params
    l232 = params['lambda_232']

    z = np.asarray(Pb208_204_S, dtype=float)
    mu = np.asarray(mu_value, dtype=float)
    t = _prepare_age_signed(t_Ma)

    denominator = np.exp(l232 * ALBAREDE_T0) - np.exp(l232 * t)
    denominator = _safe_denominator(denominator)

    delta_mu = mu - ALBAREDE_MU_STAR
    combined = (
        z - ALBAREDE_Z_STAR
        + ALBAREDE_MU_STAR * ALBAREDE_KAPPA_STAR * (np.exp(l232 * t) - 1.0)
    ) / denominator

    return (combined - ALBAREDE_KAPPA_STAR * delta_mu) / _safe_denominator(mu)


def calculate_albarede_kappa(
    Pb206_204_S: np.ndarray | float,
    Pb208_204_S: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    mu_value: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """Albarède & Juteau (1984) source κ_i = ²³²Th/²³⁸U = κ* + Δκ_i.

    Returns:
        np.ndarray: κ_i
    """
    if params is None:
        params = engine.params
    return calculate_albarede_delta_kappa(
        Pb206_204_S, Pb208_204_S, t_Ma, mu_value, params
    ) + ALBAREDE_KAPPA_STAR



