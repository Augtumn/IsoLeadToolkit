# -*- coding: utf-8 -*-
"""Delta calculations and V1-V2 projection."""
from __future__ import annotations

import numpy as np

from .engine import engine, _exp_evolution_term


def calculate_deltas(
    Pb206_204_S,
    Pb207_204_S,
    Pb208_204_S,
    t_Ma,
    params=None,
    T_mantle=None,
    use_two_stage: bool = False,
    E1=None,
    E2=None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    计算 Delta 值 (Δα, Δβ, Δγ)
    
    描述:
    计算样品相对于同期地幔参考值的偏差 (千分比)。
    
    Args:
        T_mantle: 地幔参考曲线的起始时间
        use_two_stage: 是否使用二阶段参数计算参考曲线
        E1/E2: 演化参数（对应 PbIso 模型曲线）
        
    Returns:
        (d_alpha, d_beta, d_gamma): 偏差值数组
    """
    if params is None: params = engine.params
    
    l238 = params['lambda_238']
    l235 = params['lambda_235']
    l232 = params['lambda_232']
    
    mu_M = params['mu_M']
    omega_M = params['omega_M']
    v_M = params['v_M']

    E1_val = params.get('E1', 0.0) if E1 is None else float(E1)
    E2_val = params.get('E2', 0.0) if E2 is None else float(E2)

    if use_two_stage:
        T = T_mantle if T_mantle is not None else params['Tsec']
        a_ref, b_ref, c_ref = params['a1'], params['b1'], params['c1']
    else:
        T = T_mantle if T_mantle is not None else params['T2']
        a_ref, b_ref, c_ref = params['a0'], params['b0'], params['c0']

    # 数组化与异常值处理
    t = np.asarray(t_Ma, dtype=float) if t_Ma is not None else np.array(np.nan)
    Pb206 = np.asarray(Pb206_204_S)
    Pb207 = np.asarray(Pb207_204_S)
    Pb208 = np.asarray(Pb208_204_S)
    
    # 初始化结果
    d_alpha = np.full_like(Pb206, np.nan, dtype=float)
    d_beta = np.full_like(Pb207, np.nan, dtype=float)
    d_gamma = np.full_like(Pb208, np.nan, dtype=float)
    
    # 无效年龄检查
    if t.ndim == 0 and np.isnan(t):
        return d_alpha, d_beta, d_gamma
    
    valid_mask = ~np.isnan(t)
    if not np.any(valid_mask):
         return d_alpha, d_beta, d_gamma

    t_val = np.maximum(t, 0) * 1e6
    
    # 计算同期地幔参考值
    ref206 = a_ref + mu_M * (_exp_evolution_term(l238, T, E1_val) - _exp_evolution_term(l238, t_val, E1_val))
    ref207 = b_ref + v_M * (_exp_evolution_term(l235, T, E1_val) - _exp_evolution_term(l235, t_val, E1_val))
    ref208 = c_ref + omega_M * (_exp_evolution_term(l232, T, E2_val) - _exp_evolution_term(l232, t_val, E2_val))
    
    # 计算偏差 (千分比)
    # 注意: 若 t 为标量而 Pb 为数组，numpy会自动广播 ref 值
    # 若 t 和 Pb 均为数组，形状需匹配或可广播
    
    with np.errstate(divide='ignore', invalid='ignore'):
        d_alpha = ((Pb206 / ref206) - 1) * 1000
        d_beta = ((Pb207 / ref207) - 1) * 1000
        d_gamma = ((Pb208 / ref208) - 1) * 1000
        
    return d_alpha, d_beta, d_gamma

def calculate_v1v2_coordinates(
    d_alpha,
    d_beta,
    d_gamma,
    params=None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    计算 V1, V2 判别图投影坐标
    来源: Zhu (1995)
    """
    if params is None: params = engine.params
    
    a, b, c = params['a'], params['b'], params['c']
    
    denom = 1 + b**2 + c**2
    
    d_alpha_p = ((1 + c**2) * d_alpha + b * (d_gamma - c * d_beta - a)) / denom
    d_beta_p = ((1 + b**2) * d_beta + c * (d_gamma - b * d_alpha - a)) / denom
    d_gamma_p = a + b * d_alpha_p + c * d_beta_p
    
    V1 = (b * d_gamma_p + d_alpha_p) / np.sqrt(1 + b**2)
    V2 = (np.sqrt(1 + b**2 + c**2) / np.sqrt(1 + b**2)) * d_beta_p
    
    return V1, V2

def calculate_delta_values(
    Pb206_204_S,
    Pb207_204_S,
    Pb208_204_S,
    t_Ma,
    params=None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Alias for calculate_deltas for backward compatibility"""
    return calculate_deltas(Pb206_204_S, Pb207_204_S, Pb208_204_S, t_Ma, params)

def calculate_v1v2(
    d_alpha,
    d_beta,
    d_gamma,
    a: float = 0.0,
    b: float = 2.0367,
    c: float = -6.143,
) -> tuple[np.ndarray, np.ndarray]:
    """Alias for calculate_v1v2_coordinates for backward compatibility"""
    temp_params = {'a': a, 'b': b, 'c': c}
    return calculate_v1v2_coordinates(d_alpha, d_beta, d_gamma, params=temp_params)
