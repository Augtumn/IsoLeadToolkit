# visualization/ 模块开发文档

## 模块概述

`visualization/` 是应用的渲染引擎，负责图形绑定、交互事件、样式管理。支持 8+ 种图类型，并对地球化学与 ML 依赖进行惰性加载以降低启动成本。

**文件清单 (约 3,700+ 行)**

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 89 | 模块入口，导出公共 API |
| `plotting/api.py` | ~200 | 渲染入口（汇总导出） |
| `plotting/core.py` | ~600 | 嵌入计算 + 核心工具 |
| `plotting/render.py` | ~1,400 | 嵌入渲染 + 2D/3D 绘制 |
| `plotting/geo.py` | ~400 | 地球化学叠加/等时线 |
| `plotting/ternary.py` | ~120 | 三元图工具 |
| `plotting/isochron.py` | 60 | 等时线误差配置与共享工具 |
| `events.py` | 1,057 | 交互事件 (hover, 选择, 图例点击) |
| `plotting/style.py` | 320 | 绘图样式 + 图例布局 |
| `style_manager.py` | 224 | 调色板 + 字体 + UI 主题 |
| `plotting/analysis_qt.py` | 261 | 诊断图 (scree, loadings, 相关性) |
| `plotting/kde.py` | 127 | KDE 叠加渲染 |
| `plotting/data.py` | 63 | 数据准备工具 (懒加载 ML 依赖) |
| `line_styles.py` | 22 | 线型解析工具 |

---

## 公共 API

`visualization/__init__.py` 作为外部入口，只导出以下三类 API:
- 样式管理: `StyleManager`, `style_manager_instance`, `apply_custom_style`, `COLORS`, `STYLES`
- 交互事件: `on_hover`, `on_click`, `on_legend_click`, `on_slider_change`, `refresh_selection_overlay`, `toggle_selection_mode`, `sync_selection_tools`, `draw_confidence_ellipse`
- 绘图接口: `plot_embedding`, `plot_2d_data`, `plot_3d_data`, `plot_umap`, `refresh_plot_style`, `get_embedding` 等

`plotting/api.py` 仅汇总公共绘图函数，私有 helper 保留在 `plotting/core.py`, `plotting/geo.py`, `plotting/render.py` 等模块中，不作为对外 API 承诺。

---

## 运行时状态与关键字段

下表列出 visualization 常用的 `app_state` 字段，非穷尽，仅用于理解状态流转。

| 字段 | 用途 | 主要读写位置 |
|------|------|------|
| `df_global` / `data_cols` | 全量数据与数值列 | plotting/data.py, plotting/render.py |
| `active_subset_indices` | 活动子集索引 | plotting/data.py, plotting/core.py |
| `fig` / `ax` / `legend_ax` | Matplotlib 图对象 | plotting/core.py, plotting/render.py |
| `render_mode` / `algorithm` | 当前渲染模式与算法 | events.py, plotting/render.py |
| `embedding_cache` | 嵌入缓存 (LRU) | plotting/core.py |
| `last_embedding` / `last_embedding_type` | 最近一次嵌入结果 | plotting/core.py, plotting/render.py |
| `last_pca_variance` / `last_pca_components` | PCA 诊断数据 | plotting/core.py, plotting/analysis_qt.py |
| `scatter_collections` | 主散点集合 | plotting/render.py |
| `artist_to_sample` / `sample_coordinates` | 事件索引映射 | plotting/render.py, events.py |
| `visible_groups` | 图例过滤组 | plotting/render.py, events.py |
| `current_palette` / `group_marker_map` | 当前调色板与标记映射 | plotting/render.py |
| `selection_mode` / `selection_tool` | 选择工具状态 | events.py |
| `selected_indices` / `selected_isochron_data` | 选择结果 | events.py |
| `plot_style_grid` / `color_scheme` | 样式选项 | plotting/style.py |
| `legend_position` / `legend_columns` | 图内图例位置与列数 | plotting/render.py, plotting/style.py |
| `legend_offset` / `legend_nudge_step` | 图内图例偏移与微调步长 | plotting/style.py |
| `legend_location` | 外部图例面板位置 (UI 使用) | ui/main_window.py |
| `custom_primary_font` / `custom_cjk_font` | 字体配置 | plotting/style.py, plotting/render.py |
| `plot_dpi` / `plot_facecolor` / `axes_facecolor` | 全局绘图样式 | plotting/style.py |
| `isochron_error_mode` / `isochron_*_col` | 等时线误差配置 | plotting/isochron.py |
| `show_model_curves` / `show_isochrons` / `show_paleoisochrons` | 地球化学叠加开关 | plotting/geo.py, plotting/render.py |
| `legend_update_callback` | 图例面板回调 | plotting/render.py |

