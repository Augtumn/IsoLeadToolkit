# -*- coding: utf-8 -*-
"""Source parameter inversion and initial ratios."""
from __future__ import annotations

from typing import Any

import numpy as np

from .engine import engine, EPSILON


# =============================================================================
# 内部核心函数 — 统一反演算法
# =============================================================================

def _prepare_age(t_Ma: np.ndarray | float | None) -> np.ndarray:
    """年龄预处理: Ma → 年, 处理 None 和异常值."""
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


def _invert_mu(
    x: np.ndarray | float,
    y: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    X_ref: float,
    Y_ref: float,
    T_ref: float,
    params: dict[str, Any],
) -> np.ndarray:
    """
    统一 μ (238U/204Pb) 反演核心.

    通过当今等时线斜率投影，联合 206Pb 和 207Pb 两个约束求解源区 μ。

    Args:
        x: 样品 206Pb/204Pb
        y: 样品 207Pb/204Pb
        t_Ma: 样品年龄 (Ma)
        X_ref: 参考 206Pb/204Pb (a0 或 a1)
        Y_ref: 参考 207Pb/204Pb (b0 或 b1)
        T_ref: 参考起始时间 (T2 或 T1), 单位: 年
        params: 参数字典

    Returns:
        np.ndarray: 源区 μ 值
    """
    l238 = params['lambda_238']
    l235 = params['lambda_235']
    u_ratio = params['U_ratio']

    x = np.asarray(x)
    y = np.asarray(y)
    t = _prepare_age(t_Ma)

    # 当今等时线斜率
    e5t = np.exp(l235 * t)
    e8t = np.exp(l238 * t)
    den_slope = e8t - 1
    den_slope = np.where(np.abs(den_slope) < EPSILON, EPSILON, den_slope)
    slope_t = u_ratio * (e5t - 1) / den_slope

    # 放射性成因增量
    rad207 = u_ratio * (np.exp(l235 * T_ref) - e5t)
    rad206 = np.exp(l238 * T_ref) - e8t

    # 求解 μ
    numerator = (y - Y_ref) - slope_t * (x - X_ref)
    denominator = rad207 - slope_t * rad206
    denominator = np.where(np.abs(denominator) < EPSILON, EPSILON, denominator)

    return numerator / denominator


def _invert_omega(
    z: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    Z_ref: float,
    T_ref: float,
    params: dict[str, Any],
) -> np.ndarray:
    """
    统一 ω (232Th/204Pb) 反演核心.

    从 208Pb 生长方程直接求解: ω = (z − Z_ref) / [exp(λ232·T) − exp(λ232·t)]

    Args:
        z: 样品 208Pb/204Pb
        t_Ma: 样品年龄 (Ma)
        Z_ref: 参考 208Pb/204Pb (c0 或 c1)
        T_ref: 参考起始时间, 单位: 年
        params: 参数字典

    Returns:
        np.ndarray: 源区 ω 值
    """
    l232 = params['lambda_232']

    z = np.asarray(z)
    t = _prepare_age(t_Ma)

    denom = np.exp(l232 * T_ref) - np.exp(l232 * t)
    denom = np.where(np.abs(denom) < EPSILON, EPSILON, denom)

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
    """
    统一 κ (232Th/238U) 反演核心.

    从 206Pb 和 208Pb 生长方程比值消去 μ:
    κ = [(z−Z_ref)/(x−X_ref)] × [exp(λ238·T)−exp(λ238·t)] / [exp(λ232·T)−exp(λ232·t)]

    Args:
        x: 样品 206Pb/204Pb
        z: 样品 208Pb/204Pb
        t_Ma: 样品年龄 (Ma)
        X_ref: 参考 206Pb/204Pb (a0 或 a1)
        Z_ref: 参考 208Pb/204Pb (c0 或 c1)
        T_ref: 参考起始时间, 单位: 年
        params: 参数字典

    Returns:
        np.ndarray: 源区 κ 值
    """
    l238 = params['lambda_238']
    l232 = params['lambda_232']

    x = np.asarray(x)
    z = np.asarray(z)
    t = _prepare_age(t_Ma)

    num_time = np.exp(l238 * T_ref) - np.exp(l238 * t)
    den_time = np.exp(l232 * T_ref) - np.exp(l232 * t)
    den_time = np.where(np.abs(den_time) < EPSILON, EPSILON, den_time)

    dx = x - X_ref
    dx = np.where(np.abs(dx) < EPSILON, EPSILON, dx)

    return ((z - Z_ref) / dx) * (num_time / den_time)


# =============================================================================
# 公共 API — 单阶段参考 (CDT: a0/b0/c0, T2)
# =============================================================================

