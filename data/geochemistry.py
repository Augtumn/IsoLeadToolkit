# -*- coding: utf-8 -*-
"""
核心地球化学算法库 (Geochemistry Core Library)

本模块实现了铅同位素地球化学计算的核心算法，包括：
1. 模型年龄计算 (单阶段模式年龄、Stacey-Kramers 两阶段模式年龄)
2. 源区特征参数反演 (Mu, Omega, Kappa)
3. 初始铅同位素比值计算
4. Δ值计算及 V1-V2 判别图投影
5. 等时线相关参数计算

算法来源：
- 主要适配自 Geokit (V1V2) 及其 Python 实现
- R 语言 PbIso 软件包 (用于 Stacey-Kramers 模型参数反演)
- 经典文献: Stacey & Kramers (1975), Jaffey et al. (1971), Tatsumoto et al. (1973)
"""

import numpy as np
from scipy import optimize

# =============================================================================
# 1. 物理常数与参考值定义
# =============================================================================

# 1.1 时间常数 (单位: 年)
T_EARTH_1ST = 4430e6  # 地球年龄 (Stacey & Kramers 1st stage appx)
T_EARTH_CANON = 4570e6  # 正则地球年龄 (Canonical Earth Age)
T_SK_STAGE2 = 3700e6    # Stacey-Kramers 模型第二阶段起始时间

# 1.2 衰变常数 (单位: 1/年)
# 来源: Jaffey et al. (1971) / Steiger and Jager (1977)
LAMBDA_238 = 1.55125e-10
LAMBDA_235 = 9.8485e-10
LAMBDA_232 = 4.94752e-11

# 1.3 原始铅同位素比值 (Primordial Lead)
# 来源: Tatsumoto et al. (1973) / Canyon Diablo Troilite (CDT)
A0 = 9.307   # 206Pb/204Pb
B0 = 10.294  # 207Pb/204Pb
C0 = 29.476  # 208Pb/204Pb

# 1.4 Stacey-Kramers 两阶段模型参数 (第二阶段起始值)
# 来源: Stacey & Kramers (1975) EPSL
A1_SK = 11.152
B1_SK = 12.998
C1_SK = 31.23

# 1.5 地幔参考参数
# PbIso 默认采用 Stacey & Kramers (1975) 二阶段参数
MU_M_DEFAULT = 9.74           # 默认地幔 mu 值 (238U/204Pb)
OMEGA_M_DEFAULT = 36.84       # 默认地幔 omega 值 (232Th/204Pb)

# 1.6 物理比值
U_RATIO_NATURAL = 1.0 / 137.88  # 天然 235U/238U 比值

# 1.7 V1-V2 判别图回归平面参数
# 来源: Zhu (1995, 1998)
REGRESSION_A = 0.0
REGRESSION_B = 2.0367
REGRESSION_C = -6.143

# 1.8 PbIso 模型曲线演化参数 (R: E1/E2)
E1_DEFAULT = 0.0
E2_DEFAULT = 0.0

# =============================================================================
# 2. 预设模型库
# =============================================================================