---

## 错误与降级策略

1. 必要数据缺失时函数返回 `False` 或 `None` 并记录日志，不抛出到 UI 层。
2. `umap-learn` / `sklearn` / `seaborn` / `data.geochemistry` 使用惰性导入，缺失时记录 `warning` 并跳过相关功能。
3. 数值列转换使用 `pd.to_numeric(..., errors='coerce')` 或 `astype(float)` 并在失败时退出当前渲染流程。
4. 缺失值默认采用常量填充 (`SimpleImputer` fill 0)，失败时退化为删除含 NaN 行。
5. 事件处理与渲染异常由 `events.py` 与 `plotting/render.py` 捕获，保证 UI 不崩溃。

---

## 性能与缓存

1. 嵌入缓存使用 `EmbeddingCache`，键包含算法类型、参数、数据签名与子集标识。
2. 子集标识 `subset_key` 对 `active_subset_indices` 进行排序与哈希，完整数据使用 `'full'`。
3. `plot_embedding` 会尽量复用缓存嵌入并只刷新样式，避免重复计算。
4. KDE 渲染与等时线回归成本较高，受 UI 开关与采样限制控制。

---

## 线程与 UI 约束

1. visualization 层默认在 UI 主线程执行绘图与事件处理。
2. 大规模嵌入计算建议放入后台线程或异步任务。
3. 任何跨线程回调必须回到主线程更新 Qt 控件。

---

## 渲染管线

```
用户操作 (控制面板/菜单)
  ↓
on_slider_change() [events.py]
  ↓
判断 render_mode:
  ├─ UMAP/tSNE/PCA/RobustPCA/V1V2/PB_EVOL_76/86/PB_MU_AGE/PB_KAPPA_AGE/TERNARY
  │    → plot_embedding()
  ├─ 2D → plot_2d_data()
  └─ 3D → plot_3d_data()
  ↓
计算/获取嵌入:
  ├─ get_umap_embedding() → UMAP + LRU 缓存
  ├─ get_tsne_embedding() → t-SNE + perplexity 验证
  ├─ get_pca_embedding() → PCA + 方差追踪
  ├─ get_robust_pca_embedding() → MinCovDet / PCA 回退
  ├─ V1V2 → geochemistry.calculate_all_parameters() (惰性导入)
  ├─ TERNARY → 原始数据 + 拉伸
  └─ PB_EVOL → 原始 Pb 比值 (惰性导入 geochemistry)
  ↓
构建调色板 + 准备数据:
  ├─ _build_group_palette() → 稳定颜色映射
  ├─ 按 visible_groups 过滤
  └─ 添加嵌入列到 DataFrame
  ↓
渲染散点:
  ├─ 按组循环: ax.scatter(color, marker, size, alpha)
  ├─ 存储索引映射 (artist_to_sample, sample_coordinates)
  └─ 存储 scatter_collections
  ↓
可选: KDE 叠加
  ├─ sns.kdeplot() (主图)
  └─ draw_marginal_kde() (上/右边际)
  ↓
可选: 地球化学叠加 (PB_EVOL_76/86, geochemistry 惰性导入)
  ├─ _draw_model_curves() → SK 模型曲线
  ├─ _draw_isochron_overlays() → York 回归线 + 年龄标签 + 生长曲线
  │    ├─ ISOCHRON1 (76): 直接从 207/206 斜率计算年龄
  │    └─ ISOCHRON2 (86): 需 207/206 辅助计算年龄，绘制 κ 生长曲线
  ├─ _draw_paleoisochrons() → 参考古等时线
  └─ _draw_model_age_lines() / _draw_model_age_lines_86() → 模式年龄构造线
  ↓
可选: Mu/Kappa 古等时线 (PB_MU_AGE / PB_KAPPA_AGE)
  └─ _draw_mu_kappa_paleoisochrons() → 直接以 Age 为横坐标绘制垂线，无需计算
  ↓
渲染图例:
  ├─ _legend_layout_config() → 位置/bbox
  ├─ _legend_columns_for_layout() → 自动列数
  ├─ _style_legend() → 样式
  └─ _notify_legend_panel() → 更新主窗口图例面板
  ↓
恢复选择叠加:
  ├─ refresh_selection_overlay() → 高亮选中点
  └─ draw_confidence_ellipse() → 95% 置信椭圆
  ↓
应用样式:
  ├─ _apply_current_style() → 全局 rcParams
  ├─ _enforce_plot_style() → 坐标轴级别
  └─ _apply_axis_text_style() → 标签/标题
  ↓
fig.canvas.draw_idle()
```

