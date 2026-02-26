# data/ 模块开发文档

## 模块概述

`data/` 负责数据加载、地球化学计算、端元识别、ML 产地分析和混合模型。是应用的科学计算核心。

**文件清单 (拆分后)**

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 34 | 模块入口，导出公共 API |
| `loader.py` | 239 | Excel/CSV 数据加载与列类型检测 |
| `geochemistry/` | — | 铅同位素地球化学计算引擎 (拆分模块) |
| `geochemistry.py` | 30 | 兼容 shim (保持旧导入可用) |
| `endmember.py` | 302 | 端元识别 (PCA + 地球化学过滤) |
| `provenance_ml.py` | 366 | ML 产地分类管线 (DBSCAN + XGBoost) |
| `mixing.py` | 100 | 混合模型计算 |

---

## 1. loader.py — 数据加载

### 职责
从 Excel/CSV 文件加载数据，自动检测列类型。

### 公共函数

```python
def read_data_frame(excel_file: str, sheet_name: str = None) -> pd.DataFrame
```
- 优先使用 `calamine` 引擎 (快速)，回退到 `openpyxl`
- 自动检测数值列 (>50% 数值即为数值列)
- NaN 替换为 `"empty"` 字符串

```python
def load_data(show_file_dialog=True, show_config_dialog=True) -> bool
```
- 主数据加载入口
- 显示统一导入对话框 (文件 + 工作表 + 列选择)
- 验证数值列确实为数值类型
- 清理分组列 (空值替换为 `"Unknown"`)
- 更新 `app_state.df_global`

### 数据流

```
Excel/CSV 文件
  → read_data_frame() [calamine/openpyxl]
  → 类型检测 (数值 vs 分类)
  → 对话框选择 (文件/工作表/列)
  → 验证
  → app_state.df_global
```

---

## 2. geochemistry/ — 地球化学计算引擎

### 职责
实现铅同位素地球化学的完整计算体系，包括模式年龄、Delta 值、V1V2 投影、源区参数反演。
`data/geochemistry.py` 为兼容 shim，转发到包实现。

> **详细计算原理:** 所有公式推导、物理常数来源、预设模型参数、数值实现细节及已知约定，见 [`docs/geochemistry.md`](geochemistry.md)。

### 模块拆分

```
data/geochemistry/
├── __init__.py       # 公共 API + 兼容导出
├── engine.py         # 常量 + GeochemistryEngine + modelcurve
├── age.py            # 模式年龄/求解器
├── delta.py          # Delta + V1V2
├── source.py         # 源区参数/初始比值
└── isochron.py       # 等时线/回归工具
```

### 物理常数

```python
LAMBDA_238 = 1.55125e-10   # 238U 衰变常数 (yr⁻¹)
LAMBDA_235 = 9.8485e-10    # 235U 衰变常数 (yr⁻¹)
LAMBDA_232 = 4.9475e-11    # 232Th 衰变常数 (yr⁻¹)
U_RATIO = 1/137.88         # ²³⁵U/²³⁸U 比值
A0, B0, C0 = 9.307, 10.294, 29.476  # CDT 原始比值
```

### 预设模型 (PRESET_MODELS)

| 模型名 | age_model | 说明 |
|--------|-----------|------|
| `V1V2 (Geokit)` | `single_stage` | Geokit 默认 V1V2 参数 |
| `V1V2 (Zhu 1993)` | `single_stage` | 朱炳泉 1993 系数 |
| `Stacey & Kramers (1st Stage)` | `single_stage` | SK 第一阶段 (4.57-3.7 Ga) |
| `Stacey & Kramers (2nd Stage)` | `two_stage` | SK 第二阶段 (3.7 Ga-今) — 默认 |
| `Cumming & Richards` | `single_stage` | C&R 模型 (连续演化, E1/E2≠0) |
| `Maltese & Mezger` | `single_stage` | M&M 模型 (BSE 演化) |

### GeochemistryEngine 类 (engine.py)

```python
class GeochemistryEngine:
    """全局地球化学参数管理器 (单例)"""

    def load_preset(self, model_name: str)
        """加载预设模型参数"""

    def update_parameters(self, new_params: dict)
        """更新计算参数"""

    def get_parameters(self) -> dict
        """返回当前参数副本"""

    def get_available_models(self) -> list
        """返回可用模型名列表"""
```

全局实例: `engine = GeochemistryEngine()`

### 年龄计算函数 (age.py)