PRESET_MODELS = {
    "V1V2 (Geokit)": {
        # Geokit 版本参数（与其他算法保持“年”为单位）
        'T1': 4430e6,      # Age01
        'T2': 4570e6,      # Age02
        'Tsec': 3700e6,    # Age1
        'a0': 9.307, 'b0': 10.294, 'c0': 29.476,
        'a1': 11.152, 'b1': 12.998, 'c1': 31.23,
        'mu_M': 7.8,
        'omega_M': 4.04 * 7.8,
        'U_ratio': 1.0 / 137.88,
        'E1': E1_DEFAULT,
        'E2': E2_DEFAULT
    },
    "V1V2 (Chen 1982)": {
        # Chen et al. (1982): single-stage mantle lead, mu=7.8, Th/U=4.13
        'T1': T_EARTH_CANON,
        'T2': T_EARTH_CANON,
        'Tsec': 0.0,
        'a0': 9.307, 'b0': 10.294, 'c0': 29.476,
        'a1': 9.307, 'b1': 10.294, 'c1': 29.476,
        'mu_M': 7.8,
        'omega_M': 7.8 * 4.13,
        'U_ratio': U_RATIO_NATURAL,
        'E1': E1_DEFAULT,
        'E2': E2_DEFAULT
    },
    "Stacey & Kramers (2nd Stage)": {
        # PbIso Table 1: T1 = 3700 Ma for SK2
        'T1': T_SK_STAGE2,
        'T2': T_EARTH_CANON,
        'Tsec': T_SK_STAGE2,
        'a0': A0, 'b0': B0, 'c0': C0,
        'a1': A1_SK, 'b1': B1_SK, 'c1': C1_SK,
        'mu_M': 9.74,
        'omega_M': 36.84, # Derived from kappa=3.78 or similar
        'U_ratio': U_RATIO_NATURAL,
        'E1': E1_DEFAULT,
        'E2': E2_DEFAULT
    },
    "Stacey & Kramers (1st Stage)": {
        'T1': T_EARTH_CANON,
        'T2': T_EARTH_CANON,
        'Tsec': T_SK_STAGE2,
        'a0': A0, 'b0': B0, 'c0': C0,
        'a1': A0, 'b1': B0, 'c1': C0, # Start from primordial
        # PbIso Table 3: Mu1=7.2, W1=33.2
        'mu_M': 7.2,
        'omega_M': 33.2,
        'U_ratio': U_RATIO_NATURAL,
        'E1': E1_DEFAULT,
        'E2': E2_DEFAULT
    },
    "Cumming & Richards (Model III)": {
        'T1': 4509e6, 'T2': 4509e6, 'Tsec': 0, # Continuous
        'a0': A0, 'b0': B0, 'c0': C0,
        'a1': A0, 'b1': B0, 'c1': C0,
        # PbIso Table 3: Mu1=10.8, W1=41.2, E1/E2 non-zero
        'mu_M': 10.8,
        'omega_M': 41.2,
        'U_ratio': U_RATIO_NATURAL,
        'E1': 5e-11,
        'E2': 3.7e-11
    }
}

# =============================================================================
# 3. 参数管理引擎
# =============================================================================

class GeochemistryEngine:
    """
    地球化学计算引擎单例类
    
    负责管理当前计算所需的全球参数（如地球年龄、初始比值、衰变常数等）。
    支持加载预设模型或自定义参数。
    """
    
    def __init__(self):
        # 默认参数初始化 (与 PbIso 文献默认一致: SK 2nd stage)
        self.params = {
            'T1': T_SK_STAGE2,
            'T2': T_EARTH_CANON,
            'Tsec': T_SK_STAGE2,
            
            'lambda_238': LAMBDA_238,
            'lambda_235': LAMBDA_235,
            'lambda_232': LAMBDA_232,
            
            'a0': A0, 'b0': B0, 'c0': C0,
            'a1': A1_SK, 'b1': B1_SK, 'c1': C1_SK,
            
            'mu_M': MU_M_DEFAULT,
            'omega_M': OMEGA_M_DEFAULT,
            'U_ratio': U_RATIO_NATURAL,
            
            'a': REGRESSION_A, 'b': REGRESSION_B, 'c': REGRESSION_C,
            'E1': E1_DEFAULT, 'E2': E2_DEFAULT
        }
        self.current_model_name = "Stacey & Kramers (2nd Stage)"
        self._update_derived_params()

    def _update_derived_params(self):
        """更新衍生参数 (内部使用)"""
        mu = self.params.get('mu_M', 9.74)
        u_r = self.params.get('U_ratio', U_RATIO_NATURAL)
        # v = 235U/204Pb = mu * (235U/238U)
        self.params['v_M'] = mu * u_r

    def get_available_models(self):
        """获取可用预设模型列表"""
        return list(PRESET_MODELS.keys())

    def load_preset(self, model_name):
        """
        加载预设模型参数
        
        Args:
            model_name (str): 模型名称
            
        Returns:
            bool: 加载是否成功
        """
        if model_name in PRESET_MODELS:
            preset = PRESET_MODELS[model_name]
            self.update_parameters(preset)
            self.current_model_name = model_name
            return True
        return False

    def update_parameters(self, new_params):
        """
        更新计算参数
        
        Args:
            new_params (dict): 包含参数键值对的字典
        """
        for k, v in new_params.items():
            if k in self.params:
                try:
                    self.params[k] = float(v)
                except (ValueError, TypeError):
                    pass # 忽略无效输入
        self._update_derived_params()

    def get_parameters(self):
        """获取当前参数副本"""
        return self.params.copy()

