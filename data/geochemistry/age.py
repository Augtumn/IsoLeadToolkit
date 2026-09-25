# -*- coding: utf-8 -*-
"""Model age calculations."""
from __future__ import annotations

import logging
import math
from typing import Any, Callable

import numpy as np
from scipy import optimize

from .engine import (
    engine,
    ALBAREDE_MU_STAR,
    ALBAREDE_T0,
    ALBAREDE_X_STAR,
    ALBAREDE_Y_STAR,
    EPSILON,
    calculate_model_slope,
)

logger = logging.getLogger(__name__)


_RATIO_DIFF_FLOOR = 1e-10
_SOLVER_GUARD_VALUE = 1e10
_AGE_SOLVER_XTOL = 1e-6
_AGE_SOLVER_ENDPOINT_MARGIN = 1.0
_AGE_SOLVER_BOUNDS = (-4700e6, 4700e6)
_SOLVER_ZERO_EPSILON: float = 1e-15


def _safe_scalar_denominator(value: float) -> float:
    """Apply shared scalar denominator floor to avoid division singularity.

    Preserves the sign of tiny values: flipping small negative denominators
    to +EPSILON changes the sign of the quotient and can manufacture
    spurious model ages or ±1e50 μ/ω near t ≈ T.
    """
    value = float(value)
    if abs(value) < EPSILON:
        return math.copysign(EPSILON, value)
    return value


def _solve_age_scipy(
    f: Callable[[float], float],
    bounds: tuple[float, float],
    search_points: int = 200,
) -> float | None:
    """
    使用 Brent 方法求解年龄方程的根
    
    Args:
        f (callable): 目标函数 f(t) = 0
        bounds (tuple): 求解区间 (t_min, t_max)
        
    Returns:
        float or None: 求解得到的年龄 (年)，若失败返回 None
    """
    t_min, t_max = bounds
    t_max_safe = t_max - _AGE_SOLVER_ENDPOINT_MARGIN  # 避免端点奇点

    def _eval(val: float) -> float:
        try:
            out = f(val)
            return out if np.isfinite(out) else np.nan
        except Exception as exc:
            logger.debug("Age objective evaluation failed at t=%s: %s", val, exc)
            return np.nan

    try:
        f_min = _eval(t_min)
        f_max = _eval(t_max_safe)

        if np.isnan(f_min) or np.isnan(f_max):
            f_min = np.nan
            f_max = np.nan

        # 如果端点满足异号，直接求解
        if np.isfinite(f_min) and np.isfinite(f_max) and f_min * f_max <= 0:
            return optimize.brentq(f, t_min, t_max_safe, xtol=_AGE_SOLVER_XTOL)

        # 类似 R 的 extendInt：在区间内扫描寻找变号区间
        t_samples = np.linspace(t_min, t_max_safe, search_points)
        f_samples = np.array([_eval(t) for t in t_samples])

        for i in range(len(t_samples) - 1):
            f1, f2 = f_samples[i], f_samples[i + 1]
            if not (np.isfinite(f1) and np.isfinite(f2)):
                continue
            if abs(float(f1)) < _SOLVER_ZERO_EPSILON:
                return t_samples[i]
            if f1 * f2 < 0:
                return optimize.brentq(f, t_samples[i], t_samples[i + 1], xtol=_AGE_SOLVER_XTOL)

        return None
    except Exception as exc:
        logger.warning("Age solver failed over bounds %s: %s", bounds, exc)
        return None

