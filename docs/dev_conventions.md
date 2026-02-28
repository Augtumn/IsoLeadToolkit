# 开发规范 (统一)

本规范为 Isotopes Analyse 全项目统一标准，适用于 `core/`、`ui/`、`visualization/`、`data/`、`utils/` 等所有模块。原则参考并融合以下知名规范体系：
- PEP 8 (Python 代码风格)
- PEP 257 (Docstring 规范)
- Google Python Style Guide
- Black / Ruff (自动化格式化与静态检查思想)
- NumPy Docstring Standard
- Qt / PyQt 事件与线程模型约束
- Matplotlib 组合式绘图规范

目标：让代码在一致性、可维护性、可扩展性与可测试性上达到工程级标准。

---

## 1. 命名与结构

### 1.1 命名约定

| 类型 | 风格 | 示例 |
|------|------|------|
| 模块文件 | `snake_case.py` | `data_panel.py`, `style_manager.py` |
| 类名 | `PascalCase` | `AppState`, `StyleManager`, `Qt5MainWindow` |
| 函数/方法 | `snake_case` | `plot_embedding()`, `load_data()` |
| 私有方法 | `_leading_underscore` | `_lazy_import_ml()`, `_on_style_change()` |
| 常量 | `UPPER_SNAKE_CASE` | `LAMBDA_238`, `CONFIG`, `PRESET_MODELS` |
| 信号 | `snake_case` | `parameter_changed = pyqtSignal(str, object)` |
| Qt 类前缀 | `Qt5` | `Qt5Application`, `Qt5MainWindow`, `Qt5ControlPanel` |

### 1.2 文件与包结构

1. 包对外 API 仅通过 `__init__.py` 导出，必须声明 `__all__` 列表，默认不暴露私有符号（以 `_` 开头）。
2. 单文件超过 **800 行**或职责超过 **2 个**必须拆分，按"数据准备 / 计算 / 渲染 / UI / 事件"分层。
3. 模块顶层禁止副作用（如绘图、读写文件、耗时计算），仅允许定义常量、函数、类。

### 1.3 `__init__.py` 导出规范

按类别分组导出，附注释说明：

```python
# core/__init__.py
from .config import CONFIG
from .state import app_state
from .session import load_session_params, save_session_params
from .localization import translate, set_language, available_languages

__all__ = [
    # 配置
    'CONFIG',
    # 状态
    'app_state',
    # 会话
    'load_session_params',
    'save_session_params',
    # 国际化
    'translate',
    'set_language',
    'available_languages',
]
```

---

## 2. 文件头与导入顺序

### 2.1 文件头

文件第一行必须是模块 docstring，说明职责与关键依赖：

```python
"""嵌入计算与缓存管理。

提供 UMAP / t-SNE / PCA / RobustPCA 嵌入计算，
使用 EmbeddingCache 缓存结果以避免重复计算。
"""
```

### 2.2 导入顺序

导入顺序固定为三段式，段间空一行：

```python
# 1. 标准库
import logging
import json
from pathlib import Path

# 2. 第三方库
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QWidget, QVBoxLayout

# 3. 本项目模块
from core import translate, app_state, CONFIG
```

### 2.3 logger 声明

`logger` 必须在导入之后、函数/类定义之前声明：

```python
import logging

logger = logging.getLogger(__name__)
```

### 2.4 统一导入入口

统一使用 `from core import ...`，禁止混用子模块直入：

```python
# ✅ 正确
from core import translate, app_state, CONFIG

# ❌ 禁止
from core.state import app_state
from core.localization import translate
from core.config import CONFIG
```

---

## 3. 格式化与静态检查

1. 代码风格以 Black 兼容格式为目标，行宽建议 **88–100**。
2. 统一使用 Ruff 的规则集合进行静态检查，禁止手工绕过规则。
3. 任何禁用规则必须在注释中解释原因并限定范围：

```python
x = 1e-50  # noqa: E501 — 物理常数，保持单行可读性
```

4. Python 版本要求 **≥ 3.12**，可使用 `match/case`、`type` 语句等新语法。

---

## 4. 日志规范

### 4.1 级别选择

| 场景 | 级别 | 方法 |
|------|------|------|
| 流程节点、状态变更 | INFO | `logger.info(...)` |
| 可恢复异常、降级 | WARNING | `logger.warning(...)` |
| 不可恢复错误 | ERROR | `logger.error(...)` |
| 需要堆栈的异常 | ERROR + 堆栈 | `logger.exception(...)` |
| 开发调试信息 | DEBUG | `logger.debug(...)` |

### 4.2 消息格式