# 全局单例实例
engine = GeochemistryEngine()

# =============================================================================
# 4. 数值计算辅助函数
# =============================================================================

def _solve_age_scipy(f, bounds, search_points=200):
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

    def _eval(val):
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
            return optimize.brentq(f, t_min, t_max_safe, xtol=1e-6)

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
                return optimize.brentq(f, t_samples[i], t_samples[i + 1], xtol=1e-6)

        return None
    except Exception:
        return None


def _exp_evolution_term(lmbda, t_years, E=0.0):
    """
    PbIso 模型曲线的指数演化项（对应 R: exp(lambda*t)*(1 - E*(t - 1/lambda))）
    """
    if E == 0 or E == 0.0:
        return np.exp(lmbda * t_years)
    return np.exp(lmbda * t_years) * (1.0 - E * (t_years - (1.0 / lmbda)))


def calculate_modelcurve(t_Ma, params=None, T1=None, X1=None, Y1=None, Z1=None,
                         Mu1=None, W1=None, U8U5=None, L5=None, L8=None, L2=None,
                         E1=None, E2=None):
    """
    生成 PbIso 风格的模型曲线（等价 R 的 modelcurve）

    Args:
        t_Ma: 时间或年龄 (Ma)，标量或数组
        T1: 模型起始时间 (Ma)，默认使用 params['Tsec'] (年) 转换
        X1/Y1/Z1: 起始同位素比值
        Mu1/W1: 238U/204Pb 与 232Th/204Pb 模型值
        U8U5: 238U/235U 比值（R 中为 137.88）
        L5/L8/L2: 衰变常数
        E1/E2: 演化参数（默认 0）

    Returns:
        dict: {'t_Ma', 'Pb206_204', 'Pb207_204', 'Pb208_204'}
    """
    if params is None:
        params = engine.params

    t_years = np.asarray(t_Ma, dtype=float) * 1e6

    T1_years = params['T1'] if T1 is None else float(T1) * 1e6
    X1_val = params['a1'] if X1 is None else float(X1)
    Y1_val = params['b1'] if Y1 is None else float(Y1)
    Z1_val = params['c1'] if Z1 is None else float(Z1)

    Mu1_val = params.get('mu_M', 9.74) if Mu1 is None else float(Mu1)
    W1_val = params.get('omega_M', 36.84) if W1 is None else float(W1)

    U8U5_val = (1.0 / params['U_ratio']) if U8U5 is None else float(U8U5)
    L5_val = params['lambda_235'] if L5 is None else float(L5)
    L8_val = params['lambda_238'] if L8 is None else float(L8)
    L2_val = params['lambda_232'] if L2 is None else float(L2)

    E1_val = params.get('E1', 0.0) if E1 is None else float(E1)
    E2_val = params.get('E2', 0.0) if E2 is None else float(E2)

    e8_T1 = _exp_evolution_term(L8_val, T1_years, E1_val)
    e8_t = _exp_evolution_term(L8_val, t_years, E1_val)
    e5_T1 = _exp_evolution_term(L5_val, T1_years, E1_val)
    e5_t = _exp_evolution_term(L5_val, t_years, E1_val)
    e2_T1 = _exp_evolution_term(L2_val, T1_years, E2_val)
    e2_t = _exp_evolution_term(L2_val, t_years, E2_val)

    x = X1_val + Mu1_val * (e8_T1 - e8_t)
    y = Y1_val + (Mu1_val / U8U5_val) * (e5_T1 - e5_t)
    z = Z1_val + W1_val * (e2_T1 - e2_t)

    return {
        't_Ma': np.asarray(t_Ma, dtype=float),
        'Pb206_204': x,
        'Pb207_204': y,
        'Pb208_204': z
    }

