# 开发规划（进行中）

本文件仅保留尚未完成或正在推进的事项。历史已完成条目不再重复记录。

## 核查更新（2026-03-07）

本次按代码现状逐项核查后，更新如下：

- 仍未完成（保持原计划）：
    - AppState 分层的全量字段迁移与调用切换。
    - 类型注解全覆盖（P2）。
    - 数值稳定性统一收口。
    - 测试框架落地。
    - 配置外部化。
    - 插件系统（含 ML 管线插件化）。

## 执行策略调整（2026-03-07）

按当前决策，`ML 管线增强` 延后到插件功能开发完成后再推进。

- 当前阶段只推进：第一优先级 + 第二优先级。
- 延后事项：`1.2 ML 管线增强`（依赖插件接口与插件管理能力）。
- 进入条件：`插件开发计划` 至少完成 M2（内置插件迁移）。

## 阶段进展（2026-03-31）

- 图像导出能力完成一轮增强（对应 1.1 的 E2/E3 局部落地）：
    - `ExportPanel` 图像导出新增 `Export Image` 直接导出入口，保留 `Preview Export` 预览链路。
    - 新增导出参数：`DPI`、`Tight Bounding Box`、`Padding (inch)`、`Transparent Background`。
    - 新增模板来源提示：优先 `SciencePlots`，不可用时自动回退到内置样式。
    - 统一预览保存与直接导出的 `savefig` 选项解析与后缀归一化逻辑。
    - 导出面板完成模块化拆分：`export_panel.py` 收敛为组装器，图像导出/数据导出/选择同步/公共逻辑迁移到 `ui/panels/export/` 子包。
    - E5 文档项部分完成：新增 `docs/export.md`，补充导出架构、流程、参数与依赖说明。

## 阶段进展（2026-04-01）

- 可视化渲染层完成新一轮大块拆分（保持旧入口兼容）：
    - `visualization/plotting/rendering/raw_plots.py` 收敛为兼容门面，2D/3D 原始散点实现分别下沉到 `raw_plot_2d.py` 与 `raw_plot_3d.py`。
    - `visualization/plotting/rendering/embedding_plot.py` 继续瘦身，算法归一化与嵌入计算逻辑下沉到 `embedding_algorithm.py`，DataFrame 对齐与可见组过滤下沉到 `embedding_dataframe.py`。
    - 目标达成：在不变更外部导入路径的前提下，进一步降低单文件复杂度并提升渲染链路可维护性。

## 架构现代化改造方案（2026-03-31 新增）

### 0. 现状审计摘要（基于代码检查）

当前工程已经完成部分模块化，但仍处于“单体 + 全局状态驱动”的架构阶段，主要瓶颈如下：

- 全局状态耦合高：`app_state` 仍被大量模块直接读写（跨 `ui/`、`visualization/`、`data/`）。
- 状态职责过重：`core/state.py` 仍承载大量数据、渲染、交互、UI 引用字段（含 `fig/ax`、selector、panel 引用等）。
- 大文件集中：`visualization/plotting/geo.py`（1733 行）、`visualization/plotting/render.py`（1196 行）、`visualization/events.py`（1041 行）、`ui/main_window.py`（1033 行）。
- 边界不清晰：`data/loader.py` 同时处理文件读取、对话框流程、清洗与状态写入，I/O、UI、领域逻辑混杂。
- 存在遗留路径：`Qt5ControlPanel` 标记为 deprecated，但仍保留较多兼容逻辑，增加维护负担。
- 基础设施薄弱：尚未落地自动化测试目录（`tests/` 缺失）与 CI 质量门禁。

### 1. 目标架构（PyQt 单体的现代化分层）

采用“分层整洁架构 + 事件驱动状态管理”的可渐进方案，在不推翻现有 UI 的前提下演进：

```text
presentation (PyQt Widgets/Dialog + ViewModel)
                ↓
application (UseCases / Commands / Queries)
                ↓
domain (Entities / ValueObjects / Domain Services)
                ↓
infrastructure (Pandas IO / Matplotlib adapter / Session store / Plugin loader)
```

关键原则：

1. 依赖方向只允许由外向内（UI 不直接依赖领域实现细节）。
2. 所有状态变更通过 Application 层命令执行，禁止 UI 层随意写 `app_state`。
3. 渲染与数据处理通过端口/适配器解耦（便于测试与替换）。
4. 新功能默认以模块化包落地，避免继续扩张超大文件。

### 2. 目标目录（建议）

```text
src/
├── presentation/
│   ├── qt/
│   │   ├── windows/
│   │   ├── dialogs/
│   │   └── viewmodels/
├── application/
│   ├── use_cases/
│   ├── dto/
│   └── services/
├── domain/
│   ├── model/
│   ├── services/
│   └── events/
├── infrastructure/
│   ├── data_io/
│   ├── plotting/
│   ├── session/
│   └── plugins/
└── shared/
        ├── contracts/
        └── errors/
```

说明：现阶段无需一次性物理迁移到 `src/`，可先在现有目录中建立同名子包并按能力逐步切换导入。

### 3. 分阶段改造路线（A1-A8）

#### A1 架构基线与质量门禁（1-2 周）

- 新增 `tests/` 基础骨架与 smoke 测试。
- 建立最小 CI（安装、导入、关键用例、打包冒烟）。
- 增加静态检查：`ruff` + `mypy(增量)`，先对 `core/`、`data/` 开启。

**验收：** PR 必须通过 lint + 最小测试后方可合并。

#### A2 状态管理现代化（2-3 周）

- 引入 `StateStore`（不可变快照 + action/reducer 风格），作为 `app_state` 的演进层。
- 将“数据加载、渲染模式、导出参数、选择集”迁移为第一批受控状态。
- 保留兼容适配器：旧代码可读写，但新代码只允许通过 action 更新。