禁止手工拼接 `[INFO]`/`[WARN]`/`[ERROR]` 前缀，直接使用 logging 级别：

```python
# ✅ 正确
logger.info("Session parameters saved to %s", path)
logger.warning("Dropping missing group columns: %s", missing_groups)
logger.error("Data loading failed: %s", e)

# ❌ 禁止
logger.info("[INFO] Session parameters saved to %s", path)
logger.info("[WARN] Dropping missing group columns: %s", missing_groups)
```

### 4.3 上下文要求

日志必须包含可检索上下文（算法名、列名、样本数、关键参数）：

```python
logger.info(
    "UMAP embedding computed: n_samples=%d, n_neighbors=%d, min_dist=%.2f",
    n_samples, params['n_neighbors'], params['min_dist']
)
```

### 4.4 第三方库静默

在 `utils/logger.py` 中统一设置噪声库的日志级别：

```python
logging.getLogger('matplotlib').setLevel(logging.WARNING)
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.getLogger('numba').setLevel(logging.WARNING)
```

### 4.5 Qt 调试日志（崩溃排查）

需要排查 Qt 事件链或 native 崩溃时，使用统一调试入口：

```bash
python main.py --qt-debug
```

或设置环境变量：

```bash
ISOTOPES_QT_DEBUG=1
```

**规范**：
- Qt 消息统一通过 `qInstallMessageHandler` 写入日志，格式为 `[QT][级别][category] ...`
- 不在业务代码中散落 `print()` 调试输出
- 新增调试入口时同步更新 `docs/ui.md` 与 `README.md`

---

## 5. 国际化与用户可见文本

### 5.1 基本规则

1. 所有用户可见字符串必须使用 `translate("English text")`。
2. 翻译键统一使用**英文原文**，不允许中文 key。
3. 新增 UI 文本必须同时更新 `locales/zh.json` 与 `locales/en.json`。
4. visualization 中的提示/错误同样必须翻译。

### 5.2 使用示例

```python
from core import translate

# 简单翻译
title = QLabel(translate("Visualization Controls"))
self.setWindowTitle(translate("Control Panel"))

# 带参数的翻译
message = translate("Loaded {n} samples", n=len(df))
```

### 5.3 翻译文件格式

`locales/zh.json` / `locales/en.json` 使用扁平 key-value 结构：

```json
{
  "Visualization Controls": "可视化控制",
  "Control Panel": "控制面板",
  "Loaded {n} samples": "已加载 {n} 个样本"
}
```

### 5.4 语言切换监听

使用 `app_state.register_language_listener()` 注册回调：

```python
app_state.register_language_listener(self._refresh_language)
```

---

## 6. UI 与线程模型

### 6.1 线程规则

1. 所有 UI 更新必须在主线程执行。
2. **>200ms** 的计算必须移入 `QThread` 或后台线程，并提供进度提示。
3. UI 事件回调只负责采集参数与触发，不执行长计算。
4. 线程回调必须保证 UI 状态一致性，禁止部分更新。

### 6.2 初始化守卫模式

所有面板/控件必须使用 `_is_initialized` 守卫，防止初始化期间信号触发回调：

```python
class SomePanel(BasePanel):
    def __init__(self, callback=None, parent=None):
        super().__init__(callback, parent)
        self._is_initialized = False
        # ... 构建 UI ...
        self._is_initialized = True  # 所有 UI 构建完成后才设为 True

    def _on_style_change(self, *_args):
        if not getattr(self, "_is_initialized", False):
            return  # 初始化期间跳过
        # ... 处理样式变更 ...
```

### 6.3 滑块防抖

使用 `QTimer` 单次触发实现防抖，避免高频回调：

```python
def _schedule_slider_callback(self, key):
    if key in self._slider_timers:
        self._slider_timers[key].stop()

    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: self._apply_slider_change(key))
    timer.start(self._slider_delay_ms)  # 默认 350ms
    self._slider_timers[key] = timer
```

### 6.4 样式变更流程

```
用户修改控件
  → _on_style_change()
  → 更新 app_state 属性
  → 判断是否需要完整重绘:
      - 调色板/字体/标题变更 → callback() (完整重绘)
      - 覆盖层样式变更 → refresh_overlay_styles() (轻量刷新)
      - 其他样式变更 → refresh_plot_style() (仅刷新样式)
```

### 6.5 对话框模式

对话框统一使用以下结构：

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

### 6.6 事件过滤器安全性

Qt 事件过滤器必须防御性处理对象生命周期问题，避免访问已删除的 C++ 对象导致 access violation：

