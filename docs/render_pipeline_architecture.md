# 绘图架构：现状分析与目标方案

> 本文是受控大改（"全做，顺序你定，减少兼容回退与各种补丁"）的分析与设计基线。
> 所有结论均来自对当前工作区的静态取证，条目带 `文件:行号`；未运行代码，运行期行为以探针复验为准。

## 1. 现状

### 1.1 入口与模式

| 项 | 事实 | 位置 |
|---|---|---|
| 渲染入口 | 只有 3 个：`plot_2d_data`、`plot_3d_data`、`plot_embedding` | `raw/plot2d.py:364`、`raw/plot3d.py:41`、`embedding_plot.py:34` |
| 模式清单 | 唯一主清单，14 项 `(label, value)` | `ui/render_modes.py:10-25` |
| 分派 | `3D`/`2D` 各有专用分支；4 个 ML 模式走异步；**其余 8 个模式共用一个 `plot_embedding`** | `application/use_cases/render_plot.py:325-381` |
| 多面板 | `_render_panels` 逐面板设置 figure/axes 后调 `_dispatch_render(mode=mode)` | `render_plot.py:117-238`，`:182-184` |

结论：**不是"一种图一个绘图模块"**。是"2 个专用模块 + 1 个多模式大函数（内部按 algorithm 分叉）+ 若干共享件"。

### 1.2 固定渲染序列：12 个必备步骤，三份各写一遍

三份代码的实际顺序是"**建轴 → 清轴**"（不是清→建），逐步骤行号对照：

| # | 步骤 | plot2d.py | plot3d.py | embedding_plot.py | 份数 |
|---|---|---|---|---|---|
| 0 | 入口校验 | 368（实现 29-54） | 44-60 | 49-51 | 3 |
| 1 | 捕获旧视图 | 371（实现 57-70） | 65、68 | 56-66 | 3 |
| 2 | 建轴 | 373 | 70 | 68 | 3 |
| 3 | 建轴后空检查 | 375-377 | 72-74 | 70-72 | 3 |
| 4 | 数据准备 | 379（实现 73-130） | 76-105 | 104 | 3 |
| 5 | 全局样式 | 383 | 107 | 75 | 3 |
| 6 | 轴级预设 | 386-390 | — | 113-119 | 2 |
| 7 | 清轴 | 385 | 109 | 120 | 3 |
| 8 | 轴/刻度样式 | 391 | 110 | 121 | 3 |
| 9 | 清绘图状态 | 392 | 111 | 122 | 3 |
| 10 | 配色构建 | 396 | 115 | 124 | 3 |
| 11 | 画数据 | 400-403 | 117-145 | 157、159 | 3 |
| 12 | 边缘 KDE | 434-436 | — | 195-201 | 2 |
| 13 | 图例 | 438（实现 243-290） | 170-176 | 203 | 3 |
| 14 | 标题 | 308-311 | 26-29 | 204（实现 `common/title.py:48-82`） | 3 |
| 15 | 轴标签 | 332-334 | 35-38 | `common/title.py:106-132` | 3 |
| 16 | 恢复视图 | 317-324 | 67-68、184-185 | 205 → `geo_layers.py:81-88` | 3（3 种判据写法） |
| 17 | 方程叠加 | 345 | — | `geo_layers.py:91` | 2 |
| 18 | 布局引擎 | 304 | — | — | 1 |
| 19 | 交互注释 | 348-361（调 421、451） | 160、186（置 None） | 209-220 | 3 |
| 20 | 收尾 | — | — | 207、222-225 | 1 |
| 21 | 空数据分支 | 405-426 | 150-161 | 168-193 | 3 |
| 22 | 失败兜底 | 455-461 | 189-195 | 229-236 | 3 |

**序列没有任何骨架模块**：调用点分散在 `plot2d.py`、`plot3d.py`、`embedding_plot.py`、`geo_layers.py`、`kde.py` 五个文件中。

### 1.3 共享件（已有）与其覆盖面

| 模块 | 行数 | 谁在用 | 缺口 |
|---|---|---|---|
| `common/legend.py` | 338 | 2D（`plot2d.py:277`）、3D（`plot3d.py:170`）、embedding（`embedding_plot.py:203`） | 2D 另有自己的 `_render_2d_legend`（243-290）与 `_render_legend`（275-338）高度重合 |
| `common/title.py` | 132 | **只有 embedding**（`embedding_plot.py:204`） | 2D/3D 各自内联拼标题（`plot2d.py:308-311`、`plot3d.py:26-29`） |
| `common/scatter.py` | 150 | **只有 embedding**（`embedding_plot.py:159`） | 2D/3D 各自内联散点循环（`plot2d.py:170`、`plot3d.py:117-145`） |
| `common/state_access.py` | 26 | 全部 | — |
| `view_state.py` | 71 | 3D、2D、`geo_layers` | 2D 自建 `_capture_prev_axes`（57-70）、embedding 内联（56-66）未采用 |