**验收：** 新增功能 100% 通过 action 更新状态；`app_state` 直接写入点数量较基线下降 30%。

#### A3 Application 层落地（2-4 周）

- 抽取高频流程为 UseCase：
    - `LoadDatasetUseCase`
    - `RenderPlotUseCase`
    - `ExportImageUseCase`
    - `ExportTableUseCase`
- UI 回调改为调用 UseCase，不直接拼接业务流程。

**验收：** `ui/` 目录中不再出现跨层数据清洗与核心业务分支判断。

#### A4 可视化渲染管线拆分（3-4 周）

- 将 `visualization/events.py` 拆分为：交互控制器、命中测试、选择策略。
- 将 `visualization/plotting/geo.py` 拆为：模型计算、图元生成、标签布局三层。
- 引入 `PlotAdapter` 接口，隔离 Matplotlib 细节，降低 UI/算法对底层 API 的耦合。

**验收：** 单文件控制在 800 行以内；渲染相关核心函数具备可单测入口。

#### A5 数据层解耦（2-3 周）

- 将 `data/loader.py` 切分为：
    - `data_io`（读取器）
    - `schema`（列推断/校验）
    - `cleaning`（清洗与标准化）
    - `import_flow`（仅编排）
- UI 对话框输出 DTO，禁止数据层反向依赖 UI。

**验收：** 数据导入主流程可在无 UI 环境下运行（CLI/测试可复用）。

#### A6 插件系统与算法解耦（承接现有插件计划，2-4 周）

- 按既有 M1-M5 方案推进插件 API 冻结与内置算法迁移。
- 将 UMAP/t-SNE/XGBoost 的调用统一改为插件网关。

**验收：** 禁用单个插件不影响主程序启动；算法下拉框由注册表动态驱动。

#### A7 UI 架构升级（2-3 周）

- 引入 ViewModel 层（Qt 信号/槽仅绑定 VM 状态）。
- 清理 deprecated 控制面板旧路径，统一菜单对话框模式。
- 抽象公共组件（参数输入、状态提示、错误展示）形成可复用组件库。

**验收：** `ui/main_window.py` 降至 700 行以内；界面回调不直接操作底层绘图对象。

#### A8 发布工程化（1-2 周）

- 增加版本化迁移脚本（会话配置、插件目录、导出预设）。
- 建立性能基线（导入耗时、首帧渲染耗时、导出耗时）。
- 发布检查清单自动化（依赖、字体、SciencePlots 可用性、打包完整性）。

**验收：** 发布流程可一键执行并输出质量报告。

### 4. 架构 KPI（季度跟踪）

- 结构指标：
    - 超过 800 行文件数从当前基线降至 ≤ 2。
    - `app_state` 直接写入引用数较基线下降 ≥ 60%。
- 质量指标：
    - 核心模块（`core/data/visualization`）单元测试覆盖率 ≥ 55%。
    - 关键导出/加载/渲染链路具备回归测试。
- 体验指标：
    - 冷启动到首帧渲染时间下降 ≥ 20%。
    - 常用导出路径失败率持续低于 1%。

### 5. 风险与回滚策略

1. 迁移期间保持“旧入口 + 新入口”双轨，避免一次性切换导致大面积回归。
2. 每个 A 阶段均需提供 feature flag（默认关闭新链路，逐步灰度）。
3. 对外行为不变优先：UI 文案、导出结果、会话兼容性不得破坏。
4. 如任一阶段导致关键链路（加载/渲染/导出）回归，立即回退到上一稳定里程碑。

### 6. 与现有计划的关系

- 本节作为“跨模块架构主线”，优先级高于单点优化任务。
- 现有 1.1、2.1、2.2、2.3、插件 M1-M5 仍保留，但执行时需对齐 A1-A8 的阶段门禁。
- `ML 管线增强` 继续保持延期策略，待插件迁移完成后再进入性能/算法层深化。

## 架构计划执行化优化（2026-03-31 续）

### 0. 目标

将“架构现代化改造方案”从原则级文档升级为可排期、可验收、可回滚的执行计划，确保每一阶段都能独立交付并保持主线可用。

### 1. 周期与节奏（建议 16 周）

| 阶段 | 周期 | 目标 | 准出条件 |
| --- | --- | --- | --- |
| S0 准备 | 第 1-2 周 | 建立基线与门禁 | CI 可运行；基线报告生成 |
| S1 状态治理 | 第 3-5 周 | 完成 StateStore 第一批迁移 | 新增状态变更仅走 action；关键链路回归通过 |
| S2 用例分层 | 第 6-8 周 | 导入/渲染/导出进入 UseCase | UI 回调不含核心业务分支 |
| S3 渲染解耦 | 第 9-11 周 | 交互控制与渲染适配器拆分 | 关键渲染模块可单测；大文件显著下降 |
| S4 数据层重构 | 第 12-13 周 | loader 分层与 DTO 化 | 无 UI 环境可执行导入流程 |
| S5 插件接入与发布工程化 | 第 14-16 周 | 插件主线打通 + 发布自动化 | 一键发布检查通过；插件灰度机制可用 |

### 2. 关键路径（Critical Path）

1. S0 CI 与测试骨架落地。
2. S1 StateStore 与 action 机制稳定。
3. S2 UseCase 接管导入/渲染/导出主链路。
4. S3 PlotAdapter 完成并接入 UI。
5. S4 DataLoader 分层完成并通过无 UI 回归。
6. S5 插件网关接管算法入口。

说明：若第 2 步延期，第 3-5 步将整体顺延；因此 S1 为全计划最高风险点。

### 3. 里程碑准入/准出（Stage Gate）

#### G1（S0 -> S1）

- 准入：`tests/` 骨架、最小 CI、`ruff` 基础规则已提交。
- 准出：关键模块导入测试通过；生成“架构基线报告”并归档。

#### G2（S1 -> S2）