补充说明:
图内图例仅在 `legend_position` 有效且分组数量不超过 30 时绘制。
`legend_columns > 0` 会覆盖自动列数，`legend_offset` 用于微调图内图例位置。

---

## 依赖与惰性加载

为降低启动成本与可选依赖压力，以下库使用惰性导入:
- `umap-learn` (UMAP 计算)
- `sklearn` (PCA / t-SNE / RobustPCA / 标准化)
- `seaborn` (KDE 渲染)
- `data.geochemistry` (V1V2 与 Pb 演化图)

当可选依赖不可用时，相关功能会记录日志并安全降级，不影响其他绘图模式。

---

## 1. plotting/api.py — 主渲染调度器

### 职责
嵌入计算与主渲染函数的公共入口。内部实现分散在 core/render/geo/ternary 等模块，API 层仅做汇总导出。

### 嵌入计算函数

```python
def get_umap_embedding(params: dict) -> np.ndarray
    """计算 UMAP 嵌入，带 LRU 缓存"""
    # 懒加载 umap-learn
    # 缓存键: (algorithm, params, subset_key, data_signature)

def get_tsne_embedding(params: dict) -> np.ndarray
    """计算 t-SNE 嵌入"""
    # perplexity 自动调整: min(perplexity, n_samples/3 - 1)

def get_pca_embedding(params: dict) -> np.ndarray
    """计算 PCA 嵌入"""
    # 存储 explained_variance_ratio 到 app_state.last_pca_variance
    # 存储 components 到 app_state.last_pca_components

def get_robust_pca_embedding(params: dict) -> np.ndarray
    """计算 Robust PCA (MinCovDet)"""
    # support_fraction 参数
    # MinCovDet 失败时回退到标准 PCA

def get_embedding(algorithm: str, ...) -> np.ndarray
    """调度器: 根据 algorithm 调用对应函数"""
```

### 主渲染函数

```python
def plot_embedding(group_col, algorithm, umap_params=None, tsne_params=None,
                   pca_params=None, robust_pca_params=None, size=60) -> bool
```

**支持的 algorithm 值:**
| 值 | 图类型 |
|----|--------|
| `UMAP` | UMAP 降维散点图 |
| `tSNE` | t-SNE 降维散点图 |
| `PCA` | PCA 降维散点图 |
| `RobustPCA` | Robust PCA 降维散点图 |
| `V1V2` | V1-V2 判别图 |
| `TERNARY` | 三元图 |
| `PB_EVOL_76` | 206Pb/204Pb vs 207Pb/204Pb 演化图 |
| `PB_EVOL_86` | 206Pb/204Pb vs 208Pb/204Pb 演化图 |
| `PB_MU_AGE` | μ vs Age 图 |
| `PB_KAPPA_AGE` | κ vs Age 图 |

**plot_embedding 关键参数:**
| 参数 | 说明 |
|------|------|
| `group_col` | 颜色分组列名，影响图例与调色板 |
| `algorithm` | 渲染算法/模式 |
| `umap_params` / `tsne_params` / `pca_params` / `robust_pca_params` | 对应算法参数，缺省时使用 `CONFIG` |
| `size` | 点大小 (scatter size) |

