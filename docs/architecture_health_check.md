# 架构体检报告

本报告只写**可测量的事实**与**有证据的判断**。方法：静态导入图 + AST 统计 + 守卫实测，全部数字可用文末命令复现。
范围：`main` 分支（本报告落库时的 HEAD）。

## 一、总体判断

**骨架是健康的；问题不是"散"，而是三处"重"与两处"多副本"。**

| 维度 | 结论 | 依据 |
|---|---|---|
| 循环依赖 | **0 个**（同层模块间强连通分量） | 导入图 |
| 分层违规 | **0 处** | `scripts/check_layer_dependencies.py`（presentation={ui,visualization} · application · domain={data} · infrastructure={core,utils,adapters}） |
| 完全重复函数（AST 级） | **1 组**（两个 locale 脚本里的同名小函数） | AST 体哈希，≥6 条语句 |
| 代码规模 | 生产 ~5 万行 / 测试 2.3 万行 / 守卫 1307 行（2.6%） | 文件统计 |

⇒ 这套代码**不是**"复制粘贴堆出来的"，分层与依赖方向是干净的。**不要**因为"感觉乱"而大改结构 ✗ —— 该动的是下面三处重心 ✓。

## 二、三处"重"

### 2.1 状态模型（第一重心）

| 度量 | 值 | 出处 |
|---|---|---|
| 快照投影键 | **142** | `core/state/store.py` |
| dispatch 动作类型 | **179** | `core/state/_dispatch_handlers.py` |
| 新增一个字段的成本 | **4 个文件**（`fields.py` / `store.py` / `_dispatch_handlers.py` / `persistence/schema.py`；gateway 与 normalizer 走通用路径，需 0 处） | 实测 |
| 为它存在的守卫 | **6 个**（state_mutations / gateway_direct / gateway_generic / state_dict / state_field_coverage / state_sync_coverage） | `scripts/` |

**判断**：这不是"上帝对象"式的失控 ✓（字段有登记、写入有门户、覆盖有守卫 ✓），而是一个**把所有功能的可变状态集中在一处**的设计 ✓。它的代价不在正确性，而在**每加一个功能都要在 4 个地方登记**，且 6 个守卫必须一直维护。

### 2.2 `canvas.py`（1535 行，8 类职责）

主工具栏构建/重建 · MDI 面板注册表 · 视图成帧 · 覆盖层标签重排（**其中 `_refresh_labels_for` 在 `:464` 定义，全仓无任何引用 ✗，且与 `:100-140` 逐字重复**）· 选择工具状态 · 轴锁/悬停开关 · Qt 事件过滤器（约 490 行）· 类属性契约。

**判断**：它是**唯二单点**之一（另一个是 1167 行的 `silverquest_dialog.py`）。拆分方案见 `docs/ui_architecture_review.md`（审查报告已存）。

### 2.3 面板体系

6 面板 = 24 个 mixin / 18 个文件；`build()` 有 7 份、`reset_state()` 有 8 份手写实现（`data/build.py:48-79` 恰好 30 行 `self.x = None`）；控件→状态有**三条路径**（表驱动 `_STYLE_WIDGET_MAP` · 逐控件手写 · 翻译覆盖），且消费方用 `getattr(self, attr, None)` **静默跳过** ✗ —— 新增控件忘记赋值不会失败，只会不生效。

## 三、两处"多副本"（真正会生 bug 的地方）

### 3.1 面板状态有 4 个表示 ✗

| 表示 | 引用次数 | 说明 |
|---|---|---|
| `app_state.plot_panels` | 19 | 模式列表 |
| `app_state.plot_panel_windows` | 23 | 窗口/图形/画布记录 |
| `app_state.plot_panel_states` | 13 | 每条记录的渲染状态 |
| `PanelWindows._records` | 30 | `mdi_panels` 的内部记录 |

**这四个表示今天必须手工保持一致** ⇒ 今天修的两个面板 bug（关非末位面板丢错窗口 ✓ 边缘 KDE 只能一个面板显示 ✓）都出在这里 ✓。

**方向**：让 **`PanelRecord` 成为唯一契约**（纯数据、无 Qt，放在 `visualization/plotting/panels.py`），把 43 处 `record.get("…")` 换成属性访问，并让 `PanelWindows.sync` 成为唯一生产点。

