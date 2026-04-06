# -*- coding: utf-8 -*-
"""Model age calculations."""
from __future__ import annotations

from typing import Any, Callable

import numpy as np
from scipy import optimize

from .engine import (
    engine,
    A0,
    B0,
    A1_SK,
    B1_SK,
    T_EARTH_CANON,
    T_SK_STAGE2,
    EPSILON,
)


_RATIO_DIFF_FLOOR = 1e-10
_SOLVER_GUARD_VALUE = 1e10
_AGE_SOLVER_XTOL = 1e-6


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
    t_max_safe = t_max - 1.0 # 避免端点奇点

    def _eval(val: float) -> float:
        try:
            out = f(val)
            return out if np.isfinite(out) else np.nan
        except Exception:
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
            if f1 == 0:
                return t_samples[i]
            if f1 * f2 < 0:
                return optimize.brentq(f, t_samples[i], t_samples[i + 1], xtol=_AGE_SOLVER_XTOL)

        return None
    except Exception:
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
            if abs(denom) < EPSILON: denom = EPSILON
            num = np.exp(l235 * T) - np.exp(l235 * t)
            
            if abs(S206 - a0_val) < _RATIO_DIFF_FLOOR:
                return _SOLVER_GUARD_VALUE
                
            R = (S207 - b0_val) / (S206 - a0_val)
            return R - u_ratio * num / denom
        
        t_result = _solve_age_scipy(f, bounds=(-4700e6, 4700e6))
        return t_result / 1e6 if t_result is not None else None
    
    # 数组处理
    results = []
    for s206, s207 in zip(S206.ravel(), S207.ravel()):
        if np.isnan(s206) or np.isnan(s207):
            results.append(np.nan)
            continue

        def f_scalar(t: float) -> float:
            denom = np.exp(l238 * T) - np.exp(l238 * t)
            if abs(denom) < EPSILON: denom = EPSILON
            num = np.exp(l235 * T) - np.exp(l235 * t)
            
            if abs(s206 - a0_val) < _RATIO_DIFF_FLOOR:  # 避免除零
                return _SOLVER_GUARD_VALUE
            
            R = (s207 - b0_val) / (s206 - a0_val)
            return R - u_ratio * num / denom

        t_res = _solve_age_scipy(f_scalar, bounds=(-4700e6, 4700e6))
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
            if abs(denom) < EPSILON: denom = EPSILON
            num = np.exp(l235 * T) - np.exp(l235 * t)
            
            if abs(S206 - a1_val) < _RATIO_DIFF_FLOOR:
                return _SOLVER_GUARD_VALUE
                
            R = (S207 - b1_val) / (S206 - a1_val)
            return R - u_ratio * num / denom
        
        t_result = _solve_age_scipy(f, bounds=(-4700e6, 4700e6))
        return t_result / 1e6 if t_result is not None else None
    
    # 数组处理
    results = []
    for s206, s207 in zip(S206.ravel(), S207.ravel()):
        if np.isnan(s206) or np.isnan(s207):
            results.append(np.nan)
            continue
            
        def f_scalar(t: float) -> float:
            denom = np.exp(l238 * T) - np.exp(l238 * t)
            if abs(denom) < EPSILON: denom = EPSILON
            num = np.exp(l235 * T) - np.exp(l235 * t)
            
            if abs(s206 - a1_val) < _RATIO_DIFF_FLOOR:
                return _SOLVER_GUARD_VALUE
                
            R = (s207 - b1_val) / (s206 - a1_val)
            return R - u_ratio * num / denom
        
        t_res = _solve_age_scipy(f_scalar, bounds=(-4700e6, 4700e6))
        results.append(t_res / 1e6 if t_res is not None else np.nan)

    return np.array(results).reshape(S206.shape)

def calculate_model_age(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    two_stage: bool = False,
) -> np.ndarray | float | None:
    """
    Calculate model age (backward compatible function)
    
    Args:
        Pb206_204_S: 206Pb/204Pb ratio
        Pb207_204_S: 207Pb/204Pb ratio
        two_stage: If True, use two-stage model
        
    Returns:
        Model age in Ma
    """
    if two_stage:
        return calculate_two_stage_age(Pb206_204_S, Pb207_204_S)
    else:
        return calculate_single_stage_age(Pb206_204_S, Pb207_204_S)
