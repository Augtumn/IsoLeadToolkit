# IsotopesAnalyse

面向铅同位素地球化学的桌面分析与可视化工具。基于 PyQt5 + Matplotlib，覆盖数据导入、降维分析、地球化学建模、端元/混合计算与机器学习来源判别等全流程。

![Python](https://img.shields.io/badge/Python-3.12+-blue)
![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green)
![Tests](https://img.shields.io/badge/Tests-343%20passed-brightgreen)
![Platform](https://img.shields.io/badge/Platform-Win%20x64-lightgrey)

---

## 安装

```bash
# uv（推荐）
pip install uv
git clone <url> && cd IsotopesAnalyse
uv run python main.py

# pip
pip install -e . && python main.py

# 可选依赖
uv pip install -e ".[hdbscan]"   # HDBSCAN 聚类
uv pip install -e ".[dev]"        # 测试

# 构建可执行文件
uv run pyinstaller build.spec     # → dist/IsotopesAnalyse/
```

---

## 功能

### 可视化类型

| 模式 | 说明 |
|------|------|
| UMAP / t-SNE / PCA / RobustPCA | 高维降维嵌入，叠加 KDE 等高线和置信椭圆 |
| 2D / 3D 散点 | 用户自选轴列，2D 支持边际 KDE |
| Ternary 三元图 | 基于 mpltern，支持自动/手动缩放 |
| V1V2 判别 | 铅源区投影（Geokit / Zhu 1993） |
| Pb 演化图 (76/86) | 叠加模型曲线、古等时线、York 回归 |
| Plumbotectonics (76/86) | 构造分区参考曲线 |
| Mu-Age / Kappa-Age | 同位素比值与年龄联动 |

### 算法参数

| 算法 | 参数 | 默认值 | 范围 |
|------|------|--------|------|
| UMAP | n_neighbors | 10 | 2–50 |
| | min_dist | 0.1 | 0.0–1.0 |
| t-SNE | perplexity | 30 | 5–100 |
| | learning_rate | 200 | 10–1000 |
| PCA | n_components | 2 | 2–10 |
| RobustPCA | n_components / support_fraction | 2 / 0.75 | 2–10 / 0.1–1.0 |

嵌入结果 LRU 缓存（8 条），数据重载自动失效。支持参数预设保存/加载。

### 地球化学

**预设模型**：Stacey & Kramers (1st/2nd)、Cumming & Richards (III)、Maltese & Mezger (2020)、V1V2 (Geokit / Zhu 1993)

**覆盖层**：

| 元素 | 说明 |
|------|------|
| 模型曲线 | 铅同位素演化轨迹 |
| 古等时线 | 0–3000 Ma，可调步长与独立样式 |
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

**图像导出**：
- 4 种期刊预设（Science / IEEE / Nature / Presentation），支持实时预览
- 可调 DPI、数据点大小、图例标记大小、字号（标题/标签/刻度）
- 格式：PNG / TIFF / PDF / SVG / EPS
- SciencePlots 优先，缺失自动回退内置样式

**Origin 导出 (.opju)**：
- 散点数据 → 分组工作表
- 覆盖层：模型曲线、古等时线、等时线回归、Plumbotectonics
- 三元图 → Origin 三元模板 + 归一化

### UI

- 6 个分区对话框（Data / Display / Analysis / Export / Legend / Geochemistry），菜单触发
- 快捷键：Ctrl+D / Ctrl+Shift+D / Ctrl+Shift+A / Ctrl+E / Ctrl+L / Ctrl+G
- 状态栏实时信息（样品数 / 渲染模式 / 分组数）+ 嵌入进度条
- 中文 / 英文实时切换（1000+ 翻译条目）
- 图例可拖拽排序、双击置顶、显隐切换
- 显示面板搜索过滤、样式撤销（Ctrl+Z）

### 交互

- 数据点悬停提示（可自定义列）
- 矩形框选 / 套索 / 单击选择
- 选中以橙色高亮（1.8 倍标记）
- 95% 置信椭圆（1σ / 2σ / 3σ 可选）
- 外部图例面板（左 / 右停靠）

### 会话持久化

自动保存/恢复（`~/.isotopes_analysis/params.json`）：
算法选择、参数、标记样式、分组列、文件路径、渲染模式、KDE 参数、语言、UI 主题、窗口几何

---

## 项目结构

```
IsotopesAnalyse/
├── main.py
├── pyproject.toml
├── application/         # 用例层（导入/导出/渲染编排）
├── core/
│   ├── config.py        # CONFIG + 用户配置
│   ├── state/           # StateStore + Gateway + 兼容视图 (7 文件)
│   ├── session/         # 会话持久化 + 版本迁移
│   ├── localization.py  # 双语
│   └── cache.py         # LRU 嵌入缓存
├── data/
│   ├── loader.py        # Excel/CSV 读取 + 列类型推断
│   └── geochemistry/    # 地球化学计算 (engine, age, source, delta, isochron)
├── plugins/             # 插件系统
│   ├── api.py           # PluginMeta, BasePlugin, MLClassifierPlugin
│   ├── manager.py       # 发现/加载/验证
│   ├── registry.py      # plugin_manager 单例
│   ├── builtins/        # 5 个内置分析插件
│   └── examples/        # 第三方模板
├── ui/
│   ├── main_window.py   # 主窗口 (28 行)
│   ├── main_window_parts/ # 菜单/工具栏/图例/画布
│   ├── control_panel.py # 分区对话框工厂
│   ├── panels/          # 6 个控制面板
│   ├── dialogs/         # 11 个专用对话框
│   └── widgets.py       # 可复用组件
├── visualization/
│   ├── events.py        # 交互事件编排
│   ├── embedding_worker.py # QThread 异步嵌入
│   ├── event_handlers/    # 选择/指针/图例事件
│   └── plotting/        # 渲染管线 (rendering/geochem/styling)
├── locales/             # en.json / zh.json (1000+ 条目)
├── scripts/             # 守护(4)/发布检查/脚手架
├── tests/               # 57 文件, 343 用例
├── docs/                # 架构文档
└── build.spec           # PyInstaller
```

---

## 开发

```bash
uv run pytest                              # 343 测试
uv run python scripts/release_check.py     # 13 项发布检查
uv run python scripts/new_plugin.py name  # 创建新插件
```

### 质量门禁（4 守护脚本，全部保持 TOTAL=0）

| 脚本 | 检查内容 |
|------|----------|
| `check_state_mutations.py` | 直接 `app_state.xxx =` 赋值 |
| `check_gateway_direct_state_assignments.py` | Gateway 旁路写入 |
| `check_gateway_generic_mutations.py` | 通用 `set_attr` / `set_attrs` 调用 |
| `check_state_dict_mutations.py` | Dict 原地修改 |

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

### 用户配置

`~/.isotopes_analysis/config.json`（可选）：
```json
{ "default_language": "zh", "figure_dpi": 150, "embedding_cache_size": 16 }
```
