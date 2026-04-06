# -*- coding: utf-8 -*-
"""Isochron utilities and regression helpers."""
from __future__ import annotations

from typing import Any

import numpy as np
try:
    from scipy.stats import chi2
except Exception:
    chi2 = None

from .engine import (
    engine,
    LAMBDA_238,
    LAMBDA_235,
    LAMBDA_232,
    A0,
    B0,
    C0,
    A1_SK,
    B1_SK,
    C1_SK,
    T_EARTH_CANON,
    T_SK_STAGE2,
    U_RATIO_NATURAL,
    MU_M_DEFAULT,
    OMEGA_M_DEFAULT,
    E1_DEFAULT,
    E2_DEFAULT,
    EPSILON,
    _exp_evolution_term,
)
from .age import _solve_age_scipy


_SOURCE_DEN_FLOOR = max(EPSILON, 1e-15)
_YORK_TOL_DEFAULT = 1e-15


def calculate_paleoisochron_line(
    age_ma: float,
    params: dict[str, Any] | None = None,
    algorithm: str = 'PB_EVOL_76',
) -> tuple[float, float] | None:
    """
    计算古等时线的斜率与截距。

    Args:
        age_ma (float): 年龄 (Ma)
        params (dict): 模型参数
        algorithm (str): 'PB_EVOL_76' 或 'PB_EVOL_86'

    Returns:
        tuple or None: (slope, intercept)
    """
    if params is None:
        params = engine.params

    t_years = float(age_ma) * 1e6
    lam238 = float(params.get('lambda_238', LAMBDA_238))
    lam235 = float(params.get('lambda_235', LAMBDA_235))
    lam232 = float(params.get('lambda_232', LAMBDA_232))

    T1 = float(params.get('Tsec', 0.0))
    if T1 <= 0:
        T1 = float(params.get('T2', params.get('T1', 0.0)))

    X1 = float(params.get('a1', A1_SK))
    Y1 = float(params.get('b1', B1_SK))
    Z1 = float(params.get('c1', C1_SK))

    e8T = np.exp(lam238 * T1)
    e8t = np.exp(lam238 * t_years)
    if e8T == e8t:
        return None

    if algorithm == 'PB_EVOL_76':
        U8U5 = 1.0 / float(params.get('U_ratio', U_RATIO_NATURAL))
        e5T = np.exp(lam235 * T1)
        e5t = np.exp(lam235 * t_years)
        slope = (e5T - e5t) / (U8U5 * (e8T - e8t))
        intercept = Y1 - slope * X1
        return slope, intercept
    if algorithm == 'PB_EVOL_86':
        mu_m = float(params.get('mu_M', MU_M_DEFAULT))
        omega_m = float(params.get('omega_M', OMEGA_M_DEFAULT))
        kappa = omega_m / mu_m if mu_m else 0.0
        e2T = np.exp(lam232 * T1)
        e2t = np.exp(lam232 * t_years)
        slope = kappa * (e2T - e2t) / (e8T - e8t) if kappa else 0.0
        intercept = Z1 - slope * X1
        return slope, intercept

    return None

def calculate_isochron1_growth_curve(
    slope: float,
    intercept: float,
    age_ma: float,
    params: dict[str, Any] | None = None,
    steps: int = 100,
) -> dict[str, Any] | None:
    """
    计算 207Pb/204Pb-206Pb/204Pb 等时线对应的生长曲线。

    Args:
        slope (float): 等时线斜率 (207/206)
        intercept (float): 等时线截距
        age_ma (float): 等时线年龄 (Ma)
        params (dict): 模型参数
        steps (int): 曲线采样点数

    Returns:
        dict or None: {'x', 'y', 'mu_source', 't_steps'}
    """
    if params is None:
        params = engine.params

    l238 = params['lambda_238']
    l235 = params['lambda_235']
    u_ratio = params['U_ratio']

    is_two_stage = params.get('age_model', 'single_stage') == 'two_stage'
    T_start_curve = params.get('T1', T_SK_STAGE2)
    a_start = params.get('a1', A1_SK)
    b_start = params.get('b1', B1_SK)

    t_years = float(age_ma) * 1e6
    t_steps = np.linspace(0, T_start_curve, int(steps))

    E1_val = params.get('E1', E1_DEFAULT)

    C_alpha = _exp_evolution_term(l238, T_start_curve, E1_val) - _exp_evolution_term(l238, t_years, E1_val)
    C_beta = u_ratio * (_exp_evolution_term(l235, T_start_curve, E1_val) - _exp_evolution_term(l235, t_years, E1_val))

    denom = C_beta - slope * C_alpha
    if abs(denom) <= _SOURCE_DEN_FLOOR:
        return None

    mu_source = (slope * a_start + intercept - b_start) / denom
    x_growth = a_start + mu_source * (_exp_evolution_term(l238, T_start_curve, E1_val) - _exp_evolution_term(l238, t_steps, E1_val))
    y_growth = b_start + mu_source * u_ratio * (_exp_evolution_term(l235, T_start_curve, E1_val) - _exp_evolution_term(l235, t_steps, E1_val))

    return {
        'x': x_growth,
        'y': y_growth,
        'mu_source': mu_source,
        't_steps': t_steps
    }

