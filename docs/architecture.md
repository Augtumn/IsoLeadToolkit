# 项目架构总览

## 项目概况

**Isotopes Analyse** — 基于 PyQt5 的铅同位素地球化学数据分析与可视化桌面应用。

| 指标 | 数值 |
|------|------|
| Python 代码总量 | ~54,400 行 |
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
| ui/ | [docs/ui.md](ui.md) | 17,803 | 103 文件（每段一个面板包；无 500 行以上的文件） |
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


---

## 项目结构

```
IsotopesAnalyse/
├── main.py
├── pyproject.toml
├── application/            # 用例层（导入/导出/渲染编排）
├── core/
│   ├── config.py           # CONFIG + 用户配置
│   ├── state/              # StateStore + Gateway + 声明式字段注册表
│   ├── session/            # 会话持久化 + 版本迁移
│   ├── localization.py     # 双语
│   └── cache.py            # LRU 嵌入缓存
├── data/
│   ├── loader.py           # Excel/CSV 读取 + 列类型推断
│   └── geochemistry/       # 地球化学计算 (engine, age, source, delta, isochron)
├── plugins/                # 插件系统（api / manager / registry / builtins / examples）
├── ui/
│   ├── main_window.py      # 主窗口（组合根由 ui/factory.py 提供）
│   ├── main_window_parts/  # 菜单/工具栏/图例/画布
│   ├── panels/             # 分区控制面板
│   ├── dialogs/            # 专用对话框（含尺寸记忆）
│   └── widgets.py          # 可复用组件
├── visualization/
│   ├── events.py           # 交互事件编排
│   ├── embedding_worker.py # QThread 异步嵌入
│   ├── event_handlers/     # 选择/指针/图例事件
│   └── plotting/           # 渲染管线 (rendering/geochem/styling)
├── locales/                # en.json / zh.json
├── scripts/                # 守卫脚本 / 发布检查 / 脚手架
├── tests/                  # 测试与真实窗口夹具
└── docs/                   # 本目录
```

## 质量守卫

`scripts/check_*.py` 共 11 个静态守卫，由 `tests/test_guards.py` 逐个执行，全部要求输出 `TOTAL=0`：

| 守卫 | 约束 |
|------|------|
| `check_state_mutations.py` / `check_state_dict_mutations.py` | 状态只能经 `state_gateway` 修改 |
| `check_gateway_direct_state_assignments.py` | 网关旁路写入 |
| `check_gateway_generic_mutations.py` / `check_gateway_generic_mutations_in_tests.py` | 通用 `set_attr` / `set_attrs` 调用与测试写法 |
| `check_state_sync_coverage.py` | 快照字段必须能回写到状态（运行时扰动核对，探测 174 字段） |
| `check_state_field_coverage.py` | 每个快照字段要么在 `core/state/fields.py` 注册表里，要么在允许清单里注明原因 |
| `check_self_attribute_probes.py` | 禁止 `getattr(self, "控件", None)` 式自省探测（基线为 0） |
| `check_silent_exceptions.py` | 禁止静默吞掉异常（基线为 0） |
| `check_cross_mixin_calls.py` | 跨 mixin 调用必须声明为 `REQUIRES_<Class>`，并检测同名类 |
| `check_panel_self_resolution.py` | 面板方法解析与调用参数个数 |

状态字段集中在 `core/state/fields.py` 的声明式注册表（默认值 / 强转 / 拷贝 / holder 一处声明），
强转函数集中在 `core/state/coercers.py`；新增字段只需在注册表声明一次。
