# ui/ 模块开发文档

## 模块概述

`ui/` 是应用的用户界面层，基于 PyQt5 构建。包含主窗口、控制面板、11 个专用对话框。

**文件清单 (拆分后)**

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 20 | 模块入口 |
| `app.py` | 481 | 应用生命周期管理 + Qt/Python 调试钩子 |
| `main_window.py` | 1,084 | 主窗口 (画布 + 图例面板 + 工具栏) |
| `control_panel.py` | 505 | 控制面板组装 + 对话框入口 |
| `icons.py` | 230 | UI 色块/标记图标渲染工具 |
| `panels/` | 5,312 | 6 个标签页的面板实现 |
| `dialogs/` | 3,967 | 11 个专用对话框 |

---

## 1. app.py — 应用生命周期

### 职责
Qt 应用初始化、会话恢复、图形创建、事件连接。

### Qt5Application 类

```python
class Qt5Application:
    def run(self) -> bool
```

**启动流程:**
1. `QApplication` 初始化
2. `_configure_fonts()` — 设置默认字体 (Microsoft YaHei UI, 9pt)
3. `_configure_native_style()` — 应用原生 Qt 样式 (WindowsVista/Fusion)
4. `_install_debug_handlers()` — 捕获 Qt/Python 错误
5. `_load_session()` — 加载会话参数
6. `load_data()` — 显示数据导入对话框
7. `_restore_session_state()` — 恢复算法、参数、渲染模式
8. `Qt5MainWindow` 创建并显示
9. `_create_plot_figure()` — 创建 matplotlib Figure (constrained_layout)
10. `_setup_control_panel()` — **当前已禁用** (设为 None)
11. `_connect_event_handlers()` — 连接 hover/click/legend 事件
12. `_render_initial_plot()` — 触发首次渲染

### 关键设计决策
- 控制面板已禁用，改用菜单栏弹出对话框模式
- matplotlib 使用 `constrained_layout` 自动布局
- 会话恢复包含渲染模式验证 (确保所需列存在)

### 调试模式

可通过启动参数或环境变量启用 Qt 详细日志（用于排查 C++ 层崩溃或事件链问题）：

```bash
python main.py --qt-debug
```

或：

```bash
ISOTOPES_QT_DEBUG=1 python main.py
```

启用后会：
- 设置 `QT_LOGGING_RULES` 与 `QT_DEBUG_PLUGINS`
- 通过 `qInstallMessageHandler` 输出 `[QT][级别][category] ...` 诊断日志
- 保持 Python `sys.excepthook` 与 `faulthandler` 崩溃栈输出

---

## 2. main_window.py — 主窗口

### 职责
主窗口布局、菜单栏、工具栏、图例面板、matplotlib 画布集成。

### Qt5MainWindow 类

```python
class Qt5MainWindow(QMainWindow):
    def __init__(self, parent=None)
```

### 窗口布局

```
┌─────────────────────────────────────────────────┐
│ 菜单栏: 文件 | 数据 | 显示 | 分析 | 导出 | 图例 | 地球化学 │
├─────────────────────────────────────────────────┤
│ 工具栏: [matplotlib 操作] [缩放还原] [框选] [套索]      │
├──────────┬──────────────────────────────────────┤
│ 图例面板  │  matplotlib 画布                       │
│ (可选位置) │                                      │
│          │                                      │
│ - 组名 + 显隐 │                                    │
│ - 颜色/形状 │                                     │
│ - 拖动排序 │                                      │
│ - 双击置顶 │                                      │
│          ├──────────────────────────────────────┤
│          │  matplotlib 工具栏                     │
└──────────┴──────────────────────────────────────┘
│ 状态栏: Ready                                    │
└─────────────────────────────────────────────────┘
```

### 图例位置

**外部图例面板 (`legend_location`)**

| 位置键 | 说明 |
|--------|------|
| `outside_left` | 水平分割器，图例在左 (默认) |
| `outside_right` | 水平分割器，图例在右 |
| `None` | 关闭外部图例面板 |

**图内图例 (`legend_position`)**

- 位置值: `upper left`, `upper center`, `upper right`, `center left`, `center`,
  `center right`, `lower left`, `lower center`, `lower right`
- `None` 代表关闭图内图例
- 图内图例与外部图例可同时启用
- 在图例面板中再次点击已选位置可取消显示

### 菜单操作

