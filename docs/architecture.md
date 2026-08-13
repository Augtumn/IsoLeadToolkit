# 项目架构总览

## 项目概况

**Isotopes Analyse** — 基于 PyQt5 的铅同位素地球化学数据分析与可视化桌面应用。

| 指标 | 数值 |
|------|------|
| Python 代码总量 | ~38,700 行 |
| 模块数 | 9 个主目录（core/data/ui/visualization/application/plugins/utils/scripts/tests） |
| Python 文件数 | 279 个 |
| 对话框数 | 15+ 个 |
| 支持算法 | UMAP, t-SNE, PCA, RobustPCA, V1V2 |
| 图类型 | 8+ 种 |
| 语言支持 | 中文/英文（1084 键） |

---

## 架构总览

```
┌─────────────────────────────────────────────────────────┐
│                      main.py (入口)                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  core/   │  │     ui/      │  │  visualization/   │  │
│  │          │  │              │  │                   │  │
│  │ state    │←─│ app          │──│ plotting/         │  │
│  │ config   │  │ main_window  │  │  api             │  │
│  │ session  │  │ control_panel│  │  core            │  │
│  │ locale   │  │ dialogs/     │  │  render          │  │
│  │ cache    │  │  (11 个)     │  │  geo             │  │
│  │          │  │ icons.py     │  │  ternary          │  │
│  └──────────┘  └──────────────┘  │                   │  │
│       ↑                          │ events            │  │
│       │        ┌──────────┐      │ style            │  │
│       └────────│  data/   │──────│ style_manager     │  │
│                │          │      │ kde              │  │
│                │          │      │ analysis_qt      │  │
│                │          │      │ data             │  │
│                │          │      │ isochron         │  │
│                │          │      │ line_styles       │  │
│                │          │      └───────────────────┘  │
│                │ loader   │                             │
│                │ geochem  │      ┌───────────────────┐  │
│                │ endmember│      │     utils/        │  │
│                │ prov_ml  │      │ logger            │  │
│                │ mixing   │      └───────────────────┘  │
│                └──────────┘                             │
└─────────────────────────────────────────────────────────┘
```

### 数据流

```
Excel/CSV 文件
  → data/loader.py (加载 + 列类型检测)
  → core/state/ (app_state.df_global，经 StateStore/Gateway)
  → visualization/plotting/ (嵌入计算 + 渲染)
  → matplotlib Figure (app_state.fig / app_state.ax)
  → ui/main_window.py (画布显示)
  → visualization/events.py (交互)
  → core/session/ (会话保存)
```

### 设计模式

| 模式 | 应用位置 |
|------|----------|
| 单例 | AppState, GeochemistryEngine, StyleManager |
| 观察者 | 语言变更监听器 |
| 懒加载 | sklearn, umap-learn, seaborn, xgboost |
| LRU 缓存 | 嵌入计算缓存 |
| 调度器 | plot_embedding() 根据 algorithm 分发 |
| 回调 | control_panel → on_slider_change → 重绘 |

---

## 各模块文档索引

| 模块 | 文档路径 | 行数（2026-08 实测） | 备注 |
|------|----------|------|------|
| core/ | [docs/core.md](core.md) | 4,807 | 含 state/ 子包（store 681, gateway 855, app_state 868, _normalizers 545, _views 326, _compat_builders 332, _dispatch_handlers 800, bootstrap 等） |
| data/ | [docs/data.md](data.md) | 1,731 | 地球化学逻辑已迁入 plugins/builtins/*_plugin.py |
| ui/ | [docs/ui.md](ui.md) | 13,209 | 85 文件 |
| application/ | [docs/export.md](export.md) | 2,084 | 用例层（12 use cases） |
| visualization/ | [docs/visualization.md](visualization.md) | 7,387 | 65 文件 |
| utils/ | [docs/utils.md](utils.md) | 201 | |
| plugins/ | [docs/plugins.md](plugins.md) | 1,568 | 插件系统（5 内置） |
| tests/ | - | 6,720 | 62 文件，372 用例 |

---

## 开发规划

改进计划与模块改进建议已迁移至独立文档：`docs/development_plan.md`。

---

## 已知 Bug 与技术债

| 问题 | 位置 | 状态 |
|------|------|------|
| `_on_style_change` 初始化期间崩溃 | control_panel.py:3665 | ✅ 已修复 (添加 `_is_initialized` 守卫) |
| `create_section_dialog` 未初始化属性 | control_panel.py:5614 | ✅ 已修复 (添加 `_reset_ui_state()`) |
| numba 日志过长 | utils/logger.py | ✅ 已修复 (设置 WARNING 级别) |
| `_reset_ui_state` 重复赋值 | control_panel.py:285-296 | ✅ 已不适用（相关实现已迁移） |
| 全局 widget 引用 (slider_n 等) | state.py:332-344 | ✅ 已不适用（旧 state.py 已拆分为 core/state/） |
| 循环导入风险 | visualization/plotting (旧 shim) | ✅ 已消解 (兼容入口已移除) |
| 控制面板禁用但代码保留 | ui/app_parts/plotting.py:_setup_control_panel | ✅ 已修复 (`Qt5ControlPanel` 类与 `create_control_panel` 工厂已移除，仅保留 `create_section_dialog`) |
| 可视化模块 docstring/导入顺序不规范 | visualization/events.py, visualization/plotting/* | ✅ 已修复 |
| 可视化模块日志前缀残留 | visualization/events.py, visualization/plotting/* | ✅ 已修复 |
| 可视化模块 core 导入入口不统一 | visualization/plotting/* | ✅ 已修复 |
| 诊断图未完全国际化 | visualization/plotting/analysis_qt.py | ✅ 已修复 |
| plotting/api.py 导出私有 helper | visualization/plotting/api.py | ✅ 已修复 |
| plotting/geo.py & plotting/render.py 顶层副作用 | visualization/plotting/geo.py, visualization/plotting/render.py | ✅ 已修复 |
| ui 模块 docstring/导入顺序不规范 | ui/app.py, ui/main_window.py, ui/control_panel.py, ui/dialogs/* | ✅ 已修复 |
| ui 模块日志前缀残留 | ui/app.py, ui/main_window.py, ui/panels/*, ui/dialogs/* | ✅ 已修复 |
| ui 模块 core 导入入口不统一 | ui/dialogs/*, ui/control_panel.py, ui/panels/* | ✅ 已修复 |

---

## 开发约定

统一开发规范已拆分为独立文档：`docs/dev_conventions.md`。
