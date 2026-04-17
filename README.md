# IsotopesAnalyse

中文（当前文档） | English（待补充）

一个面向铅同位素地球化学的桌面分析与可视化工具，基于 PyQt5 构建，覆盖数据处理、降维分析、地球化学建模、端元/混合分析与来源判别等全流程。

![Python](https://img.shields.io/badge/Python-3.12+-blue)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green)

*以下内容可能严重落后于代码，目前尚无精力纠正*
---

## 目录

- [功能概览](#功能概览)
- [数据导入与管理](#数据导入与管理)
- [可视化类型](#可视化类型)
- [降维与嵌入算法](#降维与嵌入算法)
- [地球化学功能](#地球化学功能)
- [分析工具](#分析工具)
- [交互功能](#交互功能)
- [样式与主题](#样式与主题)
- [导出功能](#导出功能)
- [本地化](#本地化)
- [安装与运行](#安装与运行)
- [项目结构](#项目结构)
- [依赖](#依赖)

---

## 功能概览

IsotopesAnalyse 提供从数据加载到地质解释的完整铅同位素分析链路：

- 支持 Excel/CSV 数据导入，自动识别数值列与分类列
- 5 种嵌入/判别算法：UMAP、t-SNE、PCA、RobustPCA、V1V2
- 14 种渲染模式：UMAP、t-SNE、PCA、RobustPCA、2D、3D、Ternary、V1V2、PB_EVOL_76、PB_EVOL_86、PLUMBOTECTONICS_76、PLUMBOTECTONICS_86、PB_MU_AGE、PB_KAPPA_AGE
- Windows x64 平台（Python 3.12+）
- 边际 KDE 计算参数可配置：支持显式带宽、6 种核函数与 Scott/Silverman 自动带宽估计
- 完整的地球化学建模：Stacey-Kramers、Cumming-Richards 等模型曲线与古等时线
- York 回归等时线年龄计算，支持选中样品或按分组自动计算
- PCA 端元自动识别与 geochron 斜率分组
- 混合模型最小二乘求解
- XGBoost 机器学习来源判别管线
- 菜单驱动的分区对话框工作流（Data/Display/Analysis/Export/Legend/Geo）
- 中英文双语界面，会话参数自动持久化

---

## 数据导入与管理

### 文件格式

- Excel 文件（.xlsx、.xls），通过 `python-calamine` 或 `openpyxl` 读取
- CSV 文件
- 支持多工作表选择

### 数据处理

- 自动检测数值列与分类列（>50% 数值即判定为数值列）
- 中文列名自动映射为英文（如 "省" → "Province"、"遗址" → "Discovery site"、"年代" → "Period"）
- 缺失值处理：数值列 dropna，分类列填充为 "Unknown"
- 空值/特殊值替换（"——"、"—"、"null"、"nan" → "Unknown"）

### 列配置

- 自由选择数值列（用于分析计算）和分组列（用于着色分组）
- 支持 X/Y/Z 轴列配置（二维/三维散点）
- 三元图顶/左/右轴列选择
- 分组列可动态添加（如端元分组、ML 预测结果）

---

## 可视化类型

### 降维嵌入图

将高维铅同位素数据投影到二维平面，揭示样品的自然聚类结构。支持 UMAP、t-SNE、PCA、RobustPCA 四种算法，可叠加 KDE 密度等高线和 95% 置信椭圆。

### 二维散点图

用户自选 X/Y 轴列，直接绘制原始数据散点图。支持边际 KDE 分布曲线（顶部和右侧），按分组着色。边际 KDE 支持带宽、核函数、自动带宽方法等计算参数配置。

### 三维散点图

用户自选 X/Y/Z 轴列，三维旋转散点图，支持分组着色。

### 三元图

基于 `mpltern` 的三元相图，支持三种拉伸模式：

- Power 拉伸：幂函数变换
- MinMax 拉伸：最小-最大归一化
- Hybrid 拉伸：混合模式

### Pb 演化图

- **PB_EVOL_76**：²⁰⁶Pb/²⁰⁴Pb vs ²⁰⁷Pb/²⁰⁴Pb，可叠加模型曲线、古等时线、等时线回归
- **PB_EVOL_86**：²⁰⁶Pb/²⁰⁴Pb vs ²⁰⁸Pb/²⁰⁴Pb

### Plumbotectonics 图

- **PLUMBOTECTONICS_76**：基于 ²⁰⁶Pb/²⁰⁴Pb vs ²⁰⁷Pb/²⁰⁴Pb 的构造分区参考曲线叠加
- **PLUMBOTECTONICS_86**：基于 ²⁰⁶Pb/²⁰⁴Pb vs ²⁰⁸Pb/²⁰⁴Pb 的构造分区参考曲线叠加

### μ-Age / κ-Age 图

基于 Stacey-Kramers 模型计算的 μ（²³⁸U/²⁰⁴Pb）和 κ（²³²Th/²⁰⁴Pb）与年龄列联动绘图。

### V1V2 判别图

V1/V2 地球化学判别投影（Zhu 1993 / Geokit），通过回归平面将三维铅同位素空间投影到二维判别坐标，用于铅源区判别（上地壳、下地壳、地幔、造山带等）。

---

## 降维与嵌入算法

### UMAP

均匀流形近似与投影，适合发现局部聚类结构。

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| n_neighbors | 10 | 2-50 | 局部邻域大小 |
| min_dist | 0.1 | 0.0-1.0 | 嵌入点最小距离 |
| n_components | 2 | 当前 UI 固定为 2 | 输出维度 |
| random_state | 42 | — | 随机种子 |

### t-SNE

t 分布随机邻域嵌入，擅长保留局部结构。自动钳制 perplexity 到 `max(2, n_samples-1)`，并对 learning rate 设置下限保护。

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| perplexity | 30 | 5-100 | 困惑度 |
| learning_rate | 200 | 10-1000 | 学习率 |
| n_components | 2 | 当前 UI 固定为 2 | 输出维度 |
| random_state | 42 | — | 随机种子 |

### PCA

主成分分析，使用 `StandardScaler` 标准化后降维。额外输出方差解释率和成分载荷，用于碎石图和载荷分析。

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| n_components | 2 | 2-10 | 输出维度 |
| random_state | 42 | 0-200 | 随机种子 |

### RobustPCA

稳健主成分分析。当样本数 > 特征数时使用 `MinCovDet`（最小协方差行列式）估计鲁棒协方差矩阵，再做特征分解投影；样本不足时自动回退到标准 PCA。

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| n_components | 2 | 2-10 | 输出维度 |
| support_fraction | 0.75 | 0.1-1.0 | MinCovDet 支持比例 |
| random_state | 42 | 0-9999 | 随机种子 |

### 嵌入缓存

LRU 缓存最多 8 个计算结果，缓存键由算法名、参数、数据子集哈希和数据版本号组成。加载新数据时自动清空。

---

## 地球化学功能

### 预设模型

| 模型 | 说明 |
|------|------|
| Stacey & Kramers (2nd Stage) | 两阶段铅演化模型（默认） |
| Stacey & Kramers (1st Stage) | 一阶段铅演化模型 |
| Cumming & Richards (Model III) | C-R 三阶段模型 |
| Maltese & Mezger (2020) | M-M 模型 |
| V1V2 (Geokit) | Geokit V1V2 参数 |
| V1V2 (Zhu 1993) | 朱炳泉 1993 V1V2 参数 |

每个模型包含完整的物理常数（衰变常数 λ₂₃₈、λ₂₃₅、λ₂₃₂，原始铅比值，地球年龄等）和可调参数（μ、ω、κ 等）。

### 模型曲线

在 Pb 演化图上叠加铅同位素演化曲线，显示从原始铅到现今的理论演化轨迹。

### 古等时线

- 默认年龄范围：0-3000 Ma
- 步长：50-5000 Ma（默认 1000 Ma）
- 自动标签定位，沿斜率方向旋转
- 独立线条样式配置

### 模型年龄线

从模型曲线到样品点的连接线，显示单阶段和两阶段模型年龄。

### 等时线回归

基于 York (2004) 回归算法，支持两种误差输入模式：

- **固定误差**：手动输入 1-sigma sX、sY 和误差相关系数 rXY
- **列误差**：从数据列读取每个样品的误差值

计算结果包括：
- 斜率 ± 误差
- 截距 ± 误差
- MSWD（均方加权偏差）
- R²（决定系数）
- Pb-Pb 年龄 ± 误差
- 样品数

操作方式：
- 有选中样品时：计算选中样品的等时线
- 无选中样品时：按分组自动计算所有组的等时线
- 计算后按钮变为"关闭等时线"，再次点击清除

标注显示可在样式对话框中配置（年龄、MSWD、R²、斜率、截距、样品数）。

### 方程叠加

支持在 Pb 演化图上叠加自定义线性方程（y = mx + b），支持 LaTeX 渲染，可配置颜色、线宽、线型。

---

## 分析工具

### 端元识别

基于 liaendmembers (R) 算法的 Python 实现，用于自动识别铅同位素数据中的端元源区：

1. 对 ²⁰⁶Pb/²⁰⁴Pb、²⁰⁷Pb/²⁰⁴Pb、²⁰⁸Pb/²⁰⁴Pb 做无标准化 PCA
2. 取 PC1 最小值/最大值对应样品作为两个端元
3. 从每个端元出发，沿 geochron 斜率（≈0.6262，由衰变常数动态计算）画直线
4. tolerance 范围内的样品归入对应端元组，其余为混合组
5. Shapiro-Wilk 检验 PC2/PC3 正态性验证分组合理性

支持全量数据或选中数据分析，结果可应用为分组列直接用于可视化。

### 混合模型

基于最小二乘法求解混合比例：

- 从端元均值矩阵构建方程组
- 约束比例和为 1
- 输出每个端元的贡献比例和残差（RMSE）
- 支持多端元、多混合物同时计算

### 来源判别 ML 管线

完整的机器学习来源判别流程：

1. **数据准备**：缺失值处理、数值转换、区域过滤（最少 5 个样品）
2. **异常值检测**：DBSCAN 聚类去除离群点（eps=0.18）
3. **类别平衡**：SMOTE 过采样（k_neighbors=3）
4. **模型训练**：One-vs-Rest XGBoost 分类器（200 棵树，max_depth=6）
5. **预测**：置信度阈值过滤（默认 0.9），输出每个区域的概率分数

预测结果可回写为分组列，直接在图上按来源着色。

### PCA 分析工具

- **碎石图（Scree Plot）**：柱状图 + 累积方差曲线，评估主成分数量
- **载荷热图（Loadings Heatmap）**：各特征在主成分上的载荷权重

### 质量评估

- **Shepard 图**：原始距离 vs 嵌入距离，评估降维保真度
- **相关性热图**：Pearson 相关矩阵可视化
- **嵌入相关性**：嵌入维度与原始特征的相关性

---

## 交互功能

### 悬停提示

鼠标悬停在数据点上时显示样品元数据（如实验室编号、遗址名称、年代等），可在提示配置对话框中自定义显示列。

### 选择工具

- **矩形选择**：框选区域内的样品
- **套索选择**：自由多边形选择
- **点击选择**：单击切换单个样品的选中状态
- 选中样品以橙色高亮显示（1.8 倍标记大小）

### 图例交互

- 外部图例面板：双击条目置顶（提升对应散点/覆盖层 zorder）
- 外部图例面板：拖动条目重排绘制层级
- 图内图例：点击仅切换分组可见性
- 可配置图例位置（外部左/右 + 图内九宫格位置）
- 图例显示模式：内嵌或独立窗口

### 置信椭圆

- 基于协方差矩阵的 95% 置信椭圆（卡方分布，2 自由度）
- 支持 68%（1σ）、95%（2σ）、99%（3σ）三种置信水平
- 按分组独立绘制
- 可通过选择工具对选中样品绘制椭圆

### 子集分析

选中样品后可对子集单独运行降维、端元识别等分析，结果映射回原始数据集。

---

## 样式与主题

### 配色方案

内置 8 种配色方案：vibrant、bright、high-vis、light、muted、retro、std-colors、dark_background。

### UI 主题

| 主题 | 说明 |
|------|------|
| Modern Light | 现代浅色（默认） |
| Modern Dark | 现代深色 |
| Scientific Blue | 科学蓝 |
| Retro Lab | 复古实验室 |

### 绘图样式

- 图形尺寸：13×9 英寸（可配置）
- DPI：130（可配置）
- 网格：开/关，样式、线宽、透明度可调
- 次网格：独立控制
- 刻度方向：内/外/双向
- 坐标轴边框：四边独立控制

### 标记样式

支持多种标记形状（点、圆、三角、方形、菱形、星形等，可按分组设置），大小 1-500，透明度 0.02-1.0，边缘颜色和宽度可调。

### 字体管理

- 主要字体（英文/拉丁文）和 CJK 字体（中日韩）独立选择
- 标题、标签、刻度、图例字号分别配置
- 字体缓存加速渲染

### 线条样式

每种叠加元素（模型曲线、古等时线、等时线、模型年龄线、方程线）均可独立配置颜色、线宽、线型（实线/虚线/点划线/点线）和透明度。通过颜色小方块点击打开样式对话框。

### 边际 KDE 参数

边际 KDE（顶部/右侧分布）支持以下可配置项：

- `Bandwidth Adjust`：带宽缩放系数（0.05-5.0）
- `KDE Bandwidth (0 = Auto)`：显式带宽（0-10.0），当值为 0 时使用自动估计
- `KDE Kernel`：核函数可选 `gaussian`、`tophat`、`epanechnikov`、`exponential`、`linear`、`cosine`
- `Auto Bandwidth Method`：自动带宽估计方法可选 `Scott` 与 `Silverman`
- `KDE Cut`、`Log Transform Density`、`Marginal KDE Max Points`：控制采样范围、密度缩放与计算规模

方法选择建议：

- `Scott`：适合近似正态且单峰的数据分布
- `Silverman`：适合偏态或重尾分布，通常能得到更平滑的密度曲线

### 主题管理

支持保存和加载自定义绘图主题，包含所有样式参数。

---

## 导出功能

### 数据导出

- CSV/Excel 格式导出选中样品或全部数据
- 混合模型计算结果导出
- 端元分析结果导出（含 PC 分数和分组标签）
- ML 来源判别预测结果导出

### 图形导出

通过 matplotlib 工具栏支持 PNG、PDF、SVG 等格式导出。

---

## 本地化

### 双语支持

- 中文（默认）和英文
- 960+ 翻译条目（当前 966），覆盖所有菜单、对话框、按钮、标签、状态消息和错误提示
- 实时切换语言，无需重启
- 翻译缺失时自动回退到英文

---

## 安装与运行

### 推荐方式（uv）

```bash
# 1) 安装 uv（如未安装）
pip install uv

# 2) 克隆仓库并创建虚拟环境
git clone <repository-url>
cd IsotopesAnalyse
uv venv .venv
.venv\Scripts\activate        # Windows

# 3) 安装依赖并运行
uv pip install -e .
uv run python main.py
```

### 其他方式

```bash
# pip 安装
pip install -e .
python main.py
```

### 构建独立可执行文件

```bash
uv run pyinstaller build.spec
# 输出到 dist/IsotopesAnalyse/
```

---

## 项目结构

```
IsotopesAnalyse/
├── main.py                          # 应用入口
├── pyproject.toml                   # 项目与依赖定义
├── application/                     # 用例层（导入/导出等）
├── core/
│   ├── config.py                    # 全局配置
│   ├── cache.py                     # LRU 缓存
│   ├── localization.py              # 本地化
│   ├── legend_state.py              # 图例状态
│   ├── overlay_state.py             # 叠加层状态
│   ├── session/                     # 会话持久化与迁移
│   └── state/                       # 状态 bootstrap/gateway/store
├── data/
│   ├── loader.py                    # 数据加载与清洗
│   ├── geochemistry.py              # 地球化学计算入口
│   ├── geochemistry/                # 模型细分模块
│   ├── endmember.py                 # 端元识别
│   ├── mixing.py                    # 混合模型
│   └── provenance_ml.py             # 来源判别 ML
├── ui/
│   ├── app.py                       # 应用生命周期
│   ├── main_window.py               # 主窗口
│   ├── main_window_parts/           # 主窗口拆分组件
│   ├── control_panel.py             # 分区对话框构建
│   ├── panels/                      # 各分析/显示面板
│   └── dialogs/                     # 专用对话框
├── visualization/
│   ├── events.py                    # 交互事件
│   ├── event_handlers/              # 事件处理 helper
│   ├── plotting/
│   │   ├── api.py                   # 绘图调度入口
│   │   ├── core.py                  # 计算核心
│   │   ├── render.py                # 绘制渲染
│   │   ├── geo.py                   # 地球化学叠加
│   │   ├── ternary.py               # 三元图逻辑
│   │   ├── kde.py                   # KDE 相关逻辑
│   │   ├── data.py                  # 数据准备
│   │   ├── isochron.py              # 等时线 helper
│   │   └── analysis_qt.py           # 分析图表
│   ├── style_manager.py             # 配色与字体管理
│   └── line_styles.py               # 线条样式解析
├── locales/                         # 中英文翻译
├── docs/                            # 架构与开发文档
├── tests/                           # 测试集合
└── build.spec                       # PyInstaller 构建配置
```

---

## 依赖

| 类别 | 库 | 最低版本（pyproject） |
|------|-----|------------------------|
| Python | CPython | >=3.12 |
| GUI 框架 | PyQt5, PyQt5-Qt5 | >=5.15, >=5.15 |
| 绘图与样式 | matplotlib, seaborn, scienceplots | >=3.10.7, >=0.13.2, >=2.2.0 |
| 数据处理 | pandas, numpy | >=2.3.3, >=2.3.5 |
| Excel/导出 | openpyxl, python-calamine, xlsxwriter | >=3.1.5, >=0.6.1, >=3.2.9 |
| 机器学习 | scikit-learn, umap-learn, xgboost, imbalanced-learn | >=1.5.2, >=0.5.6, >=2.0.3, >=0.12.2 |
| 三元图 | mpltern, python-ternary | >=1.0.4, >=1.0.8 |
| 文本布局 | adjusttext | >=1.3.0 |
| 构建 | pyinstaller | >=6.17.0 |

重型依赖（sklearn、umap、xgboost）采用懒加载，不影响启动速度。

---

## 会话管理

应用自动保存以下参数到 `~/.isotopes_analysis/params.json`：

- 算法选择与参数
- 标记样式（大小、形状、透明度）
- 分组列选择
- 文件路径与工作表
- 渲染模式
- 边际 KDE 参数（带宽、核函数、自动带宽方法）
- 语言偏好
- UI 主题
- 窗口位置与大小

重启后自动恢复上次的工作状态。