```python
class _NativeStyleFilter(QObject):
    """Clear per-widget stylesheets on show to keep native Qt styling."""

    def eventFilter(self, obj, event):
        try:
            if event.type() == QEvent.Show and isinstance(obj, QWidget):
                _clear_widget_styles(obj)
        except RuntimeError:
            # Object may have been deleted
            pass
        return False
```

**规范**：
- 事件过滤器必须捕获 `RuntimeError`（Qt 对象已删除）
- 访问 Qt 对象属性前检查类型（`isinstance(obj, QWidget)`）
- 遍历子控件时也需要 try/except 保护
- 事件过滤器对象必须存储为实例变量，避免被垃圾回收：

```python
# ✅ 正确
self._style_filter = _NativeStyleFilter(self.app)
self.app.installEventFilter(self._style_filter)

# ❌ 错误 - 临时对象会被 GC，导致 access violation
self.app.installEventFilter(_NativeStyleFilter(self.app))
```

### 6.7 QListWidget 拖拽安全规范（`setItemWidget` 场景）

对 `QListWidget + setItemWidget` 的内部拖拽（`InternalMove`），必须避免对象生命周期风险：

```python
legend_list.setDragDropMode(QAbstractItemView.InternalMove)
legend_list.setDragDropOverwriteMode(False)   # 仅插入，不覆盖

# item flags: 可拖拽，不开启 ItemIsDropEnabled
item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
```

**规范**：
- 避免在拖拽回调中直接复用旧 `QWidget` 指针（`takeItem/insertItem + setItemWidget`）  
- 优先维护“顺序状态”（如 `legend_item_order`），再整体重建列表项
- `rowsMoved` 后使用 `QTimer.singleShot(0, ...)` 延迟到事件循环稳定后再刷新视图
- 若出现 native `access violation`，优先检查 accessibility cache 与 itemWidget 生命周期

---

## 7. 可视化层规范

### 7.1 渲染入口

绘图入口统一通过 `visualization/plotting/api.py`，内部实现分散在子模块：

| 子模块 | 职责 |
|--------|------|
| `api.py` | 公共入口，汇总导出 |
| `core.py` | 嵌入计算 + 核心工具 |
| `render.py` | 散点渲染 + 2D/3D 绘制 |
| `geo.py` | 地球化学叠加/等时线 |
| `ternary.py` | 三元图工具 |
| `style.py` | 绘图样式 + 图例布局 + 轻量刷新 |
| `kde.py` | KDE 渲染 |
| `data.py` | 数据准备 (懒加载 ML 依赖) |
| `isochron.py` | 等时线误差配置 |
| `analysis_qt.py` | 诊断图 |
| `legend_model.py` | 图例条目数据模型 |
| `overlay_helpers.py` | 覆盖层绘制通用工具 |

### 7.2 渲染函数约束

1. 渲染函数不得直接修改 UI 控件，仅操作 `app_state` 与 matplotlib 绑定对象。
2. 所有 Matplotlib 样式设置集中在 `plotting/style.py`。
3. 渲染流程必须可重入，异常时要回滚或保持一致状态。

### 7.3 返回约定

| 函数类型 | 成功 | 失败 |
|----------|------|------|
| `plot_embedding` / `plot_2d_data` / `plot_3d_data` | `True` | `False` |
| `get_*_embedding` | `np.ndarray` | `None` |

### 7.4 渲染管线

```
用户操作 → on_slider_change() → 判断 render_mode
  → 计算/获取嵌入 (带 LRU 缓存)
  → 构建调色板 + 准备数据
  → 渲染散点 + 索引映射
  → 可选: KDE / 地球化学叠加
  → 渲染图例 + 同步 UI 面板
  → 恢复选择叠加
  → 应用样式
  → fig.canvas.draw_idle()
```

### 7.5 覆盖层渲染架构

#### 7.5.1 覆盖层类型与 Toggle 映射

所有覆盖层的开关状态通过 `OVERLAY_TOGGLE_MAP` 集中管理（定义在 `visualization/plotting/legend_model.py`）：

```python
OVERLAY_TOGGLE_MAP = {
    'model_curve': 'show_model_curves',
    'plumbotectonics_curve': 'show_plumbotectonics_curves',
    'paleoisochron': 'show_paleoisochrons',
    'model_age_line': 'show_model_age_lines',
    'isochron': 'show_isochrons',
    'growth_curve': 'show_growth_curves',
}
```

**规范**：
- 新增覆盖层类型必须在此映射中注册
- UI 层通过此映射查询开关状态，避免硬编码条件判断
- 样式键（style_key）与 `app_state.overlay.line_styles` 中的键一致