# =============================================================================
# 5. 模式年龄计算
# =============================================================================

def calculate_single_stage_age(Pb206_204_S, Pb207_204_S, params=None, initial_age=None):
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
    if params is None: params = engine.params
    
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
        def f(t):
            denom = np.exp(l238 * T) - np.exp(l238 * t)
            if abs(denom) < 1e-50: denom = 1e-50
            num = np.exp(l235 * T) - np.exp(l235 * t)
            
            if abs(S206 - a0_val) < 1e-10: return 1e10
                
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

        def f_scalar(t):
            denom = np.exp(l238 * T) - np.exp(l238 * t)
            if abs(denom) < 1e-50: denom = 1e-50
            num = np.exp(l235 * T) - np.exp(l235 * t)
            
            if abs(s206 - a0_val) < 1e-10: return 1e10 # 避免除零
            
            R = (s207 - b0_val) / (s206 - a0_val)
            return R - u_ratio * num / denom

        t_res = _solve_age_scipy(f_scalar, bounds=(-4700e6, 4700e6))
        results.append(t_res / 1e6 if t_res is not None else np.nan)
        
    return np.array(results).reshape(S206.shape)


def calculate_two_stage_age(Pb206_204_S, Pb207_204_S, params=None):
    """
    计算两阶段模式年龄 (Two Stage Model Age - Stacey & Kramers)
    基于 SK 模型第二阶段方程求解。
    
    Args:
        Pb206_204_S: 样品 206Pb/204Pb 比值
        Pb207_204_S: 样品 207Pb/204Pb 比值
        
    Returns:
        np.ndarray or float: 模式年龄 (Ma)
    """
    if params is None: params = engine.params

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
        def f(t):
            denom = np.exp(l238 * T) - np.exp(l238 * t)
            if abs(denom) < 1e-50: denom = 1e-50
            num = np.exp(l235 * T) - np.exp(l235 * t)
            
            if abs(S206 - a1_val) < 1e-10: return 1e10
                
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
            
        def f_scalar(t):
            denom = np.exp(l238 * T) - np.exp(l238 * t)
            if abs(denom) < 1e-50: denom = 1e-50
            num = np.exp(l235 * T) - np.exp(l235 * t)
            
            if abs(s206 - a1_val) < 1e-10: return 1e10
                
            R = (s207 - b1_val) / (s206 - a1_val)
            return R - u_ratio * num / denom
        
        t_res = _solve_age_scipy(f_scalar, bounds=(-4700e6, 4700e6))
        results.append(t_res / 1e6 if t_res is not None else np.nan)

    return np.array(results).reshape(S206.shape)

# =============================================================================
# 6. 源区特征参数计算 (传统/混合方法)
# =============================================================================