- 准入：StateStore 已覆盖数据加载与渲染模式。
- 准出：`app_state` 直接写入点较基线下降至少 20%。

#### G3（S2 -> S3）

- 准入：导入/渲染/导出均有对应 UseCase。
- 准出：UI 事件回调仅做参数采集与结果展示。

#### G4（S3 -> S4）

- 准入：`PlotAdapter` 接口稳定，事件控制器拆分完成。
- 准出：`visualization/events.py`、`visualization/plotting/geo.py` 任一文件行数下降到 900 行以内。

#### G5（S4 -> S5）

- 准入：导入流程可在无 Qt 环境运行。
- 准出：插件网关接管主要算法入口，发布检查脚本可一键执行。

### 4. 工作分解（WBS）

| 编号 | 工作包 | 主要输出 | 依赖 | 风险等级 |
| --- | --- | --- | --- | --- |
| WP-01 | 架构基线采集 | 依赖图、文件体量、状态写入热力图 | 无 | 中 |
| WP-02 | 测试与 CI 最小闭环 | `pytest` 冒烟 + lint 流水线 | WP-01 | 中 |
| WP-03 | StateStore 核心 | action/reducer/store 与兼容适配层 | WP-02 | 高 |
| WP-04 | UseCase 化导入 | `LoadDatasetUseCase` + DTO | WP-03 | 高 |
| WP-05 | UseCase 化渲染导出 | `RenderPlotUseCase`、`ExportImageUseCase`、`ExportTableUseCase` | WP-03 | 高 |
| WP-06 | 渲染管线拆分 | 控制器、命中测试、图元生成分层 | WP-05 | 高 |
| WP-07 | 数据层拆分 | `data_io/schema/cleaning/import_flow` | WP-04 | 中 |
| WP-08 | 插件网关接入 | 注册表驱动算法入口 | WP-05 | 中 |
| WP-09 | 发布工程化 | 质量报告、迁移脚本、发布检查 | WP-08 | 中 |

### 5. 两周执行计划（可立即开工）

#### Sprint-Next-1（第 1 周）

1. 建立 `tests/` 最小结构，落地 3 条 smoke：启动导入、渲染分发、导出调用。
2. 新增 `scripts/architecture_baseline.py`，输出：
    - 超大文件排行。
    - `app_state` 直接写入统计。
    - 模块间导入关系摘要。
3. 引入 `ruff` 基础规则并在 CI 中执行。

**验收：** 本周所有 PR 必须通过 lint + smoke。

#### Sprint-Next-2（第 2 周）

1. 新建 `core/state_store.py`，支持 `dispatch(action)` 与快照读取。
2. 迁移第一批状态域：
    - render mode
    - selected indices
    - export image options
3. 在 UI 层新增兼容桥接，保持旧调用不崩溃。

**验收：** 新增状态改动不得直接写入 `app_state` 原字段。

### 6. 质量与进度度量（每周更新）

| 指标 | 当前基线 | 4 周目标 | 8 周目标 | 16 周目标 |
| --- | --- | --- | --- | --- |
| 超过 900 行文件数 | 4 | 3 | 2 | ≤1 |
| `app_state` 直接写入点 | 100%（基线待脚本固化） | -20% | -40% | -60% |
| 核心链路自动化覆盖 | 低 | 冒烟覆盖 | 关键链路回归 | 覆盖率 ≥55% |
| 发布前人工检查项 | 高 | 部分脚本化 | 大部分脚本化 | 一键检查 |

### 7. 风险台账（执行版）

| 风险 | 触发条件 | 监测信号 | 缓解措施 | 回滚策略 |
| --- | --- | --- | --- | --- |
| 状态迁移导致行为漂移 | S1 大规模替换写路径 | 交互异常、导出参数失效 | 双写 + 快照对比 + feature flag | 关闭新 store，回落旧状态 |
| 渲染拆分引入性能回退 | S3 拆分后 draw 频率变化 | 首帧时间上升、卡顿 | 增量渲染 + 性能剖析基线 | 回退到旧渲染分发路径 |
| 插件接入稳定性不足 | 第三方插件异常 | 启动失败、算法列表空 | 启动降级 + 隔离失败插件 | 禁用插件模式启动 |
| CI 过慢影响迭代 | 检查项过多 | 合并队列堆积 | 分层流水线（快速/完整） | 临时降级为快速检查 |

### 8. 管理机制

1. 每周一次架构评审（30 分钟），仅检查 KPI 与阶段门，不讨论实现细节。
2. 每两周一次里程碑评审，决定是否进入下一阶段。
3. 每个工作包必须附带“变更影响面 + 回滚点 + 验收脚本”。
4. 所有重构 PR 必须绑定至少 1 条回归测试或 1 条 smoke 用例。

### 9. 文档联动要求

1. 目录或职责变更后，同步更新 `docs/architecture.md`。
2. 导出链路变更后，同步更新 `docs/export.md`。
3. UI 入口/交互变更后，同步更新 `docs/ui.md`。
4. 架构约束或流程变更后，同步更新 `docs/dev_conventions.md`（尤其是分层依赖、PR 门禁、分支策略）。
5. 本计划每周更新一次“完成度与偏差”。

---

## 阶段进展（2026-04-01）

- 已完成 A1（测试与 CI 最小门禁）首轮落地：
    - 新增 `tests/` 最小 smoke 集合，覆盖导出用例、选择/tooltip 用例、状态直写检查脚本调用。
    - 新增 `pyproject.toml` 中的 `pytest` 配置与 `dev` 可选依赖（`pytest`）。
    - 新增 GitHub Actions 工作流 `.github/workflows/quality-gate.yml`（Windows）执行：`pytest` + `scripts/check_state_mutations.py --fail-on-hits`。
    - 本地验证已通过：`8 passed`，状态直写检查保持 `TOTAL=0`。