### 1.4 已证实的缺陷（大改要消灭的对象）

| # | 缺陷 | 位置 |
|---|---|---|
| 1 | 异步算法集合重复两份字面量 | `render_plot.py:12`、`events.py:27` |
| 2 | **异步路径丢掉 `mode`**：`_dispatch_render` 只传 `group_col`，`events.py` 内部改读全局 `app_state.render_mode` ⇒ 多面板下非当前面板的 UMAP/tSNE/PCA/RobustPCA 会按别的面板的模式分流 | `render_plot.py:366`、`events.py:306`、`:364` |
| 3 | 模式值两套拼写：`"Ternary"` vs `'TERNARY'`、`"tSNE"` vs `'TSNE'` | `render_modes.py:17`、`panels.py:13`、`canvas.py:540`、`algorithm.py:38` |
| 4 | 清单外的值可进入分派（`ISOCHRON1/2`、`PB_MODELS_76/86`、`ROBUSTPCA`），无白名单 | `algorithm.py:17-44`、`base_panel.py:93-102` |
| 5 | **第二份手写模式下拉**（值同、顺序不同，未引用唯一清单） | `ui/panels/data/dialogs/data_import/build.py:285-300` |
| 6 | `_validate_render_columns` 只覆盖 3 个模式 | `render_plot.py:273/288/303` |
| 7 | "换模型后重绘"清单重复两处，且 `grouping.py:51-54` 漏 `PLUMBOTECTONICS_76/86` | `geochemistry/panel.py:306`、`:344`、`data/grouping.py:51-54` |
| 8 | 别名归一覆盖不一致（一处处理 ISOCHRON1/2，另一处不处理） | `algorithm.py:17-33` vs `base_panel.py:93-102` |
| 9 | 无脚本校验"清单 ↔ 分派 ↔ 适配器"一致性 | `scripts/` 无对应检查 |
| 10 | 参数腐化：`size` 三处形参未被使用；`prev_2d_cols`、`prev_embedding_type` 传参但函数体不读 | `plot2d.py:364/175`、`plot3d.py:41`、`embedding_plot.py:41`、`plot2d.py:299/302-345`、`geo_layers.py:30/34-91` |

### 1.5 为什么必须改：本次会话的修复成本

| 修复 | 触及源文件数 | 说明 |
|---|---|---|
| 图例标题（`b741c94`） | **1** | 改在共享件 `common/legend.py` |
| 视图保留（`2dd9abc`） | **1** + 新共享模块 | 抽 `view_state.py` 后 3D 只接一次 |
| 2D/嵌入接入（`cb0db41`） | **2** | 必须逐个渲染器接入 |
| 标题命名（`8316b25`） | **3** | 因 2D 内联标题，`title.py` 之外还要改 `plot2d.py` |
| 列清单过滤（`c54bed8`） | **3** | 常量属主 + 两个出口 |

期间 `render_plot.py` 被功能提交触及 6 次、`plot2d.py` 4 次、`ternary.py` 4 次、`themes.py`/`panel_style.py` 各 4 次 —— 热点正好落在没有骨架的地方。

## 2. 目标架构

原则：**一个骨架，每个模式只写自己那一段；一处真源，机制化防止再漏项。**

```
visualization/plotting/rendering/
    pipeline.py        唯一渲染骨架：run(mode, ctx)
    context.py         只读 RenderContext（替代散读 app_state 的散字段）
    registry.py        mode -> ModeAdapter 注册表 + 与 ui/render_modes.py 的一致性断言
    modes/             每个模式一个薄适配器
        two_d.py  three_d.py  ternary.py  v1v2.py  pb_evol.py
        plumbotectonics.py  mu_kappa.py  embedding_ml.py  kde.py
    common/  geo_layers.py  kde.py  view_state.py     ← 保留为共享绘制件
```

### 2.1 骨架（唯一的序列实现）