def calculate_mu_sk(Pb206_204_S, Pb207_204_S, t_Ma, params=None):
    """
    计算源区 Mu 值 (238U/204Pb)
    
    说明:
    此函数基于给定的样品年龄 t 和测量比值，反演产生该铅同位素组成的源区 U/Pb 比。
    计算假设铅从初始时间 T (T2) 以单一阶段演化到 t (近似)。
    
    Returns:
        np.ndarray: 源区 Mu 值
    """
    if params is None: params = engine.params
    
    l238 = params['lambda_238']
    l235 = params['lambda_235']
    T = params['T2']
    a_init = params['a0']
    b_init = params['b0']
    u_ratio = params['U_ratio']

    # 数据预处理
    Pb206 = np.asarray(Pb206_204_S)
    Pb207 = np.asarray(Pb207_204_S)
    
    # 年龄预处理
    if t_Ma is None:
        t = np.array(np.nan)
    else:
        try:
            t = np.asarray(t_Ma, dtype=float)
        except (ValueError, TypeError):
             # 处理可能包含 None 的对象数组
             t_arr = np.asarray(t_Ma)
             if t_arr.ndim == 0:
                 t = np.array(np.nan)
             else:
                 t_flat = []
                 for x in t_arr.ravel():
                     try: t_flat.append(float(x)) 
                     except: t_flat.append(np.nan)
                 t = np.array(t_flat).reshape(t_arr.shape)

    t = np.maximum(t, 0) * 1e6
    
    # 1. 计算等时线斜率 slope
    num = np.exp(l235 * t) - 1
    den = np.exp(l238 * t) - 1
    den = np.where(np.abs(den) < 1e-50, 1e-50, den)
    slope_t = num / ((1.0 / u_ratio) * den)
    
    # 2. 计算放射性成因增量因子
    rad207_growth = u_ratio * (np.exp(l235 * T) - np.exp(l235 * t))
    rad206_growth = np.exp(l238 * T) - np.exp(l238 * t)
    
    # 3. 求解 Mu
    numerator = (Pb207 - b_init) - slope_t * (Pb206 - a_init)
    denominator = rad207_growth - slope_t * rad206_growth
    denominator = np.where(np.abs(denominator) < 1e-50, 1e-50, denominator)
    
    return numerator / denominator


def calculate_omega_sk(Pb208_204_S, t_Ma, params=None):
    """
    计算源区 Omega 值 (232Th/204Pb)
    
    基于 208Pb 生长方程: Pb208 = c0 + omega * (e^λ2*T - e^λ2*t)
    """
    if params is None: params = engine.params
    l232 = params['lambda_232']
    T = params['T2']
    c_init = params['c0']
    
    Pb208 = np.asarray(Pb208_204_S)
    
    if t_Ma is None:
        t = np.array(np.nan)
    else:
        try:
             t = np.asarray(t_Ma, dtype=float)
        except:
             # 简化处理异常
             t = np.full_like(Pb208, np.nan)

    t = np.maximum(t, 0) * 1e6
    
    denom = np.exp(l232 * T) - np.exp(l232 * t)
    denom = np.where(np.abs(denom) < 1e-50, 1e-50, denom)
    
    return (Pb208 - c_init) / denom


def calculate_nu_sk(mu, params=None):
    """
    计算源区 Nu 值 (235U/204Pb)
    nu = mu * (235U/238U)
    """
    if params is None: params = engine.params
    u_ratio = params['U_ratio']
    return mu * u_ratio

# =============================================================================
# 7. 源区特征参数计算 (R语言 PbIso 算法适配)
# =============================================================================

def calculate_mu_sk_model(Pb206_204_S, Pb207_204_S, t_Ma, params=None):
    """
    计算模型源区 Mu (对应 R 包 PbIso 中的 CalcMu)
    此函数严格遵循 Stacey & Kramers (1975) 第二阶段模型参数。
    
    Args:
        Pb206_204_S, Pb207_204_S: 样品同位素比值
        t_Ma: 样品年龄 (Ma)
        
    Returns:
        np.ndarray: 源区 Mu 值, 表示从 Tsec (3.7Ga) 到 t 阶段的 238U/204Pb 比值。
    """
    if params is None: params = engine.params
    
    l5 = params['lambda_235']
    l8 = params['lambda_238']
    
    T1 = params['T1'] 
    X1 = params['a1']
    Y1 = params['b1']
    u_ratio = params['U_ratio']
    U8U5 = 1.0 / u_ratio if u_ratio != 0 else 137.88
    
    t = np.asarray(t_Ma) * 1e6
    x = np.asarray(Pb206_204_S)
    y = np.asarray(Pb207_204_S)
    
    # 核心算法 (源自 PbIso CalcMu)
    e5t = np.exp(l5 * t)
    e8t = np.exp(l8 * t)
    e5T = np.exp(l5 * T1)
    e8T = np.exp(l8 * T1)
    
    term_slope = (e5t - 1) / (U8U5 * (e8t - 1))
    
    num = term_slope * (X1 - x) + y - Y1
    den = (e5T - e5t) / U8U5 - term_slope * (e8T - e8t)
    den = np.where(np.abs(den) < 1e-50, 1e-50, den)
    
    return num / den


