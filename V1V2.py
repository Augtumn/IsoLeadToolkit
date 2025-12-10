import numpy as np
import math
from scipy import optimize

# ==================== 常数定义 ====================
# 时间常数 (年)
T1 = 4570e6  # 地球年龄
T2 = 3700e6  # 两阶段演化开始时间

# 衰变常数 (a^-1)
lambda_238 = 1.55125e-10
lambda_235 = 9.8485e-10
lambda_232 = 4.94752e-11  # 修正为正确的值

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

# ==================== 计算现代地幔值 ====================
def calculate_modern_mantle():
    """计算现代地幔铅比值"""
    Pb206_204_M = a0 + mu_M * (np.exp(lambda_238 * T1) - 1)
    Pb207_204_M = b0 + v_M * (np.exp(lambda_235 * T1) - 1)
    Pb208_204_M = c0 + omega_M * (np.exp(lambda_232 * T1) - 1)
    return Pb206_204_M, Pb207_204_M, Pb208_204_M

# 预先计算现代地幔值
Pb206_204_M_modern, Pb207_204_M_modern, Pb208_204_M_modern = calculate_modern_mantle()

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
        denominator = np.exp(lambda_238 * T2) - np.exp(lambda_238 * t)
        if abs(denominator) < 1e-50:
            denominator = 1e-50
        numerator = np.exp(lambda_235 * T2) - np.exp(lambda_235 * t)
        
        if abs(Pb206_204_S - a1) < 1e-10:
             return 1e10
             
        R = (Pb207_204_S - b1) / (Pb206_204_S - a1)
        return R - U_ratio * numerator / denominator
    
    # 使用scipy求解
    # 允许负年龄（未来年龄/异常铅），扩大搜索下界
    t_result = solve_age_scipy(f, bounds=(-T1, T2))
    
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
def calculate_delta(Pb206_204_S, Pb207_204_S, Pb208_204_S):
    """
    计算Δα, Δβ, Δγ
    注意：这里总是使用现代地幔值
    """
    Delta_alpha = (Pb206_204_S / Pb206_204_M_modern - 1) * 1000
    Delta_beta = (Pb207_204_S / Pb207_204_M_modern - 1) * 1000
    Delta_gamma = (Pb208_204_S / Pb208_204_M_modern - 1) * 1000
    
    return Delta_alpha, Delta_beta, Delta_gamma

# ==================== V1, V2计算 ====================
def calculate_V1V2(Delta_alpha, Delta_beta, Delta_gamma):
    """
    计算V1, V2
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
def calculate_all_parameters(Pb206_204_S, Pb207_204_S, Pb208_204_S, calculate_ages=True):
    """
    计算所有参数
    
    参数:
        Pb206_204_S, Pb207_204_S, Pb208_204_S: 样品铅同位素比值
        calculate_ages: 是否计算模式年龄（True/False）
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
    
    # 1. 计算Δα, Δβ, Δγ
    Delta_alpha, Delta_beta, Delta_gamma = calculate_delta(Pb206_204_S, Pb207_204_S, Pb208_204_S)
    results['Delta_alpha'] = Delta_alpha
    results['Delta_beta'] = Delta_beta
    results['Delta_gamma'] = Delta_gamma
    
    # 2. 计算V1, V2
    V1, V2 = calculate_V1V2(Delta_alpha, Delta_beta, Delta_gamma)
    results['V1'] = V1
    results['V2'] = V2
    
    # 3. 计算模式年龄（如果要求）
    if calculate_ages:
        # 单阶段模式年龄
        tCDT = calculate_tCDT(Pb206_204_S, Pb207_204_S)
        results['tCDT (Ma)'] = tCDT
        
        # 两阶段模式年龄
        tSK = calculate_tSK(Pb206_204_S, Pb207_204_S)
        results['tSK (Ma)'] = tSK
    
    return results

# ==================== 批量处理函数 ====================
def batch_process_samples(samples):
    """
    批量处理多个样品
    
    参数:
        samples: 字典或列表，包含样品数据
        格式: [{'name': '样品1', 'Pb206_204': 12.73, 'Pb207_204': 14.09, 'Pb208_204': 32.32}, ...]
    """
    # 提取数据
    names = [sample['name'] for sample in samples]
    Pb206_204 = [sample['Pb206_204'] for sample in samples]
    Pb207_204 = [sample['Pb207_204'] for sample in samples]
    Pb208_204 = [sample['Pb208_204'] for sample in samples]
    
    # 计算所有参数
    results = calculate_all_parameters(Pb206_204, Pb207_204, Pb208_204, calculate_ages=True)
    
    # 将结果组织成表格形式
    output = []
    for i, name in enumerate(names):
        sample_result = {
            '样品': name,
            '206Pb/204Pb': results['Pb206_204_S'][i],
            '207Pb/204Pb': results['Pb207_204_S'][i],
            '208Pb/204Pb': results['Pb208_204_S'][i],
            'Δα': results['Delta_alpha'][i],
            'Δβ': results['Delta_beta'][i],
            'Δγ': results['Delta_gamma'][i],
            'V1': results['V1'][i],
            'V2': results['V2'][i],
        }
        
        if 'tCDT (Ma)' in results:
            sample_result['tCDT (Ma)'] = results['tCDT (Ma)'][i] if results['tCDT (Ma)'][i] is not None else 'N/A'
        
        if 'tSK (Ma)' in results:
            sample_result['tSK (Ma)'] = results['tSK (Ma)'][i] if results['tSK (Ma)'][i] is not None else 'N/A'
        
        output.append(sample_result)
    
    return output