| 菜单 | 操作 | 快捷键 |
|------|------|--------|
| 文件 | 重新加载数据、退出 | Ctrl+R / Ctrl+Q |
| 数据 | 打开数据配置对话框 | Ctrl+D |
| 显示 | 打开显示设置对话框 | Ctrl+Shift+D |
| 分析 | 打开分析工具对话框 | Ctrl+Shift+A |
| 导出 | 打开导出对话框 | Ctrl+E |
| 图例 | 打开图例配置对话框 | Ctrl+L |
| 地球化学 | 打开地球化学对话框 | Ctrl+G |

### 关键方法

```python
def _show_section_dialog(self, section_key: str)
    """打开对应的控制面板区段对话框"""
    # 使用 create_section_dialog() 创建对应面板对话框 (DataPanel/DisplayPanel/...)
    # 对话框缓存在 self._section_dialogs 中

def _apply_legend_panel_layout(self)
    """根据 app_state.legend_location 调整外部图例面板位置"""

def _update_legend_panel(self, title, handles, labels)
    """更新图例列表 (颜色/形状、显隐、拖动排序、双击置顶)"""

def _rebuild_legend_after_reorder(self)
    """拖动完成后应用 z-order 并重建图例项，避免复用失效 QWidget"""

def _move_legend_item_to_top(self, entry_type, entry_key)
    """双击置顶：更新顺序状态并重建列表，不直接搬运 item/widget 指针"""

def _build_marker_icon(self, marker, color, size=16) -> QIcon
    """委托到 ui.icons.build_marker_icon()"""

def closeEvent(self, event)
    """关闭时保存会话参数"""
```

外部图例面板支持:
- 颜色与形状菜单
- 分组/覆盖层显隐
- 拖动重排（仅插入模式，不覆盖目标条目）
- 双击置顶（将对应散点/覆盖层置于最上层）

补充：
- 图内 legend (`on_legend_click`) 的点击行为是**切换可见性**，不负责置顶。
- 外部 legend 的置顶与重排由 `Qt5MainWindow` 维护 `legend_item_order` 后统一重建。

### 选择工具

```python
def _toggle_selection_tool(self, tool_type: str)
    """切换框选/套索工具"""
    # tool_type: 'export' (框选), 'lasso' (套索)

def _zoom_out_view(self)
    """缩放还原 (扩展轴范围 25%)"""
```

---

## 3. control_panel.py — 控制面板组装

### 职责
负责控制面板整体布局、状态区、标签页组装，以及分区对话框入口。

### Qt5ControlPanel 类 (组装器)

```python
class Qt5ControlPanel(QWidget):
    parameter_changed = pyqtSignal(str, object)

    def __init__(self, callback=None, parent=None, build_ui=True)
```

### 面板拆分

```
ui/
├── control_panel.py
└── panels/
    ├── base_panel.py
    ├── data_panel.py  # 组装器
    ├── data/
    │   ├── __init__.py
    │   ├── build.py
    │   ├── projection.py
    │   ├── geochem.py
    │   └── grouping.py
    ├── display_panel.py
    ├── analysis_panel.py
    ├── export_panel.py
    ├── export/
    │   ├── __init__.py
    │   ├── build.py
    │   ├── selection.py
    │   ├── data_export.py
    │   ├── image_export.py
    │   └── common.py
    ├── legend_panel.py
    └── geo_panel.py
```

### 6 个标签页 (对应面板)

#### Data (数据)
- 数据加载状态
- 分组列选择 (单选按钮组)
- 渲染模式切换 (UMAP/tSNE/PCA/RobustPCA/2D/3D/Ternary/地球化学)
- 算法参数 (UMAP: n_neighbors/min_dist, tSNE: perplexity/learning_rate 等)
- 2D/3D/三元图轴选择

#### Display (显示)
- UI 主题 (Modern Light/Dark, Scientific Blue, Retro Lab)
- 保存/加载绘图主题
- 三段式分区：`Presets & Themes`、`Text & Markers`、`Axes, Grid & Canvas`
- 字体设置 (主字体 + CJK 字体)
- 字体大小 (标题/标签/刻度/图例)
- 标记大小/透明度
- 图形 DPI/背景色
- 网格样式 (颜色/宽度/透明度/线型)
- 次网格
- 刻度样式 (方向/颜色/长度/宽度)
- 次刻度
- 坐标轴线宽/颜色
- 脊柱显示 (上/右)
- 标签/标题样式 (颜色/粗细/间距)
- 图例框样式
- 颜色选择统一为“小方块按钮”交互，点击弹出取色器；按钮实时显示当前颜色
- `Axes & Lines` 高级参数使用单列分组布局（Figure/Grid/Ticks/Spines/Text）

调色板/色阶选择已移至 Legend 面板的自动样式配置。

#### Analysis (分析)
- 相关性热图
- 轴相关性
- Shepard 图
- 选择工具 (框选/椭圆/套索)
- 子集分析
- 数据重置

