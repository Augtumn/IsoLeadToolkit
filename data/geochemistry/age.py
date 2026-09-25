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
# 参考: Albarède, F. & Juteau, M. (1984). Unscrambling the lead model ages.
#       Geochimica et Cosmochimica Acta 48(1), 207-212.
#       doi:10.1016/0016-7037(84)90364-8
# 参考模型 (常数见 engine.py §1.9, 与 R 包 ASTR::albarede_juteau_1984() 一致):
#   原始铅锚点自 T0 = 3.8 Ga 以 μ* = 9.66、κ* = 3.90 演化至现代 common Pb
#   x*/y*/z* = 18.750/15.63/38.83; ²³⁸U/²³⁵U = 137.79。
# 矿床按硫化物处理 (T_i 后不再含 U/Th)。AJ84 的解法是对两条生长方程
#     x_i = x0 + μ_i (e^{λT0} − e^{λT_i})
#     y_i = y0 + (μ_i/U)(e^{λ'T0} − e^{λ'T_i})
# 同时解出 (T_i, μ_i) (Albarède 的 MATLAB 脚本 / ASTR 用 rootSolve::multiroot);
# 下面的残差是这两式消去 μ_i 后的等价 1-D 形式 (已数值验证: 同一常数下两者
# 相差 ≤ 3.5e-12 Ma)。
#
# 求解区间: T_i ∈ (−SPAN·T0, T0), SPAN = 4, 即约 (−15.2 Ga, 3.8 Ga)。
# **负模式年龄是有意义的**: 当样品的 207Pb/204Pb 比现代参考更低 (比现代 common Pb
# 更不放射成因) 时, 生长曲线交点落在 T = 0 之外, 表示源区 μ 低于参考值 μ* (U 相对
# 贫化)。Albarède 的 MATLAB 脚本、ASTR 与 SilverQuest 矿石库都保留这类结果
# (该库 6938 行中有 407 行 Tmod < 0, 最低 −8980 Ma)。只有整个区间内都无根时才返回
# NaN —— 这与 ASTR 的无界 Newton 的差别仅在"无根"情形的处理, 不再丢弃负年龄。

_ALBAREDE_SEARCH_POINTS = 400
#: 负向扫描跨度 (以 T0 为单位): 覆盖到约 −15 Ga, 足以涵盖参考生长曲线的负年龄分支。
_ALBAREDE_NEGATIVE_SPAN = 4.0


def albarede_model_age_residual(
    t_Ma: np.ndarray | float,
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray | float:
    """
    Albarède & Juteau (1984) 模式年龄方程的残差

    AJ84 同时解 (T_i, μ_i); 消去 μ_i 后等价于:
        f(T_i) = (y_i − y*)/(x_i − x*) − s(T0, T_i)
                 − μ*(e^{λT_i} − 1)/(x_i − x*) · [s(T0, T_i) − s(T_i, 0)] = 0
    其中 s 为 engine.calculate_model_slope() (式: s(T0,T) = (1/U)(e^{λ'T0} − e^{λ'T})
    / (e^{λT0} − e^{λT})), U = 137.79 (AJ84/ASTR 口径, 由预设的 U_ratio 提供)。

    历史备注: Albarède et al. (2012, Archaeometry) 给出过同一模型族的 T–μ–κ
    版本, 其式 (12) 印刷版第三项分子为 e^{λ'T_i} − 1 (²³⁵U), 与式 (11) 的消元
    结果 (²³⁸U 项) 不一致; 且作者本人表示 2012 版不应使用 (见 ASTR 文档)。
    因此本工程实现 AJ84, 不实现 2012 版。

    Args:
        t_Ma: 待求模式年龄 (Ma)
        Pb206_204_S, Pb207_204_S: 样品 206Pb/204Pb、207Pb/204Pb
        params: 参数字典 (可选; 需为 AJ84 预设, 以提供 U_ratio = 1/137.79)

    Returns:
        np.ndarray or float: 残差 (无量纲; = f·(x_i − x*), 见下文)
    """
    # 返回"清分母"形式 g = (x_i − x*)·f: 与本函数文档中的 f 零点相同, 但 x_i = x*
    # (现代参考值; 实测数据把 206Pb/204Pb 取整到 18.750 很常见) 时不再奇异, 自动退化
    # 为极限方程 (y_i − y*) = μ*(e^{λT_i} − 1)[s(T0,T_i) − s(T_i,0)]。
    # 该退化形式与第三方矿石库一致 (18.750/15.770 → T_i ≈ 270 Ma)。
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

    标量输入返回标量年龄 (无解时返回 None); 数组输入返回数组, 无解位置为 NaN。
    求解区间 (−4·T0, T0), 即约 (−15.2 Ga, 3.8 Ga); **负年龄是合法结果** (样品的
    ²⁰⁷Pb/²⁰⁴Pb 低于现代参考 → 源区 μ 低于 μ*, 比现代 common Pb 更不放射成因)。

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
    参考模型 T0 选择对模式年龄的灵敏度 dT_i/dT_0 (无量纲)

        dT_i = (Δμ_i/μ_i) · [λ'e^{λ'T0} − U·λ·s(T0,T_i)·e^{λT0}]
                          / [λ'e^{λ'T_i} − U·λ·s(T0,T_i)·e^{λT_i}] · dT0

    (U = 1/U_ratio = 137.79 (AJ84); 指数以"年"为量纲。)

    出处: 该式由 Albarède et al. (2012, Archaeometry) 式 (16) 给出 (AJ84 原文
    未列此式), 此处作为本模型族的 T0 灵敏度诊断量保留; 与所选模型的参考常数
    自动一致。验证方式: 与"把 T0 扰动后重解模式年龄方程"的数值导数对比 (见
    tests/test_geochemistry_albarede.py)。

    Args:
        t_Ma: 模式年龄 T_i (Ma), 由 calculate_albarede_model_age 得到
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