```python
def calculate_single_stage_age(Pb206_204_S, Pb207_204_S, params=None, initial_age=None)
    """Holmes-Houtermans 单阶段模式年龄 (Ma)"""

def calculate_two_stage_age(Pb206_204_S, Pb207_204_S, params=None)
    """Stacey-Kramers 两阶段模式年龄 (Ma)"""

def calculate_model_age(Pb206_204_S, Pb207_204_S, two_stage=False)
    """兼容性入口"""

def calculate_pbpb_age_from_ratio(r76, sr76=None, params=None)
    """从 207Pb/206Pb 比值计算年龄及误差"""

def calculate_isochron_age_from_slope(slope, params=None)
    """从等时线斜率计算年龄"""
```

### 模型曲线函数 (engine.py / isochron.py)

```python
def calculate_modelcurve(t_Ma, params=None, ...)
    """生成 PbIso 风格模型曲线 (206/204, 207/204, 208/204 随时间演化)"""

def calculate_paleoisochron_line(age_ma, params=None, algorithm='PB_EVOL_76')
    """计算古等时线的斜率和截距"""
```

### Delta 值与 V1V2 (delta.py)

```python
def calculate_deltas(Pb206_204_S, Pb207_204_S, Pb208_204_S, t_Ma,
                     params=None, T_mantle=None, use_two_stage=False, E1=None, E2=None)
    """计算 Δα, Δβ, Δγ (千分比偏差)"""
    # 返回: (d_alpha, d_beta, d_gamma)

def calculate_v1v2_coordinates(d_alpha, d_beta, d_gamma, params=None)
    """计算 V1, V2 判别图投影坐标 (Zhu 1995)"""
    # 返回: (V1, V2)
```

### 源区参数反演 (source.py)

```python
# 原始铅参考（单阶段，使用 T2/a0/b0）
def calculate_source_mu(Pb206_204_S, Pb207_204_S, t_Ma, params=None)     # μ (238U/204Pb)
def calculate_source_omega(Pb208_204_S, t_Ma, params=None)                # ω (232Th/204Pb)
def calculate_source_nu(mu, params=None)                                   # ν = μ × U_ratio

# 模型参考（使用 T1/a1/b1，适用于任何模型）
def calculate_model_mu(Pb206_204_S, Pb207_204_S, t_Ma, params=None)       # CalcMu
def calculate_model_kappa(Pb208_204_S, Pb206_204_S, t_Ma, params=None)    # CalcKa
```

### 初始比值反演 (source.py)

```python
def calculate_initial_ratio_64(t_Ma, Pb206_204_S, Pb207_204_S, params=None)              # 初始 206/204
def calculate_initial_ratio_74(t_Ma, Pb206_204_S, Pb207_204_S, params=None)              # 初始 207/204
def calculate_initial_ratio_84(t_Ma, Pb206_204_S, Pb207_204_S, Pb208_204_S, params=None) # 初始 208/204
```

### 等时线回归 (isochron.py)

```python
def york_regression(x, sx, y, sy, rxy=None, max_iter=50, tol=1e-15)
    """York (2004) 相关误差回归"""
    # 返回: {a, b, sa, sb, cov_ab, mswd, p_value, df}

def calculate_source_mu_from_isochron(slope, intercept, age_ma, params=None)
    """从等时线参数反演源区 μ"""

def calculate_source_kappa_from_slope(slope_208_206, age_ma, params=None)
    """从 208/206 斜率反演源区 κ"""
```

### 主入口函数 (__init__.py)

```python
def calculate_all_parameters(Pb206_204_S, Pb207_204_S, Pb208_204_S,
                             calculate_ages=True, a=None, b=None, c=None,
                             scale=1.0, t_Ma=None, **kwargs) -> dict
```

返回字典包含:
- `tCDT (Ma)`, `tSK (Ma)` — 模式年龄
- `Delta_alpha`, `Delta_beta`, `Delta_gamma` — Delta 值
- `V1`, `V2` — V1V2 坐标
- `mu`, `nu`, `omega` — 传统源区参数
- `mu_model`, `kappa_model`, `omega_model` — 模型参考源区参数（使用 T1/a1/b1）
- `Init_206_204`, `Init_207_204`, `Init_208_204` — 初始比值

### 内部求解器 (age.py)

```python
def _solve_age_scipy(f, bounds=(-4700e6, 4700e6), search_points=200)
    """Brent 法求根，带扫描回退"""
```

---

## 3. endmember.py — 端元识别

### 职责
基于 PCA 和地球化学约束识别铅同位素端元。

### 公共函数