#### Export (导出)
- 数据导出：导出选中数据（CSV/Excel/追加）
- 图像导出：按期刊预设离屏重绘导出（优先 SciencePlots，缺失时自动回退内置样式）
- 图像参数：格式、DPI、点大小、图例大小、紧凑边界框、透明背景、边距
- 导出流程：支持“直接导出”与“预览后导出”两种模式

#### Legend (图例)
- 图例位置 (外部 OUT L/OUT R，图内九宫格)
- 图内图例样式 (列数仅影响图内图例，含微调步长与方向微调)
- 自动样式 (色阶、形状集合、基准形状、自动分配)
- 自定义色阶/形状阶梯 (图形化选择)

补充说明:
色阶下拉框以色条显示，形状相关选择器与菜单仅显示图标。

#### Geochemistry (地球化学)
- 地球化学模型选择
- 模型参数
- 模型曲线/古等时线/模式年龄线/等时线开关
- V1-V2 参数
- 方程叠加
- 等时线回归
- 端元分析
- 产地 ML
- 混合计算器

### 对话框模式 (分区面板)

```python
def create_section_dialog(section_key: str, callback, parent=None) -> QDialog
    """创建单区段对话框"""
    # 1. 创建对应 panel 类 (DataPanel/DisplayPanel/...)
    # 2. panel.reset_state()
    # 3. panel.build()
    # 4. 包装在 QDialog + QScrollArea 中
```

### 样式变更流程 (BasePanel)

```
用户修改控件
  → _on_style_change()
  → 更新 app_state 属性
  → 判断是否需要重绘:
      - 调色板/字体/标题变更 → callback() (完整重绘)
      - 其他样式变更 → refresh_plot_style() (仅刷新样式)
```

### 关键保护机制

```python
def _on_style_change(self, *_args):
    if not self._is_initialized:  # 防止初始化期间信号触发
        return
    ...
```

### 主题管理 (DisplayPanel)

```python
def _save_theme(self)     # 保存当前样式到 app_state.saved_themes
def _load_theme(self)     # 从已保存主题恢复
def _delete_theme(self)   # 删除已保存主题
```

---

## 4. panels/ — 面板子模块

### BasePanel (base_panel.py)
- 统一 `_on_style_change()` 与防抖逻辑
- 统一 `_is_initialized` 守卫
- 提供 `_set_combo_value()` / `_combo_value()`
- 提供通用 `_debounce(key, func, delay_ms)` 方法，支持任意回调防抖

### DataPanel
- 数据/分组/算法/投影/地球化学曲线控制
- 维护与 LegendPanel/GeoPanel 的联动
- 使用 `QToolBox` 折叠分区：`Coloring / Grouping`、`Render Mode`

### DisplayPanel
- UI 主题/绘图样式/主题保存
- 样式变更统一走 BasePanel._on_style_change()
- 标题显隐/标题间距走轻量刷新 (`refresh_plot_style`)；调色板/字体等关键变更仍触发完整重绘
- 使用 `QToolBox` 折叠分区：`Presets & Themes`、`Text & Markers`、`Axes, Grid & Canvas`

### AnalysisPanel
- KDE、选择工具、分析/混合/端元/ML
- 选择状态同步与配置对话框
- 使用 `QToolBox` 折叠分区：KDE、方程叠加、选择工具、数据分析、子集分析、混合、端元识别、ML、置信椭圆

### ExportPanel
- 数据导出：导出选中数据 (CSV/Excel/追加)
- 图像导出：期刊预设离屏重绘导出（PNG/TIFF/PDF/SVG/EPS）
- SciencePlots 可用时使用期刊样式链；不可用时自动回退内置 rcParams 样式
- 图像参数控制：DPI、点大小、图例大小、tight bbox、padding、透明背景
- 导出入口：`Export Image`（直接导出）+ `Preview Export`（预览后保存）
- 选择状态同步
- 使用 `QToolBox` 折叠分区：`Data Export`、`Image Export`
- 专题文档：`docs/export.md`

模块拆分说明（2026-03）:
- `panels/export_panel.py` 仅保留 `ExportPanel` 组装类与轻量入口方法。
- `panels/export/build.py`：UI 构建、控件初始化、信号连接。
- `panels/export/selection.py`：选择状态同步、选择工具联动。
- `panels/export/data_export.py`：CSV/Excel/追加导出流程。
- `panels/export/image_export.py`：离屏重绘、预览导出、直接导出。
- `panels/export/common.py`：导出通用工具与共享辅助逻辑。