```
pipeline.run(mode, ctx):
    1  ctx = context.build(mode, ...)        # 一次性取齐数据/分组/样式，之后不再读全局
    2  adapter = registry.adapter_for(mode)  # 未知模式直接拒绝（白名单，取代"else 兜底"）
    3  adapter.validate(ctx)                 # 列选择/参数校验，所有模式统一有
    4  captured = capture_view(ctx.axes, adapter.token(ctx))
    5  ensure_axes(ctx, adapter.axes_spec(ctx))
    6  apply_current_style()  →  clear()  →  enforce_plot_style()  →  clear_plot_state()
    7  adapter.draw(ctx)                     # ← 模式唯一的"画什么"
    8  adapter.marginal(ctx)                 # 可选：边缘 KDE
    9  adapter.overlays(ctx)                 # 可选：模型曲线/等时线/方程叠加
   10  adapter.legend(ctx)                   # 统一走 common/legend
   11  adapter.title(ctx)                    # 统一走 common/title（含 display_group_col）
   12  restore_view(ctx.axes, captured, adapter.token(ctx))
   13  finish(ctx)                           # 布局/注释/selection overlay/重绘通知
   14  失败与空数据：由骨架统一处理（保模式、通知图例、draw_idle）
```

### 2.2 适配器接口（每个模式只实现这些）

```python
class ModeAdapter(Protocol):
    mode: str                       # 规范值，唯一拼写（见 2.4）
    def axes_spec(self, ctx) -> AxesSpec
    def validate(self, ctx) -> None
    def token(self, ctx) -> Hashable            # 内容身份：模式 + 影响画面的参数
    def draw(self, ctx) -> None
    def legend(self, ctx) -> None
    def title(self, ctx) -> None
    def capabilities(self) -> ModeCapabilities  # 见 2.5
    # 可选
    def marginal(self, ctx) -> None: ...
    def overlays(self, ctx) -> None: ...
```

### 2.3 令牌与视图（把踩过的坑变成机制）

- 令牌统一为 `(规范模式, 影响画面的参数…)`：2D/3D 用列元组，嵌入用算法 + 相关参数（现存实现只看算法，`pca_component_indices` 变了也不算新内容 —— 一并修正）。
- 视图保留只由骨架调用，任何模式**不可能**再"忘记保留视图"（3D 曾如此）。
- 用户可见命名一律经 `display_group_col`，伪列不可能再从任何出口泄漏。

### 2.4 模式拼写唯一化

- `ui/render_modes.py` 的 14 项即规范值；`Ternary`/`tSNE` 的规范化只在**一个**函数里发生，内部一律使用规范值。
- `ISOCHRON1/2`、`PB_MODELS_76/86`、`ROBUSTPCA` 等别名集中在同一处归一，且**归一到清单内的值**。
- 导入向导的第二份手写下拉（`data_import/build.py:285-300`）删除，改读唯一清单。

### 2.5 模式能力表（消灭"漏在清单外"）

```python
@dataclass(frozen=True)
class ModeCapabilities:
    uses_geochem_params: bool      # 换模型/参数后需要重绘
    shows_geochem_controls: bool   # 地学面板分区可见性
    shows_plumbotectonics_model: bool
    shows_isochron_controls: bool
    projection: str                # "2d" | "3d" | "ternary"
```

面板与对话框一律**查能力表**，不再各自维护模式元组（缺陷 6、7、8 的根因）。

## 3. 迁移顺序（每阶段全绿才提交）

| 阶段 | 内容 | 验收 |
|---|---|---|
| 0 | 14 模式参数化真渲染基线测试（安全网） | 每模式：能渲染、画出预期艺术家、刷新后视图不变、标题/图例命名正确、能力表驱动的可见性正确 |
| 1 | 新增 `pipeline.py`/`context.py`/`registry.py` + 守卫脚本 `check_render_modes.py`（清单 ⇄ 适配器 ⇄ 分派三方一致），旧代码不动 | 新守卫通过；旧测试全绿 |
| 2 | 2D、3D 搬入适配器（各一提交） | 基线逐项通过 |
| 3 | embedding 的 algorithm 分叉拆成适配器：TERNARY / V1V2 / PB_EVOL_76 / PB_EVOL_86 / PLUMBOTECTONICS_76 / PLUMBOTECTONICS_86 / PB_MU_AGE / PB_KAPPA_AGE / 4 个 ML 模式 | 基线逐项通过；异步路径**显式传 mode**（修缺陷 2） |
| 4 | 删除旧入口、三份重复序列、参数腐化项（`size`、`prev_2d_cols`、`prev_embedding_type`），不留兼容层 | 全量测试 + 守卫全绿 |
| 5 | 能力表驱动 UI（面板分区可见性、换模型重绘、列校验、导入向导清单） | 各缺陷 5/6/7/8 有回归测试 |

## 4. 验收基线

- 每个阶段：`uv run pytest`（当前 1917 passed）、`scripts/check_*.py --fail-on-hits` 全部 `TOTAL=0`、`locales/check_untranslated.py` 通过。
- 阶段 0 的 14 模式参数化测试在大改全程保持通过，是"行为不变"的唯一凭据。
- 大改完成后不得留下：兼容层、第二份模式清单、按模式枚举的元组清单（一律改为能力表查询）、未被使用的参数。