**返回约定:**
| 函数 | 成功 | 失败 |
|------|------|------|
| `plot_embedding` / `plot_2d_data` / `plot_3d_data` | `True` | `False` |
| `get_*_embedding` | `np.ndarray` | `None` |

**状态更新:**
1. `plot_embedding` 成功后更新 `app_state.last_embedding` 与 `app_state.last_embedding_type`。
2. PCA 系列更新 `app_state.last_pca_variance` 与 `app_state.last_pca_components`。
3. `plot_embedding` / `plot_2d_data` / `plot_3d_data` 会刷新 `scatter_collections`、`artist_to_sample` 与图例状态。

```python
def plot_2d_data(group_col, data_columns, size=60, show_kde=False) -> bool
    """原始 2D 散点图 (用户选择的两列)"""

def plot_3d_data(group_col, data_columns, size=60) -> bool
    """原始 3D 散点图 (用户选择的三列)"""
```

`plot_umap()` 仅为兼容入口，内部调用 `plot_embedding()`。

### 地球化学叠加函数 (内部实现位于 plotting/geo.py)

```python
def _draw_model_curves(ax, algorithm, params_list)
    """绘制 Stacey-Kramers 模型曲线 + 年龄标记点"""

def _draw_isochron_overlays(ax, algorithm, df, indices)
    """绘制等时线回归线 + 年龄/MSWD 标签 + 生长曲线"""
    # ISOCHRON1: 207/206 等时线，直接计算年龄
    # ISOCHRON2: 208/206 等时线，需 207/206 辅助计算年龄

def _build_isochron_label(result_dict) -> str
    """根据 isochron_label_options 动态构建等时线标签"""

def _draw_selected_isochron(ax)
    """高亮当前选中的等时线"""

def _draw_paleoisochrons(ax, algorithm, ages, params)
    """绘制参考古等时线 (0-3000 Ma)"""

def _resolve_model_age(pb206, pb207, params) -> tuple
    """解析模式年龄 (tCDT/tSK) 和 T1 覆盖值"""

def _draw_model_age_lines(ax, pb206, pb207, params)
    """绘制 206-207 模式年龄构造线"""

def _draw_model_age_lines_86(ax, pb206, pb207, pb208, params)
    """绘制 206-208 模式年龄构造线"""

def _draw_mu_kappa_paleoisochrons(ax, ages)
    """Mu/Kappa 图古等时线：以 Age 为横坐标直接画垂线/标签，无需计算"""

def _draw_equation_overlays(ax)
    """绘制自定义方程/线叠加"""
```

### 三元图支持 (内部实现位于 plotting/ternary.py)

```python
def _apply_ternary_stretch(t_vals, l_vals, r_vals)
    """应用拉伸模式 (power/minmax/hybrid)"""

def calculate_auto_ternary_factors()
    """基于几何均值的自动居中因子"""
```

### 工具函数 (内部实现位于 plotting/core.py)

```python
def _ensure_axes(dimensions=2)
    """创建/切换 2D/3D 坐标轴"""

def _build_group_palette(unique_cats) -> dict
    """构建稳定的组→颜色映射"""
    # 保持已有颜色，仅为新组分配新颜色

def _get_subset_dataframe() -> tuple[DataFrame, str]
    """返回活动子集或完整数据"""

def _get_pb_columns(columns) -> tuple[str, str, str]
    """查找 Pb 同位素比值列 (206/204, 207/204, 208/204)"""

def _find_age_column(columns) -> str | None
    """查找年龄列 (用于 Mu/Kappa 图)"""
```

---

## 2. plotting/core.py / plotting/render.py / plotting/geo.py / plotting/ternary.py

### 拆分职责
1. `plotting/core.py`：嵌入计算 + 核心工具函数
2. `plotting/render.py`：嵌入渲染 + 2D/3D 绘制
3. `plotting/geo.py`：地球化学叠加与等时线相关逻辑
4. `plotting/ternary.py`：三元图拉伸与自动因子

### plotting/core.py — 嵌入计算与缓存

**关键点:**
1. UMAP / t-SNE / PCA / RobustPCA 统一在此计算。
2. 使用 `EmbeddingCache` 缓存嵌入结果，避免重复计算。
3. 自动处理 2D/3D 轴切换 `_ensure_axes()`。
4. 对 `umap-learn` / `sklearn` 采用惰性导入。