def calculate_single_stage_age(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    params: dict[str, Any] | None = None,
    initial_age: float | None = None,
) -> np.ndarray | float | None:
    """
    计算单阶段模式年龄 (Single Stage Model Age)
    通常称为 Holmes-Houtermans 年龄或 CDT 模式年龄。
    
    基于方程:
    (207Pb/204Pb_S - b0) / (206Pb/204Pb_S - a0) = (1/137.88) * (e^λ5*T - e^λ5*t) / (e^λ8*T - e^λ8*t)
    
    Args:
        Pb206_204_S: 样品 206Pb/204Pb 比值 (标量或数组)
        Pb207_204_S: 样品 207Pb/204Pb 比值 (标量或数组)
        params: 参数字典 (可选)
        initial_age: 初始演化时间 T (默认为 params['T2'])
        
    Returns:
        np.ndarray or float: 模式年龄 (Ma)
    """
    if params is None:
        params = engine.params
    
    l238 = params['lambda_238']
    l235 = params['lambda_235']
    T = initial_age if initial_age is not None else params['T2']
    
    a0_val = params['a0']
    b0_val = params['b0']
    u_ratio = params['U_ratio']

    # 统一转换为数组处理
    S206 = np.asarray(Pb206_204_S)
    S207 = np.asarray(Pb207_204_S)
    
    # 标量处理优化
    if S206.ndim == 0:
        def f(t: float) -> float:
            denom = np.exp(l238 * T) - np.exp(l238 * t)
            denom = _safe_scalar_denominator(float(denom))
            num = np.exp(l235 * T) - np.exp(l235 * t)
            
            if abs(S206 - a0_val) < _RATIO_DIFF_FLOOR:
                return _SOLVER_GUARD_VALUE
                
            R = (S207 - b0_val) / (S206 - a0_val)
            return R - u_ratio * num / denom
        
        t_result = _solve_age_scipy(f, bounds=_AGE_SOLVER_BOUNDS)
        return t_result / 1e6 if t_result is not None else None
    
    # 数组处理
    results = []
    for s206, s207 in zip(S206.ravel(), S207.ravel()):
        if np.isnan(s206) or np.isnan(s207):
            results.append(np.nan)
            continue

        def f_scalar(t: float) -> float:
            denom = np.exp(l238 * T) - np.exp(l238 * t)
            denom = _safe_scalar_denominator(float(denom))
            num = np.exp(l235 * T) - np.exp(l235 * t)
            
            if abs(s206 - a0_val) < _RATIO_DIFF_FLOOR:  # 避免除零
                return _SOLVER_GUARD_VALUE
            
            R = (s207 - b0_val) / (s206 - a0_val)
            return R - u_ratio * num / denom

        t_res = _solve_age_scipy(f_scalar, bounds=_AGE_SOLVER_BOUNDS)
        results.append(t_res / 1e6 if t_res is not None else np.nan)
        
    return np.array(results).reshape(S206.shape)

