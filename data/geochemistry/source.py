# -*- coding: utf-8 -*-
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
# 内部核心函数 — 统一反演算法
# =============================================================================


def _safe_denominator(values: np.ndarray | float) -> np.ndarray:
    """Apply shared denominator floor for scalar/array-like values.

    Preserves the sign of tiny values so small negative denominators do not
    flip the sign of the quotient near singularities.
    """
    arr = np.asarray(values, dtype=float)
    return np.where(np.abs(arr) < EPSILON, np.copysign(EPSILON, arr), arr)

def _prepare_age(t_Ma: np.ndarray | float | None) -> np.ndarray:
    """年龄预处理: Ma → 年, 处理 None 和异常值 (负年龄夹紧到 0)."""
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
    """年龄预处理: Ma → 年, 处理 None/异常值但**保留符号**.

    AJ84 的负模式年龄有物理含义 (源区 μ 低于参考 μ*, Pb 比现代 common Pb 更不
    放射成因), 因此不能像 PbIso 口径那样夹紧到 0。
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
    den_slope = _safe_denominator(den_slope)
    slope_t = u_ratio * (e5t - 1) / den_slope

    # 放射性成因增量
    rad207 = u_ratio * (np.exp(l235 * T_ref) - e5t)
    rad206 = np.exp(l238 * T_ref) - e8t

    # 求解 μ
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
    den_time = _safe_denominator(den_time)

    dx = x - X_ref
    dx = _safe_denominator(dx)

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
# 公共 API — 模型参考（按 age_model 自动选择）
# =============================================================================

def calculate_model_mu(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """
    计算模型源区 Mu (对应 R 包 PbIso 中的 CalcMu) — 模型参考

    根据 age_model 自动选择参考参数进行反演：
    - two_stage: (T1, a1, b1)
    - single_stage: (T2, a0, b0)
    适用于任何已配置的地球化学模型（SK、CR、MM 等）。

    Args:
        Pb206_204_S, Pb207_204_S: 样品同位素比值
        t_Ma: 样品年龄 (Ma)

    Returns:
        np.ndarray: 源区 Mu 值, 表示从 T1 到 t 阶段的 238U/204Pb 比值。
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
    """
    计算模型源区 Kappa (Th/U) (对应 R 包 PbIso 中的 CalcKa) — 模型参考

    根据 age_model 自动选择参考参数进行反演：
    - two_stage: (T1, a1, c1)
    - single_stage: (T2, a0, c0)
    适用于任何已配置的地球化学模型。

    Args:
        Pb206_204_S: 样品 206Pb/204Pb 比值
        Pb208_204_S: 样品 208Pb/204Pb 比值
        t_Ma: 样品年龄 (Ma)

    Returns:
        np.ndarray: 源区 Kappa 值 (232Th/238U)
    """
    if params is None:
        params = engine.params
    x_ref, _, z_ref, t_ref = _model_reference_params(params)
    return _invert_kappa(Pb206_204_S, Pb208_204_S, t_Ma,
                         x_ref, z_ref, t_ref, params)


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
    x_ref, _, _, t_ref = _model_reference_params(params)
    # 与 μ/κ 反演用同一套年龄处理 (None → NaN, 夹紧 ≥ 0), 否则与 μ 所用年龄不一致。
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
    """
    计算样品形成时的初始 207Pb/204Pb (对应 PbIso Calc74in)
    """
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
    """
    计算样品形成时的初始 208Pb/204Pb (对应 PbIso Calc84in)
    """
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
# Albarède & Juteau (1984) T–μ–κ 模型 — 源区参数
# =============================================================================
# 参考: Albarède, F. & Juteau, M. (1984). GCA 48(1), 207-212.
#       doi:10.1016/0016-7037(84)90364-8
# 常数见 engine.py §1.9。AJ84 由 x/z 生长方程直接得绝对量:
#     μ_i = (x_i − x0) / (e^{λT0} − e^{λT_i})
#     κ_i = (z_i − z0) / [(e^{λ''T0} − e^{λ''T_i}) · μ_i]
# 下面同时给出相对现代 common Pb 参考的 Δμ/Δκ 记法 (源自 2012 版记号):
# μ_i = μ* + Δμ_i, κ_i = κ* + Δκ_i。
# T_i 可为负 (负模式年龄有物理含义, 见 age.py), 故用 _prepare_age_signed()
# 而非夹紧到 0 的 _prepare_age()。

def calculate_albarede_delta_mu(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    params: dict[str, Any] | None = None,
) -> np.ndarray:
    """
    Albarède & Juteau (1984) 源区 Δμ_i = μ_i − μ* = [x_i − x* + μ*(e^{λT_i} − 1)]
    / (e^{λT0} − e^{λT_i}), 即 x 生长方程 (x0 = x* − μ*(e^{λT0} − 1)) 的解。

    Args:
        Pb206_204_S, Pb207_204_S: 样品 206Pb/204Pb、207Pb/204Pb
        t_Ma: 模式年龄 T_i (Ma), 由 calculate_albarede_model_age 得到
        params: 参数字典 (可选)

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
    """
    Albarède & Juteau (1984) 源区 μ_i = ²³⁸U/²⁰⁴Pb = μ* + Δμ_i

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
    """
    Albarède & Juteau (1984) 源区 Δκ_i = κ_i − κ*, 由 z 生长方程 (z0 = z* −
    μ*κ*(e^{λ''T0} − 1)) 得:
        Δκ_i = { [z_i − z* + μ*κ*(e^{λ''T_i} − 1)] / (e^{λ''T0} − e^{λ''T_i})
                 − κ* Δμ_i } / μ_i

    (2012 版式 (15) 的印刷版使 Δκ_i 自相消、一般无不动点解, 故不采用; 见
    docs/geochemistry.md §16.5。)

    Args:
        Pb206_204_S, Pb208_204_S: 样品 206Pb/204Pb、208Pb/204Pb
        t_Ma: 模式年龄 T_i (Ma)
        mu_value: 同一样品的 μ_i (calculate_albarede_mu 的结果)
        params: 参数字典 (可选)

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
    """
    Albarède & Juteau (1984) 源区 κ_i = ²³²Th/²³⁸U = κ* + Δκ_i

    Returns:
        np.ndarray: κ_i
    """
    if params is None:
        params = engine.params
    return calculate_albarede_delta_kappa(
        Pb206_204_S, Pb208_204_S, t_Ma, mu_value, params
    ) + ALBAREDE_KAPPA_STAR



