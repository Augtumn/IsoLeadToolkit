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
| **A** | 声明式状态字段注册表（消灭漏登记类 bug） | **已完成（基线组）**：`core/state/fields.py` 声明 10 个 ternary/limit 字段，初始快照、投影、回写、持久化白名单四处由声明派生；守卫 `check_state_sync_coverage.py` 探测 174 字段；`tests/test_state_fields.py` 16 例。迁移中顺带发现并修复 `ternary_render_margin` **未纳入持久化白名单**（跨会话丢失） |
| **B** | 组合根 + 显式依赖 | **已完成**：组合根 `build_main_window()`（`ui/app.py` 亦使用）、`tests/conftest.py` 的 `qapp`/`main_window` 夹具、4 个真实窗口测试；**95 处 `hasattr/getattr(self, …)` 探测全部迁移为显式类属性声明（现为 0）**，迁移工具 `scripts/migrate_self_probes.py`，棘轮守卫 `check_self_attribute_probes.py` 保持为 0 |
| **C** | 图例单一真源 | **进行中**：显示策略已从 8 处重复判定（三种写法，对 outside_* 新值语义不一致）收敛到 core/legend_state.py 的 wants_inline_legend() / wants_docked_legend()，tests/test_legend_policy.py 覆盖；投影化（图内图例与 zorder 由面板列表派生）仍待定语义 |
| **D** | 统一输入管线并写入 `docs/dev_conventions.md` | 待做 |
| **E** | 日志语义分离 | **已完成** |
| **F** | 布局策略定案（三元图不用 constrained_layout） | 待做 |

## 判断

分层方向（`core ← data ← visualization ← application ← ui`）是合理的；问题不在分层，而在**组合与契约层缺失**，以及"每个状态字段的登记成本"与收益严重失衡。因此收敛重点是**把隐式约定变成显式声明**（A、B），而不是重写。
