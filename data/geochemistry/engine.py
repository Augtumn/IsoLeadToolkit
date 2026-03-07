# -*- coding: utf-8 -*-
"""Geochemistry parameters and model engine."""
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
try:
    from scipy.stats import chi2
except Exception:
    chi2 = None

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
EPSILON = 1e-50  # Shared denominator floor for numerical stability

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
        # Geokit 版本参数（与其他算法保持"年"为单位）
        'age_model': 'single_stage',
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
    "V1V2 (Zhu 1993)": {
        # Zhu (1993): Pb isotope 3D topological projection (forced through origin)
        'age_model': 'single_stage',
        'T1': T_EARTH_CANON,
        'T2': T_EARTH_CANON,
        'Tsec': 0.0,
        'a0': A0, 'b0': B0, 'c0': C0,
        'a1': A0, 'b1': B0, 'c1': C0,
        'mu_M': 7.8,
        'omega_M': 7.8 * 4.04,
        'U_ratio': U_RATIO_NATURAL,
        'E1': E1_DEFAULT,
        'E2': E2_DEFAULT,
        'v1v2_formula': 'zhu1993'
    },
    "Stacey & Kramers (2nd Stage)": {
        # PbIso Table 1: T1 = 3700 Ma for SK2
        'age_model': 'two_stage',
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
        'age_model': 'single_stage',
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
        'age_model': 'single_stage',
        'T1': 4509e6, 'T2': 4509e6, 'Tsec': 0, # Continuous
        'a0': A0, 'b0': B0, 'c0': C0,
        'a1': A0, 'b1': B0, 'c1': C0,
        # PbIso Table 3: Mu1=10.8, W1=41.2, E1/E2 non-zero
        'mu_M': 10.8,
        'omega_M': 41.2,
        'U_ratio': U_RATIO_NATURAL,
        'E1': 5e-11,
        'E2': 3.7e-11
    },
    "Maltese & Mezger (2020)": {
        # BSE evolution model: initial BSE composition at t1 = 4.498 Ga
        # From Maltese & Mezger (2020), GCA
        'age_model': 'single_stage',
        'T1': 4498e6,
        'T2': 4498e6,
        'Tsec': 0.0,
        'a0': A0, 'b0': B0, 'c0': C0,
        'a1': 9.345, 'b1': 10.37, 'c1': 29.51,
        'mu_M': 8.63,
        'omega_M': 34.8,  # kappa~4.05 -> omega ~ 34.8
        'U_ratio': U_RATIO_NATURAL,
        'E1': E1_DEFAULT,
        'E2': E2_DEFAULT
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
            'age_model': 'two_stage',
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
                if k == 'age_model':
                    self.params[k] = str(v)
                else:
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
