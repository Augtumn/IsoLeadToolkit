# 开发规划

本文件汇总项目级改进计划与各模块改进建议，作为统一的开发规划入口。

---

## 全局改进计划

### 第一优先级: 代码结构

#### 1.1 拆分 control_panel.py (5,700 行) — ✅ 已完成

**现状:** 单个文件包含 6 个标签页的全部逻辑，100+ 方法。

**目标结构:**
```
ui/
├── control_panel.py          # 组装逻辑 + create_section_dialog()
├── panels/
│   ├── __init__.py
│   ├── data_panel.py         # 数据标签页
│   ├── display_panel.py      # 显示标签页
│   ├── analysis_panel.py     # 分析标签页
│   ├── export_panel.py       # 导出标签页
│   ├── legend_panel.py       # 图例标签页
│   └── geo_panel.py          # 地球化学标签页
```

**已完成内容:**
- 每个 `_build_xxx_section()` 拆分为独立面板类
- 相关 `_on_xxx_change()` 方法迁移到对应面板
- `control_panel.py` 仅保留组装与 `create_section_dialog()`
- `_on_style_change()` 下沉至 `BasePanel` (跨面板共享)

#### 1.2 拆分 plotting 子包并规范命名 — ✅ 已完成

**现状:** 两个文件有大量重复代码和循环导入风险。

**调整结果:**
```
visualization/
├── plotting/            # plotting 子包
│   ├── __init__.py       # 汇总导出
│   ├── api.py            # 渲染入口（汇总导出）
│   ├── core.py           # 嵌入计算 + 核心工具
│   ├── render.py         # 嵌入渲染 + 2D/3D 绘制
│   ├── geo.py            # 地球化学叠加/等时线
│   ├── ternary.py        # 三元图工具
│   ├── style.py          # 绘图样式 + 图例布局
│   ├── kde.py            # KDE 渲染
│   ├── data.py           # 数据准备
│   ├── isochron.py       # 等时线误差共享工具
│   └── analysis_qt.py    # 诊断图
```

#### 1.3 拆分 geochemistry.py (1,369 行)

**目标结构:**
```
data/
├── geochemistry/
│   ├── __init__.py       # 导出公共 API
│   ├── engine.py         # GeochemistryEngine + 预设模型
│   ├── age.py            # 年龄计算
│   ├── delta.py          # Delta + V1V2
│   ├── source.py         # 源区参数反演
│   └── isochron.py       # 等时线工具
```

**调整结果:**
```
data/
├── geochemistry/
│   ├── __init__.py       # 公共 API + 兼容导出
│   ├── engine.py         # 常量 + GeochemistryEngine + modelcurve
│   ├── age.py            # 模式年龄/求解器
│   ├── delta.py          # Delta + V1V2
│   ├── source.py         # 源区参数/初始比值
│   └── isochron.py       # 等时线/回归工具
└── geochemistry.py       # 兼容 shim (旧导入保留)
```

---

### 第二优先级: 功能改进

#### 2.1 后台计算 + 进度指示

**现状:** UMAP/t-SNE 在大数据集上阻塞 UI。

**方案:**
```python
class EmbeddingWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(np.ndarray)

    def run(self):
        # 在后台线程计算嵌入
        result = get_umap_embedding(self.params)
        self.finished.emit(result)
```

#### 2.2 ML 管线增强

- 添加交叉验证 (cross_val_score)
- XGBoost tree_method 改为 `'hist'`
- 支持 per-label 阈值
- 添加训练/测试集划分报告

#### 2.3 语言切换优化

**现状:** `_rebuild_ui()` 销毁并重建所有控件。

**方案:** 改为遍历控件树，仅更新文本:
```python
def _update_translations(self):
    for group_box in self.findChildren(QGroupBox):
        key = group_box.property('translate_key')
        if key:
            group_box.setTitle(translate(key))
```

---

### 第三优先级: 代码质量

#### 3.1 消除重复代码

| 重复项 | 位置 | 处理 |
|--------|------|------|
| `_resolve_isochron_errors()` | plotting/geo.py + events.py | 提取到 visualization/plotting/isochron.py |
| `_build_marker_icon()` | main_window.py + control_panel.py | 提取到 utils/icons.py |
| 图例布局逻辑 | plotting/api.py + plotting/style.py | 统一到 plotting/style.py |

#### 3.2 国际化完善

- events.py 中硬编码中文字符串改用 `translate()`
- 统一 geochemistry/ 中的中英文注释

