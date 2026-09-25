# -*- coding: utf-8 -*-
"""Geochemistry package exports."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)
_AGE_MODEL_PARAM_DELTA_FLOOR = 1e-6

from .engine import (
    PRESET_MODELS,
    GeochemistryEngine,
    engine,
    calculate_modelcurve,
    calculate_model_slope,
    T_EARTH_1ST,
    T_EARTH_CANON,
    T_SK_STAGE2,
    LAMBDA_238,
    LAMBDA_235,
    LAMBDA_232,
    A0,
    B0,
    C0,
    A1_SK,
    B1_SK,
    C1_SK,
    MU_M_DEFAULT,
    OMEGA_M_DEFAULT,
    U_RATIO_NATURAL,
    EPSILON,

    E1_DEFAULT,
    E2_DEFAULT,

    ALBAREDE_T0,
    ALBAREDE_X_STAR,
    ALBAREDE_Y_STAR,
    ALBAREDE_Z_STAR,
    ALBAREDE_MU_STAR,
    ALBAREDE_KAPPA_STAR,
    ALBAREDE_OMEGA_STAR,
    ALBAREDE_U238_235,
    U_RATIO_AJ84,
    ALBAREDE_X0,
    ALBAREDE_Y0,
    ALBAREDE_Z0,
)
from .age import (
    calculate_single_stage_age,
    calculate_two_stage_age,
    calculate_albarede_model_age,
    calculate_albarede_age_sensitivity,
    albarede_model_age_residual,
)
from .source import (
    _invert_mu,
    _invert_omega,
    calculate_source_mu,
    calculate_source_omega,
    calculate_source_nu,
    calculate_model_mu,
    calculate_model_kappa,
    calculate_initial_ratio_64,
    calculate_initial_ratio_74,
    calculate_initial_ratio_84,
    calculate_albarede_delta_mu,
    calculate_albarede_mu,
    calculate_albarede_delta_kappa,
    calculate_albarede_kappa,
)
from .delta import (
    calculate_deltas,
    calculate_v1v2_coordinates,
)
from .isochron import (
    calculate_paleoisochron_line,
    calculate_isochron1_growth_curve,
    calculate_isochron2_growth_curve,
    york_regression,
    calculate_pbpb_age_from_ratio,
    calculate_isochron_age_from_slope,
    calculate_source_mu_from_isochron,
    calculate_source_kappa_from_slope,
)

def resolve_age_model(params: dict | None = None, model_name: str | None = None) -> str:
    """Resolve age model mode from params and model name."""
    if params is None:
        params = engine.params
    if model_name is None:
        model_name = getattr(engine, 'current_model_name', '')

    # Prefer explicit flag
    age_model = params.get('age_model')
    if isinstance(age_model, str):
        mode = age_model.strip().lower().replace('_', '-')
        if mode in ('two-stage', 'two stage', '2-stage', '2nd', 'second'):
            return 'two_stage'
        if mode in ('single-stage', 'single stage', '1-stage', '1st', 'first'):
            return 'single_stage'

    # Fallback heuristics (for backward compatibility with custom params)
    logger.debug("age_model flag not found in params, falling back to heuristics for model '%s'", model_name)

    if isinstance(model_name, str):
        if 'Geokit' in model_name:
            return 'single_stage'
        if '1st Stage' in model_name:
            return 'single_stage'
        if '2nd Stage' in model_name:
            return 'two_stage'

    try:
        tsec = float(params.get('Tsec', 0.0))
    except Exception:
        tsec = 0.0
    if not np.isfinite(tsec) or tsec <= 0:
        return 'single_stage'

    try:
        a0, b0, c0 = params.get('a0'), params.get('b0'), params.get('c0')
        a1, b1, c1 = params.get('a1'), params.get('b1'), params.get('c1')
        if all(np.isfinite([a0, b0, c0, a1, b1, c1])):
            if max(abs(a1 - a0), abs(b1 - b0), abs(c1 - c0)) < _AGE_MODEL_PARAM_DELTA_FLOOR:
                return 'single_stage'
    except Exception:
        pass

    return 'two_stage'


def calculate_all_parameters(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    Pb208_204_S: np.ndarray | float,
    calculate_ages: bool = True,
    a: float | None = None,
    b: float | None = None,
    c: float | None = None,
    scale: float = 1.0,
    t_Ma: np.ndarray | float | None = None,
    **kwargs: Any,
) -> dict[str, np.ndarray | float | int | str | None]:
    """
    计算所有地球化学参数 (主调用接口)
    
    集成功能:
    1. 计算单阶段(CDT)和两阶段(SK)模式年龄
    2. 计算 Delta 值和 V1-V2 坐标
    3. 计算源区特征 (Mu, Omega, Kappa)
    4. 计算初始同位素比值
    
    Args:
        Pb206_204_S, ...: 同位素比值数据
        a, b, c: 可选的 V1V2 回归参数覆盖
        t_Ma: 样品真实年龄 (Ma)，用于 CalcMu/CalcKa/Calc*in（若未提供则使用 tSK）
        
    Returns:
        dict: 包含所有计算结果的字典
    """
    # 1. 数据标准化
    Pb206 = np.asarray(Pb206_204_S)
    Pb207 = np.asarray(Pb207_204_S)
    Pb208 = np.asarray(Pb208_204_S)
    
    results = {
        'Pb206_204_S': Pb206,
        'Pb207_204_S': Pb207,
        'Pb208_204_S': Pb208,
    }
    
    # 获取当前模型设置
    params_calc = engine.get_parameters()
    current_model = getattr(engine, 'current_model_name', '')
    # V1V2 (Geokit) 模式特殊处理: 使用 T1=4.43Ga 计算 tCDT
    is_geokit = "Geokit" in current_model
    # 使用模型参数与名称判定年龄模型
    age_model = resolve_age_model(params_calc, current_model)
    is_two_stage = age_model == 'two_stage'

    # 2. 模式年龄计算
    if is_geokit:
        tCDT = calculate_single_stage_age(Pb206, Pb207, initial_age=engine.params['T1'])
    else:
        tCDT = calculate_single_stage_age(Pb206, Pb207)

    if calculate_ages:
        tSK = calculate_two_stage_age(Pb206, Pb207)
    else:
        # Callers that only need single-stage quantities (V1V2 discrimination)
        # skip the two-stage age; degrade to tCDT so t_model/t_input stay finite.
        tSK = tCDT

    t_model = tSK if is_two_stage else tCDT
    # Finite fallback: a two-stage solve can fail (None/NaN) while the
    # single-stage age is still valid, and vice versa.
    if is_two_stage:
        if t_model is None:
            t_model = tCDT
        elif tCDT is not None:
            t_model = np.where(np.isfinite(t_model), t_model, tCDT)
    if t_model is None:
        t_model = np.nan

    if t_Ma is None:
        t_input = t_model
    else:
        t_input = np.asarray(t_Ma, dtype=float)
        if t_input.ndim == 0:
            if not np.isfinite(t_input):
                t_input = t_model
        else:
            t_input = np.where(np.isfinite(t_input), t_input, t_model)
    
    results['tCDT (Ma)'] = tCDT
    results['tSK (Ma)'] = tSK
    # Unified model-age output: each parameter set yields exactly one model
    # age, chosen by the resolved age model (two-stage → tSK, single-stage →
    # tCDT). This is the canonical "模式年龄" column used by UI/export/validation.
    results['t_Model (Ma)'] = t_model
    
    # 3. Delta 值计算
    E1_val = kwargs.get('E1', None)
    E2_val = kwargs.get('E2', None)

    if is_two_stage:
        t_model = tSK
        d_alpha, d_beta, d_gamma = calculate_deltas(
            Pb206, Pb207, Pb208, t_model, params=params_calc, use_two_stage=True, E1=E1_val, E2=E2_val
        )
    else:
        # 单阶段逻辑: Geokit 用 T1 计算年龄，但 Delta 地幔参考采用 T2 口径
        t_calc = tCDT if is_geokit else calculate_single_stage_age(Pb206, Pb207, params=params_calc, initial_age=params_calc.get('T2'))
        if t_calc is None:
            # Scalar solve failed; degrade to the CDT model age instead of
            # crashing in np.maximum below.
            logger.warning("Single-stage age solve failed; falling back to tCDT")
            t_calc = tCDT
        if t_calc is None:
            # Both solves failed: keep going with NaN so the remaining
            # outputs degrade instead of raising TypeError.
            logger.warning("No finite single-stage age available; deltas will be NaN")
            t_calc = np.nan
        if is_geokit or params_calc.get('v1v2_formula') == 'zhu1993':
            t_calc = np.maximum(t_calc, 0)
        t_mantle = params_calc.get('T2') if is_geokit else None
        d_alpha, d_beta, d_gamma = calculate_deltas(
            Pb206,
            Pb207,
            Pb208,
            t_calc,
            params=params_calc,
            T_mantle=t_mantle,
            use_two_stage=False,
            E1=E1_val,
            E2=E2_val,
        )
        
    results.update({
        'Delta_alpha': d_alpha,
        'Delta_beta': d_beta,
        'Delta_gamma': d_gamma
    })
    
    # 4. V1-V2 坐标计算
    params_temp = params_calc.copy()
    if a is not None: params_temp['a'] = a
    if b is not None: params_temp['b'] = b
    if c is not None: params_temp['c'] = c
    
    v1, v2 = calculate_v1v2_coordinates(d_alpha, d_beta, d_gamma, params=params_temp)
    results['V1'] = v1
    results['V2'] = v2
    
    # 5. 源区参数反演 — 根据模型自动选择参考参数
    if is_two_stage:
        X_ref, Y_ref, Z_ref = params_calc['a1'], params_calc['b1'], params_calc['c1']
        T_ref = params_calc['T1']
    else:
        X_ref, Y_ref, Z_ref = params_calc['a0'], params_calc['b0'], params_calc['c0']
        T_ref = params_calc['T2']

    mu_val = _invert_mu(Pb206, Pb207, t_input, X_ref, Y_ref, T_ref, params_calc)
    omega_val = _invert_omega(Pb208, t_input, Z_ref, T_ref, params_calc)
    if mu_val is None:
        # Solver failure: degrade to NaN instead of crashing downstream in
        # calculate_source_nu / initial-ratio inversion.
        logger.warning("Mu inversion failed; using NaN for affected samples")
        mu_val = np.nan
    if omega_val is None:
        logger.warning("Omega inversion failed; using NaN for affected samples")
        omega_val = np.nan
    results['mu'] = mu_val
    results['nu'] = calculate_source_nu(mu_val, params=params_calc)
    results['omega'] = omega_val

    # 5.2 模型参考参数（按 age_model 自动选择参考参数）
    mu_model = calculate_model_mu(Pb206, Pb207, t_input, params=params_calc)
    kappa_model = calculate_model_kappa(Pb206, Pb208, t_input, params=params_calc)
    results['mu_model'] = mu_model
    results['kappa_model'] = kappa_model
    results['omega_model'] = kappa_model * mu_model
    
    # 6. 初始比值反演 (基于真实年龄或 tSK)
    results['Init_206_204'] = calculate_initial_ratio_64(t_input, Pb206, Pb207, params=params_calc)
    results['Init_207_204'] = calculate_initial_ratio_74(t_input, Pb206, Pb207, params=params_calc)
    results['Init_208_204'] = calculate_initial_ratio_84(t_input, Pb206, Pb207, Pb208, params=params_calc)
    
    return results


# =============================================================================
# Albarède & Juteau (1984) T–μ–κ 结果键名与一站式反演
# =============================================================================
# 参考: Albarède, F. & Juteau, M. (1984). Unscrambling the lead model ages.
#       Geochimica et Cosmochimica Acta 48(1), 207-212.
#       doi:10.1016/0016-7037(84)90364-8
# 常数与解法与 R 包 ASTR::albarede_juteau_1984() 一致; 2012 版 T–μ–κ 作者本人
# 表示不应使用, 故未实现 (见 engine.py §1.9)。
# 这组量与 calculate_all_parameters() 刻意分开: 它的参考组成/年龄锚点 (T0 =
# 3.8 Ga, 现代 common Pb) 与 PbIso 系列预设 (CDT/a₁) 不同, 混在同一字典里会让
# 下游误用错参考。

ALBAREDE_T_MODEL_KEY = 't_Albarede (Ma)'
ALBAREDE_MU_KEY = 'mu_Albarede'
ALBAREDE_KAPPA_KEY = 'kappa_Albarede'
ALBAREDE_OMEGA_KEY = 'omega_Albarede'
ALBAREDE_DELTA_MU_KEY = 'Delta_mu_Albarede'
ALBAREDE_DELTA_KAPPA_KEY = 'Delta_kappa_Albarede'
#: 式 (16): dT_i/dT_0 (无量纲), 参考模型 T0 选择对模式年龄的灵敏度
ALBAREDE_AGE_SENSITIVITY_KEY = 'dT_dT0_Albarede'


def calculate_albarede_parameters(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    Pb208_204_S: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> dict[str, np.ndarray]:
    """
    Albarède & Juteau (1984) T–μ–κ 一站式反演

    按 AJ84 的两条生长方程解出 (T_i, μ_i), 并由 z 生长方程求 κ_i
    (ω_i = μ_i·κ_i); 另返回相对现代 common Pb 参考的 Δμ_i/Δκ_i 与 T0 灵敏度
    dT_i/dT0。模型族外样品 (T_i 不在 (0, T0) 内) 返回 NaN。

    Args:
        Pb206_204_S, Pb207_204_S, Pb208_204_S: 样品 206/204、207/204、208/204
        params: 参数字典 (可选; 应为 AJ84 预设, 提供 U_ratio = 1/137.79)

    Returns:
        dict: 键为 ALBAREDE_*_KEY 常量 (T_i, μ, κ, ω, Δμ, Δκ, dT/dT0)
    """
    if params is None:
        params = engine.params

    age = calculate_albarede_model_age(Pb206_204_S, Pb207_204_S, params)
    if age is None:
        age = np.full(np.shape(Pb206_204_S), np.nan, dtype=float)

    mu = calculate_albarede_mu(Pb206_204_S, Pb207_204_S, age, params)
    kappa = calculate_albarede_kappa(Pb206_204_S, Pb208_204_S, age, mu, params)
    delta_mu = mu - ALBAREDE_MU_STAR

    return {
        ALBAREDE_T_MODEL_KEY: age,
        ALBAREDE_MU_KEY: mu,
        ALBAREDE_KAPPA_KEY: kappa,
        ALBAREDE_OMEGA_KEY: mu * kappa,
        ALBAREDE_DELTA_MU_KEY: delta_mu,
        ALBAREDE_DELTA_KAPPA_KEY: kappa - ALBAREDE_KAPPA_STAR,
        ALBAREDE_AGE_SENSITIVITY_KEY: calculate_albarede_age_sensitivity(age, delta_mu, mu, params),
    }

__all__ = [
    'T_EARTH_1ST',
    'T_EARTH_CANON',
    'T_SK_STAGE2',
    'LAMBDA_238',
    'LAMBDA_235',
    'LAMBDA_232',
    'A0',
    'B0',
    'C0',
    'A1_SK',
    'B1_SK',
    'C1_SK',
    'MU_M_DEFAULT',
    'OMEGA_M_DEFAULT',
    'U_RATIO_NATURAL',
    'E1_DEFAULT',
    'E2_DEFAULT',
    'ALBAREDE_T0',
    'ALBAREDE_X_STAR',
    'ALBAREDE_Y_STAR',
    'ALBAREDE_Z_STAR',
    'ALBAREDE_MU_STAR',
    'ALBAREDE_KAPPA_STAR',
    'ALBAREDE_OMEGA_STAR',
    'ALBAREDE_U238_235',
    'U_RATIO_AJ84',
    'ALBAREDE_X0',
    'ALBAREDE_Y0',
    'ALBAREDE_Z0',
    'PRESET_MODELS',
    'GeochemistryEngine',
    'engine',
    'calculate_modelcurve',
    'calculate_model_slope',
    'calculate_single_stage_age',
    'calculate_two_stage_age',
    'calculate_source_mu',
    'calculate_source_omega',
    'calculate_source_nu',
    'calculate_model_mu',
    'calculate_model_kappa',
    'calculate_initial_ratio_64',
    'calculate_initial_ratio_74',
    'calculate_initial_ratio_84',
    'calculate_deltas',
    'calculate_v1v2_coordinates',
    'calculate_albarede_model_age',
    'calculate_albarede_age_sensitivity',
    'albarede_model_age_residual',
    'calculate_albarede_mu',
    'calculate_albarede_delta_mu',
    'calculate_albarede_kappa',
    'calculate_albarede_delta_kappa',
    'calculate_albarede_parameters',
    'ALBAREDE_T_MODEL_KEY',
    'ALBAREDE_MU_KEY',
    'ALBAREDE_KAPPA_KEY',
    'ALBAREDE_OMEGA_KEY',
    'ALBAREDE_DELTA_MU_KEY',
    'ALBAREDE_DELTA_KAPPA_KEY',
    'ALBAREDE_AGE_SENSITIVITY_KEY',
    'calculate_paleoisochron_line',
    'calculate_isochron1_growth_curve',
    'calculate_isochron2_growth_curve',
    'york_regression',
    'calculate_pbpb_age_from_ratio',
    'calculate_isochron_age_from_slope',
    'calculate_source_mu_from_isochron',
    'calculate_source_kappa_from_slope',
    'resolve_age_model',
    'calculate_all_parameters',
]