- 已创建并推送架构改造总分支：`epic/architecture-modernization-2026q2`。
- 已完成 A3（Application 层）导出链路的一步到位迁移：
    - 新增 `application/use_cases/export_data.py`，统一承载导出 DataFrame 构建、CSV/Excel 写出、Excel 追加。
    - 新增 `application/use_cases/export_image.py`，统一承载图像导出预设、后缀归一化、保存参数解析与 `savefig` 调用。
    - `application/use_cases/export_dataframe.py` 转为兼容代理，避免旧引用断裂。
    - 导出 UI 层 `ui/panels/export/data_export.py` 与 `ui/panels/export/common.py` 已切换为调用应用层用例，UI 仅保留交互与反馈职责。
- 已完成 A3（Application 层）渲染编排迁移：
    - 新增 `application/use_cases/render_plot.py`，引入 `RenderPlotUseCase` 统一承载渲染模式校验、列选择修正、渲染分发与失败回退。
    - `visualization/events.py` 的 `on_slider_change` 已降级为薄入口，事件层保留异步任务管理和 UI 同步钩子。
    - Application 包已导出 `RenderPlotUseCase`，形成导入/渲染/导出三条主链路均可由 UseCase 编排的基础形态。
- 已完成 A2/A3 交界的数据导入编排迁移：
    - 新增 `application/use_cases/load_dataset.py`，将数据导入流程编排（文件/工作表选择、列配置、清洗、状态注入）上移到 Application 层。
    - `ui/app.py` 与 `ui/main_window.py` 已改为调用 `load_dataset`，UI 入口不再直接依赖 `data.loader.load_data`。
    - `data/loader.py` 的 `load_data` 已降级为兼容代理，`read_data_frame` 保留为数据读取工具函数。
- 已完成 A2（状态治理）第一步落地：
    - 新增 `core/state_gateway.py`，提供 `AppStateGateway` 与 `state_gateway`，作为导入/渲染链路的统一状态写入口。
    - `load_dataset` 与 `RenderPlotUseCase` 已切换关键状态写操作到 gateway，减少 UseCase 内部散落的字段级直接写入。
    - `visualization/events.py` 的渲染模式同步和异步 embedding 任务状态（token/worker/running）已切换到 gateway。
- 已完成 A2（状态治理）第二步收口：
    - `visualization/events.py` 中选择工具与等时线主链路状态写入已切换到 gateway。
    - 新增 gateway 写入口：rectangle/lasso selector、selection overlay/ellipse、selected isochron data、selection tool、visible groups。
    - `selected_indices` 的清空/增删也已通过 gateway 命令化封装（clear/add/remove），事件层不再直接调用集合变更方法。
    - 事件层中 `app_state.xxx = ...` 的残余已收敛为判断语句（无字段赋值）。
    - 导出子域状态写入已继续收口：`ui/panels/export/common.py`、`ui/panels/export/image_export.py`、`ui/panels/export/selection.py` 已切换到 gateway，移除导出链路中的字段级直接赋值与选择集合直接变更。
- 本次迁移目标：在不改变外部行为前提下，直接完成导出子域“规则下沉 + 责任分层”，作为后续 `LoadDatasetUseCase` / `RenderPlotUseCase` 迁移模板。
- 已完成 A2 提速批处理（状态直写快速收口）：
    - 新增 gateway 通用接口：`set_attr` / `set_attrs`，用于高频状态写入批量迁移。
    - 高价值入口文件完成收口：`ui/app.py`、`ui/main_window.py`、`visualization/plotting/render.py`、`visualization/plotting/core.py`。
    - 中小文件尾项收口完成：`ui/panels/analysis_panel.py`、`ui/panels/legend_panel.py`、`ui/panels/display_panel.py`、`ui/dialogs/line_style_dialog.py`、`visualization/plotting/geo.py`、`ui/dialogs/provenance_ml_dialog.py`、`ui/control_panel.py`、`ui/dialogs/data_import_dialog.py`、`ui/dialogs/endmember_dialog.py`、`visualization/plotting/kde.py`、`visualization/plotting/label_layout.py`、`core/localization.py`。
    - 大文件瓶颈收口完成：`ui/panels/data_panel.py` 与 `ui/panels/base_panel.py` 字段级直写已全部迁移至 gateway。
    - 可量化结果：`app_state.xxx = ...` 全仓计数已从 **294 降到 0**（净减少 294，完成率 **100%**）。
    - 新增基线检查脚本：`scripts/check_state_mutations.py`，支持本地与 CI 持续检查（可选 `--fail-on-hits`）。
- 已完成 A3（交互业务下沉）新一轮迁移：
    - 新增 `application/use_cases/selection_interaction.py`，承载矩形/套索圈选、最近邻索引匹配、工具切换策略、图例可见组计算等纯业务逻辑。
    - 新增 `application/use_cases/selected_isochron.py`，承载选中样本等时线结果计算与结果载荷构建。
    - 新增 `application/use_cases/tooltip_content.py`，承载 hover 提示文本拼装逻辑（默认字段、空列回退、选中状态标记）。
    - `visualization/events.py` 相关路径已改为调用 use case，事件层进一步收敛为交互编排与 UI 回调。
    - 新增 `visualization/selection_overlay.py`，将选中高亮圈与置信椭圆绘制从 events 模块拆分为独立渲染服务。
- 已完成 UI 大文件结构化拆分（DataPanel）：
    - `ui/panels/data_panel.py` 已收敛为薄组装器（18 行），仅负责 mixin 组合。
    - 新增 `ui/panels/data/` 子包并拆分职责：`build.py`（UI 构建）、`projection.py`（渲染/算法参数）、`geochem.py`（地球化学交互）、`grouping.py`（分组与 tooltip）。
    - 可量化结果：原 `ui/panels/data_panel.py` 约 1356 行已拆分为多个职责模块，降低单文件认知复杂度并与 `export/` 子包模式保持一致。