#### 3.3 类型注解

为核心模块添加类型注解:
```python
# 优先级: core/ > data/ > visualization/ > ui/
def calculate_single_stage_age(
    Pb206_204_S: np.ndarray,
    Pb207_204_S: np.ndarray,
    params: dict | None = None,
    initial_age: float | None = None
) -> np.ndarray: ...
```

#### 3.4 AppState 拆分

```python
class AppState:
    def __init__(self):
        self.data = DataState()           # df_global, data_cols, group_cols
        self.algorithm = AlgorithmState() # algorithm, params, cache
        self.visual = VisualState()       # fig, ax, scatter_collections
        self.geochem = GeochemState()     # model, line_styles, paleoisochrons
        self.style = StyleState()         # colors, fonts, grid, ticks
        self.interaction = InteractionState()  # selection, tooltip
```

---

### 第四优先级: 基础设施

#### 4.1 单元测试

```
tests/
├── test_geochemistry.py    # 年龄计算、Delta、V1V2
├── test_cache.py           # 嵌入缓存
├── test_session.py         # 会话持久化
├── test_localization.py    # 翻译系统
├── test_endmember.py       # 端元识别
├── test_mixing.py          # 混合模型
├── test_provenance_ml.py   # ML 管线
```

#### 4.2 配置外部化

支持用户配置文件 `~/.isotopes_analysis/config.json`:
```json
{
  "default_language": "zh",
  "figure_dpi": 150,
  "embedding_cache_size": 16,
  "xgboost_tree_method": "hist"
}
```

#### 4.3 日志改进

- 添加模块名和行号到日志格式 ✅ 已完成
- LoggerWriter 添加 `fileno()` 支持 faulthandler ✅ 已完成
- 统一日志级别使用 (移除字符串前缀 `[INFO]`) ✅ 已完成 (ui/ + visualization/ + main.py + data/loader.py + core/session.py 全模块)
- 日志级别可通过环境变量 `ISOTOPES_LOG_LEVEL` 配置 ✅ 已完成

#### 4.4 Qt 调试与图例拖拽稳定性（2026-02）— ✅ 已完成

**问题描述：**
- 外部图例拖拽后出现条目重叠/“消失”
- 双击置顶或拖拽在 Windows 下触发 `access violation`
- 崩溃前缺少 Qt 框架级上下文日志

**方案与变更：**
- `main.py`：新增 `--qt-debug` 启动参数，统一开启 Qt 详细日志
- `ui/app.py`：增强 `qInstallMessageHandler`，输出 `[QT][级别][category]` 诊断信息
- `ui/main_window.py`：
  - 拖拽项改为插入模式 (`setDragDropOverwriteMode(False)`)
  - 图例项关闭 `ItemIsDropEnabled`，避免覆盖式 drop
  - 双击置顶改为“更新顺序状态 + 重建列表”，不直接搬运旧 item/widget 指针
  - `rowsMoved` 后延迟重建，规避 Qt 对象生命周期不稳定窗口

**结果：**
- 解决闪退与条目消失问题
- 图例拖拽吸附到上/下插入位，行为稳定

---

## 模块改进建议

### data/ 模块

#### 高优先级

1. **provenance_ml.py 缺少交叉验证** — 无训练/测试集划分，无 CV 指标。应添加 `cross_val_score` 或至少 train/test split 报告。
2. **XGBoost tree_method='exact'** — 大数据集上很慢，应改为 `'hist'`。

#### 中优先级

3. **列名规范化** — 当前不再做中文列名映射，需要时可在导入配置或上游数据中完成规范化。
4. **GeochemistryEngine 全局单例** — 多线程不安全。当前单线程无问题，但若引入后台计算需加锁。
5. **数值稳定性** — 多处使用 `1e-50` 作为除零保护，应统一为常量并考虑使用 `np.errstate`。
6. **mixing.py 无误差传播** — 输入不确定度未传递到混合权重。

#### 低优先级

7. **中英文注释混杂** — geochemistry/ 中中文注释和英文 docstring 混用，建议统一。
8. **向后兼容别名** — `calculate_delta_values`, `calculate_v1v2`, `calculate_model_age` 等别名函数可在下个大版本移除。
9. **endmember.py 硬编码阈值** — tolerance, clamp, PC1 方差阈值 (95%) 应可配置。

---

### visualization/ 模块

#### 规范修复