# ==================== 测试函数 ====================
def test_calculations():
    """测试计算结果"""
    print("现代地幔值：")
    print(f"  206Pb/204Pb = {Pb206_204_M_modern:.4f}")
    print(f"  207Pb/204Pb = {Pb207_204_M_modern:.4f}")
    print(f"  208Pb/204Pb = {Pb208_204_M_modern:.4f}")
    print()
    
    # 测试数据
    test_samples = [
        # 两阶段模式年龄测试数据
        {"name": "Sample1", "Pb206_204": 12.73, "Pb207_204": 14.09, "Pb208_204": 32.32},
        {"name": "Sample2", "Pb206_204": 12.75, "Pb207_204": 14.07, "Pb208_204": 32.22},
        {"name": "Sample3", "Pb206_204": 13.986, "Pb207_204": 15.085, "Pb208_204": 34.038},
        {"name": "Sample4", "Pb206_204": 13.59, "Pb207_204": 14.72, "Pb208_204": 33.53},
        {"name": "Sample5", "Pb206_204": 13.28, "Pb207_204": 14.53, "Pb208_204": 33.43},
        {"name": "Sample6", "Pb206_204": 13.16, "Pb207_204": 14.5, "Pb208_204": 35.08},
        
        # V1, V2测试数据
        {"name": "308-10", "Pb206_204": 19.141, "Pb207_204": 15.668, "Pb208_204": 40.268},
        {"name": "YL-90", "Pb206_204": 20.475, "Pb207_204": 15.856, "Pb208_204": 40.846},
        {"name": "8702-1", "Pb206_204": 19.525, "Pb207_204": 15.672, "Pb208_204": 40.221},
        {"name": "7903A-1", "Pb206_204": 19.799, "Pb207_204": 15.671, "Pb208_204": 40.758},
        {"name": "YL-74", "Pb206_204": 20.05, "Pb207_204": 15.708, "Pb208_204": 40.544},
        {"name": "PD2-2", "Pb206_204": 20.023, "Pb207_204": 15.701, "Pb208_204": 40.734},
    ]
    
    print("批量处理测试：")
    print("=" * 120)
    
    results = batch_process_samples(test_samples)
    
    # 打印表头
    header = ["样品", "206/204", "207/204", "208/204", "Δα", "Δβ", "Δγ", "V1", "V2", "tCDT", "tSK"]
    print(f"{'样品':<10} {'206/204':<8} {'207/204':<8} {'208/204':<8} {'Δα':<8} {'Δβ':<8} {'Δγ':<8} {'V1':<8} {'V2':<8} {'tCDT':<8} {'tSK':<8}")
    print("-" * 120)
    
    for result in results:
        print(f"{result['样品']:<10} {result['206Pb/204Pb']:<8.3f} {result['207Pb/204Pb']:<8.3f} "
              f"{result['208Pb/204Pb']:<8.3f} {result['Δα']:<8.1f} {result['Δβ']:<8.1f} {result['Δγ']:<8.1f} "
              f"{result['V1']:<8.1f} {result['V2']:<8.1f} {result.get('tCDT (Ma)', 'N/A'):<8} {result.get('tSK (Ma)', 'N/A'):<8}")

if __name__ == '__main__':
    # 运行测试
    test_calculations()
    
    # 示例：单个样品计算
    print("\n\n单个样品计算示例：")
    print("=" * 80)
    
    single_result = calculate_all_parameters(
        Pb206_204_S=19.141,
        Pb207_204_S=15.668,
        Pb208_204_S=40.268,
        calculate_ages=True
    )
    
    print("样品 308-10 的计算结果：")
    for key, value in single_result.items():
        if isinstance(value, np.ndarray) and value.ndim == 0:
             print(f"  {key}: {value}")
        elif hasattr(value, '__len__') and not isinstance(value, str):
             print(f"  {key}: {value[0]}")
        else:
             print(f"  {key}: {value}")