- 已完成 UI 面板第二轮结构化拆分（Analysis/Display/Legend）：
    - `ui/panels/analysis_panel.py`、`ui/panels/display_panel.py`、`ui/panels/legend_panel.py` 已收敛为薄组装器。
    - 新增子包：`ui/panels/analysis/`、`ui/panels/display/`、`ui/panels/legend/`，对应 `panel.py` 承载原业务逻辑。
    - 兼容性验证：原导入路径保持不变，面板类名保持不变。
- 已完成 Analysis 子包内部模块化拆分（第四轮）：
    - `ui/panels/analysis/panel.py` 已收敛为 mixin 组合层。
    - 新增 `ui/panels/analysis/build.py`、`diagnostics.py`、`selection.py`、`equations.py`、`mixing.py`。
    - 兼容性验证：`AnalysisPanelMixin` 对外名称不变，`ui/panels/analysis_panel.py` 调用路径不变。
- 已完成 UI 面板第三轮细化拆分（Display/Legend 内部模块）：
    - `ui/panels/display/panel.py` 已收敛为 mixin 组合层，新增 `ui/panels/display/build.py` 与 `ui/panels/display/themes.py`。
    - `ui/panels/legend/panel.py` 已收敛为 mixin 组合层，新增 `ui/panels/legend/build.py` 与 `ui/panels/legend/actions.py`。
    - 兼容性验证：`DisplayPanelMixin` / `LegendPanelMixin` 对外名称不变，`ui/panels/display_panel.py` 与 `ui/panels/legend_panel.py` 无需变更调用。
- 已完成对话框模块化拆分（DataImportDialog）：
    - `ui/dialogs/data_import_dialog.py` 已收敛为包装器（保留 `Qt5DataImportDialog` 与 `get_data_import_configuration` 兼容入口）。
    - `ui/dialogs/data_import/dialog.py` 已收敛为组合层。
    - 新增 `ui/dialogs/data_import/build.py`、`workflow.py`、`submit.py`，实现 UI 构建、导入流程、提交校验解耦。
    - 导入冒烟检查通过，UI 对外 API 无破坏性变更。
- 已完成主窗口模块化拆分（MainWindow）：
    - `ui/main_window.py` 已收敛为薄入口组合类（`Qt5MainWindow` 保持不变）。
    - 新增 `ui/main_window_parts/` 子包并拆分职责：`setup.py`（窗口/菜单/工具栏/状态栏）、`legend.py`（图例面板交互）、`canvas.py`（画布与工具操作）、`lifecycle.py`（会话与事件绑定）。
    - 兼容性验证：外部导入路径 `from ui.main_window import Qt5MainWindow` 无变化。
- 已完成应用启动层模块化拆分（Qt5Application）：
    - `ui/app.py` 已收敛为薄编排入口，职责拆分到 `ui/app_parts/`。
    - 新增 `ui/app_parts/styles.py`、`session.py`、`plotting.py`，分别承载样式与调试钩子、会话恢复、绘图构建与事件连接。
    - 兼容性验证：外部导入路径 `from ui.app import Qt5Application` 无变化，导入冒烟通过。
- 已完成主窗口图例模块二次拆分（Legend internals）：
    - `ui/main_window_parts/legend.py` 已收敛为组合入口。
    - 新增 `ui/main_window_parts/legend_core.py` 与 `legend_actions.py`，将图例排序核心与 UI 交互动作解耦。
    - 兼容性验证：`Qt5MainWindow` 外部行为不变，图例导入与启动冒烟通过。
- 已完成 Display/Legend 与 ProvenanceML 第四轮模块细化（2026-04-01 夜间）：
    - `ui/panels/display/build.py` 已剥离颜色与图例按钮辅助逻辑到 `ui/panels/display/helpers.py`，`DisplayPanelMixin` 更新为 build/themes/helpers 三层组合。
    - `ui/panels/legend/build.py` 已剥离色阶/形状编辑器逻辑到 `ui/panels/legend/editors.py`，`LegendPanelMixin` 更新为 build/editors/actions 三层组合。
    - `ui/dialogs/provenance_ml_dialog.py` 已收敛为兼容包装器，新增 `ui/dialogs/provenance_ml/dialog.py`、`build.py`、`workflow.py` 形成初始化/构建/执行分层。
    - 兼容性验证：`ProvenanceMLDialog` 与 `show_provenance_ml` 入口保持不变，导入冒烟通过。
- 已完成可视化绘图层双模块拆分（2026-04-01 夜间续）：
    - `visualization/plotting/render.py` 已抽离通用绘图辅助逻辑到 `visualization/plotting/render_helpers.py`，主文件聚焦 `plot_embedding` / `plot_2d_data` / `plot_3d_data` 主流程。
    - `visualization/plotting/geo.py` 已抽离覆盖层与 plumbotectonics 逻辑到 `visualization/plotting/geo_overlay_helpers.py`，主文件聚焦等时线拟合、模型年龄线、方程覆盖等核心计算。
    - 兼容性验证：`pytest`（8 passed）与导入冒烟通过，`scripts/check_state_mutations.py --fail-on-hits` 仍保持 `TOTAL=0`。
    - 量化结果：`render.py` 由约 1297 行降至 758 行；`geo.py` 由约 1733 行降至 1140 行。
- 已完成 plotting 包结构清理（2026-04-01 夜间补充）：
    - 删除未被引用的冗余模块 `visualization/plotting/overlay_helpers.py`，减少同类 helper 重叠。
    - 新增 `visualization/plotting/event_bridge.py`，统一 `plotting -> events` 的回调桥接，移除 `render.py` 与 `style.py` 的分散式动态导入。
    - `visualization/plotting/legend_model.py` 已改为直接依赖 `geo_overlay_helpers` 的元数据函数，减少对 `geo.py` 主模块的耦合。
    - 验证结果：`pytest` 全通过，改动文件错误检查通过。