1. **docstring/导入顺序不规范** — 多处文件 docstring 不在第一行，`logger` 定义早于 docstring。✅ 已完成
2. **日志前缀残留** — 仍使用 `[INFO]`/`[WARN]`/`[ERROR]` 字符串前缀，需统一为 logging 级别。✅ 已完成
3. **core 导入入口不统一** — 混用 `core.state` 与 `core.localization`，需统一 `from core import translate, app_state`。✅ 已完成
4. **诊断图国际化缺失** — `analysis_qt.py` 中窗口标题与提示文本未走 `translate()`。✅ 已完成
5. **API 暴露过多** — `plotting/api.py` 导出私有 helper，需收敛 `__all__`。✅ 已完成
6. **顶层副作用** — `plotting/geo.py` 与 `plotting/render.py` 顶层导入并记录日志，需改为惰性加载。✅ 已完成

#### 新增功能

1. **Plumbotectonics 演化曲线模式** — 新增 `PLUMBOTECTONICS_76/86` 渲染模式，支持模型切换与同年龄连线等时线，数据内置至 `data/plumbotectonics_data.py`。✅ 已完成

#### 规范审查发现

**高优先级:**

1. **`eval()` 安全风险** — 使用 AST 安全解析器替代 `eval()`，仅允许算术运算和白名单 numpy 函数。✅ 已完成
   - 变更: `visualization/plotting/geo.py` — 新增 `_safe_eval_expression()` 函数

2. **`_lazy_import_geochemistry()` 重复** — 提取到 `plotting/data.py` 统一管理，`render.py` 和 `geo.py` 改为从 `data.py` 导入。✅ 已完成
   - 变更: `visualization/plotting/data.py`, `render.py`, `geo.py`

3. **`api.py` 导入私有符号** — facade 层仅导入公共符号，私有函数由内部模块直接互相引用。✅ 已完成
   - 变更: `visualization/plotting/api.py`

4. **`print()` 代替 `logger`** — 替换为 `logger.debug()` / `logger.error()`。✅ 已完成
   - 变更: `visualization/plotting/render.py`

**中优先级:**

5. **裸 `except:` (无异常类型)** — 全部改为 `except Exception:`。✅ 已完成
   - 变更: `visualization/events.py` (4 处)

6. **`astype(float)` 代替 `pd.to_numeric`** — 改为 `pd.to_numeric(..., errors='coerce')`。✅ 已完成
   - 变更: `visualization/plotting/data.py`, `plotting/geo.py`, `events.py`

7. **日志 f-string 替代 `%s` 占位符** — 全模块已修复 (`events.py`, `core.py`, `geo.py`, `kde.py`, `ternary.py`, `data.py`)。✅ 已完成
   - 变更: `visualization/events.py`, `plotting/core.py`, `plotting/geo.py`, `plotting/kde.py`, `plotting/ternary.py`, `plotting/data.py`

8. **日志前缀残留** — `[OK]` 前缀已移除。✅ 已完成
   - 变更: `visualization/events.py`

9. **`on_slider_change()` 过长 (227 行)** — 拆分为 `_resolve_group_col()`、`_sync_visible_groups()`、`_validate_render_columns()`、`_sync_render_mode()`、`_dispatch_render()`、`_handle_render_fallback()` 等子函数。✅ 已完成
   - 变更: `visualization/events.py`

10. **`style_manager.py` 缺少 logger 且导入顺序不规范** — 添加 logger，导入顺序按标准库 → 第三方 → 本项目分段。✅ 已完成
    - 变更: `visualization/style_manager.py`

**低优先级:**

11. **魔法数字散落** — 图例 bbox 偏移、除零保护、选择阈值、悬停距离、KDE 采样上限均已提取为命名常量。✅ 已完成
    - 变更: `plotting/style.py`, `plotting/geo.py`, `events.py`, `plotting/kde.py`

12. **`ternary.py` 函数内重复导入** — 移除函数内重复的 `import numpy` 和 `from scipy.stats import gmean`。✅ 已完成
    - 变更: `visualization/plotting/ternary.py`

13. **`plotting/__init__.py` 星号导入** — 改为显式导入并声明 `__all__`。✅ 已完成
    - 变更: `visualization/plotting/__init__.py`

