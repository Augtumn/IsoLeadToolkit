# -*- coding: utf-8 -*-
"""
端元识别算法模块 (Endmember Identification)

基于 liaendmembers (R) 的算法实现：
1. 对 3 列铅同位素比值做无标准化 PCA
2. 取 PC1 极值作为两个端元
3. 用 geochron 斜率过滤归组
4. Shapiro-Wilk 检验验证

参考文献:
- Albarède et al. (2024)
- Eshel et al. (2019)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, Any

logger = logging.getLogger(__name__)


def compute_geochron_slope(t_earth: Optional[float] = None) -> float:
    """
    动态计算 geochron 斜率。

    公式: (1/137.88) * (exp(λ235 * T) - 1) / (exp(λ238 * T) - 1)

    Args:
        t_earth: 地球年龄(年)，默认使用 T_EARTH_CANON (4.57Ga)

    Returns:
        geochron 斜率 (约 0.6262)
    """
    from data.geochemistry import LAMBDA_238, LAMBDA_235, U_RATIO_NATURAL, T_EARTH_CANON, EPSILON

    if t_earth is None:
        t_earth = T_EARTH_CANON

    e235 = np.exp(LAMBDA_235 * t_earth) - 1.0
    e238 = np.exp(LAMBDA_238 * t_earth) - 1.0

    if abs(e238) < EPSILON:
        return 0.0

    return U_RATIO_NATURAL * e235 / e238


def run_endmember_pca(data: np.ndarray) -> Dict[str, Any]:
    """
    对铅同位素数据做无标准化 PCA。

    与 R 包一致使用 scale=FALSE，因为 3 个 Pb 比值量纲相近。

    Args:
        data: (n, 3) 数组，列为 206/204, 207/204, 208/204

    Returns:
        dict: scores, loadings, explained_variance_ratio, mean
    """
    from sklearn.decomposition import PCA

    n_components = min(3, data.shape[1], data.shape[0])
    pca = PCA(n_components=n_components)
    scores = pca.fit_transform(data)

    return {
        'scores': scores,
        'loadings': pca.components_,
        'explained_variance_ratio': pca.explained_variance_ratio_,
        'mean': pca.mean_,
    }


def _filter_by_geochron(
    data_206: np.ndarray,
    data_207: np.ndarray,
    em_206: float,
    em_207: float,
    geo_slope: float,
    tolerance: float,
    clamp: float,
    all_data: np.ndarray,
) -> np.ndarray:
    """
    在 206/207 空间中用 geochron 斜率过滤样品。

    从端元点出发画斜率为 geo_slope 的直线，
    207 偏差 < tolerance 且欧氏距离 < clamp 的样品归入该端元组。

    Args:
        data_206: 所有样品的 206Pb/204Pb
        data_207: 所有样品的 207Pb/204Pb
        em_206: 端元的 206Pb/204Pb
        em_207: 端元的 207Pb/204Pb
        geo_slope: geochron 斜率
        tolerance: 207 方向容差
        clamp: 欧氏距离上限
        all_data: (n, 3) 完整数据，用于计算 3D 欧氏距离

    Returns:
        布尔掩码数组
    """
    # 端元处的截距
    intercept = em_207 - em_206 * geo_slope
    # 每个样品在 geochron 线上的预测 207 值
    predicted_207 = geo_slope * data_206 + intercept
    # 207 方向偏差
    within_tolerance = np.abs(data_207 - predicted_207) < tolerance

    # 3D 欧氏距离
    em_point = np.array([em_206, em_207, all_data[0, 2] if all_data.shape[1] > 2 else 0])
    # 用端元的实际 208 值
    em_row_mask = (data_206 == em_206) & (data_207 == em_207)
    em_row_indices = np.where(em_row_mask)[0]
    if len(em_row_indices) > 0:
        em_point = all_data[em_row_indices[0]]

    dists = np.sqrt(np.sum((all_data - em_point) ** 2, axis=1))
    within_clamp = dists < clamp

    return within_tolerance & within_clamp


def _shapiro_wilk_test(values: np.ndarray) -> Tuple[Optional[float], Optional[float]]:
    """Shapiro-Wilk 正态性检验，样品数 < 3 时返回 None。"""
    if len(values) < 3:
        return None, None
    try:
        from scipy.stats import shapiro
        stat, p_val = shapiro(values)
        return float(stat), float(p_val)
    except Exception:
        return None, None


def validate_groups(
    scores: np.ndarray,
    assignments: np.ndarray,
    label_map: Dict[int, str],
) -> Dict[str, Dict[str, Any]]:
    """
    对每个分组的 PC2/PC3 做 Shapiro-Wilk 正态性检验。

    Args:
        scores: PCA 分数矩阵
        assignments: 分组标签数组 (0, 1, 2)
        label_map: {0: 'Endmember_A', 1: 'Endmember_B', 2: 'Mixing'}

    Returns:
        {组名: {n_samples, pc2_W, pc2_p, pc3_W, pc3_p}}
    """
    results = {}
    for gid, gname in label_map.items():
        mask = assignments == gid
        n = int(np.sum(mask))
        entry = {'n_samples': n}

        if n >= 3 and scores.shape[1] >= 2:
            w, p = _shapiro_wilk_test(scores[mask, 1])
            entry['pc2_W'] = w
            entry['pc2_p'] = p
        else:
            entry['pc2_W'] = None
            entry['pc2_p'] = None

        if n >= 3 and scores.shape[1] >= 3:
            w, p = _shapiro_wilk_test(scores[mask, 2])
            entry['pc3_W'] = w
            entry['pc3_p'] = p
        else:
            entry['pc3_W'] = None
            entry['pc3_p'] = None

        results[gname] = entry

    return results


def run_endmember_analysis(
    df: pd.DataFrame,
    col_206: str,
    col_207: str,
    col_208: str,
    tolerance: Tuple[float, float] = (0.01, 0.01),
    clamp: Tuple[float, float] = (np.inf, np.inf),
    t_earth: Optional[float] = None,
) -> Dict[str, Any]:
    """
    端元识别主入口。

    Args:
        df: pandas DataFrame
        col_206, col_207, col_208: 铅同位素列名
        tolerance: (容差A, 容差B)
        clamp: (钳制A, 钳制B)
        t_earth: 地球年龄(年)，None 使用默认值

    Returns:
        dict: pca, geochron_slope, endmember_indices, group_labels,
              validation, warnings 等
    """
    # 提取数据
    data = (
        df[[col_206, col_207, col_208]]
        .apply(pd.to_numeric, errors='coerce')
        .to_numpy()
    )
    valid_mask = ~np.isnan(data).any(axis=1)
    data_clean = data[valid_mask]
    valid_indices = np.where(valid_mask)[0]

    warnings = []

    if data_clean.shape[0] < 3:
        raise ValueError("有效样品数不足 3 个，无法进行端元分析。")

    # PCA (无标准化)
    pca_result = run_endmember_pca(data_clean)

    # PC1 方差检查
    pc1_var = pca_result['explained_variance_ratio'][0]
    cumulative_var = np.cumsum(pca_result['explained_variance_ratio'])
    if cumulative_var[0] < 0.95:
        warnings.append(
            f"PC1 仅解释 {pc1_var * 100:.1f}% 的方差（累积 < 95%），"
            f"可能存在两个以上端元。"
        )

    # Geochron 斜率
    geo_slope = compute_geochron_slope(t_earth)

    # 找 PC1 极值作为端元
    pc1 = pca_result['scores'][:, 0]
    idx_min = int(np.argmin(pc1))
    idx_max = int(np.argmax(pc1))

    # Geochron 斜率过滤分组
    data_206 = data_clean[:, 0]
    data_207 = data_clean[:, 1]

    mask_a = _filter_by_geochron(
        data_206, data_207,
        data_clean[idx_min, 0], data_clean[idx_min, 1],
        geo_slope, tolerance[0], clamp[0], data_clean,
    )
    mask_b = _filter_by_geochron(
        data_206, data_207,
        data_clean[idx_max, 0], data_clean[idx_max, 1],
        geo_slope, tolerance[1], clamp[1], data_clean,
    )

    # 检查重叠
    overlap = mask_a & mask_b
    if np.any(overlap):
        warnings.append(
            f"两个端元组存在 {int(np.sum(overlap))} 个重叠样品，"
            f"建议降低 tolerance 值。"
        )
        # 重叠样品归入距离更近的端元
        for i in np.where(overlap)[0]:
            dist_a = np.sqrt(np.sum((data_clean[i] - data_clean[idx_min]) ** 2))
            dist_b = np.sqrt(np.sum((data_clean[i] - data_clean[idx_max]) ** 2))
            if dist_a <= dist_b:
                mask_b[i] = False
            else:
                mask_a[i] = False

    # 分组赋值
    label_map = {0: 'Endmember_A', 1: 'Endmember_B', 2: 'Mixing'}
    assignments = np.full(data_clean.shape[0], 2, dtype=int)
    assignments[mask_a] = 0
    assignments[mask_b] = 1

    # 检查端元组大小
    for gid, gname in [(0, 'A'), (1, 'B')]:
        n = int(np.sum(assignments == gid))
        if n < 2:
            warnings.append(f"端元 {gname} 组仅有 {n} 个样品，结果可能不可靠。")

    # Shapiro-Wilk 验证
    validation = validate_groups(pca_result['scores'], assignments, label_map)

    # 构建完整长度的分组标签
    group_labels = np.full(len(df), '', dtype=object)
    for i, orig_idx in enumerate(valid_indices):
        group_labels[orig_idx] = label_map[assignments[i]]

    # 端元在原始 DataFrame 中的索引
    em_orig_indices = [int(valid_indices[idx_min]), int(valid_indices[idx_max])]

    return {
        'pca': pca_result,
        'geochron_slope': geo_slope,
        'endmember_indices': em_orig_indices,
        'endmember_clean_indices': [idx_min, idx_max],
        'assignments': assignments,
        'label_map': label_map,
        'group_labels': group_labels,
        'valid_indices': valid_indices,
        'validation': validation,
        'warnings': warnings,
        'tolerance': tolerance,
        'clamp': clamp,
        'columns_used': [col_206, col_207, col_208],
    }
