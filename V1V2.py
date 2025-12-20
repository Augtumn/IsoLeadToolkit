import numpy as np
import math
from scipy import optimize

# ==================== 常数定义 ====================
# 时间常数 (年)
T1 = 4430e6  # 地球年龄1
T2 = 4570e6  # 地球年龄2
Tsec = 3700e6 # 二阶段地球年龄

# 衰变常数 (a^-1)
lambda_238 = 1.55125e-10
lambda_235 = 9.8485e-10
lambda_232 = 4.94752e-11  

# 原始铅比值
a0 = 9.307
b0 = 10.294
c0 = 29.476

# 地幔参数
mu_M = 7.8  # 238U/204Pb
v_M = mu_M / 137.88  # 235U/204Pb
omega_M = 4.04 * mu_M  # 232Th/204Pb

# 235U/238U 比值
U_ratio = 1 / 137.88

# 回归平面参数
a = 0.0
b = 2.0367
c = -6.143

# 两阶段初始铅
a1 = 11.152
b1 = 12.998
c1 = 31.23



# ==================== 数值求解函数 ====================
def solve_age_scipy(f, bounds):
    """
    使用scipy.optimize.brentq求解年龄方程
    """
    t_min, t_max = bounds
    # 避免在t=T时的奇点，稍微减小上界
    t_max_safe = t_max - 1.0
    
    try:
        f_min = f(t_min)
        f_max = f(t_max_safe)
        
        if np.isnan(f_min) or np.isnan(f_max):
            return None
            
        # 检查是否有根（异号）
        if f_min * f_max > 0:
            return None
            
        return optimize.brentq(f, t_min, t_max_safe, xtol=1e-6)
    except Exception:
        return None

# ==================== 单阶段模式年龄计算 ====================
def calculate_tCDT_single(Pb206_204_S, Pb207_204_S):
    """
    计算单个样品的单阶段模式年龄T_CDT
    """
    # 定义方程
    def f(t):
        denominator = np.exp(lambda_238 * T1) - np.exp(lambda_238 * t)
        if abs(denominator) < 1e-50:
            denominator = 1e-50
        numerator = np.exp(lambda_235 * T1) - np.exp(lambda_235 * t)
        
        # 避免除以零
        if abs(Pb206_204_S - a0) < 1e-10:
             return 1e10 
             
        R = (Pb207_204_S - b0) / (Pb206_204_S - a0)
        return R - U_ratio * numerator / denominator
    
    # 使用scipy求解
    # 允许负年龄（未来年龄/异常铅），扩大搜索下界
    t_result = solve_age_scipy(f, bounds=(-T1, T1))
    
    if t_result is None:
        return None
    
    # 转换为Ma
    return t_result / 1e6

def calculate_tCDT(Pb206_204_S, Pb207_204_S):
    """
    计算单阶段模式年龄T_CDT（支持向量化）
    """
    # 确保输入是数组
    Pb206_204_S = np.asarray(Pb206_204_S)
    Pb207_204_S = np.asarray(Pb207_204_S)

    if Pb206_204_S.ndim == 0:
        # 0-d 数组 (标量)
        return calculate_tCDT_single(Pb206_204_S.item(), Pb207_204_S.item())
    
    # 1-d 数组
    results = []
    for pb206, pb207 in zip(Pb206_204_S, Pb207_204_S):
        results.append(calculate_tCDT_single(pb206, pb207))
    return np.array(results)

# ==================== 两阶段模式年龄计算 ====================
def calculate_tSK_single(Pb206_204_S, Pb207_204_S):
    """
    计算单个样品的两阶段模式年龄T_SK
    """
    # 定义方程
    def f(t):
        denominator = np.exp(lambda_238 * Tsec) - np.exp(lambda_238 * t)
        if abs(denominator) < 1e-50:
            denominator = 1e-50
        numerator = np.exp(lambda_235 * Tsec) - np.exp(lambda_235 * t)
        
        if abs(Pb206_204_S - a1) < 1e-10:
             return 1e10
             
        R = (Pb207_204_S - b1) / (Pb206_204_S - a1)
        return R - U_ratio * numerator / denominator
    
    # 使用scipy求解
    # 允许负年龄（未来年龄/异常铅），扩大搜索下界
    t_result = solve_age_scipy(f, bounds=(-Tsec, Tsec))
    
    if t_result is None:
        return None
    
    # 转换为Ma
    return t_result / 1e6

def calculate_tSK(Pb206_204_S, Pb207_204_S):
    """
    计算两阶段模式年龄T_SK（支持向量化）
    """
    # 确保输入是数组
    Pb206_204_S = np.asarray(Pb206_204_S)
    Pb207_204_S = np.asarray(Pb207_204_S)

    if Pb206_204_S.ndim == 0:
        # 0-d 数组 (标量)
        return calculate_tSK_single(Pb206_204_S.item(), Pb207_204_S.item())
    
    # 1-d 数组
    results = []
    for pb206, pb207 in zip(Pb206_204_S, Pb207_204_S):
        results.append(calculate_tSK_single(pb206, pb207))
    return np.array(results)