- 已完成 plotting 子目录重组（2026-04-01 夜间续）：
    - 新增 `visualization/plotting/rendering/`，并迁移 `render_helpers.py`、`render_kde.py`、`render_geo_layers.py` 到子目录（分别为 `helpers.py`、`kde.py`、`geo_layers.py`）。
    - 新增 `visualization/plotting/styling/`，并迁移 `style_core.py`、`style_legend.py`、`style_overlays.py` 到子目录（分别为 `core.py`、`legend.py`、`overlays.py`）。
    - 新增 `visualization/plotting/geochem/`，并迁移 `geo_overlay_helpers.py` 到 `overlay_helpers.py`。
    - `render.py`、`style.py`、`geo.py`、`legend_model.py` 已完成导入路径切换，plotting 顶层文件堆积明显下降。
- 已完成 visualization 事件层拆分（2026-04-01 夜间续）：
    - 新增 `visualization/event_handlers/selection_interaction.py`，迁移 hover、点击、图例可见性切换、选择工具与选中等时线计算链路。
    - 新增 `visualization/event_handlers/__init__.py` 聚合交互事件公开函数，保留外部导入习惯。
    - `visualization/events.py` 已收敛为渲染触发与异步 embedding 编排入口（164 行），对外 API 名称保持不变。
    - 兼容性验证：`pytest` 全通过（8 passed），`from visualization.events import ...` 冒烟导入通过。
- 已完成 visualization 事件子包二次细拆（2026-04-01 夜间续）：
    - 新增 `visualization/event_handlers/shared.py`、`overlay.py`、`isochron.py`、`selection_tools.py`、`pointer_events.py`、`legend.py`，将共享状态、覆盖层刷新、等时线计算、选择工具、指针事件、图例事件进一步解耦。
    - `visualization/event_handlers/selection_interaction.py` 已收敛为兼容门面，继续保留原导入路径。
    - 兼容性验证：`pytest` 全通过（8 passed），`visualization.events` 与 `visualization.event_handlers.selection_interaction` 双路径导入冒烟通过。
- 已完成 geochem 等时线渲染模块细拆（2026-04-01 夜间续）：
    - `visualization/plotting/geochem/isochron_rendering.py` 已收敛为兼容门面。
    - 新增 `visualization/plotting/geochem/isochron_fits.py`（等时线拟合主流程）、`selected_isochron_overlay.py`（选中等时线高亮）、`paleoisochron_overlays.py`（古等时线覆盖层）。
    - 兼容性验证：`pytest` 全通过（8 passed），`isochron_rendering` 与 `isochron_overlays` 双路径导入冒烟通过。
- 已完成 geochem 等时线拟合二次细拆（2026-04-01 夜间续）：
    - 新增 `visualization/plotting/geochem/isochron_fit_76.py` 与 `isochron_fit_86.py`，将 PB_EVOL_76/PB_EVOL_86 模式分支从主流程中解耦。
    - `visualization/plotting/geochem/isochron_fits.py` 已收敛为主流程编排层（分组循环 + 公共拟合预处理 + 分支分发）。
    - 兼容性验证：`pytest` 全通过（8 passed），`isochron_fits` 与 `isochron_rendering` 导入冒烟通过。
    - 验证结果：`pytest` 全通过（8 passed），导入冒烟通过。
- 已完成 geochem 第二轮拆分（2026-04-01 夜间续）：
    - `visualization/plotting/geo.py` 已收敛为兼容门面，保留原函数导出以避免外部调用断裂。
    - 新增 `visualization/plotting/geochem/isochron_overlays.py`，承载等时线拟合、选中等时线、古等时线、模型年龄线、标签刷新。
    - 新增 `visualization/plotting/geochem/equation_overlays.py`，承载方程表达式安全求值与曲线叠加渲染。
    - 量化结果：`geo.py` 由约 1233 行降至 64 行。
    - 验证结果：`pytest` 全通过（8 passed），兼容导入冒烟通过。
- 已完成 geochem 第三轮拆分（2026-04-01 夜间续）：
    - `visualization/plotting/geochem/isochron_overlays.py` 已收敛为兼容门面。
    - 新增 `visualization/plotting/geochem/isochron_labels.py`，承载等时线标签构建与标签重布局刷新。
    - 新增 `visualization/plotting/geochem/isochron_rendering.py`，承载等时线/选中等时线/古等时线渲染。
    - 新增 `visualization/plotting/geochem/model_age_lines.py`，承载模型年龄线与年龄解算逻辑。
    - 量化结果：`isochron_overlays.py` 由约 1021 行降至 27 行。
    - 验证结果：`pytest` 全通过（8 passed），兼容导入冒烟通过。
- 已完成 rendering 第二轮拆分（2026-04-01 夜间续）：
    - `visualization/plotting/render.py` 已收敛为兼容门面，保留 `plot_embedding` / `plot_umap` / `plot_2d_data` / `plot_3d_data` 导出。
    - 新增 `visualization/plotting/rendering/embedding_plot.py`，承载 `plot_embedding` 主流程。
    - 新增 `visualization/plotting/rendering/raw_plots.py`，承载 `plot_2d_data` 与 `plot_3d_data`。
    - 量化结果：`render.py` 由约 902 行降至 17 行。
    - 验证结果：`pytest` 全通过（8 passed），兼容导入冒烟通过。
- 已完成 geochem 第四轮拆分（2026-04-01 夜间续）：
    - `visualization/plotting/geochem/overlay_helpers.py` 已收敛为兼容门面。
    - 新增 `visualization/plotting/geochem/overlay_common.py`，承载通用覆盖层标签/样式辅助函数。
    - 新增 `visualization/plotting/geochem/model_overlays.py`，承载模型曲线与 Mu/Kappa 古等时线绘制。
    - 新增 `visualization/plotting/geochem/plumbotectonics.py`，承载 Plumbotectonics 分组元数据、曲线拟合与曲线/同龄线绘制。
    - 量化结果：`overlay_helpers.py` 由约 686 行降至 45 行。
    - 验证结果：`pytest` 全通过（8 passed），兼容导入冒烟通过。