#### 7.5.2 覆盖层绘制通用工具

`visualization/plotting/overlay_helpers.py` 提供通用绘制函数，避免重复代码：

```python
from visualization.plotting.overlay_helpers import (
    draw_curve,           # 绘制单条曲线
    draw_label,           # 绘制文本标签
    compute_label_position,  # 计算标签位置
    filter_valid_points,  # 过滤 NaN/Inf
    clip_to_axes_limits,  # 裁剪到坐标轴范围
    store_overlay_artist, # 注册 artist 到 app_state
    clear_overlay_category,  # 清除某类 artist
)

# 示例：绘制模型曲线
line = draw_curve(
    ax, x_data, y_data,
    style_key='model_curve',
    line_styles=app_state.overlay.line_styles,
    label='Stacey-Kramers',
    zorder=1
)
if line:
    store_overlay_artist(
        app_state.overlay.overlay_artists,
        'model_curves',
        'stacey_kramers',
        line
    )
```

**规范**：
- 新增覆盖层绘制逻辑优先使用这些工具函数
- 避免在 `geo.py` 中重复实现样式解析、artist 注册等逻辑
- 标签定位使用 `compute_label_position()` 统一处理

#### 7.5.3 Artist 跟踪与管理

所有覆盖层 artist 存储在 `app_state.overlay.overlay_artists`，按类别分组：

```python
app_state.overlay.overlay_artists = {
    'model_curves': {
        'stacey_kramers': [line1, text1],
        'cumming_richards': [line2, text2],
    },
    'paleoisochrons': {
        '4500': [line3, text3],
        '3800': [line4, text4],
    },
    # ...
}
```

**规范**：
- 每次重绘前调用 `clear_overlay_category()` 清除旧 artist
- 绘制后立即调用 `store_overlay_artist()` 注册新 artist
- 轻量刷新时直接遍历 artist 更新属性，无需重绘

### 7.6 图例数据模型

#### 7.6.1 统一图例条目生成

图例条目通过 `visualization/plotting/legend_model.py` 统一生成，避免多处重复定义：

```python
from visualization.plotting.legend_model import (
    group_legend_items,    # 生成分组图例条目
    overlay_legend_items,  # 生成覆盖层图例条目
)

# 获取分组图例条目
group_items = group_legend_items(
    palette=app_state.current_palette,
    marker_map=app_state.group_marker_map,
    visible_groups=app_state.visible_groups,
    all_groups=all_groups
)

# 获取覆盖层图例条目
overlay_items = overlay_legend_items(
    actual_algorithm='PB_EVOL_76'
)
```

**规范**：
- `render.py` 中的图例构建使用这些函数生成数据
- `main_window.py` 中的图例面板同步使用相同数据源
- 新增覆盖层类型需在 `overlay_legend_items()` 中添加条目定义

#### 7.6.2 图例条目数据结构

```python
# 分组条目
{
    'type': 'group',
    'label': 'Group A',
    'color': '#1f77b4',
    'marker': 'o',
    'visible': True
}

# 覆盖层条目
{
    'type': 'overlay',
    'style_key': 'model_curve',
    'label_key': 'Model Curves',
    'fallback': {'color': '#64748b', 'linewidth': 1.5, ...},
    'default_color': '#64748b'
}
```

### 7.7 轻量刷新机制

#### 7.7.1 刷新路径分类

| 变更类型 | 刷新方法 | 耗时 | 触发场景 |
|----------|----------|------|----------|
| 调色板/字体/标题 | `callback()` (完整重绘) | ~100ms | 调色板切换、字体变更 |
| 覆盖层样式 | `refresh_overlay_styles()` | ~10ms | 线宽、颜色、透明度变更 |
| 覆盖层可见性 | `refresh_overlay_visibility()` | ~5ms | 覆盖层开关切换 |
| 图例位置 | `refresh_plot_style()` | ~20ms | 图例位置、列数变更 |

#### 7.7.2 轻量刷新实现