### LegendPanel
- 图例位置 (外部/图内)
- 图内图例样式 (列数、偏移微调)
- 自动样式 (色阶/形状集合/基准形状)
- 自定义色阶/形状阶梯
- 使用 `QToolBox` 折叠分区：`Legend Position`、`Inline Legend Style`

### GeoPanel
- 模型选择与参数管理
- 使用 `QToolBox` 折叠分区：模型、时间参数、衰变常数、初始铅组成、地幔参数、应用操作

### 面板布局约定（新增）
- 6 个面板统一采用 `QToolBox` 作为顶层分区容器，减少长页面滚动。
- 分区标题使用 `translate()` 文本，保持中英文切换一致。
- 分区内控件行为不变，布局重构不改变原有业务回调。

---

## 5. dialogs/ — 对话框子模块

### 对话框清单

| 对话框 | 行数 | 职责 |
|--------|------|------|
| `data_import_dialog.py` | 694 | 统一数据导入 (文件+工作表+列) |
| `provenance_ml_dialog.py` | 663 | ML 产地分析配置 |
| `endmember_dialog.py` | 431 | 端元识别参数 |
| `isochron_dialog.py` | 317 | 等时线回归设置 |
| `ternary_dialog.py` | 243 | 三元图配置 |
| `data_config.py` | 229 | 数据列映射配置 |
| `file_dialog.py` | 227 | 文件选择 |
| `mixing_dialog.py` | 217 | 混合模型结果 |
| `three_d_dialog.py` | 192 | 3D 散点图配置 |
| `two_d_dialog.py` | 183 | 2D 散点图配置 |
| `tooltip_dialog.py` | 127 | 悬停提示配置 |
| `sheet_dialog.py` | 116 | Excel 工作表选择 |
| `progress_dialog.py` | 64 | 进度指示器 |

### 通用对话框模式

```python
class SomeDialog(QDialog):
    def __init__(self, ..., parent=None):
        super().__init__(parent)
        self.result = None
        self._setup_ui()

    def _setup_ui(self):
        # 标题 + 副标题
        # 内容区 (可滚动)
        # 底部按钮 (取消/确定)

    def _ok_clicked(self):
        # 验证输入
        # self.result = {...}
        # self.accept()
```

### 关键对话框详解

#### Qt5DataImportDialog (data_import_dialog.py)
- 三栏布局: 文件 | 工作表 | 列选择
- 数据预览表 (前 8 行 × 6 列)
- 最近文件列表 (最多 8 个)
- 自动推荐数据列 (206Pb/204Pb, 207Pb/204Pb, 208Pb/204Pb)
- 内置语言切换

#### Qt5IsochronDialog (isochron_dialog.py)
- 误差输入模式: 固定值 / 列选择
- York 回归参数设置
- 支持 x/y 误差和相关系数

#### Qt5TernaryDialog (ternary_dialog.py)
- 点击选择列顺序 (Top, Left, Right)
- 拉伸模式 (power/minmax/hybrid)
- 缩放因子

#### Qt5ProvenanceMLDialog (provenance_ml_dialog.py)
- 训练数据配置 (区域列 + 特征列)
- 预测范围 (全部/选中/子集)
- ML 参数 (DBSCAN eps, XGBoost 参数, SMOTE 开关)
- 预测阈值

---

## 信号/槽连接模式

### 参数变更
```
控件 valueChanged/stateChanged/currentTextChanged
  → _on_style_change() / _on_xxx_change()
  → 更新 app_state
  → callback() [= on_slider_change()]
  → 重新渲染
```

### 语言切换
```
lang_combo.currentIndexChanged
  → _on_language_change()
  → set_language(code)
  → app_state.notify_language_change()
  → 所有监听器 _refresh_language()
  → _rebuild_ui() (完整重建)
```

### 选择工具
```
工具栏按钮 clicked
  → _toggle_selection_tool(tool_type)
  → toggle_selection_mode(tool_type) [visualization.events]
  → 创建/销毁 RectangleSelector / LassoSelector
```

---

## 依赖关系

```
app.py
  ├→ main_window.py
  ├→ data.loader
  ├→ core (app_state, CONFIG, session, localization)
  └→ visualization.events

main_window.py
  ├→ control_panel.py (create_section_dialog)
  ├→ visualization.events
  └→ data.loader

control_panel.py
  ├→ core (app_state, translate)
  └→ panels/*

panels/*
  ├→ core (app_state, CONFIG, translate)
  ├→ visualization.events / plotting/style.py
  ├→ data.loader / data.endmember
  └→ dialogs/*

dialogs/*
  ├→ core (app_state, translate)
  └→ data.loader
```

---

## 改进建议

改进建议已迁移至 `docs/development_plan.md`。