### 3.2 渲染模式相关：2 处真重复 ✗

- `visualization/plotting/panels.py` 的 `PROJECTIONS` 是**第二份**投影映射（`MODE_CAPABILITIES.projection` 之外 ✓），`check_render_modes.py` **不检查它** ✗；
- `_ASYNC_EMBEDDING_ALGORITHMS` 在 `application/use_cases/render_plot.py` 与 `visualization/events.py` **各有一份** ✗（守卫强制一致，但仍是两份 ✓）。

**方向**：删 `PROJECTIONS` 改用 `capabilities_for(mode).projection`，并把守卫扩一条"适配器投影 == 能力投影"；异步集合只留一份。

### 3.3 另外两处小的"多副本"

- **每面板图例**：全局 `legend_position`/`legend_location` 各被引用 32/33 次，而每面板 `record["legend"]` 只被引用 **1** 次 ✗ ⇒ 这是一个"存在但不会持久化"的选项（重启即丢 ✓）⇒ 要么做成真状态，要么去掉；
- **paleoisochron**：`ages` 是 `min/max/step` 的派生量却与三者一起持久化（各 ~14 次引用 ✓）⇒ 会话文件可能出现互相矛盾的组合；应由 dispatch 层重算、只持久化 min/max/step。

## 四、问题清单（分三档，避免"什么都要改"）

### 必须改（会继续生 bug）

1. **面板 4 表示 → `PanelRecord` 单一契约**（§3.1）。验证：`git grep 'record\.get('` 归零；两面板各画 UMAP/2D 并切换激活面板，两个面板都完成绘制。
2. **`canvas.py` 拆分 + 视图计算下沉 `visualization/plotting/view_fit.py`**（§2.2）。验证：`test_fit_panels / test_fit_policy / test_panel_windows_wiring / test_ternary_zoom_qt / test_view_zoom / test_multi_panel_end_to_end` 全绿；`check_panel_singletons` 基线下降。
3. **删除 `_refresh_labels_for` 死代码**（`:464` 无引用 ✓ 与 `:100-140` 重复）。验证：无测试引用它即可删。

### 值得改（成本可控、收益明确）

4. **`PROJECTIONS` 并入能力表**（§3.2）；
5. **异步算法集合去重**（§3.2）；
6. **每面板图例做成真状态或删除**（§3.3）；
7. **paleoisochron 派生量由 dispatch 层重算**（§3.3）；
8. **面板控件显式容器**（`PanelWidgets`），删 98 处 `= None` 影子声明（§2.3）。

### 可以不改（记录在案，避免反复讨论）

- **142 字段 / 179 动作的状态模型**：它是"全局状态中心"设计的自然结果，且有 6 个守卫在防 ✓ 简化它是一次**大工程** ✓ 建议**先做 1/2/3**，看面板契约收拢后字段是否自然减少 ✓ 再决定 ✓；
- **守卫 1307 行（2.6%）**：成本合理 ✓ 保留 ✓；
- **`silverquest_dialog` 1167 行 / `adapters/silverquest` 1142 行**：前者是一个完整功能的对话框 ✓ 后者是对 R 脚本的移植 ✓ 拆分收益低于风险 ✓；
- **`metadata_profile/*`（三个 700–1073 行文件）**：数据格式的表驱动实现 ✓ 测试很厚（`test_metadata_ratios_validate` 56KB）✓。

## 五、如何复现本报告的数字

```bash
uv run python scripts/check_layer_dependencies.py --fail-on-hits     # 分层违规 0
uv run python scripts/check_render_modes.py --fail-on-hits           # 模式清单/能力/适配器一致
uv run python scripts/check_panel_singletons.py --fail-on-hits       # 单例访问棘轮
uv run python scripts/check_cross_mixin_calls.py --fail-on-hits      # 跨 mixin 调用声明
# 导入图 / 循环依赖 / 重复函数 / 上帝文件：见本次体检用的一次性 AST 脚本（未入库，按需重写）
```

**下一次动结构前**：先跑上一节的命令，并把"面板 4 表示是否已收拢成一个"作为唯一的结构进度指标 ✓。