```python
# visualization/plotting/style.py

def refresh_overlay_styles():
    """就地更新覆盖层 artist 样式，无需重绘"""
    overlay_artists = app_state.overlay.overlay_artists
    line_styles = app_state.overlay.line_styles

    category_to_style = {
        'model_curves': 'model_curve',
        'paleoisochrons': 'paleoisochron',
        # ...
    }

    for category, style_key in category_to_style.items():
        if category not in overlay_artists:
            continue
        style = line_styles.get(style_key, {})
        for key, artists in overlay_artists[category].items():
            for artist in artists:
                if hasattr(artist, 'set_color'):
                    artist.set_color(style.get('color'))
                if hasattr(artist, 'set_linewidth'):
                    artist.set_linewidth(style.get('linewidth', 1.0))
                # ...

    app_state.fig.canvas.draw_idle()

def refresh_overlay_visibility():
    """切换覆盖层可见性，若需要则返回 True 触发完整重绘"""
    from visualization.plotting.legend_model import OVERLAY_TOGGLE_MAP

    overlay_artists = app_state.overlay.overlay_artists
    needs_replot = False

    for style_key, attr_name in OVERLAY_TOGGLE_MAP.items():
        enabled = getattr(app_state.overlay, attr_name, False)
        category = _style_key_to_category(style_key)

        if category in overlay_artists:
            for artists in overlay_artists[category].values():
                for artist in artists:
                    artist.set_visible(enabled)
        elif enabled:
            # 覆盖层启用但无 artist，需要重绘
            needs_replot = True

    if not needs_replot:
        app_state.fig.canvas.draw_idle()

    return needs_replot
```

**规范**：
- UI 层样式变更时优先调用轻量刷新函数
- 仅在轻量刷新无法满足时才调用 `callback()` 完整重绘
- `refresh_plot_style()` 末尾自动调用 `refresh_overlay_styles()`

---

## 8. 数据处理与数值稳定性

### 8.1 数值解析

数值列解析必须使用安全转换，禁止裸 `float()` 或 `int()`：

```python
# ✅ 正确
df[col] = pd.to_numeric(df[col], errors='coerce')

# ❌ 禁止
df[col] = df[col].astype(float)  # 非数值字符串会抛异常
```

### 8.2 缺失值策略

缺失值必须有明确策略并记录日志：

```python
# 策略 1: SimpleImputer 常量填充
from sklearn.impute import SimpleImputer
imputer = SimpleImputer(strategy='constant', fill_value=0)
X = imputer.fit_transform(X)

# 策略 2: 删除含 NaN 行 (回退方案)
mask = ~np.isnan(X).any(axis=1)
X = X[mask]
logger.warning("Dropped %d rows with NaN values", (~mask).sum())
```

### 8.3 除零保护

统一使用常量，禁止散落的魔法数字：

```python
# ✅ 正确 — 在模块顶部定义
EPSILON = 1e-50

result = numerator / (denominator + EPSILON)

# ❌ 禁止
result = numerator / (denominator + 1e-50)
```

### 8.4 列名管理

列名推断规则集中管理，禁止多处复制。对外输入必须验证并给出清晰错误提示。

---

## 9. API 边界与依赖管理

### 9.1 模块边界

1. 模块内 helper 使用 `_` 前缀且不导出。
2. 跨模块调用优先走公开 API（`__init__.py` 导出），不直接访问内部状态。

### 9.2 懒加载模式

大型依赖（sklearn / umap / seaborn / xgboost）必须懒加载。使用模块级全局变量 + 守卫函数：

```python
# 模块级全局变量
PCA = None
TSNE = None

def _lazy_import_ml():
    """懒加载 sklearn 模块"""
    global PCA, TSNE
    if PCA is None:
        from sklearn.decomposition import PCA as _PCA
        PCA = _PCA
    if TSNE is None:
        from sklearn.manifold import TSNE as _TSNE
        TSNE = _TSNE
```

对于可选依赖，使用 try/except + `_checked` 标志避免重复尝试：

```python
_geochemistry = None
_geochem_checked = False

def _lazy_import_geochemistry():
    global _geochemistry, _geochem_checked
    if _geochem_checked:
        return _geochemistry
    _geochem_checked = True
    try:
        from data import geochemistry as _mod
        _geochemistry = _mod
    except ImportError as err:
        logger.warning("Geochemistry module not available: %s", err)
        _geochemistry = None
    return _geochemistry
```

### 9.3 循环导入规避

在 `translate()` 等基础函数中，使用函数内延迟导入避免循环：

```python
def translate(text, language=None, **kwargs):
    if language is None:
        try:
            from .state import app_state  # 延迟导入避免循环
        except Exception:
            app_state = None
        # ...
```

---

## 10. 类型注解与文档

### 10.1 类型注解

1. 新增或重构的核心函数必须补充类型注解。
2. 使用 `from __future__ import annotations` 启用延迟求值。
3. 优先级：`core/` > `data/` > `visualization/` > `ui/`。

```python
from __future__ import annotations
from typing import Any, Hashable

def build_embedding_cache_key(
    app_state,
    algorithm: str,
    params: Any,
    subset_key: Hashable,
) -> tuple[Any, ...]:
    ...
```

### 10.2 Docstring 规范