def calculate_two_stage_age(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray | float | None:
    """
    计算两阶段模式年龄 (Two Stage Model Age - Stacey & Kramers)
    基于 SK 模型第二阶段方程求解。
    
    Args:
        Pb206_204_S: 样品 206Pb/204Pb 比值
        Pb207_204_S: 样品 207Pb/204Pb 比值
        
    Returns:
        np.ndarray or float: 模式年龄 (Ma)
    """
    if params is None:
        params = engine.params

    l238 = params['lambda_238']
    l235 = params['lambda_235']
    T = params['Tsec'] # SK 模型第二阶段起始
    a1_val = params['a1']
    b1_val = params['b1']
    u_ratio = params['U_ratio']

    S206 = np.asarray(Pb206_204_S)
    S207 = np.asarray(Pb207_204_S)

    # 标量处理
    if S206.ndim == 0:
        def f(t: float) -> float:
            denom = np.exp(l238 * T) - np.exp(l238 * t)
            denom = _safe_scalar_denominator(float(denom))
            num = np.exp(l235 * T) - np.exp(l235 * t)
            
            if abs(S206 - a1_val) < _RATIO_DIFF_FLOOR:
                return _SOLVER_GUARD_VALUE
                
            R = (S207 - b1_val) / (S206 - a1_val)
            return R - u_ratio * num / denom
        
        t_result = _solve_age_scipy(f, bounds=_AGE_SOLVER_BOUNDS)
        return t_result / 1e6 if t_result is not None else None
    
    # 数组处理
    results = []
    for s206, s207 in zip(S206.ravel(), S207.ravel()):
        if np.isnan(s206) or np.isnan(s207):
            results.append(np.nan)
            continue
            
        def f_scalar(t: float) -> float:
            denom = np.exp(l238 * T) - np.exp(l238 * t)
            denom = _safe_scalar_denominator(float(denom))
            num = np.exp(l235 * T) - np.exp(l235 * t)
            
            if abs(s206 - a1_val) < _RATIO_DIFF_FLOOR:
                return _SOLVER_GUARD_VALUE
                
            R = (s207 - b1_val) / (s206 - a1_val)
            return R - u_ratio * num / denom
        
        t_res = _solve_age_scipy(f_scalar, bounds=_AGE_SOLVER_BOUNDS)
        results.append(t_res / 1e6 if t_res is not None else np.nan)

    return np.array(results).reshape(S206.shape)


# =============================================================================
# Albarède & Juteau (1984) T–μ–κ 模型 — 模式年龄
# =============================================================================
# 参考: Albarède, F. & Juteau, M. (1984). GCA 48(1), 207-212.
#       doi:10.1016/0016-7037(84)90364-8
# 常数见 engine.py §1.9 (与 ASTR::albarede_juteau_1984() 一致)。
#
# AJ84 对两条生长方程同时求解 (T_i, μ_i) (原脚本/ASTR 用 rootSolve::multiroot):
#     x_i = x0 + μ_i (e^{λT0} − e^{λT_i})
#     y_i = y0 + (μ_i/U)(e^{λ'T0} − e^{λ'T_i})
# 本模块用消去 μ_i 后的等价 1-D 残差 (同一常数下两者相差 ≤ 3.5e-12 Ma)。
#
# 求解区间 T_i ∈ (−4·T0, T0) ≈ (−15.2 Ga, 3.8 Ga):
#   负年龄是合法结果 —— ²⁰⁷Pb/²⁰⁴Pb 低于现代参考即源区 μ < μ* (U 相对贫化),
#   参考矿石库 6938 行中有 407 行 Tmod < 0 (最低 −8980 Ma)。
#   区间内无根才返回 NaN (如 206/204 = x* 时, y 只在 (14.06, 22.68) 内有解)。

_ALBAREDE_SEARCH_POINTS = 400
#: 负向扫描跨度 (以 T0 为单位), 覆盖参考生长曲线的负年龄分支。
_ALBAREDE_NEGATIVE_SPAN = 4.0


def albarede_model_age_residual(
    t_Ma: np.ndarray | float,
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray | float:
    """
    Albarède & Juteau (1984) 模式年龄方程的残差

    消去 μ_i 后 (s 见 engine.calculate_model_slope, U = params['U_ratio']):
        f(T_i) = (y_i − y*)/(x_i − x*) − s(T0, T_i)
                 − μ*(e^{λT_i} − 1)/(x_i − x*) · [s(T0, T_i) − s(T_i, 0)]

    实际返回清分母形式 g = (x_i − x*)·f: 零点与 f 相同, 但 x_i = x* (即 206/204 =
    18.750, 实测常见) 时不奇异, 退化为极限方程
        (y_i − y*) = μ*(e^{λT_i} − 1)·[s(T0, T_i) − s(T_i, 0)]。

    Args:
        t_Ma: 待求模式年龄 (Ma, 可为负)
        Pb206_204_S, Pb207_204_S: 样品 206Pb/204Pb、207Pb/204Pb
        params: 参数字典 (可选; 需为 AJ84 预设, 提供 U_ratio = 1/137.79)

    Returns:
        np.ndarray or float: 残差 (无量纲; = f·(x_i − x*))
    """
    if params is None:
        params = engine.params
    t_years = np.asarray(t_Ma, dtype=float) * 1e6

    x = np.asarray(Pb206_204_S, dtype=float)
    y = np.asarray(Pb207_204_S, dtype=float)
    dx = x - ALBAREDE_X_STAR

    s_t0_t = calculate_model_slope(ALBAREDE_T0, t_years, params)
    s_t_0 = calculate_model_slope(t_years, 0.0, params)

    residual = (
        (y - ALBAREDE_Y_STAR)
        - dx * s_t0_t
        - ALBAREDE_MU_STAR * (np.exp(float(params['lambda_238']) * t_years) - 1.0)
        * (s_t0_t - s_t_0)
    )
    if np.ndim(residual) == 0:
        return float(residual)
    return residual


def _solve_albarede_age_scalar(
    x_i: float,
    y_i: float,
    params: dict[str, Any],
) -> float | None:
    """求解单个样品的模式年龄方程根, 返回年龄 (年, 可为负) 或 None."""
    if not (np.isfinite(x_i) and np.isfinite(y_i)):
        return None

    def _f(t_years: float) -> float:
        try:
            value = float(albarede_model_age_residual(t_years / 1e6, x_i, y_i, params))
        except Exception as exc:  # pragma: no cover - 数值保护
            logger.debug("Albarède age evaluation failed at t=%s: %s", t_years, exc)
            return np.nan
        return value if np.isfinite(value) else np.nan

    t_min = -_ALBAREDE_NEGATIVE_SPAN * ALBAREDE_T0
    try:
        f_low = _f(t_min)
        f_high = _f(ALBAREDE_T0)
        if np.isfinite(f_low) and np.isfinite(f_high) and f_low * f_high <= 0:
            return float(optimize.brentq(_f, t_min, ALBAREDE_T0, xtol=_AGE_SOLVER_XTOL))

        # 端点不异号时在区间内扫描变号子区间 (残差在 T0 附近很陡)。
        grid = np.linspace(t_min, ALBAREDE_T0, _ALBAREDE_SEARCH_POINTS)
        for t_left, t_right in zip(grid[:-1], grid[1:]):
            f_left = _f(float(t_left))
            f_right = _f(float(t_right))
            if not (np.isfinite(f_left) and np.isfinite(f_right)):
                continue
            if f_left == 0.0:
                return float(t_left)
            if f_left * f_right < 0:
                return float(optimize.brentq(_f, float(t_left), float(t_right), xtol=_AGE_SOLVER_XTOL))
        return None
    except Exception as exc:
        logger.warning("Albarède model-age solve failed (x=%s, y=%s): %s", x_i, y_i, exc)
        return None


def calculate_albarede_model_age(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray | float | None:
    """
    Albarède & Juteau (1984) 模式年龄 T_i (Ma)

    标量输入返回标量 (无解为 None); 数组输入返回数组 (无解位置 NaN)。
    区间 (−4·T0, T0); 负年龄是合法结果 (²⁰⁷Pb/²⁰⁴Pb 低于现代参考 → 源区 μ < μ*)。

    Args:
        Pb206_204_S, Pb207_204_S: 样品 206Pb/204Pb、207Pb/204Pb
        params: 参数字典 (可选; AJ84 预设提供 U_ratio = 1/137.79)

    Returns:
        np.ndarray or float or None: 模式年龄 (Ma)
    """
    if params is None:
        params = engine.params

    x = np.asarray(Pb206_204_S, dtype=float)
    y = np.asarray(Pb207_204_S, dtype=float)

    if x.ndim == 0:
        t_years = _solve_albarede_age_scalar(float(x), float(y), params)
        return None if t_years is None else t_years / 1e6

    ages = []
    for x_i, y_i in zip(x.ravel(), y.ravel()):
        t_years = _solve_albarede_age_scalar(float(x_i), float(y_i), params)
        ages.append(np.nan if t_years is None else t_years / 1e6)
    return np.array(ages, dtype=float).reshape(x.shape)


def calculate_albarede_age_sensitivity(
    t_Ma: np.ndarray | float | None,
    delta_mu: np.ndarray | float,
    mu_value: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray | float:
    """
    参考模型 T0 对模式年龄的灵敏度 dT_i/dT_0 (无量纲)

        dT_i = (Δμ_i/μ_i) · [λ'e^{λ'T0} − U·λ·s(T0,T_i)·e^{λT0}]
                          / [λ'e^{λ'T_i} − U·λ·s(T0,T_i)·e^{λT_i}] · dT0

    出处为 Albarède et al. (2012) 式 (16) (AJ84 原文未列), 用作本模型族的 T0
    灵敏度诊断量; U = 1/U_ratio, 指数以"年"为量纲。正确性由"扰动 T0 后重解模式
    年龄"的数值导数验证, 见 tests/test_geochemistry_albarede.py。

    Args:
        t_Ma: 模式年龄 T_i (Ma), 可为负
        delta_mu: Δμ_i = μ_i − μ* (由 calculate_albarede_delta_mu 得到)
        mu_value: μ_i
        params: 参数字典 (可选)

    Returns:
        np.ndarray or float: dT_i/dT_0; μ_i 无效时为 NaN
    """
    if params is None:
        params = engine.params

    l238 = float(params['lambda_238'])
    l235 = float(params['lambda_235'])
    u8u5 = 1.0 / float(params['U_ratio'])

    # Ma → 年 (None/NaN 保留为 NaN); 保留符号 —— 负模式年龄同样适用该灵敏度式。
    t_years = np.asarray(t_Ma, dtype=float) * 1e6

    delta_mu_arr = np.asarray(delta_mu, dtype=float)
    mu_arr = np.asarray(mu_value, dtype=float)
    mu_safe = np.where(np.abs(mu_arr) < EPSILON, np.copysign(EPSILON, mu_arr), mu_arr)

    s_t0_t = calculate_model_slope(ALBAREDE_T0, t_years, params)
    numerator = l235 * np.exp(l235 * ALBAREDE_T0) - u8u5 * l238 * s_t0_t * np.exp(l238 * ALBAREDE_T0)
    denominator = l235 * np.exp(l235 * t_years) - u8u5 * l238 * s_t0_t * np.exp(l238 * t_years)
    denominator = np.where(
        np.abs(denominator) < EPSILON, np.copysign(EPSILON, denominator), denominator
    )

    result = (delta_mu_arr / mu_safe) * numerator / denominator
    if np.ndim(result) == 0:
        return float(result)
    return result