**主要函数:**
```python
def get_umap_embedding(params) -> np.ndarray | None
def get_tsne_embedding(params) -> np.ndarray | None
def get_pca_embedding(params) -> np.ndarray | None
def get_robust_pca_embedding(params) -> np.ndarray | None
def get_embedding(algorithm, ...) -> np.ndarray | None
```

**缓存键:**
1. 算法名 + 参数
2. 数据签名 (data_version / 列名 / 样本量)
3. 子集标识 `subset_key` (完整数据为 `'full'`)

### plotting/render.py — 绘图渲染与图例

**核心流程:**
1. 解析算法与参数，准备 `DataFrame` 与嵌入结果。
2. 生成稳定调色板 `_build_group_palette()`，应用 `visible_groups` 过滤。
3. 绘制主散点并建立索引映射 `artist_to_sample` / `sample_coordinates`。
4. 可选 KDE 叠加与边际 KDE。
5. 可选地球化学叠加、等时线与模型年龄线。
6. 绘制图例并同步到 UI 面板。
7. 恢复选择叠加与注释标记。

**数据列约束:**
1. 2D / 3D 绘制要求指定列数量正确。
2. 地球化学绘图依赖 Pb 同位素列与可选年龄列。
3. 三元图要求三列且支持拉伸模式。

**常用开关字段:**
1. `show_kde` / `show_marginal_kde` 控制 KDE 叠加。
2. `show_model_curves` / `show_isochrons` / `show_paleoisochrons` 控制地球化学叠加。
3. `show_model_age_lines` 控制模式年龄构造线。
4. `show_plot_title` / `title_pad` 控制标题显示与间距。

### plotting/geo.py — 地球化学叠加

**功能范围:**
1. Stacey-Kramers 模型曲线绘制
2. York 回归等时线拟合与标签生成 (ISOCHRON1 + ISOCHRON2)
3. 古等时线与增长曲线绘制
4. 模式年龄构造线 (206-207 / 206-208)
5. Mu/Kappa 古等时线 (PB_MU_AGE / PB_KAPPA_AGE 图)。古等时线即为 Age 横坐标，直接绘制垂线与标签，不做计算。

**等时线模式:**

| 模式 | 坐标系 | 年龄计算 | 生长曲线 |
|------|--------|---------|---------|
| ISOCHRON1 | 207/204 vs 206/204 | 直接从斜率 | μ 曲线 |
| ISOCHRON2 | 208/204 vs 206/204 | 需 207/206 辅助 | κ 曲线 |

**关键函数:**

```python
def _draw_isochron_overlays(ax, actual_algorithm, df, indices)
    """绘制等时线回归线 + 年龄标签 + 生长曲线"""
    # ISOCHRON1: 直接从 207/206 斜率计算年龄
    # ISOCHRON2: 需要同时拟合 207/206 获取年龄，再绘制 208/206 等时线

def _build_isochron_label(result_dict) -> str
    """根据 isochron_label_options 动态构建标签"""
    # 支持: age, n_points, mswd, r_squared, slope

def _resolve_model_age(pb206, pb207, params) -> tuple
    """解析模式年龄和 T1 覆盖值"""
    # Tsec <= 0 → 单阶段 (tCDT, T2)
    # Tsec > 0 → 两阶段优先 (tSK, Tsec)

def _draw_model_age_lines(ax, pb206, pb207, params)
    """绘制 206-207 模式年龄构造线"""
    # 确定性采样 (RandomState(42))，最多 200 条

def _draw_model_age_lines_86(ax, pb206, pb207, pb208, params)
    """绘制 206-208 模式年龄构造线"""

def _draw_mu_kappa_paleoisochrons(ax, ages)
    """Mu/Kappa 图古等时线：Age 即横坐标，直接绘制垂线/标签"""
```

**实现约束:**
1. `data.geochemistry` 采用惰性导入
2. 缺失依赖时功能降级，不影响其他模式
3. 大数据集使用确定性随机采样避免图表拥挤

### plotting/ternary.py — 三元图工具

**拉伸模式:**
1. `power`：指数拉伸
2. `minmax`：Min-Max 标准化
3. `hybrid`：先 Min-Max 再 Power