def calculate_source_mu(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """
    计算源区 Mu 值 (238U/204Pb) — 原始铅参考（单阶段）

    使用 CDT 原始铅参考值 (a0, b0) 和地球年龄 T2。

    Returns:
        np.ndarray: 源区 Mu 值
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
    """
    计算源区 Omega 值 (232Th/204Pb) — 原始铅参考（单阶段）

    使用 CDT 原始铅参考值 (c0) 和地球年龄 T2。
    """
    if params is None:
        params = engine.params
    return _invert_omega(Pb208_204_S, t_Ma,
                         params['c0'], params['T2'], params)


def calculate_source_nu(
    mu: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray | float:
    """
    计算源区 Nu 值 (235U/204Pb)
    nu = mu * (235U/238U)
    """
    if params is None:
        params = engine.params
    return mu * params['U_ratio']


# =============================================================================
# 公共 API — 模型参考 (a1/b1/c1, T1)
# =============================================================================

def calculate_model_mu(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """
    计算模型源区 Mu (对应 R 包 PbIso 中的 CalcMu) — 模型参考

    使用当前模型的参考参数 (T1, a1, b1) 反演源区 238U/204Pb 比值。
    适用于任何已配置的地球化学模型（SK、CR、MM 等）。

    Args:
        Pb206_204_S, Pb207_204_S: 样品同位素比值
        t_Ma: 样品年龄 (Ma)

    Returns:
        np.ndarray: 源区 Mu 值, 表示从 T1 到 t 阶段的 238U/204Pb 比值。
    """
    if params is None:
        params = engine.params
    return _invert_mu(Pb206_204_S, Pb207_204_S, t_Ma,
                      params['a1'], params['b1'], params['T1'], params)


def calculate_model_kappa(
    Pb208_204_S: np.ndarray | float,
    Pb206_204_S: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """
    计算模型源区 Kappa (Th/U) (对应 R 包 PbIso 中的 CalcKa) — 模型参考

    使用当前模型的参考参数 (T1, a1, c1) 反演源区 232Th/238U 比值。
    适用于任何已配置的地球化学模型。

    Returns:
        np.ndarray: 源区 Kappa 值 (232Th/238U)
    """
    if params is None:
        params = engine.params
    return _invert_kappa(Pb206_204_S, Pb208_204_S, t_Ma,
                         params['a1'], params['c1'], params['T1'], params)


# =============================================================================
# 初始比值反演 (复用 calculate_model_mu / calculate_model_kappa)
# =============================================================================

def calculate_initial_ratio_64(
    t_Ma: np.ndarray | float,
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """
    计算样品形成时的初始 206Pb/204Pb (对应 PbIso Calc64in)
    """
    if params is None:
        params = engine.params
    mu = calculate_model_mu(Pb206_204_S, Pb207_204_S, t_Ma, params)
    t = np.asarray(t_Ma) * 1e6
    e8T = np.exp(params['lambda_238'] * params['T1'])
    e8t = np.exp(params['lambda_238'] * t)
    return params['a1'] + mu * (e8T - e8t)


def calculate_initial_ratio_74(
    t_Ma: np.ndarray | float,
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """
    计算样品形成时的初始 207Pb/204Pb (对应 PbIso Calc74in)
    """
    if params is None:
        params = engine.params
    mu = calculate_model_mu(Pb206_204_S, Pb207_204_S, t_Ma, params)
    t = np.asarray(t_Ma) * 1e6
    U8U5 = 1.0 / params['U_ratio']
    e5T = np.exp(params['lambda_235'] * params['T1'])
    e5t = np.exp(params['lambda_235'] * t)
    return params['b1'] + (mu / U8U5) * (e5T - e5t)


def calculate_initial_ratio_84(
    t_Ma: np.ndarray | float,
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    Pb208_204_S: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """
    计算样品形成时的初始 208Pb/204Pb (对应 PbIso Calc84in)
    """
    if params is None:
        params = engine.params
    mu = calculate_model_mu(Pb206_204_S, Pb207_204_S, t_Ma, params)
    kappa = calculate_model_kappa(Pb208_204_S, Pb206_204_S, t_Ma, params)
    omega = kappa * mu
    t = np.asarray(t_Ma) * 1e6
    e2T = np.exp(params['lambda_232'] * params['T1'])
    e2t = np.exp(params['lambda_232'] * t)
    return params['c1'] + omega * (e2T - e2t)


# Backward-compatible aliases (deprecated)
calculate_mu_sk = calculate_source_mu
calculate_omega_sk = calculate_source_omega
calculate_nu_sk = calculate_source_nu
calculate_mu_sk_model = calculate_model_mu
calculate_kappa_sk_model = calculate_model_kappa