def calculate_isochron2_growth_curve(
    slope_208: float,
    slope_207: float,
    intercept_207: float,
    age_ma: float,
    params: dict[str, Any] | None = None,
    steps: int = 100,
) -> dict[str, Any] | None:
    """
    计算 208Pb/204Pb-206Pb/204Pb 等时线对应的生长曲线 (需 207/206 约束)。

    Args:
        slope_208 (float): 208/206 等时线斜率
        slope_207 (float): 207/206 等时线斜率
        intercept_207 (float): 207/206 等时线截距
        age_ma (float): 年龄 (Ma)
        params (dict): 模型参数
        steps (int): 曲线采样点数

    Returns:
        dict or None: {'x', 'y', 'mu_source', 'kappa_source', 't_steps'}
    """
    if params is None:
        params = engine.params

    kappa_source = calculate_source_kappa_from_slope(slope_208, age_ma, params=params)
    mu_source = calculate_source_mu_from_isochron(slope_207, intercept_207, age_ma, params=params)

    if not kappa_source or not mu_source or kappa_source <= 0 or mu_source <= 0:
        return None

    l238 = params['lambda_238']
    l232 = params['lambda_232']
    T_start = params.get('T1', params.get('T2', T_EARTH_CANON))
    a0 = params.get('a1', params.get('a0', A0))
    c0 = params.get('c1', params.get('c0', C0))
    E1_val = params.get('E1', E1_DEFAULT)
    E2_val = params.get('E2', E2_DEFAULT)

    omega_source = mu_source * kappa_source
    t_steps = np.linspace(0, T_start, int(steps))

    x_growth = a0 + mu_source * (_exp_evolution_term(l238, T_start, E1_val) - _exp_evolution_term(l238, t_steps, E1_val))
    y_growth = c0 + omega_source * (_exp_evolution_term(l232, T_start, E2_val) - _exp_evolution_term(l232, t_steps, E2_val))

    return {
        'x': x_growth,
        'y': y_growth,
        'mu_source': mu_source,
        'kappa_source': kappa_source,
        't_steps': t_steps
    }

