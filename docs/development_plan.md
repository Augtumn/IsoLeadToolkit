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

---

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