14. **类型注解缺失** — 为所有公共函数添加类型注解 (`get_*_embedding`, `get_embedding`, `plot_embedding`, `plot_umap`, `plot_2d_data`, `plot_3d_data`, `on_hover`, `on_click`, `on_legend_click`, `on_slider_change`, `draw_confidence_ellipse`, `refresh_selection_overlay`, `calculate_selected_isochron`, `toggle_selection_mode`, `sync_selection_tools`, `resolve_line_style`, `refresh_plot_style`, `calculate_auto_ternary_factors`)。添加 `from __future__ import annotations`。✅ 已完成
    - 变更: `plotting/core.py`, `plotting/render.py`, `plotting/style.py`, `plotting/ternary.py`, `events.py`, `line_styles.py`

#### 既有问题

1. **plot_embedding() 过长 (~757 行)** — 应拆分为子函数:
   - `_render_scatter_groups()` — 散点渲染
   - `_render_kde_overlay()` — KDE 叠加
   - `_render_geo_overlays()` — 地球化学叠加
   - `_render_legend()` — 图例
   - `_render_title_labels()` — 标题和标签

2. **无进度指示** — UMAP/t-SNE 在大数据集 (10k+) 上可能耗时数分钟，UI 冻结。应添加进度条或后台线程。
3. **诊断图无导出功能** — scree plot, loadings 等无法保存为图片。应添加 "另存为" 按钮。
4. **scatter_collections 全量迭代** — `refresh_plot_style()` 遍历所有散点集合，即使只有一个变更。
5. **单元测试缺失** — 复杂的渲染逻辑无测试覆盖，重构风险高。
6. **等时线工具仅支持 206-207** — 应扩展 `calculate_selected_isochron()` 支持 206-208 模式。

---

### ui/ 模块

#### 规范修复

1. **docstring/导入顺序不规范** — `app.py`, `main_window.py`, `control_panel.py`, `sheet_dialog.py`, `endmember_dialog.py`, `mixing_dialog.py` 中 logger 定义早于 docstring，导入顺序不规范。✅ 已完成
2. **日志前缀残留** — `app.py`, `main_window.py`, `analysis_panel.py`, `data_panel.py`, `display_panel.py`, `export_panel.py`, `geo_panel.py`, `legend_panel.py`, `sheet_dialog.py`, `endmember_dialog.py`, `mixing_dialog.py`, `provenance_ml_dialog.py` 中约 50 处 `[INFO]`/`[WARN]`/`[ERROR]`/`[DEBUG]` 前缀及 f-string 日志，已统一为 `%s` 占位符。✅ 已完成
3. **core 导入入口不统一** — `data_import_dialog.py`, `file_dialog.py`, `data_config.py`, `three_d_dialog.py`, `two_d_dialog.py`, `ternary_dialog.py`, `isochron_dialog.py`, `sheet_dialog.py`, `progress_dialog.py`, `control_panel.py` 中混用 `core.localization` 与 `core.state`，已统一为 `from core import ...`。✅ 已完成

#### 高优先级

1. **语言切换重建整个 UI** — `BasePanel` 新增 `_update_translations()` 方法，通过 `translate_key` 属性就地刷新控件文本；`create_section_dialog()` 语言切换时优先使用轻量级更新，失败时回退到完整重建。全部 6 个面板已标记 `translate_key`。✅ 已完成
   - 变更: `panels/base_panel.py` — 新增 `_update_translations()`
   - 变更: `panels/data_panel.py`, `display_panel.py`, `analysis_panel.py`, `export_panel.py`, `legend_panel.py`, `geo_panel.py` — 所有静态 QGroupBox/QPushButton/QCheckBox 添加 `translate_key` 属性
   - 变更: `control_panel.py` — `_try_lightweight_update()` 优先于 `_rebuild_section()`
2. **标记图标渲染重复** — `main_window.py` 和 `legend_panel.py` 各有一份 `_build_marker_icon()`，已提取到 `utils/icons.py`。✅ 已完成
   - 变更: 新增 `utils/icons.py`，`main_window.py` 和 `legend_panel.py` 改为调用 `build_marker_icon()`

#### 中优先级

3. **对话框缓存无失效** — `_section_dialogs` 缓存对话框实例，语言切换后已缓存对话框现在会在重新打开时检测语言变化并自动重建。✅ 已完成
   - 变更: `control_panel.py` — `_on_show()` 重新注册语言监听器并检测关闭期间的语言变化
4. **控制面板禁用但代码仍在** — `Qt5ControlPanel` 已添加 deprecation 标记，明确标注将在下个大版本移除。✅ 已完成
   - 变更: `control_panel.py` — 类 docstring 添加 `.. deprecated::` 说明