使用 Google 风格 docstring：

```python
def calculate_single_stage_age(
    Pb206_204_S: np.ndarray,
    Pb207_204_S: np.ndarray,
    params: dict | None = None,
    initial_age: float | None = None,
) -> np.ndarray:
    """Holmes-Houtermans 单阶段模式年龄计算。

    Args:
        Pb206_204_S: 206Pb/204Pb 测量值数组。
        Pb207_204_S: 207Pb/204Pb 测量值数组。
        params: 模型参数字典，缺省使用当前引擎参数。
        initial_age: 初始年龄估计 (Ma)。

    Returns:
        模式年龄数组 (Ma)。

    Raises:
        ValueError: 输入数组长度不一致时抛出。
    """
```

对外 API 必须有完整 docstring（Args / Returns / Raises）。内部 helper 可使用单行 docstring。

### 10.3 文档同步

重要 UI 行为或架构变更需同步更新 `docs/` 下对应文档。

---

## 11. 错误处理与防御编程

### 11.1 异常处理层级

| 层级 | 策略 |
|------|------|
| 数据加载 (`data/`) | try/except → 日志 + 返回 `False`/`None` |
| 渲染层 (`visualization/`) | try/except → 日志 + 保持画布一致状态 |
| UI 层 (`ui/`) | try/except → 日志 + 用户提示 |
| 事件回调 | try/except → 日志 + 静默失败 |

### 11.2 安全属性访问

使用 `getattr()` 带默认值，避免 `AttributeError`：

```python
# ✅ 正确
panel = getattr(app_state, 'control_panel_ref', None)
if panel is None:
    return

# ❌ 禁止
panel = app_state.control_panel_ref  # 可能抛 AttributeError
```

### 11.3 安全回调执行

调用外部回调前检查可调用性：

```python
update_fn = getattr(panel, 'update_selection_controls', None)
if not callable(update_fn):
    return
try:
    update_fn()
except Exception as err:
    logger.warning("Unable to update selection controls: %s", err)
```

### 11.4 资源清理

确保异常路径上的资源释放：

```python
progress = None
try:
    progress = ProgressDialog(parent)
    # ... 主逻辑 ...
except Exception as e:
    logger.error("Operation failed: %s", e)
finally:
    if progress:
        try:
            progress.close()
        except Exception:
            pass
```

---

## 12. 状态管理

### 12.1 AppState 单例与状态组合

全局状态通过 `app_state` 单例访问。为避免 God Object 反模式，使用**状态组合模式**将相关字段分组到子对象：

```python
from core import app_state

# 读取基础状态
current_algo = app_state.algorithm
df = app_state.df_global

# 写入基础状态
app_state.algorithm = 'tSNE'
app_state.umap_params['n_neighbors'] = 15

# 访问组合子状态
app_state.overlay.show_model_curves = True
app_state.overlay.line_styles['model_curve']['linewidth'] = 2.0
app_state.legend.legend_position = 'upper right'
app_state.legend.legend_columns = 2
```

#### 12.1.1 状态组合子对象

| 子对象 | 模块 | 职责 |
|--------|------|------|
| `app_state.overlay` | `core/overlay_state.py` | 覆盖层开关、样式、配置、artist 跟踪 |
| `app_state.legend` | `core/legend_state.py` | 图例位置、样式、可见性、回调 |

#### 12.1.2 向后兼容的 Property 委托

为保持向后兼容，`AppState` 为所有移入子对象的字段提供 property 委托：

```python
# core/state.py
class AppState:
    def __init__(self):
        self.overlay = OverlayState()
        self.legend = LegendState()

    @property
    def show_model_curves(self):
        return self.overlay.show_model_curves

    @show_model_curves.setter
    def show_model_curves(self, value):
        self.overlay.show_model_curves = value
```

**规范**：
- 新代码优先使用 `app_state.overlay.xxx` / `app_state.legend.xxx` 访问
- 旧代码的 `app_state.xxx` 访问通过 property 透明工作
- 重构时逐步迁移到新访问方式

### 12.2 CONFIG 访问

使用 `.get()` 带默认值安全访问配置：

```python
from core import CONFIG

cache_size = CONFIG.get('embedding_cache_size', 8)
options = CONFIG['algorithm_options']  # 仅确定存在的键可直接访问
```

存储 CONFIG 值到 app_state 时使用 `.copy()` 避免意外修改：

```python
self.umap_params = CONFIG['umap_params'].copy()
```

### 12.3 嵌入缓存

缓存键包含算法、参数、数据签名与子集标识：