**自动因子:**
1. 使用几何均值计算三元图自动拉伸因子。
2. 结果写入 `app_state.ternary_factors`。

---

## 3. events.py — 交互事件

### 职责
处理所有用户交互: 悬停提示、点击选择、图例交互、选择工具。

### 事件处理器

```python
def on_hover(event)
    """鼠标悬停 → 显示样本信息提示"""
    # 查找最近散点 → 显示 tooltip_columns 信息
    # 显示选中状态标记

def on_click(event)
    """双击 → 选择/取消选择样本"""

def on_legend_click(event)
    """点击图例 → 切换组可见性"""
    # 仅更新散点/图例项可见性与 alpha，不处理置顶排序

def on_slider_change(val=None)
    """参数变更 → 重新渲染"""
    # 调度到 plot_embedding / plot_2d_data / plot_3d_data
    # 保存会话参数
    # 刷新画布
```

说明：外部图例面板的“拖动重排/双击置顶”属于 `ui/main_window.py` 的 UI 行为，
通过维护 `app_state.legend_item_order` + `artist.set_zorder()` 实现，不在 `events.py` 内处理。

**关键状态更新:**
1. 重新计算 `render_mode` 与 `algorithm` 并同步 `app_state`。
2. 校验 2D/3D/三元图列选择，必要时回退到 UMAP。
3. 触发 `plot_embedding` 或 `plot_2d_data` / `plot_3d_data`，刷新 `fig.canvas`。

### 选择工具

```python
def toggle_selection_mode(tool_type: str)
    """启用/禁用选择工具"""
    # tool_type: 'export' (框选), 'lasso' (套索), 'isochron' (等时线)
    # 创建 RectangleSelector 或 LassoSelector

def sync_selection_tools()
    """确保选择器匹配当前坐标轴"""

def refresh_selection_overlay()
    """更新选择高亮散点 + 置信椭圆"""
    # 红色高亮选中点
    # 可选 95% 置信椭圆

def calculate_selected_isochron()
    """对选中点计算等时线年龄"""
    # York 回归 → 年龄 + MSWD + R²
    # 存储到 app_state.selected_isochron_data
```

**选择工具细节:**
1. `selection_tool` 支持 `export` / `lasso` / `isochron`。
2. 框选与套索选择均更新 `selected_indices`，同时触发高亮叠加。
3. 等时线工具仅在 Pb 演化图模式下可用。

**事件索引映射:**
1. `artist_to_sample` 用于从 matplotlib artist 反查样本索引。
2. `sample_coordinates` 用于最近邻查找，处理非标准 artist。
3. 选择与悬停均依赖上述映射以获取 tooltip 与选中状态。

### 选择回调

```python
def _handle_rectangle_select(eclick, erelease)
    """框选回调 → 选中矩形内的点"""

def _handle_lasso_select(vertices)
    """套索回调 → 选中多边形内的点"""
```

### 置信椭圆

```python
def draw_confidence_ellipse(x, y, ax, confidence=0.95, facecolor='none',
                            edgecolor='red', linewidth=1.5, linestyle='--',
                            zorder=10, **kwargs) -> Ellipse
    """绘制基于卡方分布的 95% 置信椭圆"""
    # 协方差矩阵 → 特征值分解 → 椭圆参数
```

### 样本索引解析

```python
def _resolve_sample_index(event) -> int | None
    """从 matplotlib 事件解析样本索引"""
    # 1. 尝试 artist_to_sample 映射
    # 2. 回退到 sample_coordinates 最近邻搜索
```

---

## 4. plotting/style.py — 绘图样式

### 职责
管理 matplotlib rcParams、坐标轴样式、图例布局。

### 全局样式

```python
def _apply_current_style()
    """从 app_state 应用全局 matplotlib 样式"""
    # 设置 rcParams: DPI, 背景色, 网格, 刻度, 坐标轴, 标签
```

### 坐标轴样式

```python
def _enforce_plot_style(ax)
    """在特定坐标轴上强制样式"""
    # 网格 (主/次)
    # 刻度 (方向/长度/宽度/颜色)
    # 次刻度
    # 脊柱 (线宽/颜色/可见性)

def _apply_axis_text_style(ax)
    """应用标签/标题样式"""
    # 颜色, 粗细, 间距
```

