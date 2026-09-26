# UI 框架评审（含量化数据与收敛计划）

本文件记录对 UI 层结构性缺陷的评审结论与收敛顺序。**过程由 git 历史承担**；本文件只保留"问题 → 证据 → 方向 → 状态"。

## 量化事实（评审时实测）

| 指标 | 数值 |
|---|---|
| `ui/` 规模 | 103 个文件 / 15,360 行 ≈ 全项目 40%（303 文件 / 38,882 行） |
| `ui/main_window_parts/` 的 mixin 类 | 10 个 |
| UI 层 `hasattr(self, …)` / `getattr(self, …)` 自省探测 | 74 处 |
| 新增一个状态字段需改动处数 | `ternary_render_margin`：core 5 文件 + ui 3 文件 + 测试 2 文件 |
| 约束框架自身不变式的守卫脚本 | 7 个（`scripts/check_*.py`） |

## 五个结构性缺陷

### 1. mixin 组合依赖隐式契约（无接口、无 owner）

10 个 mixin 通过 `self` 共享 74 处运行时探测的属性（`self._legend_list`、`self.toolbar`、`self.legend_splitter`…），谁在何时设置、谁可以依赖全靠约定。

- 后果：静态不可判定 → 需要自研守卫 `check_panel_self_resolution.py`；跨 mixin 调用迫使守卫放宽到组合类；UI 行为测试必须临时构造假宿主。
- 方向：组合根 + 显式依赖（`build_main_window()` 工厂，mixin 接收显式上下文），并用测试夹具替代假宿主。

### 2. 状态字段是仪式化登记，遗漏静默

一个字段要在 `bootstrap`（默认值）、`_normalizers`（强转 + 回写同步）、`_dispatch_handlers`、`persistence/schema`（白名单）、`store`（初始快照 + 投影两处）、`gateway`（setter）、测试镜像中各登记一次。

- 实证：`ternary_render_margin` 漏在回写清单 → 每次派发刷 `modified outside the gateway`，且值永远送不到渲染层。
- 现状：已加运行时守卫 `scripts/check_state_sync_coverage.py`（**先扰动再同步**，探测 174 个字段）兜住这一类遗漏。
- 方向：声明式注册表（字段 → 类型/默认值/持久化/回写），把 6 处登记降为 1 处。

### 3. 视图与控制器混层，同一语义多份实现

面板既渲染又直接读写 `state_gateway`；"图内/图外互斥"这类**策略**写在按钮处理函数里；图例语义同时存在于面板列表、matplotlib 图内图例、`_apply_legend_z_order`、`_bring_to_front`、`group_to_scatter` / `legend_to_scatter` 映射。

- 实证：切回"图外左侧"面板不显示（`_apply_legend_panel_layout()` 的缓存有两条出口，其中一条未写缓存）。
- 方向：图例单一真源（面板列表为模型，图内图例与 zorder 为投影）。

### 4. 输入层两套栈，归属不清

悬停/点击走 matplotlib `mpl_connect`；三元拖拽缩放**实测**必须走 Qt 事件过滤器（mpl 回调收不到事件）。

- 方向：统一输入管线并在 `docs/dev_conventions.md` 写明（画布手势一律 Qt 过滤器；matplotlib 事件仅在验证过的地方保留）。

### 5. 日志语义混淆

`setup_logging()` 把 stderr 整体接到 ERROR，而 `warnings` 模块正是写到 stderr 的 → `isotopes_analyse.error.log` 被 `UserWarning` 淹没；同时视图层大量 `except Exception: pass/debug` 把真实错误吞成静默。

- 状态：已修（`level_for_stderr_line()` 降级 + `enable_warning_capture()` 从源头改道）。
- 待办：视图层异常至少记 WARNING。

## 收敛顺序与状态

| 项 | 内容 | 状态 |
|---|---|---|
| **A** | 声明式状态字段注册表 | **已完成（全量）**：`core/state/fields.py` 驱动 **159 个字段**（默认值 + `normalize`/`copy` + 非对称时的 `project`/`restore` + `holder`；带参强转用 `functools.partial`）；**所有已持久化字段均由注册表驱动**，store 两个字典各只剩一处 `**` 解包、`_normalizers` 只剩一次 `sync_fields()`；仅 **40 个瞬态字段**（运行时不持久化）保持显式，由 `check_state_field_coverage.py` 登记；`check_state_sync_coverage.py` 扰动 174 字段无缺口 |
| **B** | 组合根 + 显式依赖 | **已完成**：组合根 `build_main_window()`（`ui/app.py` 亦使用）、`tests/conftest.py` 的 `qapp`/`main_window` 夹具、4 个真实窗口测试；**95 处 `hasattr/getattr(self, …)` 探测全部迁移为显式类属性声明（现为 0）**，迁移工具 `scripts/migrate_self_probes.py`，棘轮守卫 `check_self_attribute_probes.py` 保持为 0 |
| **C** | 图例单一真源 | **已完成**：显示策略收敛到 `core/legend_state.py`（原先 8 处重复、三种写法）；模型为面板列表顺序（`app_state.legend_item_order`，拖拽时持久化），图内图例条目顺序经 `legend_order_permutation()` 由模型派生（保留 30 项上限与父分组折叠，并行数组同步重排以免图例点击错配图层），zorder 由列表顺序派生；`tests/test_legend_policy.py`、`tests/test_legend_projection.py` 覆盖 |
| **D** | 统一输入管线并写入 `docs/dev_conventions.md` | **已完成**：`docs/dev_conventions.md` §19 规定画布手势一律走 Qt 事件过滤器（`mpl_connect` 实测收不到事件）、多副本经 `globalPos()` 映射、不得在不可映射副本上销毁手势、交互按工具/模式分流、必须用真实 Qt 事件测试 |
| **E** | 日志语义分离 | **已完成** |
| **F** | 布局策略定案（三元图不用 constrained_layout） | **已完成**：`use_ternary_layout()` 在 `configure_ternary_axis()` 中关闭布局引擎，`_render_2d_title_and_axes()` 在 2D 渲染时恢复；`tests/test_ternary_layout.py` 4 例含「绘制不再出现 collapsed to zero」 |

## 判断

分层方向（`core ← data ← visualization ← application ← ui`）是合理的；问题不在分层，而在**组合与契约层缺失**，以及"每个状态字段的登记成本"与收益严重失衡。因此收敛重点是**把隐式约定变成显式声明**（A、B），而不是重写。