## 全局改进计划

### 第一优先级：功能与性能

#### 1.1 图像导出能力建设（新）

**目标:** 将导出能力明确拆分为“数据导出”和“图像导出”，并为学术期刊投稿场景提供可复用的标准化输出。

**范围定义:**

- 数据导出：保持现有 CSV/Excel/追加导出能力。
- 图像导出：新增统一入口，支持位图（PNG/TIFF）与矢量（PDF/SVG/EPS）导出。

**核心要求（期刊适配）:**

- 导出时优先选择“期刊预设”，预设锁定尺寸与字体大小。
- 其余参数（线宽、标记大小、网格透明度、留白等）按预先定义模板自动应用，避免用户逐项调整。
- 提供最小可用预设集：
  - `Single Column`：约 `85 mm` 宽，适合单栏图。
  - `Double Column`：约 `180 mm` 宽，适合跨双栏图。
  - `Presentation`：用于报告/答辩，尺寸较宽，字体略大。
- 字体等级按预设固定：标题/坐标轴标题/刻度/图例四级联动。

**实现方案优先级（新增）:**

- 方案 A（优先）：基于 `SciencePlots` 组合样式实现期刊预设。
    - 依据：官方支持 `plt.style.use(['science', 'ieee'])` 与 `['science', 'nature']`，用于覆盖列宽与字体等级。
    - 适配策略：
        - 默认链路使用 `science + no-latex`，降低 LaTeX 依赖门槛。
        - 对 IEEE/Nature 预设追加对应 journal style。
        - 中文场景追加 CJK font style（按字体可用性回退）。
- 方案 B（回退）：不依赖外部包，使用内置 `rcParams` 预设（保持当前规划中的 `ExportProfile`）。

**实现路线（E1-E5）:**

1. E1 导出模型抽象
    - 新增 `ExportProfile` 数据结构（尺寸、DPI、字体等级、格式、背景策略）。
    - 在 `core/config.py` 或独立配置模块维护内置预设，支持后续外置配置。
2. E2 图像导出引擎
    - 封装 `figure.savefig(...)` 调用链，统一处理尺寸换算（mm/inch）、DPI 与 bbox。
    - 增加导出前样式快照与导出后恢复，避免污染当前交互视图。
3. E3 UI 接入
    - `ExportPanel` 拆分为 `Data Export` 与 `Image Export` 两个折叠区。
    - 图像导出区提供：预设选择、格式选择、输出路径、导出按钮。
    - 当检测到 `SciencePlots` 可用时显示“期刊模板来源: SciencePlots”；不可用时自动切回内置模板。
4. E4 质量与兼容性
    - 增加字体可用性检查与回退策略（Windows 字体缺失时自动回退并提示）。
    - 验证图内文本在常见缩放比例下不重叠（标题、轴标签、图例）。
5. E5 文档与回归
    - 新增 `docs/export.md`（预设说明、格式建议、投稿建议流程）。
    - 为关键导出路径补充最小回归脚本（不同格式 + 不同预设）。

**验收标准:**

- 用户在 3 步内完成期刊风格导出：选预设 -> 选格式 -> 导出。
- 同一图在不同机器上导出后，尺寸与字体等级与预设一致（允许极小字体渲染差异）。
- 图像导出不改变当前画布交互状态（导出前后视图一致）。

#### 1.2 ML 管线增强（延期）

**状态:** 延期，待插件功能完成后执行。

**延期原因:** ML 算法将转为插件化实现，当前直接改造主仓库会导致重复重构。

**重启条件:** 插件开发计划达到 M2（XGBoost/UMAP 等内置插件迁移完成）。

**后续实施要点（保留）:**

- 增加 train/valid/test 划分与固定随机种子报告。
- 增加交叉验证指标（macro-F1、balanced accuracy、AUC-ovr）。
- XGBoost 默认 `tree_method='hist'`，并在报告中标注训练耗时。
- 支持 per-label 阈值与阈值搜索结果导出。

### 第二优先级：代码质量

#### 2.1 类型注解补齐（部分完成）

**范围优先级:** `core/` > `data/` > `visualization/` > `ui/`

**要求:**

- 新增/重构公共函数必须含类型注解。
- 公共 API 使用 Google 风格 docstring（Args/Returns/Raises）。
- 剩余重点：`core/state.py`、`core/session.py`、`data/` 核心计算函数。

#### 2.2 AppState 分层拆分

**目标:** 将 `AppState` 按职责拆分为子状态对象，降低耦合。

**建议结构:**

```python
class AppState:
    data: DataState
    algorithm: AlgorithmState
    visual: VisualState
    geochem: GeochemState
    style: StyleState
    interaction: InteractionState
```

**实现状态:** 进行中（已新增分层兼容视图、可写属性与顶层别名；正在分批迁移调用方）

#### 2.3 数值稳定性统一（部分完成）

**目标:** 统一除零与无效值处理策略。

**实施要点:**

- 统一 `EPSILON` 常量来源，避免散落魔法数字。
- 在关键计算路径中使用 `np.errstate`。
- 所有外部输入统一 `pd.to_numeric(errors='coerce')`。
- 剩余重点：扩展到其余模块并补充相应回归验证。

### 当前阶段交付顺序（仅 P2）

1. P2-1：类型注解补齐（先 core/data）
2. P2-2：AppState 分层拆分
3. P2-3：数值稳定性统一收口

### 第三优先级：基础设施

#### 3.1 单元测试框架落地

**最小目标:** 建立可运行测试骨架并覆盖关键数值模块。