```python
from core.cache import build_embedding_cache_key

key = build_embedding_cache_key(app_state, algorithm, params, subset_key)
cached = app_state.embedding_cache.get(key)
if cached is not None:
    return cached
```

### 12.4 会话持久化

会话数据存储在 `~/.isotopes_analysis/params.json`，包含版本号用于迁移：

```python
session_data = {
    'session_version': CONFIG.get('session_version', 1),
    'algorithm': algorithm,
    'umap_params': umap_params,
    # ...
}
```

新增会话字段必须在 `core/session.py` 的 `_migrate_session_data()` 中处理向后兼容。

### 12.5 观察者模式

语言切换等全局事件使用监听器模式：

```python
# 注册
app_state.register_language_listener(self._refresh_language)

# 通知 (内部安全迭代，异常不中断)
app_state.notify_language_change()
```

---

## 13. 测试与回归

### 13.1 测试策略

| 类型 | 适用范围 | 工具 |
|------|----------|------|
| 单元测试 | 算法逻辑、数据处理、缓存 | pytest |
| 集成测试 | UI 交互、渲染管线 | pytest + PyQt5 |
| 验收清单 | 复杂 UI 流程 | 手动检查 |

### 13.2 测试目录结构

```
tests/
├── test_geochemistry.py    # 年龄计算、Delta、V1V2
├── test_cache.py           # 嵌入缓存
├── test_session.py         # 会话持久化
├── test_localization.py    # 翻译系统
├── test_endmember.py       # 端元识别
├── test_mixing.py          # 混合模型
└── test_provenance_ml.py   # ML 管线
```

### 13.3 测试规则

1. 修复 bug 必须提供回归测试或最小复现步骤。
2. 算法逻辑优先单元测试，UI 逻辑优先集成测试或验收清单。
3. 关键重构需提供性能与行为一致性说明。

---

## 14. 配置与演进

### 14.1 配置集中管理

可配置项集中于 `core/config.py`：

```python
CONFIG = {
    'algorithm_options': ['UMAP', 'tSNE', 'PCA', 'RobustPCA', 'V1V2'],
    'umap_params': {'n_neighbors': 10, 'min_dist': 0.1, ...},
    'embedding_cache_size': 8,
    'session_version': 2,
    # ...
}
```

### 14.2 新增配置要求

1. 必须提供默认值。
2. 必须在 `docs/` 中说明用途与取值范围。
3. 用户可覆盖的配置通过 `~/.isotopes_analysis/config.json` 管理。

### 14.3 兼容性管理

1. 兼容性 shim 必须显式标注，并在 **2 个版本内**移除。
2. 废弃函数使用注释标记：

```python
# DEPRECATED: 使用 calculate_two_stage_age() 替代，将在 v0.4 移除
def calculate_model_age(Pb206_204_S, Pb207_204_S, two_stage=False):
    ...
```

---

## 15. Git 与版本控制

### 15.1 分支模型

| 分支 | 用途 |
|------|------|
| `master` | 稳定发布分支 |
| `dev` | 日常开发分支 |
| `feature/*` | 功能开发分支 |
| `fix/*` | Bug 修复分支 |

### 15.2 提交信息格式

使用语义化前缀：

```
feat: 添加三元图拉伸模式支持
fix: 修复等时线误差列类型转换异常
refactor: 拆分 plotting 子包并规范命名
docs: 更新 visualization 模块文档
style: 统一日志前缀格式
perf: 优化嵌入缓存键计算
test: 添加地球化学年龄计算单元测试
chore: 更新依赖版本
```

### 15.3 敏感文件

以下文件禁止提交：
- `.env`、`credentials.json` 等凭证文件
- `*.log` 日志文件
- `dist/`、`build/` 构建产物
- `__pycache__/`、`*.pyc` 缓存文件

---

## 16. 变更流程

### 16.1 变更前准备

修改任何模块代码之前，必须先完成以下步骤：

1. 阅读 `docs/` 下与目标模块对应的文档（`architecture.md`、`visualization.md`、`ui.md`、`data.md`、`utils.md`），理解现有架构与约定。
2. 阅读 `docs/dev_conventions.md`（本文件），确认变更符合开发规范。
3. 阅读 `docs/development_plan.md`，了解当前改进计划与已知问题，避免重复工作或与规划冲突。

### 16.2 变更计划记录

非 trivial 的变更（新功能、重构、Bug 修复）在动手编码前，必须将开发计划写入 `docs/development_plan.md` 对应模块章节，包括：

- 问题描述与现状
- 预期方案或目标结构
- 涉及的文件与影响范围

完成后将状态标记为 ✅ 已完成。

### 16.3 文档同步