def york_regression(
    x: np.ndarray,
    sx: np.ndarray,
    y: np.ndarray,
    sy: np.ndarray,
    rxy: np.ndarray | None = None,
    max_iter: int = 50,
    tol: float = _YORK_TOL_DEFAULT,
) -> dict[str, Any]:
    """York (2004) regression with correlated errors.

    Args:
        x, y: data arrays
        sx, sy: 1-sigma uncertainties for x and y
        rxy: correlation coefficients between x and y
    Returns:
        dict with slope/intercept, errors, cov, mswd, p_value, df
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    sx = np.asarray(sx, dtype=float)
    sy = np.asarray(sy, dtype=float)
    if rxy is None:
        rxy = np.zeros_like(x, dtype=float)
    else:
        rxy = np.asarray(rxy, dtype=float)

    if x.size < 2:
        raise ValueError("At least two points are required for York regression.")

    rxy = np.clip(rxy, -0.999999, 0.999999)

    if np.any(sx <= 0) or np.any(sy <= 0):
        raise ValueError("All uncertainties must be > 0 for York regression.")

    ab = np.polyfit(x, y, 1)
    b = float(ab[0])
    if not np.isfinite(b):
        raise ValueError("Cannot fit a straight line through these data.")

    wX = 1.0 / (sx ** 2)
    wY = 1.0 / (sy ** 2)

    for _ in range(max_iter):
        bold = b
        A = np.sqrt(wX * wY)
        denom = wX + b * b * wY - 2.0 * b * rxy * A
        denom = np.where(denom <= 0, np.nan, denom)
        W = wX * wY / denom
        if not np.all(np.isfinite(W)):
            raise ValueError("Invalid weights in York regression.")

        Xbar = np.nansum(W * x) / np.nansum(W)
        Ybar = np.nansum(W * y) / np.nansum(W)
        U = x - Xbar
        V = y - Ybar
        B = W * (U / wY + b * V / wX - (b * U + V) * rxy / A)
        b = np.nansum(W * B * V) / np.nansum(W * B * U)
        if b != 0 and (bold / b - 1) ** 2 < tol:
            break

    a = Ybar - b * Xbar
    xadj = Xbar + B
    xbar = np.nansum(W * xadj) / np.nansum(W)
    u = xadj - xbar
    sb = np.sqrt(1.0 / np.nansum(W * u * u))
    sa = np.sqrt(1.0 / np.nansum(W) + (xbar * sb) ** 2)
    cov_ab = -xbar * sb ** 2

    chi2_val = np.nansum(W * (y - (b * x + a)) ** 2)
    df = int(x.size - 2)
    mswd = chi2_val / df if df > 0 else np.nan
    p_value = 1.0 - chi2.cdf(chi2_val, df) if chi2 is not None and df > 0 else np.nan

    return {
        'a': a,
        'b': b,
        'sa': sa,
        'sb': sb,
        'cov_ab': cov_ab,
        'mswd': mswd,
        'p_value': p_value,
        'df': df,
    }

def calculate_pbpb_age_from_ratio(
    r76: float,
    sr76: float | None = None,
    params: dict[str, Any] | None = None,
) -> tuple[float, float | None]:
    """Calculate Pb-Pb age from 207Pb/206Pb ratio and its uncertainty."""
    if params is None:
        params = engine.params

    if r76 <= 0:
        return 0.0, None

    l238 = params['lambda_238']
    l235 = params['lambda_235']
    u_ratio = params['U_ratio']

    def f(t: float) -> float:
        if t <= 0:
            return -r76
        num = np.exp(l235 * t) - 1.0
        den = np.exp(l238 * t) - 1.0
        if abs(den) < EPSILON:
            den = EPSILON
        return (u_ratio * num / den) - r76

    res = _solve_age_scipy(f, bounds=(1e6, 10e9))
    if not res:
        return 0.0, None

    age_ma = res / 1e6

    if sr76 is None:
        return age_ma, None

    e5 = np.exp(l235 * res)
    e8 = np.exp(l238 * res)
    den = (e8 - 1.0) ** 2
    if abs(den) < EPSILON:
        return age_ma, None

    dRdt = u_ratio * ((l235 * e5 * (e8 - 1.0)) - ((e5 - 1.0) * l238 * e8)) / den
    if dRdt == 0:
        return age_ma, None

    dt_dR = 1.0 / dRdt
    age_err_ma = abs(dt_dR * sr76) / 1e6
    return age_ma, age_err_ma

def calculate_isochron_age_from_slope(
    slope: float,
    params: dict[str, Any] | None = None,
) -> float:
    """
    从 Pb-Pb 等时线斜率计算年龄

    对于 207Pb/204Pb vs 206Pb/204Pb 图，等时线斜率为：
    Slope = (235U/238U) * (exp(λ235*t) - 1) / (exp(λ238*t) - 1)
          = U_ratio * (exp(λ235*t) - 1) / (exp(λ238*t) - 1)

    其中 U_ratio = 235U/238U ≈ 1/137.88 ≈ 0.00725
    """
    age_ma, _ = calculate_pbpb_age_from_ratio(slope, sr76=None, params=params)
    return age_ma

def calculate_source_mu_from_isochron(
    slope: float,
    intercept: float,
    age_ma: float,
    params: dict[str, Any] | None = None,
) -> float:
    """从等时线参数反演源区 Mu (model-aware: 使用 T1, a1, b1)"""
    if params is None:
        params = engine.params

    T = params['T1']
    t = age_ma * 1e6
    u_r = params['U_ratio']

    C1 = np.exp(params['lambda_238'] * T) - np.exp(params['lambda_238'] * t)
    C2 = u_r * (np.exp(params['lambda_235'] * T) - np.exp(params['lambda_235'] * t))

    num = slope * params['a1'] + intercept - params['b1']
    den = C2 - slope * C1

    return num / den if abs(den) > _SOURCE_DEN_FLOOR else 0.0

def calculate_source_kappa_from_slope(
    slope_208_206: float,
    age_ma: float,
    params: dict[str, Any] | None = None,
) -> float:
    """从 208/204 vs 206/204 斜率反演源区 Kappa (model-aware: 使用 T1)"""
    if params is None:
        params = engine.params

    T = params['T1']
    t = age_ma * 1e6
    
    num = np.exp(params['lambda_238'] * T) - np.exp(params['lambda_238'] * t)
    den = np.exp(params['lambda_232'] * T) - np.exp(params['lambda_232'] * t)
    
    return slope_208_206 * (num / den) if abs(den) > _SOURCE_DEN_FLOOR else 0.0
