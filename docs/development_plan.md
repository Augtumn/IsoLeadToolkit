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

- 添加模块名和行号到日志格式
- LoggerWriter 添加 `fileno()` 支持 faulthandler
- 统一日志级别使用 (移除字符串前缀 `[INFO]`)

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

7. **日志 f-string 替代 `%s` 占位符** — `events.py` 全文件已修复。`core.py` 和 `geo.py` 待修复。
   - 变更: `visualization/events.py` ✅ 已完成
   - 待修复: `visualization/plotting/core.py`, `visualization/plotting/geo.py`

8. **日志前缀残留** — `[OK]` 前缀已移除。✅ 已完成
   - 变更: `visualization/events.py`

9. **`on_slider_change()` 过长 (227 行)** — 应拆分为 `_validate_render_columns()`、`_dispatch_render()`、`_handle_render_fallback()` 等子函数。
   - 位置: `visualization/events.py:810-1037`

10. **`style_manager.py` 缺少 logger 且导入顺序不规范** — 添加 logger，导入顺序按标准库 → 第三方 → 本项目分段。✅ 已完成
    - 变更: `visualization/style_manager.py`

**低优先级:**

11. **魔法数字散落** — 图例 bbox 偏移、除零保护、选择阈值、悬停距离已提取为命名常量。KDE 采样上限 (`5000`) 待处理。
    - 变更: `plotting/style.py`, `plotting/geo.py`, `events.py` ✅ 已完成
    - 待修复: `plotting/kde.py:43` (`max_points=5000`)

12. **`ternary.py` 函数内重复导入** — 移除函数内重复的 `import numpy` 和 `from scipy.stats import gmean`。✅ 已完成
    - 变更: `visualization/plotting/ternary.py`

13. **`plotting/__init__.py` 星号导入** — 改为显式导入并声明 `__all__`。✅ 已完成
    - 变更: `visualization/plotting/__init__.py`

14. **类型注解缺失** — 所有公共函数缺少类型注解 (`get_*_embedding`, `plot_embedding`, `on_hover`, `draw_confidence_ellipse`, `resolve_line_style` 等)。
    - 位置: 全模块

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

#### 高优先级

1. **语言切换重建整个 UI** — `_rebuild_ui()` 仍会销毁并重建控件，可改为仅更新文本 (`setText`/`setTitle`)，保留控件状态。
2. **标记图标渲染重复** — `main_window.py` 和 `control_panel.py` 各有一份 `_build_marker_icon()`，应提取到 `utils/icons.py`。

#### 中优先级

3. **对话框缓存无失效** — `_section_dialogs` 缓存对话框实例，但语言切换后不会更新已缓存对话框的文本。
4. **控制面板禁用但代码仍在** — `app.py` 中 `_setup_control_panel()` 直接设为 None，但 control_panel.py 仍有完整的嵌入面板逻辑。应清理或明确标记。
5. **滑块防抖** — 使用 QTimer 实现，但每个滑块创建独立 timer。可改用统一的防抖装饰器。

#### 低优先级

6. **对话框验证不一致** — 部分对话框在 `_ok_clicked()` 中验证，部分无验证。应统一模式。
7. **无键盘快捷键** — 菜单操作无快捷键绑定。

---

### utils/ 模块

#### 中优先级

1. **日志格式增强** — 添加模块名和行号:
   ```python
   formatter = logging.Formatter('%(asctime)s [%(name)s:%(lineno)d] %(message)s')
   ```
2. **LoggerWriter 添加 fileno()** — 返回原始流的 fileno，使 faulthandler 可用:
   ```python
   def fileno(self):
       return self.original_stream.fileno()
   ```
3. **移除 utils/line_styles.py** — 功能已迁移到 visualization/line_styles.py，此文件仅 4 行且无引用。

#### 低优先级

4. **结构化日志** — 当前使用字符串前缀 `[INFO]`, `[WARN]`, `[ERROR]`。应直接使用 logging 级别:
   ```python
   logger.info("Message")      # 而非 logger.info("[INFO] Message")
   logger.warning("Message")   # 而非 logger.info("[WARN] Message")
   ```
5. **日志级别可配置** — 当前硬编码 DEBUG 级别，应支持通过环境变量或配置文件调整。