```text
tests/
├── test_geochemistry.py
├── test_cache.py
├── test_session.py
├── test_localization.py
├── test_endmember.py
├── test_mixing.py
└── test_provenance_ml.py
```

#### 3.2 配置外部化

支持用户配置文件 `~/.isotopes_analysis/config.json`，并与 `CONFIG` 合并。

```json
{
  "default_language": "zh",
  "figure_dpi": 150,
  "embedding_cache_size": 16,
  "xgboost_tree_method": "hist"
}
```

---

## 模块改进建议（进行中）

### data/ 模块

#### 高优先级

1. `provenance_ml.py` 增加交叉验证与测试集报告（延期，插件完成后执行）。
2. XGBoost 训练默认切换到 `tree_method='hist'`（延期，插件完成后执行）。

#### 中优先级

3. 列名规范化策略外置（导入配置或映射表）。
4. `GeochemistryEngine` 为后台线程场景增加并发保护。
5. `mixing.py` 增加误差传播能力（不确定度输入到权重区间）。

#### 低优先级

6. 清理 geochemistry 兼容别名函数（下个大版本）。
7. `endmember.py` 中阈值参数可配置化。

### visualization/ 模块

#### 高优先级

1. 补充渲染子函数级测试（覆盖散点/KDE/地球化学覆盖层/图例/标题路径）。
2. 继续增强 UI 进度展示与异常可视反馈（与后台任务联动）。

#### 中优先级

3. 诊断图增加“另存为”导出能力。
4. `refresh_plot_style()` 支持增量更新，避免全量遍历散点集合。
5. `calculate_selected_isochron()` 扩展 206-208 模式。

#### 低优先级

6. 完善渲染异常回滚测试，确保失败时 canvas 状态一致。

---

## 插件开发计划（扩展版）

### 目标

- 将机器学习能力从主仓库解耦为插件，降低核心代码耦合。
- 支持第三方算法快速接入，保持 UI 与数据层兼容。
- 保证插件 API 稳定、可发现、可诊断、可回退。

### 设计原则

1. **稳定接口优先**：先定义最小可用 API，再扩展能力。
2. **弱依赖核心**：插件只依赖公开接口，不直接访问内部状态。
3. **可观测性**：插件加载、执行、失败必须有结构化日志。
4. **兼容演进**：通过 API 版本协商避免一次性破坏升级。

### V1 插件范围

- `MLClassifierPlugin`：监督分类（训练/预测/概率输出）。
- `EmbeddingPlugin`：降维嵌入（fit_transform/transform）。
- `FeatureEngineeringPlugin`：特征构造与清洗。

### 目录与发现机制

```text
plugins/
├── __init__.py
├── api.py                 # 抽象接口、类型定义、错误类型
├── manager.py             # 插件发现、加载、生命周期管理
├── registry.py            # 已加载插件注册表
├── builtins/
│   ├── xgboost_plugin.py
│   └── umap_plugin.py
└── third_party/
    └── ...
```

**发现策略（按优先顺序）:**

1. 内置目录 `plugins/builtins/`
2. 用户目录 `~/.isotopes_analysis/plugins/`
3. 可选 entry points（后续版本）

### 接口草案（V1）

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class PluginMeta:
    name: str
    version: str
    api_version: str
    plugin_type: str
    author: str = ""


class BasePlugin(Protocol):
    meta: PluginMeta

    def validate_environment(self) -> tuple[bool, str]:
        ...

    def get_default_params(self) -> dict[str, Any]:
        ...


class MLClassifierPlugin(BasePlugin, Protocol):
    def fit(self, x: Any, y: Any, **params: Any) -> dict[str, Any]:
        ...

    def predict(self, x: Any) -> Any:
        ...

    def predict_proba(self, x: Any) -> Any:
        ...
```

### 生命周期管理

1. `discover`：扫描插件并解析元数据。
2. `validate`：检查依赖、API 版本、运行环境。
3. `register`：写入注册表并暴露给 UI。
4. `execute`：统一调用并捕获异常。
5. `dispose`：释放资源并记录统计信息。

### 兼容性策略

- `api_version` 采用 `MAJOR.MINOR`。
- 主版本不匹配时拒绝加载并给出可读错误。
- 次版本不匹配时允许加载但记录 warning。
- 保留 `capabilities` 字段，支持按能力降级。

### 安全与隔离

- 默认与主进程同进程运行（V1）。
- 对插件异常做边界捕获，不允许异常穿透到 UI 事件循环。
- 严禁插件直接读写 `app_state` 内部字段；通过受控上下文对象访问。
- 对第三方插件开启“受限模式”标记（禁用敏感入口）。

### 开发者体验

- 提供 `plugins/examples/` 最小模板。
- 提供 `scripts/new_plugin.py` 脚手架命令。
- 提供插件自检命令：`uv run python -m plugins.manager --check`。
- 在 UI 中新增“插件管理”对话框（启用/禁用/诊断信息）。

### 里程碑

#### M1（接口冻结）

- 完成 `plugins/api.py` 与 `PluginMeta`。
- 实现 `PluginManager` 基础加载链路。

#### M2（内置插件迁移）

- 将当前 XGBoost 管线迁移为内置 `MLClassifierPlugin`。
- 将 UMAP/t-SNE 包装为 `EmbeddingPlugin`。

#### M3（UI 接入）

- 算法下拉框改为读取注册表。
- 新增插件状态与失败原因展示。

#### M4（第三方支持）

- 支持用户目录安装插件。
- 增加插件签名/来源标识字段。

#### M5（测试与文档）

- 增加插件加载、执行、回退、兼容性测试。
- 新增 `docs/plugins.md`（开发指南 + API 参考）。

### 验收标准

- 关闭/卸载某个插件不影响应用启动。
- 插件执行失败时 UI 不冻结，且有可检索日志。
- 至少 2 个内置插件完成迁移并通过回归验证。
- 插件接口升级时，旧插件可得到明确兼容性提示。

---