### 图例布局

```python
def _legend_layout_config(ax, show_marginal_kde=False)
    """解析图内图例位置 → (loc, bbox, mode, borderaxespad)，支持 legend_offset 微调"""

def _legend_columns_for_layout(labels, ax, location_key) -> int | None
    """自动计算图例列数 (外部图例固定 1 列，图内可自动或手动)"""

def _style_legend(legend, show_marginal_kde=False)
    """应用图例样式 (框架, 透明度, 颜色)"""
```

`legend_offset` 以坐标轴比例为单位，用于微调图内图例锚点位置。

### 样式刷新

```python
def refresh_plot_style()
    """不重新计算嵌入，仅刷新样式"""
    # 1. _apply_current_style() → rcParams
    # 2. 遍历所有 axes → _enforce_plot_style() + _apply_axis_text_style()
    # 3. 更新 scatter_collections (大小, 透明度, 边框)
    # 4. 刷新选择叠加
    # 5. fig.canvas.draw_idle()
```

**常用样式字段:**
1. `plot_style_grid` / `grid_color` / `grid_linewidth` / `grid_alpha`
2. `tick_direction` / `tick_length` / `tick_width` / `minor_ticks`
3. `plot_dpi` / `plot_facecolor` / `axes_facecolor`
4. `label_color` / `title_color` / `label_weight` / `title_weight`

---

## 5. style_manager.py — 样式管理器

### 职责
调色板定义、字体管理、UI 主题。

### StyleManager 类

```python
class StyleManager:
    def get_available_fonts(self) -> list[str]
        """获取系统可用字体 (带缓存)"""

    def get_palette_names(self) -> list[str]
        """获取调色板名列表"""

    def get_ui_theme_names(self) -> list[str]
        """获取 UI 主题名列表"""

    def get_ui_theme(self, name: str) -> dict
        """获取 UI 主题配置"""

    def apply_style(self, show_grid, color_scheme, primary_font, cjk_font, font_sizes)
        """应用全局 matplotlib 样式"""
```

### 调色板

| 名称 | 说明 |
|------|------|
| `vibrant` | 鲜艳色 (默认) |
| `bright` | 明亮色 |
| `high-vis` | 高对比度 |
| `light` | 浅色 |
| `muted` | 柔和色 |
| `retro` | 复古色 |
| `std-colors` | 标准色 |
| `dark_background` | 深色背景 |

### UI 主题

| 名称 | 背景 | 前景 | 风格 |
|------|------|------|------|
| Modern Light | 白色 | 深灰 | 默认 |
| Modern Dark | 深色 | 浅色 | dark_background |
| Scientific Blue | 蓝白 | 深蓝 | seaborn-v0_8-whitegrid |
| Retro Lab | 米色 | 棕色 | ggplot |

### 字体缓存
- 缓存路径: `~/.isotopes_analysis/font_cache.json`
- 存储字体名 → 路径映射
- 避免每次启动重新扫描系统字体

**输出约定:**
1. `apply_style()` 会调用 Matplotlib 样式与 rcParams 组合应用。
2. `get_ui_theme()` 返回 UI 主题字典，包含背景色、前景色、绘图样式名等字段。

---

## 6. plotting/kde.py — KDE 渲染

### 职责
KDE 等高线叠加和边际 KDE 分布。

```python
def lazy_import_seaborn()
    """懒加载 seaborn"""

def clear_marginal_axes()
    """清除边际 KDE 坐标轴"""

def draw_marginal_kde(ax, df_plot, group_col, palette, unique_cats, x_col, y_col)
    """绘制上/右边际 KDE"""
    # 使用 make_axes_locatable 创建附加坐标轴
    # 可配置大小 (5-40%)
    # 大数据集采样 (max_points)
```

**可配置项:**
1. `marginal_kde_max_points` — 采样上限 (默认 5000)
2. `marginal_kde_top_size` / `marginal_kde_right_size` — 边际 KDE 轴尺寸 (百分比)
3. `marginal_kde_style` — `{alpha, linewidth, fill}` 样式字典
4. `marginal_axes` — 缓存边际坐标轴，用于清理与重绘