5. **滑块防抖** — 已在 `BasePanel` 添加通用 `_debounce(key, func, delay_ms)` 方法，支持任意回调防抖。✅ 已完成
   - 变更: `panels/base_panel.py` — 新增 `_debounce()` 和 `_fire_debounced()`

#### 低优先级

6. **对话框验证不一致** — `tooltip_dialog.py` 已添加 `_ok_clicked()` 验证（至少选择一列）。✅ 已完成
   - 变更: `dialogs/tooltip_dialog.py`，`locales/zh.json`，`locales/en.json`
7. **无键盘快捷键** — 菜单操作已绑定快捷键。✅ 已完成
   - Ctrl+D (数据), Ctrl+Shift+D (显示), Ctrl+Shift+A (分析), Ctrl+E (导出), Ctrl+L (图例), Ctrl+G (地球化学)
   - 变更: `main_window.py`

---

### utils/ 模块

#### 中优先级

1. **日志格式增强** — 添加模块名和行号: ✅ 已完成
   ```python
   formatter = logging.Formatter('%(asctime)s [%(name)s:%(lineno)d] %(message)s')
   ```
2. **LoggerWriter 添加 fileno()** — 返回原始流的 fileno，使 faulthandler 可用: ✅ 已完成
   ```python
   def fileno(self):
       return self.original_stream.fileno()
   ```
3. **移除 utils/line_styles.py** — 功能已迁移到 visualization/line_styles.py，此文件仅 4 行且无引用。✅ 已完成

#### 低优先级

4. **结构化日志** — 当前使用字符串前缀 `[INFO]`, `[WARN]`, `[ERROR]`。应直接使用 logging 级别: ✅ 已完成 (main.py, data/loader.py, core/session.py)
   ```python
   logger.info("Message")      # 而非 logger.info("[INFO] Message")
   logger.warning("Message")   # 而非 logger.info("[WARN] Message")
   ```
5. **日志级别可配置** — 支持通过环境变量 `ISOTOPES_LOG_LEVEL` 调整日志级别 (默认 DEBUG)。✅ 已完成

---

### geochemistry/ 模块

#### 已完成

1. **源区反演函数统一** — 提取 `_invert_mu`, `_invert_omega`, `_invert_kappa` 三个核心函数，公共 API 改为薄委托层。✅ 已完成
   - 变更: `data/geochemistry/source.py`

2. **自动匹配单/双阶段算法** — `calculate_all_parameters()` 根据 `resolve_age_model()` 自动选择参考参数 (单阶段→CDT, 两阶段→模型参考)。✅ 已完成
   - 变更: `data/geochemistry/__init__.py`

3. **初始比值函数复用** — `calculate_initial_ratio_64/74/84` 改为调用 `calculate_model_mu/kappa`，消除内联重复。✅ 已完成
   - 变更: `data/geochemistry/source.py`

4. **PB_EVOL_86 等时线支持** — 添加 ISOCHRON2 模式，支持 208/206 等时线拟合、年龄计算 (需 207/206 辅助)、κ 生长曲线。✅ 已完成
   - 变更: `visualization/plotting/geo.py`

5. **等时线标签 age=0 bug 修复** — `_build_isochron_label()` 改为显式 None 检查，支持 age=0 显示。✅ 已完成
   - 变更: `visualization/plotting/geo.py`

6. **模式年龄解析提取** — 新增 `_resolve_model_age()` 辅助函数，统一 206-207 和 206-208 模式年龄构造线的年龄解析逻辑。✅ 已完成
   - 变更: `visualization/plotting/geo.py`

7. **确定性随机采样** — 模式年龄构造线采样改用 `RandomState(42)`，确保结果可复现。✅ 已完成
   - 变更: `visualization/plotting/geo.py`

8. **古等时线失败日志** — `calculate_paleoisochron_line()` 返回 None 时记录 debug 日志。✅ 已完成
   - 变更: `visualization/plotting/geo.py`

9. **x_min 硬编码移除** — 古等时线 x 范围不再强制从 0 开始，改为使用实际 xlim。✅ 已完成
   - 变更: `visualization/plotting/geo.py`

10. **详细计算文档** — 新增 `docs/geochemistry.md`，包含 15 章节的完整公式推导、物理常数、预设模型、数值实现细节。✅ 已完成
    - 变更: `docs/geochemistry.md`