变更完成后，同步更新 `docs/` 下受影响的文档，确保文档与代码一致。

---

## 17. 构建与发布

### 17.1 开发环境

```bash
# 安装依赖 (推荐 uv)
uv pip install -e .

# 或使用 pip
pip install -e .
```

### 17.2 构建可执行文件

```bash
pyinstaller build.spec
# 输出: dist/IsotopesAnalyse/
```

### 17.3 构建注意事项

1. `build.spec` 中必须声明所有隐式依赖 (`hiddenimports`)。
2. `locales/` 目录必须包含在数据文件中。
3. 新增大型依赖需同步更新 `build.spec`。

---

## 18. 架构演进记录

### 18.1 图例与覆盖层可视化重构 (2026-02)

**背景**：原 `app_state` 包含 330+ 字段，图例和覆盖层状态散落其中；`geo.py` 中 10+ 个 `_draw_*` 函数重复实现样式解析、artist 注册、标签定位逻辑；图例条目在 `render.py`、`main_window.py`、`legend_model.py` 三处定义；样式变更触发全量重绘（含 embedding 重算）。

**目标**：状态内聚、消除重复、轻量刷新。

#### 18.1.1 Phase 1: 状态组合

**新增文件**：
- `core/overlay_state.py` — 封装 40+ 覆盖层相关字段
- `core/legend_state.py` — 封装 10+ 图例相关字段

**修改文件**：
- `core/state.py` — 创建 `self.overlay` 和 `self.legend` 子对象，添加 property 委托实现向后兼容

**效果**：
- `app_state` 字段按职责分组，避免 God Object
- 旧代码通过 property 透明访问，无需修改
- 新代码优先使用 `app_state.overlay.xxx` / `app_state.legend.xxx`

#### 18.1.2 Phase 2: 统一图例数据源

**修改文件**：
- `visualization/plotting/legend_model.py` — 新增 `OVERLAY_TOGGLE_MAP`、`overlay_legend_items()`
- `visualization/plotting/render.py` — 提取 `_place_inline_legend()` 辅助函数，消除三处重复图例构建代码
- `ui/main_window.py` — 使用 `OVERLAY_TOGGLE_MAP` 统一覆盖层开关查询

**效果**：
- 图例条目定义集中在 `legend_model.py`
- 消除 200+ 行重复代码
- UI 层与渲染层使用相同数据源

#### 18.1.3 Phase 3: 覆盖层绘制工具

**新增文件**：
- `visualization/plotting/overlay_helpers.py` — 提供 `draw_curve()`、`draw_label()`、`compute_label_position()` 等通用函数

**效果**：
- `geo.py` 中的 `_draw_*` 函数复用通用工具，代码量减半
- 标签定位、样式解析、artist 注册逻辑统一
- 新增覆盖层类型更容易实现

#### 18.1.4 Phase 4: 轻量刷新机制

**修改文件**：
- `visualization/plotting/style.py` — 新增 `refresh_overlay_styles()`、`refresh_overlay_visibility()`
- `ui/main_window.py` — 覆盖层开关切换优先使用轻量刷新
- `ui/panels/base_panel.py` — 覆盖层样式变更调用 `refresh_overlay_styles()`

**效果**：
- 样式变更耗时从 ~100ms 降至 ~10ms
- 覆盖层开关切换无闪烁
- 图例位置调整无需重绘散点

#### 18.1.5 关键设计决策

1. **向后兼容优先**：使用 property 委托而非直接重命名字段，避免破坏现有代码
2. **渐进式重构**：分 4 个阶段，每阶段结束后应用可正常运行
3. **数据驱动**：图例条目、覆盖层映射通过数据结构定义，减少硬编码
4. **性能优化**：区分完整重绘与轻量刷新路径，避免不必要的计算

#### 18.1.6 文件变更汇总

| 阶段 | 新增 | 修改 |
|------|------|------|
| P1 | `core/overlay_state.py`, `core/legend_state.py` | `core/state.py` |
| P2 | — | `visualization/plotting/legend_model.py`, `render.py`, `ui/main_window.py` |
| P3 | `visualization/plotting/overlay_helpers.py` | `visualization/plotting/geo.py` |
| P4 | — | `visualization/plotting/style.py`, `ui/main_window.py`, `ui/panels/base_panel.py` |

#### 18.1.7 后续改进方向

- 将 `geo.py` 中的 `_draw_*` 函数进一步重构为数据驱动模式
- 考虑将覆盖层配置（年龄范围、步长等）移入独立配置文件
- 为覆盖层添加交互式编辑功能（拖拽标签、调整曲线参数）
