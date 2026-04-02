# -*- coding: utf-8 -*-
"""Geochemistry package exports."""
import logging
import numpy as np

logger = logging.getLogger(__name__)

from .engine import (
    PRESET_MODELS,
    GeochemistryEngine,
    engine,
    calculate_modelcurve,
    _exp_evolution_term,
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
    REGRESSION_A,
    REGRESSION_B,
    REGRESSION_C,
    E1_DEFAULT,
    E2_DEFAULT,
)
from .age import (
    calculate_single_stage_age,
    calculate_two_stage_age,
    calculate_model_age,
)
from .source import (
    _invert_mu,
    _invert_omega,
    _invert_kappa,
    calculate_source_mu,
    calculate_source_omega,
    calculate_source_nu,
    calculate_model_mu,
    calculate_model_kappa,
    # Backward-compatible aliases
    calculate_mu_sk,
    calculate_omega_sk,
    calculate_nu_sk,
    calculate_mu_sk_model,
    calculate_kappa_sk_model,
    calculate_initial_ratio_64,
    calculate_initial_ratio_74,
    calculate_initial_ratio_84,
)
from .delta import (
    calculate_deltas,
    calculate_v1v2_coordinates,
    calculate_delta_values,
    calculate_v1v2,
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
            if max(abs(a1 - a0), abs(b1 - b0), abs(c1 - c0)) < 1e-6:
                return 'single_stage'
    except Exception:
        pass

    return 'two_stage'


def calculate_all_parameters(
    Pb206_204_S,
    Pb207_204_S,
    Pb208_204_S,
    calculate_ages=True,
    a=None,
    b=None,
    c=None,
    scale: float = 1.0,
    t_Ma=None,
    **kwargs,
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

    tSK = calculate_two_stage_age(Pb206, Pb207)

    t_model = tSK if is_two_stage else tCDT

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
    
    # 3. Delta 值计算
    E1_val = kwargs.get('E1', None)
    E2_val = kwargs.get('E2', None)

    if is_two_stage:
        t_model = tSK
        d_alpha, d_beta, d_gamma = calculate_deltas(
            Pb206, Pb207, Pb208, t_model, params=params_calc, use_two_stage=True, E1=E1_val, E2=E2_val
        )
    else:
        # 默认 V1V2 逻辑: 使用 T1=4.43Ga 计算出的单阶段年龄作为基准
        t_calc = tCDT if is_geokit else calculate_single_stage_age(Pb206, Pb207, params=params_calc, initial_age=params_calc.get('T2'))
        if is_geokit or params_calc.get('v1v2_formula') == 'zhu1993':
            t_calc = np.maximum(t_calc, 0)
        d_alpha, d_beta, d_gamma = calculate_deltas(
            Pb206, Pb207, Pb208, t_calc, params=params_calc, use_two_stage=False, E1=E1_val, E2=E2_val
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
    results['mu'] = mu_val
    results['nu'] = calculate_source_nu(mu_val, params=params_calc)
    results['omega'] = omega_val

    # 5.2 模型参考参数（按 age_model 自动选择参考参数）
    mu_model = calculate_model_mu(Pb206, Pb207, t_input, params=params_calc)
    kappa_model = calculate_model_kappa(Pb208, Pb206, t_input, params=params_calc)
    results['mu_model'] = mu_model
    results['kappa_model'] = kappa_model
    results['omega_model'] = kappa_model * mu_model
    
    # 6. 初始比值反演 (基于真实年龄或 tSK)
    results['Init_206_204'] = calculate_initial_ratio_64(t_input, Pb206, Pb207, params=params_calc)
    results['Init_207_204'] = calculate_initial_ratio_74(t_input, Pb206, Pb207, params=params_calc)
    results['Init_208_204'] = calculate_initial_ratio_84(t_input, Pb206, Pb207, Pb208, params=params_calc)
    
    return results

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
    'REGRESSION_A',
    'REGRESSION_B',
    'REGRESSION_C',
    'E1_DEFAULT',
    'E2_DEFAULT',
    'PRESET_MODELS',
    'GeochemistryEngine',
    'engine',
    'calculate_modelcurve',
    'calculate_single_stage_age',
    'calculate_two_stage_age',
    'calculate_model_age',
    'calculate_source_mu',
    'calculate_source_omega',
    'calculate_source_nu',
    'calculate_model_mu',
    'calculate_model_kappa',
    # Deprecated aliases
    'calculate_mu_sk',
    'calculate_omega_sk',
    'calculate_nu_sk',
    'calculate_mu_sk_model',
    'calculate_kappa_sk_model',
    'calculate_initial_ratio_64',
    'calculate_initial_ratio_74',
    'calculate_initial_ratio_84',
    'calculate_deltas',
    'calculate_v1v2_coordinates',
    'calculate_delta_values',
    'calculate_v1v2',
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
