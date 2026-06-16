# IsotopesAnalyse

一个面向铅同位素地球化学的桌面分析与可视化工具，基于 PyQt5 + Matplotlib 构建，覆盖数据处理、降维分析、地球化学建模、端元/混合分析与来源判别等全流程。

![Python](https://img.shields.io/badge/Python-3.12+-blue)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green)
![Tests](https://img.shields.io/badge/Tests-343%20passed-brightgreen)
![Platform](https://img.shields.io/badge/Platform-Windows%20x64-lightgrey)

---

## 安装

### uv（推荐）

```bash
pip install uv
git clone <repository-url>
cd IsotopesAnalyse
uv run python main.py
```

### pip

```bash
pip install -e .
python main.py
```

### 可选依赖

```bash
uv pip install -e ".[hdbscan]"   # HDBSCAN 聚类
uv pip install -e ".[dev]"        # 开发测试
```

### 构建可执行文件

```bash
uv run pyinstaller build.spec
# 输出 → dist/IsotopesAnalyse/
```

---

## 功能概览

- **5 种降维算法**：UMAP、t-SNE、PCA、RobustPCA、V1V2
- **14 种渲染模式**：嵌入图、2D/3D 散点、三元图、Pb 演化图、Plumbotectonics、μ-Age / κ-Age
- **地球化学建模**：Stacey-Kramers、Cumming-Richards 等模型曲线、古等时线、York 回归
- **分析工具**：端元识别（PCA+geochron）、混合模型（最小二乘+MC 不确定度）、HDBSCAN 聚类、XGBoost 产地分类
- **插件系统**：分析功能通过可发现插件加载，支持第三方扩展
- **图像导出**：期刊预设（Science/IEEE/Nature）+ 实时预览 + DPI/字号/标记大小调节
- **Origin 导出**：散点数据 + 覆盖层（模型曲线/等时线）+ 三元图 → .opju
- **中英文双语**：1000+ 翻译条目，实时切换
- **会话持久化**：参数自动保存到 `~/.isotopes_analysis/`

---

## 可视化类型

| 模式 | 说明 |
|------|------|
| UMAP / t-SNE / PCA / RobustPCA | 高维降维嵌入，叠加 KDE 密度等高线和置信椭圆 |
| 2D / 3D | 用户自选轴列散点图，支持边际 KDE |
| Ternary | 基于 mpltern 的三元相图 |
| V1V2 | 铅源区判别投影（Zhu 1993 / Geokit） |
| PB_EVOL_76 / 86 | Pb 同位素演化图 + 模型曲线/古等时线/等时线回归 |
| PLUMBOTECTONICS | 构造分区参考曲线叠加 |
| PB_MU_AGE / PB_KAPPA_AGE | μ / κ 与年龄联动 |

---

## 算法参数

| 算法 | 参数 | 默认值 | 范围 |
|------|------|--------|------|
| UMAP | n_neighbors | 10 | 2-50 |
| | min_dist | 0.1 | 0.0-1.0 |
| t-SNE | perplexity | 30 | 5-100 |
| | learning_rate | 200 | 10-1000 |
| PCA | n_components | 2 | 2-10 |
| RobustPCA | support_fraction | 0.75 | 0.1-1.0 |

嵌入结果 LRU 缓存（8 个），数据重载时自动清空。

---

## 地球化学功能

### 预设模型

Stacey & Kramers (1st/2nd)、Cumming & Richards (III)、Maltese & Mezger (2020)、V1V2 (Geokit/Zhu 1993)

### 覆盖层

| 类型 | 说明 |
|------|------|
| 模型曲线 | 铅同位素演化轨迹 |
| 古等时线 | 0-3000 Ma，可调步长 |
| 等时线回归 | York (2004)，MSWD/R²/年龄 ± 误差 |
| 模型年龄线 | 单阶段/两阶段连接线 |
| 方程叠加 | 自定义 y = mx + b，支持 LaTeX |

---

## 分析工具

| 工具 | 方法 |
|------|------|
| 端元识别 | 无标准化 PCA + geochron 斜率过滤 + Shapiro-Wilk 检验 |
| 混合模型 | 单纯形约束最小二乘 + 蒙特卡洛不确定度 |
| HDBSCAN | 密度聚类（嵌入坐标输入） |
| 产地分类 | DBSCAN 去离群 → SMOTE 过采样 → OvR XGBoost |
| 诊断图 | 碎石图、载荷热图、Shepard 图、相关热图 |

---

## 导出

### 图像导出

- 4 种期刊预设：Science Single / IEEE Single / Nature Double / Presentation
- 实时预览对话框，可调 DPI、点大小、字号（标题/标签/刻度/图例）
- 格式：PNG / TIFF / PDF / SVG / EPS
- SciencePlots 优先，缺失时自动回退内置样式

### Origin 导出（.opju）

- 散点数据 → 分组工作表
- 覆盖层：模型曲线、古等时线、等时线回归、Plumbotectonics
- 三元图 → Origin 三元模板 + `cols_axis('xyz')` 归一化

---

## 项目结构

```
IsotopesAnalyse/
├── main.py                    # 入口
├── pyproject.toml
├── application/               # 用例层（导入/导出/渲染）
├── core/
│   ├── config.py              # 全局配置
│   ├── state/                 # StateStore + Gateway
│   ├── localization.py        # 双语切换
│   └── session/               # 会话持久化
├── data/
│   ├── loader.py              # 数据加载
│   └── geochemistry/          # 地球化学计算
├── plugins/                   # 插件系统
│   ├── api.py                 # 接口定义
│   ├── manager.py             # 发现/加载/验证
│   ├── builtins/              # 内置插件（5 个）
│   └── examples/              # 第三方模板
├── ui/
│   ├── main_window.py         # 主窗口
│   ├── panels/                # 6 个控制面板
│   ├── dialogs/               # 专用对话框
│   └── widgets.py             # 可复用组件
├── visualization/
│   ├── events.py              # 交互编排
│   ├── plotting/              # 渲染管线
│   └── style_manager.py       # 配色与字体
├── locales/                   # en / zh JSON
├── scripts/                   # 守护 / 发布 / 脚手架
├── tests/                     # 343 tests
└── build.spec                 # PyInstaller
```

---

## 开发

```bash
uv run pytest                          # 运行测试
uv run python scripts/release_check.py # 发布前检查（13 项）
uv run python scripts/new_plugin.py my_plugin  # 创建新插件
```

### 依赖

| 类别 | 库 |
|------|-----|
| GUI | PyQt5 |
| 绘图 | matplotlib, seaborn, scienceplots, mpltern |
| 数据 | pandas, numpy, scipy, openpyxl, calamine |
| ML | scikit-learn, umap-learn, xgboost, imbalanced-learn |
| 构建 | pyinstaller |

重型依赖（sklearn, umap, xgboost）采用懒加载，不影响启动速度。