def calculate_kappa_sk_model(Pb208_204_S, Pb206_204_S, t_Ma, params=None):
    """
    计算模型源区 kappa (Th/U) (对应 R 包 PbIso 中的 CalcKa)
    
    Returns:
        np.ndarray: 源区 Kappa 值 (232Th/238U)
    """
    if params is None: params = engine.params
    
    l238 = params['lambda_238']
    l232 = params['lambda_232']
    
    T = params['T1']
    X1 = params['a1']
    Z1 = params['c1']
    
    t = np.asarray(t_Ma) * 1e6
    x = np.asarray(Pb206_204_S)
    z = np.asarray(Pb208_204_S)
    
    num_time = np.exp(l238 * T) - np.exp(l238 * t)
    den_time = np.exp(l232 * T) - np.exp(l232 * t)
    den_time = np.where(np.abs(den_time) < 1e-50, 1e-50, den_time)
    
    dx = x - X1
    dx = np.where(np.abs(dx) < 1e-50, 1e-50, dx)
    
    kappa = ((z - Z1) / dx) * (num_time / den_time)
    
    return kappa

# =============================================================================
# 8. 初始比值反演 (PbIso 算法适配)
# =============================================================================

def calculate_initial_ratio_64(t_Ma, Pb206_204_S, Pb207_204_S, params=None):
    """
    计算样品形成时的初始 206Pb/204Pb (对应 PbIso Calc64in)
    """
    if params is None: params = engine.params
    
    l5 = params['lambda_235']
    l8 = params['lambda_238']
    T1 = params['T1']
    X1 = params['a1']
    Y1 = params['b1']
    u_ratio = params['U_ratio']
    U8U5 = 1.0 / u_ratio
    
    t = np.asarray(t_Ma) * 1e6
    x = np.asarray(Pb206_204_S)
    y = np.asarray(Pb207_204_S)

    # 1. 计算 Mu
    e5t = np.exp(l5 * t)
    e8t = np.exp(l8 * t)
    e5T = np.exp(l5 * T1)
    e8T = np.exp(l8 * T1)
    
    term_slope = (e5t - 1) / (U8U5 * (e8t - 1))
    mu_num = term_slope * (X1 - x) + y - Y1
    mu_den = (e5T - e5t) / U8U5 - term_slope * (e8T - e8t)
    mu_den = np.where(np.abs(mu_den) < 1e-50, 1e-50, mu_den)
    mu = mu_num / mu_den
    
    # 2. 计算初始比值: X_init = X1 + mu * (e^λ8*T1 - e^λ8*t)
    # 实际上这是计算模型在时间 t 的值
    res = X1 + mu * (e8T - e8t)
    return res

def calculate_initial_ratio_74(t_Ma, Pb206_204_S, Pb207_204_S, params=None):
    """
    计算样品形成时的初始 207Pb/204Pb (对应 PbIso Calc74in)
    """
    if params is None: params = engine.params
    
    l5 = params['lambda_235']
    l8 = params['lambda_238']
    T1 = params['T1']
    X1 = params['a1']
    Y1 = params['b1']
    u_ratio = params['U_ratio']
    U8U5 = 1.0 / u_ratio
    
    t = np.asarray(t_Ma) * 1e6
    x = np.asarray(Pb206_204_S)
    y = np.asarray(Pb207_204_S)
    
    # 1. 计算 Mu
    e5t = np.exp(l5 * t)
    e8t = np.exp(l8 * t)
    e5T = np.exp(l5 * T1)
    e8T = np.exp(l8 * T1)
    
    term_slope = (e5t - 1) / (U8U5 * (e8t - 1))
    mu_num = term_slope * (X1 - x) + y - Y1
    mu_den = (e5T - e5t) / U8U5 - term_slope * (e8T - e8t)
    mu_den = np.where(np.abs(mu_den) < 1e-50, 1e-50, mu_den)
    mu = mu_num / mu_den
    
    # 2. 计算初始比值: Y_init = Y1 + (mu/U_ratio) * (e^λ5*T1 - e^λ5*t)
    res = Y1 + (mu / U8U5) * (e5T - e5t)
    return res