---

## 7. plotting/analysis_qt.py — 诊断图

### 职责
Qt 对话框中的诊断分析图。对话框标题与标签文本统一走 `translate()`，数据来源于 `app_state.last_*`。

```python
def show_scree_plot(parent_window)
    """PCA 方差解释图 (碎石图)"""

def show_pca_loadings(parent_window)
    """PCA 成分载荷热图"""

def show_embedding_correlation(parent_window)
    """特征-嵌入相关性"""

def show_shepard_diagram(parent_window)
    """距离保持图 (Shepard diagram)"""
    # 采样上限 1000 点

def show_correlation_heatmap(parent_window)
    """特征相关性矩阵热图"""
```

**数据来源与约束:**
1. `show_scree_plot` / `show_pca_loadings` 依赖 `last_pca_variance` 与 `last_pca_components`。
2. `show_embedding_correlation` / `show_shepard_diagram` 依赖 `last_embedding`。
3. Shepard 图样本数上限 1000，避免 O(n^2) 距离计算过载。

---

## 8. plotting/data.py — 数据准备

### 职责
ML 算法的数据提取和懒加载。

```python
def _lazy_import_ml()
    """懒加载 sklearn 模块 (TSNE, PCA, MinCovDet, StandardScaler, SimpleImputer)"""

def _get_analysis_data() -> tuple[np.ndarray, np.ndarray]
    """提取数值数据子集用于分析"""
    # 返回活动子集或完整数据
    # 转换为 float，NaN 用 0 填充
    # 返回 (X, indices)
```

**实现细节:**
1. 若存在 `active_subset_indices`，仅提取子集数据。
2. 使用 `astype(float)` 做基础数值转换，失败则返回 `None`。
3. 若存在 NaN，使用 `SimpleImputer` 以常量 0 填充，失败时删除含 NaN 行。
4. 返回 `indices` 以保持嵌入结果与原始数据对齐。

---

## 9. plotting/isochron.py — 等时线误差配置

### 职责
为等时线回归提供 sX/sY/rXY 误差数组，支持固定值与列映射两种模式。

```python
def resolve_isochron_errors(df, size)
    """从 app_state 解析误差列或固定值"""
```

**误差模式:**
1. `columns`：从 `isochron_sx_col` / `isochron_sy_col` / `isochron_rxy_col` 中读取。
2. `fixed`：使用 `isochron_sx_value` / `isochron_sy_value` / `isochron_rxy_value` 常量填充。

---

## 10. line_styles.py — 线型解析

```python
def resolve_line_style(app_state, style_key: str, fallback: dict) -> dict
    """合并 app_state 线型覆盖与回退默认值"""
    # 检查 app_state.line_styles[style_key]
    # 非 None 值覆盖 fallback
```

**覆盖规则:**
1. 若 `line_styles[style_key]` 中字段非空，则覆盖 `fallback`。
2. `color` 仅在非空字符串时覆盖，避免意外置空。

---

## 依赖关系

```
style_manager.py (无内部依赖)
  ↓
plotting/style.py ← style_manager, app_state
  ↓
plotting/data.py ← app_state, sklearn (懒加载)
  ↓
plotting/kde.py ← seaborn (懒加载), app_state
  ↓
line_styles.py ← app_state
  ↓
plotting/isochron.py ← app_state
  ↓
plotting/core.py ← plotting/data.py, app_state, sklearn (懒加载)
  ↓
plotting/geo.py ← plotting/core.py, line_styles, plotting/isochron.py, geochemistry (lazy)
  ↓
plotting/ternary.py ← app_state, scipy
  ↓
plotting/render.py ← plotting/core.py, plotting/geo.py, plotting/ternary.py, plotting/style.py, plotting/kde.py, geochemistry (lazy)
  ↓
plotting/api.py ← plotting/core.py, plotting/render.py, plotting/geo.py, plotting/ternary.py
  ↓
events.py ← plotting/api.py, app_state
  ↓
plotting/analysis_qt.py ← plotting/data.py, PyQt5
  ↓
plotting/__init__.py ← 导出所有公共 API
```

---

## 改进建议

改进建议已迁移至 `docs/development_plan.md`。
