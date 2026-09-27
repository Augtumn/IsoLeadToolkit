# IsotopesAnalyse

面向铅同位素地球化学的桌面分析与可视化工具：从原始测试数据到出版级图件与来源判别，一体化完成。
基于 PyQt5 + Matplotlib，支持中文 / 英文界面。

![Python](https://img.shields.io/badge/Python-3.12+-blue)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green)
![Tests](https://img.shields.io/badge/Tests-pytest-brightgreen)
![License](https://img.shields.io/badge/License-GPLv3-blue)
![Platform](https://img.shields.io/badge/Platform-Win%20x64-lightgrey)

---

## 一条典型流程

```
导入 Excel/CSV ──▶ 选分组列 ──▶ 降维/三元/2D/3D 出图 ──▶ 地球化学建模与覆盖层
      └──▶ 端元识别 / 混合计算 / 聚类 / 产地分类 ──▶ 选中子集深挖 ──▶ 出版级导出（图像 / Origin）
```

全过程状态（算法、参数、样式、分组、语言、几何）自动保存，下次启动原样恢复。

---

## 功能

### 数据导入

- Excel / CSV 读取，列类型自动推断；多工作表选择
- 分组列指定、分组显隐与配色/形状自定义
- 大表友好：分组数不设上限（图例面板可搜索、可滚动）

### 可视化类型

| 模式 | 说明 |
|------|------|
| UMAP / t-SNE / PCA / RobustPCA | 高维降维嵌入，可叠加 KDE 等高线与置信椭圆 |
| 2D / 3D 散点 | 自选轴列；2D 支持边际 KDE |
| Ternary 三元图 | 基于 mpltern，支持局部放大、手动限值与数据范围自动适配 |
| V1V2 判别 | 铅源区投影（Geokit / Zhu 1993） |
| Pb 演化图（76/86） | 叠加模型曲线、古等时线、York 回归 |
| Plumbotectonics（76/86） | 构造分区参考曲线 |
| Mu-Age / Kappa-Age | 同位素比值与年龄联动 |

### 降维算法与参数

| 算法 | 参数 | 默认值 | 范围 |
|------|------|--------|------|
| UMAP | n_neighbors | 10 | 2–50 |
| | min_dist | 0.1 | 0.0–1.0 |
| t-SNE | perplexity | 30 | 5–100 |
| | learning_rate | 200 | 10–1000 |
| PCA | n_components | 2 | 2–10 |
| RobustPCA | n_components / support_fraction | 2 / 0.75 | 2–10 / 0.1–1.0 |

嵌入结果 LRU 缓存（8 条），数据重载自动失效；参数预设可保存/加载；长任务在后台线程执行并显示进度。

### 地球化学建模

**预设模型**：Stacey & Kramers (1st/2nd)、Cumming & Richards (III)、Maltese & Mezger (2020)、V1V2 (Geokit / Zhu 1993)

**覆盖层**：

| 元素 | 说明 |
|------|------|
| 模型曲线 | 铅同位素演化轨迹 |
| 古等时线 | 0–3000 Ma，步长与样式独立可调 |
| 等时线回归 | York (2004)，输出 MSWD / R² / 年龄 ± 误差 |
| 模型年龄线 | 单阶段 / 两阶段连接线 |
| 方程叠加 | y = mx + b，LaTeX 渲染 |

### 分析工具（插件驱动）

| 工具 | 方法 | 插件名 |
|------|------|--------|
| 端元识别 | PCA + geochron 斜率过滤 + Shapiro-Wilk 检验 | `endmember` |
| 混合模型 | 单纯形约束最小二乘 + 蒙特卡洛不确定度 | `mixing` |
| HDBSCAN 聚类 | 密度聚类（嵌入坐标输入） | `hdbscan_clustering` |
| 产地分类 | DBSCAN→SMOTE→OvR XGBoost | `provenance_ml` |
| 子集分析 | 选中样品重分析 | `subset_analysis` |
| 诊断图 | 碎石图 / 载荷热图 / Shepard 图 / 相关矩阵 | — |

### 导出

**出版级图像**

- 8 种投稿预设（Science / IEEE / Nature / Presentation / 单栏 / 双栏等），实时预览
- 可调 DPI、点大小、图例标记大小、字号（标题 / 标签 / 刻度）
- 格式：PNG / TIFF / PDF / SVG / EPS，可嵌入 TrueType 字体、白底、PDF 元数据
- SciencePlots 优先，缺失时自动回退内置样式

**Origin（.opju）**

- 散点数据 → 分组工作表
- 覆盖层：模型曲线、古等时线、等时线回归、Plumbotectonics
- 三元图 → Origin 三元模板 + 归一化

### 交互

| 操作 | 行为 |
|------|------|
| 悬停数据点 | 提示框显示自选列；该点放大显示 |
| 滚轮 | 以光标为中心缩放（2D 与三元图通用） |
| 中键拖动 | 平移视图 |
| 左键拖动（工具栏放大镜选中时） | 三元图拖出相似子三角形放大，向外拖还原 |
| 矩形框选 / 套索 / 单击 | 选择样品（工具栏或面板启用） |
| 双击数据点 | 图例面板滚动到并选中该点所属分组 |
| 双击图例项 | 该分组图层置顶 |
| 图例拖拽 | 调整叠放顺序；搜索框支持关键字过滤与 Enter 逐项跳转 |
| **Esc** | 取消选择工具；再按一次清除已选样品 |
| **Delete / Backspace** | 删除已选样品 |
| **Ctrl+Z** | 撤销上一步删除/清空（仅选择状态） |
| **Ctrl+F** | 聚焦图例搜索框 |

输入框内打字时上述按键不会被抢占（Esc 只清空输入框，Delete/Ctrl+Z 不影响数据）。

### 界面与会话

- 6 个分区对话框（Data / Display / Analysis / Export / Legend / Geochemistry），菜单或快捷键触发
- 状态栏实时信息（样品数 / 渲染模式 / 分组数）+ 嵌入进度条；启用选择工具时提示如何退出
- 中文 / 英文实时切换
- 图内图例与图外图例面板可同时显示；置信椭圆 1σ / 2σ / 3σ 可选
- 应用内日志查看器（文件 → 查看日志），主日志 / 错误日志切换
- 对话框记住上次尺寸与位置；会话状态自动保存（`~/.isotopes_analysis/params.json`）

---

## 安装与运行

```bash
# uv（推荐）
pip install uv
git clone <url> && cd IsotopesAnalyse
uv run python main.py

# pip
pip install -e . && python main.py

# 可选依赖
uv pip install -e ".[hdbscan]"   # HDBSCAN 聚类
uv pip install -e ".[dev]"       # 测试

# 打包
uv run pyinstaller build.spec    # → dist/IsotopesAnalyse/
```

用户配置（可选）：`~/.isotopes_analysis/config.json`

```json
{ "default_language": "zh", "figure_dpi": 150, "embedding_cache_size": 16 }
```

---

## 文档

| 文档 | 内容 |
|------|------|
| [docs/architecture.md](docs/architecture.md) | 分层架构、状态管理、目录结构、质量守卫与工程约定 |
| [docs/dev_conventions.md](docs/dev_conventions.md) | 编码与提交约定、类型注解、输入事件归属 |
| [docs/visualization.md](docs/visualization.md) | 渲染管线与三元视图细节 |
| [docs/export.md](docs/export.md) | 图像预设、字体嵌入、Origin 导出路径 |
| [docs/ui_architecture_review.md](docs/ui_architecture_review.md) | UI 框架评审与收敛记录 |
| [docs/development_plan.md](docs/development_plan.md) | 待办（仅未完成项） |

---

## 开发

```bash
uv run pytest                              # 测试
uv run python scripts/release_check.py     # 发布前检查
uv run python scripts/new_plugin.py name   # 生成插件骨架
```

工程约束（状态只能经网关修改、禁止静默异常、跨 mixin 调用需声明等）与 11 个守卫脚本列表见
[docs/architecture.md](docs/architecture.md)。

### 插件开发

```python
# 放入 ~/.isotopes_analysis/plugins/ 或 plugins/builtins/
from plugins.api import BasePlugin, PluginMeta

class MyPlugin(BasePlugin):
    meta = PluginMeta(name="my_plugin", version="0.1", plugin_type="analysis",
                      description="My analysis tool")
    def validate_environment(self): return True, "ok"
    def get_default_params(self): return {}
    def build_ui(self, parent=None, callback=None):
        """返回 QWidget 自动显示在分析面板，返回 None 表示不显示 UI"""
        ...
```

---

## 参考文献

文献以 BibTeX 维护在 [IsoLeadToolkit.bib](IsoLeadToolkit.bib)（22 条，引用键来自 Zotero / Better BibTeX），
与 Zotero 集合 `IsoLeadToolkit` 同源。正文与代码注释按**引用键**引用，例如 `\cite{staceyApproximationTerrestrialLead1975}`。

| 用途 | 引用键 |
|------|--------|
| Plumbotectonics 模型（1981） | `zartmanPlumbotectonicsModel1981` |
| Plumbotectonics 双向传输（1988） | `zartmanPlumbotectonicModelPb1988` |
| PLUMBO 程序（1988） | `hainesPLUMBOHewlettpackardSeries1988` |
| Albarède & Juteau T–μ–κ（1984） | `albaredeUnscramblingLeadModel1984` |
| 考古 Pb 同位素方法（2012） | `albaredeGEOLOGICALPERSPECTIVEUSE2012` |
| 银币混合模型（2024） | `albaredeBullionMixturesSilver2024` |
| 中国地球化学省（1995） | `zhuMappingGeochemicalProvinces1995` |
| Zhu 1993 V1V2 投影 | `ZhuBingQuanKuangShiPbTongWeiSuSanWeiKongJianTuoBuTuJieYongYuDiQiuHuaXueShengYuKuangZhongQuHua1993` |
| 中国大陆地壳动力学模型 | `LiLongZhengYongFeiZhouJianBoZhongGuoDaLuDiKeQianTongWeiSuYanHuaDeDongLiXueMoXing2001` |
| 朱炳泉 1998 教材 | `ZhuBingQuanDiQiuKeXueZhongTongWeiSuTiXiLiLunYuYingYongJianLunZhongGuoDaLuKeManYanHua1998` |
| PbIso 实现参考 | `armisteadPbIsoPackageWeb2024` |
| IsoplotR 实现参考 | `vermeeschIsoplotRFreeOpen2018` |
| ASTR 工具箱 | `roseArchaeothommyASTR2026` |
| GeoKit（V1V2 参数体系） | `LuYuanFaGeoKitYiGeYongVBAGouJianDeDiQiuHuaXueGongJuRuanJianBao2004` |
| 流形学习 + 贝叶斯混合（案例） | `sunResolvingComplexMixing2023` |

---

## 许可证

本项目以 **GNU General Public License v3.0 or later（GPL-3.0-or-later）** 发布，全文见 [LICENSE](LICENSE)。

- **可以**：自由使用、修改、再分发，**包括商业用途**（GPL 并不禁止商用）；
- **条件**：分发修改版或二进制时，必须同样以 GPL-3.0 授权，并向接收者提供**完整对应源码**（含构建脚本）；
- **无担保**：软件按"现状"提供，不附带任何明示或默示担保。

本项目的界面依赖 PyQt5（GPL v3），与本项目许可一致。若要把本项目用于**闭源商业产品**，
需自行取得 PyQt5 的商业许可（Riverbank）并遵守其条款，或改用 LGPL 授权的 PySide6。

分发打包产物（`dist/IsotopesAnalyse/`）时，对应源码即本仓库。