def calculate_initial_ratio_84(t_Ma, Pb206_204_S, Pb207_204_S, Pb208_204_S, params=None):
    """
    计算样品形成时的初始 208Pb/204Pb (对应 PbIso Calc84in)
    """
    if params is None: params = engine.params
    
    l5 = params['lambda_235']
    l8 = params['lambda_238']
    l2 = params['lambda_232']
    T1 = params['T1']
    X1 = params['a1']
    Y1 = params['b1']
    Z1 = params['c1']
    u_ratio = params['U_ratio']
    U8U5 = 1.0 / u_ratio
    
    t = np.asarray(t_Ma) * 1e6
    x = np.asarray(Pb206_204_S)
    y = np.asarray(Pb207_204_S)
    z = np.asarray(Pb208_204_S)
    
    e5t = np.exp(l5 * t)
    e8t = np.exp(l8 * t)
    e2t = np.exp(l2 * t)
    e5T = np.exp(l5 * T1)
    e8T = np.exp(l8 * T1)
    e2T = np.exp(l2 * T1)
    
    # 1. 计算 Mu
    term_slope = (e5t - 1) / (U8U5 * (e8t - 1))
    mu_num = term_slope * (X1 - x) + y - Y1
    mu_den = (e5T - e5t) / U8U5 - term_slope * (e8T - e8t)
    mu_den = np.where(np.abs(mu_den) < 1e-50, 1e-50, mu_den)
    mu = mu_num / mu_den
    
    # 2. 计算 Kappa
    den_k_num = e2T - e2t
    den_k_den = e8T - e8t
    den_k_den = np.where(np.abs(den_k_den) < 1e-50, 1e-50, den_k_den)
    kappa = ((z - Z1) / (x - X1)) / (den_k_num / den_k_den)
    
    # 3. 计算 Omega 并得出初始 208
    omega = kappa * mu
    res = Z1 + omega * (e2T - e2t)
    
    return res

# =============================================================================
# 9. 地球化学异常 Delta Calculation
# =============================================================================

def calculate_deltas(Pb206_204_S, Pb207_204_S, Pb208_204_S, t_Ma, params=None,
                     T_mantle=None, use_two_stage=False, E1=None, E2=None):
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


def calculate_v1v2_coordinates(d_alpha, d_beta, d_gamma, params=None):
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


# Backward compatible aliases
def calculate_delta_values(Pb206_204_S, Pb207_204_S, Pb208_204_S, t_Ma, params=None):
    """Alias for calculate_deltas for backward compatibility"""
    return calculate_deltas(Pb206_204_S, Pb207_204_S, Pb208_204_S, t_Ma, params)


def calculate_v1v2(d_alpha, d_beta, d_gamma, a=0.0, b=2.0367, c=-6.143):
    """Alias for calculate_v1v2_coordinates for backward compatibility"""
    temp_params = {'a': a, 'b': b, 'c': c}
    return calculate_v1v2_coordinates(d_alpha, d_beta, d_gamma, params=temp_params)


def calculate_model_age(Pb206_204_S, Pb207_204_S, two_stage=False):
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

# =============================================================================
# 10. 等时线工具函数
# =============================================================================

def calculate_isochron_age_from_slope(slope, params=None):
    """
    从 Pb-Pb 等时线斜率计算年龄
    Slope = (1/U_ratio) * (exp(λ5*t) - 1) / (exp(λ8*t) - 1)
    """
    if params is None: params = engine.params
    
    if slope <= 0: return 0.0
    
    l238 = params['lambda_238']
    l235 = params['lambda_235']
    u_inv = 1.0 / params['U_ratio']
    
    def f(t):
        if t <= 0: return -slope
        num = np.exp(l235 * t) - 1
        den = np.exp(l238 * t) - 1
        if abs(den) < 1e-50: den = 1e-50
        return (u_inv * num / den) - slope

    res = _solve_age_scipy(f, bounds=(1e6, 10e9))
    return res / 1e6 if res else 0.0