# ==================== Δ值计算 ====================
def calculate_delta(Pb206_204_S, Pb207_204_S, Pb208_204_S, tCDT):
    """
    计算Δα, Δβ, Δγ
    注意：这里总是使用同时期地幔值
    """
    # 确保 tCDT 是数组
    tCDT = np.asarray(tCDT)
    
    # 处理 None 值 (如果有)，将其转换为 NaN 以避免计算错误
    if tCDT.dtype == object or np.issubdtype(tCDT.dtype, np.object_):
        # 使用列表推导式处理 None，然后转回 numpy 数组
        tCDT_flat = [x if x is not None else np.nan for x in tCDT.ravel()]
        tCDT = np.array(tCDT_flat).reshape(tCDT.shape)
        
    # 确保为浮点型并处理负值
    tCDT = tCDT.astype(float)
    tCDT = np.maximum(tCDT, 0)
    
    # 将 Ma 转换为 年
    t = tCDT * 1e6
    # 此处使用时间为T2，原因未知，实测GeoKit使用这一参数
    
    Pb206_204_M = a0 + mu_M * (np.exp(lambda_238 * T2) - np.exp(lambda_238 * t))
    Pb207_204_M = b0 + v_M * (np.exp(lambda_235 * T2) - np.exp(lambda_235 * t))
    Pb208_204_M = c0 + omega_M * (np.exp(lambda_232 * T2) - np.exp(lambda_232 * t))
    
    Delta_alpha = ((Pb206_204_S / Pb206_204_M) - 1) * 1000
    Delta_beta = ((Pb207_204_S / Pb207_204_M) - 1) * 1000
    Delta_gamma = ((Pb208_204_S / Pb208_204_M) - 1) * 1000
    
    return Delta_alpha, Delta_beta, Delta_gamma

# ==================== V1, V2计算 ====================
def calculate_V1V2(Delta_alpha, Delta_beta, Delta_gamma, a=0.0, b=2.0367, c=-6.143):
    """
    计算V1, V2
    参数 a, b, c 可选，默认使用全局定义值(如果未传入)
    """
    # 计算Δα_p, Δβ_p, Δγ_p
    denom = 1 + b**2 + c**2
    
    Delta_alpha_p = ((1 + c**2) * Delta_alpha + b * (Delta_gamma - c * Delta_beta - a)) / denom
    Delta_beta_p = ((1 + b**2) * Delta_beta + c * (Delta_gamma - b * Delta_alpha - a)) / denom
    Delta_gamma_p = a + b * Delta_alpha_p + c * Delta_beta_p
    
    # 计算V1, V2
    V1 = (b * Delta_gamma_p + Delta_alpha_p) / np.sqrt(1 + b**2)
    V2 = (np.sqrt(1 + b**2 + c**2) / np.sqrt(1 + b**2)) * Delta_beta_p
    
    return V1, V2

# ==================== 主计算函数 ====================
def calculate_all_parameters(Pb206_204_S, Pb207_204_S, Pb208_204_S, calculate_ages=True, a=0.0, b=2.0367, c=-6.143, scale=1.0, **kwargs):
    """
    计算所有参数
    
    参数:
        Pb206_204_S, Pb207_204_S, Pb208_204_S: 样品铅同位素比值
        calculate_ages: 兼容性参数，实际总是计算年龄
        a, b, c: 回归平面参数
        scale: 缩放参数 (预留，当前未在计算中使用)
        **kwargs: 接收其他可能的参数以防止报错
    """
    # 将输入转换为numpy数组以便向量化计算
    Pb206_204_S = np.asarray(Pb206_204_S)
    Pb207_204_S = np.asarray(Pb207_204_S)
    Pb208_204_S = np.asarray(Pb208_204_S)
    
    # 检查输入形状是否一致
    if not (Pb206_204_S.shape == Pb207_204_S.shape == Pb208_204_S.shape):
        raise ValueError("输入数组形状不一致")
    
    # 初始化结果字典
    results = {
        'Pb206_204_S': Pb206_204_S,
        'Pb207_204_S': Pb207_204_S,
        'Pb208_204_S': Pb208_204_S,
    }
    
    # 计算模式年龄 (总是计算)
    tCDT = calculate_tCDT(Pb206_204_S, Pb207_204_S)
    results['tCDT (Ma)'] = tCDT
    
    tSK = calculate_tSK(Pb206_204_S, Pb207_204_S)
    results['tSK (Ma)'] = tSK
        
    # 计算Δα, Δβ, Δγ
    Delta_alpha, Delta_beta, Delta_gamma = calculate_delta(Pb206_204_S, Pb207_204_S, Pb208_204_S, tCDT)
    results['Delta_alpha'] = Delta_alpha
    results['Delta_beta'] = Delta_beta
    results['Delta_gamma'] = Delta_gamma
    
    # 计算V1, V2 (使用传入的参数)
    V1, V2 = calculate_V1V2(Delta_alpha, Delta_beta, Delta_gamma, a=a, b=b, c=c)
    results['V1'] = V1
    results['V2'] = V2

    return results


if __name__ == '__main__':
    mantle_206, mantle_207, mantle_208 = 16.589,15.317,36.784
    tCDT = calculate_tCDT_single(mantle_206, mantle_207)
    delta=calculate_delta(mantle_206, mantle_207, mantle_208 , tCDT)
    print(tCDT,delta)
