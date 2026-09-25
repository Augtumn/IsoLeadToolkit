# 项目架构总览

## 项目概况

**Isotopes Analyse** — 基于 PyQt5 的铅同位素地球化学数据分析与可视化桌面应用。

| 指标 | 数值 |
|------|------|
| Python 代码总量 | ~52,200 行 |
| 模块数 | 9 个主目录（core/data/ui/visualization/application/plugins/utils/scripts/tests） |
| Python 文件数 | 301 个 |
| 对话框数 | 15+ 个 |
| 支持算法 | UMAP, t-SNE, PCA, RobustPCA, V1V2 |
| 图类型 | 8+ 种 |
| 语言支持 | 中文/英文（1152 键） |

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
│  │ cache    │  │  (19 个)     │  │  geo             │  │
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
│                │          │      │     plugins/      │  │
│                │          │      │ builtins/ (6)     │  │
│                │          │      └───────────────────┘  │
│                │          │      ┌───────────────────┐  │
│                │          │      │     utils/        │  │
│                │          │      │ logger            │  │
│                │          │      └───────────────────┘  │
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

| 模块 | 文档路径 | 行数（2026-09 实测，含空行） | 备注 |
|------|----------|------|------|
| core/ | — | 6,457 | 含 state/ 子包（store 829, gateway 808, app_state 899, _normalizers 537, _views 326, _panel_style_handlers 187, _dispatch_handlers 838, bootstrap 227）、persistence/、session/（io 单一入口） |
| data/ | [docs/data.md](data.md) | 2,578 | 地球化学逻辑已迁入 plugins/builtins/*_plugin.py；含 Albarède & Juteau (1984) T–μ–κ 模型 |
| ui/ | [docs/ui.md](ui.md) | 17,512 | 103 文件（每段一个面板包；无 500 行以上的文件） |
| application/ | [docs/export.md](export.md) | 2,834 | 用例层（13 use cases） |
| visualization/ | [docs/visualization.md](visualization.md) | 9,113 | 65 文件 |
| utils/ | [docs/utils.md](utils.md) | 252 | |
| plugins/ | [docs/plugins.md](plugins.md) | 1,933 | 插件系统（6 内置） |
| tests/ | [docs/dev_conventions.md](dev_conventions.md) §13 | 10,095 | 31 文件，401 用例（按子系统组织） |

---

## 开发规划

改进计划与模块改进建议已迁移至独立文档：`docs/development_plan.md`。

---

## 已知 Bug 与技术债

当前没有已知未修复缺陷。历次审查发现的问题均已修复，修复过程见 git 历史；待办事项见 `docs/development_plan.md`。

---

## 开发约定

统一开发规范已拆分为独立文档：`docs/dev_conventions.md`。