def calculate_source_mu_from_isochron(slope, intercept, age_ma, params=None):
    """从等时线参数反演源区 Mu"""
    if params is None: params = engine.params
    
    T = params['T2']
    t = age_ma * 1e6
    u_r = params['U_ratio']
    
    C1 = np.exp(params['lambda_238'] * T) - np.exp(params['lambda_238'] * t)
    C2 = u_r * (np.exp(params['lambda_235'] * T) - np.exp(params['lambda_235'] * t))
    
    num = slope * params['a0'] + intercept - params['b0']
    den = C2 - slope * C1
    
    return num / den if abs(den) > 1e-15 else 0.0

def calculate_source_kappa_from_slope(slope_208_206, age_ma, params=None):
    """从 208/204 vs 206/204 斜率反演源区 Kappa"""
    if params is None: params = engine.params
    
    T = params['T2']
    t = age_ma * 1e6
    
    num = np.exp(params['lambda_238'] * T) - np.exp(params['lambda_238'] * t)
    den = np.exp(params['lambda_232'] * T) - np.exp(params['lambda_232'] * t)
    
    return slope_208_206 * (num / den) if abs(den) > 1e-15 else 0.0

# =============================================================================
# 11. 主入口函数
# =============================================================================

def calculate_all_parameters(Pb206_204_S, Pb207_204_S, Pb208_204_S, calculate_ages=True, a=None, b=None, c=None, scale=1.0, t_Ma=None, **kwargs):
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
    current_model = getattr(engine, 'current_model_name', '')
    # V1V2 (Geokit) 模式特殊处理: 使用 T1=4.43Ga 计算 tCDT
    is_geokit = "V1V2" in current_model or "Geokit" in current_model
    # 仅在明确的两阶段模型中使用两阶段逻辑
    is_two_stage = "2nd Stage" in current_model or current_model.endswith("(2nd Stage)")
    
    # 2. 模式年龄计算
    params_calc = engine.get_parameters()
    if is_geokit:
        tCDT = calculate_single_stage_age(Pb206, Pb207, initial_age=engine.params['T1'])
    else:
        tCDT = calculate_single_stage_age(Pb206, Pb207)

    tSK = calculate_two_stage_age(Pb206, Pb207)

    if t_Ma is None:
        t_input = tSK
    else:
        t_input = np.asarray(t_Ma, dtype=float)
        if t_input.ndim == 0:
            if not np.isfinite(t_input):
                t_input = tSK
        else:
            t_input = np.where(np.isfinite(t_input), t_input, tSK)
    
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
        t_calc = tCDT if is_geokit else calculate_single_stage_age(Pb206, Pb207, params=params_calc, initial_age=params_calc.get('T1'))
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
    
    # 5. 源区参数反演
    # 使用真实年龄（若提供），否则回退到 tSK
    mu_val = calculate_mu_sk(Pb206, Pb207, t_input, params=params_calc)
    results['mu'] = mu_val
    results['nu'] = calculate_nu_sk(mu_val, params=params_calc)
    results['omega'] = calculate_omega_sk(Pb208, t_input, params=params_calc)
    
    # 5.2 R语言 PbIso 对应参数 (严格 SK 模型)
    mu_sk = calculate_mu_sk_model(Pb206, Pb207, t_input, params=params_calc)
    kappa_sk = calculate_kappa_sk_model(Pb208, Pb206, t_input, params=params_calc)
    results['mu_SK'] = mu_sk
    results['kappa_SK'] = kappa_sk
    results['omega_SK'] = kappa_sk * mu_sk # Omega = Kappa * Mu
    
    # 6. 初始比值反演 (基于真实年龄或 tSK)
    results['Init_206_204'] = calculate_initial_ratio_64(t_input, Pb206, Pb207, params=params_calc)
    results['Init_207_204'] = calculate_initial_ratio_74(t_input, Pb206, Pb207, params=params_calc)
    results['Init_208_204'] = calculate_initial_ratio_84(t_input, Pb206, Pb207, Pb208, params=params_calc)
    
    return results