```python
def run_endmember_analysis(df, col_206, col_207, col_208,
                           tolerance=(0.01, 0.01), clamp=(inf, inf),
                           t_earth=None) -> dict
```

**算法流程:**
1. 提取 3 列铅同位素数据，移除 NaN
2. 无标准化 PCA (保留原始尺度)
3. 找 PC1 极值点作为端元候选
4. 按地球化学斜率 (geochron slope) 过滤
5. 3D 距离约束 (clamp)
6. 重叠解决 (分配到最近端元)
7. Shapiro-Wilk 正态性检验

**返回:**
```python
{
    'pca': {scores, loadings, explained_variance_ratio, mean},
    'geochron_slope': float,
    'endmember_indices': {0: [...], 1: [...]},
    'group_labels': np.ndarray,  # 全长标签数组
    'validation': {group: {n_samples, pc2_W, pc2_p, pc3_W, pc3_p}},
    'warnings': [str, ...]
}
```

```python
def compute_geochron_slope(t_earth=None) -> float
    """计算地球化学斜率 ≈ 0.6262"""

def run_endmember_pca(data: np.ndarray) -> dict
    """无标准化 PCA"""

def validate_groups(scores, assignments, label_map) -> dict
    """Shapiro-Wilk 正态性检验"""
```

---

## 4. provenance_ml.py — ML 产地分类

### 职责
基于 DBSCAN 异常值移除 + One-vs-Rest XGBoost 的产地分类管线。

### 自定义异常

```python
class ProvenanceMLError(RuntimeError)
```

### 公共函数

```python
def prepare_training_data(df, region_col, feature_cols,
                          min_region_samples=5, dbscan_min_region_samples=20,
                          dbscan_eps=0.18, dbscan_min_samples_ratio=0.1,
                          standardize=True, random_state=42) -> dict
```
- 清洗训练数据
- 按区域 DBSCAN 异常值移除
- 可选标准化
- 返回: `{X, y, scaler, feature_cols, kept_indices, stats, cluster_info, region_counts}`

```python
def train_ovr_xgboost(x, y, xgb_params=None, smote_enabled=True,
                      smote_k_neighbors=3, smote_sampling_strategy=1.0,
                      random_state=42) -> tuple[dict, dict]
```
- One-vs-Rest XGBoost 训练
- 可选 SMOTE 过采样平衡
- 返回: `(models_dict, model_info_dict)`

```python
def predict_provenance(models, scaler, x_raw, threshold=0.9) -> tuple
```
- 预测产地标签
- 最大概率 < threshold 时标记为 `'None'`
- 返回: `(pred_labels, max_prob, proba_matrix, label_order)`

```python
def run_provenance_pipeline(training_df, region_col, feature_cols,
                            target_df, target_feature_cols, ...) -> dict
```
- 端到端管线编排
- 返回: `{training, models, model_info, predictions}`

### 数据流

```
训练数据 (区域 + 特征)
  → 清洗验证
  → DBSCAN 异常值移除 (按区域)
  → 标准化
  → OvR XGBoost 训练 (+ SMOTE)
  → 预测数据
  → 缩放 + 预测
  → 阈值过滤
  → 产地标签
```

---

## 5. mixing.py — 混合模型

### 职责
计算端元混合比例 (单纯形约束最小二乘)。

### 公共函数

```python
def calculate_mixing(df, endmember_groups, mixture_groups, columns) -> list[dict]
```

**算法:**
1. 计算每个端元的平均组成
2. 构建端元矩阵 (列 = 端元)
3. 对每个混合组:
   - 计算平均组成
   - 求解单纯形权重: `min ||A·w - target||²`, s.t. `w ≥ 0, Σw = 1`
4. 返回权重 + RMSE

```python
def _solve_simplex_weights(endmember_matrix, target) -> tuple[np.ndarray, float]
    """SLSQP 约束优化，回退到无约束最小二乘 + 裁剪"""
```

**返回:**
```python
[
    {'mixture': str, 'endmember': str, 'weight': float, 'rmse': float, 'columns': list},
    ...
]
```

---

## 模块间依赖

```
loader.py
  → app_state.df_global (pandas DataFrame)
      ├→ geochemistry/ (年龄, Delta, V1V2, 源区参数)
      ├→ endmember.py (PCA + 地球化学过滤)
      ├→ mixing.py (端元混合比例)
      └→ provenance_ml.py (DBSCAN + XGBoost 分类)
```

---

## 改进建议

改进建议已迁移至 `docs/development_plan.md`。
