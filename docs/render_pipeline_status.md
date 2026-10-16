# 绘图架构大改：交付状态（实事求是）

本文记录这次受控大改**真正交付了什么**、**什么还没做**以及**为什么**。分析过程见
[render_pipeline_architecture.md](render_pipeline_architecture.md)。

## 一、已完成

| 阶段 | 内容 | 证据 |
|---|---|---|
| 0 | **14 个模式的参数化基线测试**（42 条：能渲染/画出样本/标题算得出 · 刷新后视图保留 · 标题用用户选的分组列名且不打印工作列） | `tests/test_render_modes_baseline.py`，全绿 |
| 1 | **模式清单下沉 `core/render_modes.py`**（删除 `ui/render_modes.py` 与导入向导里手写的第二份清单）；每个模式一份**能力记录**；新增第 14 个守卫 `scripts/check_render_modes.py` | 守卫 `TOTAL=0`，且**被反证过**：清单缺能力/能力缺模式/值重复/异步集合不符都会报错（反证已固化为测试） |
| 2 | **唯一渲染骨架** `rendering/pipeline.py` + 只读 `context.py` + `registry.py`；**2D 与 3D 适配器**；`plot_2d_data`／`plot_3d_data` 改为走骨架（旧函数体删除，无兼容层） | 42 条基线全过；骨架序列由 `tests/test_render_pipeline_steps.py` 固定；单例散读 **204 处/31 文件 → 184 处/34 文件** |
| 3（部分） | 骨架接口按嵌入族**真实用法**修好：`configure_axes(context, prepared)`、context 携带算法参数与预算嵌入；**缺陷 2 根治**：异步路径不再读全局模式，mode 随请求传递 | `tests/test_async_render_mode.py`；实测"全局=2D、请求=UMAP ⇒ 启动 UMAP" |
| 5 | **能力表驱动 UI**：地学面板分区可见性、换模型是否重绘、会话算法恢复全部改为查能力表；**界面里已无手写模式元组**（`git grep "render_mode in (" -- ui` 无命中） | `tests/test_render_modes_capabilities.py` + 替换前**逐项证明等价**（6/2/2/1/7 全对） |

顺带修掉的真缺陷（都是"清单漏项"或"全局状态"这一类）：

1. 地体构造面板不显示控件（面板只在构建时算过一次可见性）；
2. 地体构造模式下换模型不重绘（重绘清单漏了这两个模式）；
3. PCA / RobustPCA 会话加载后不恢复算法（清单只列了 UMAP/tSNE）；
4. 多面板下异步渲染会串到别的面板的算法（异步路径读全局模式）；
5. 3D 标题会把分解的工作列 `__decomposed_group__` 印出来（最后一处该泄漏）；
6. 视图保留：3D 从未捕获过视图；嵌入族恢复判据用了全局值。

## 二、已完成（全部阶段）

| 阶段 | 内容 | 证据 |
|---|---|---|
| 3 | **11 个嵌入模式全部搬入适配器**（TERNARY / V1V2 / PB_EVOL_76,86 / PLUMBOTECTONICS_76,86 / PB_MU_AGE / PB_KAPPA_AGE / UMAP,tSNE,PCA,RobustPCA）；`plot_embedding` 从 237 行分支函数变为 45 行"取上下文 + 跑骨架" | 14 模式基线 **原样 42 全过**；`adapters/embedding_modes.py` |
| 3 | **缺陷 2 根治**：异步路径不再读全局模式 | `tests/test_async_render_mode.py` |
| 3 | **卡住搬迁的根因**：`geo_layers` 用旧令牌**无条件覆盖**骨架令牌 ⇒ 骨架永远判定"画面变了" ⇒ 视图不恢复 | 对照实验（2D 路径必正常）+ `tests/test_overlay_view_keeps.py` |
| 4 | **删除旧入口与重复序列**：2D 的两个死函数 ✓ 嵌入的 200 行序列 ✓ `prev_*` 参数（生产端已无人传真值 ✓ 核实后删除 ✓） | `git grep prev_embedding_type` 无命中 |
| 4 | **守卫收紧**：`check_render_modes.py` 现在要求**每个模式都有适配器**，并**已反证**：从注册源去掉 Ternary ⇒ 报 `no adapter draws Ternary` | 见守卫输出 |

单例散读的下降轨迹：**204 → 195 → 184 → 181 → 166**（35 文件）—— 渲染序列从三个渲染器里各一份，变成骨架里一份。

## 三、遗留（不影响正确性，供后续判断）

- `geo_layers` 的导入里可能仍有只为旧参数服务的名字；`scripts/release_check.py` 只纳入 4 个守卫
  （未纳入 panel_singletons / silent_exceptions / cross_mixin_calls / layer_dependencies）。

## 四、给下一次接手的最小步骤

1. 先跑 `uv run pytest tests/test_render_modes_baseline.py -q`（14 模式安全网，必须全绿）；
2. 任何新模式：在 `core/render_modes.py` 加一条**能力记录**，写一个适配器并注册；
   `check_render_modes.py` 会检查"清单 ⇄ 能力 ⇄ 适配器"三方一致；
3. 每步跑全量：`uv run pytest` + `scripts/check_*.py --fail-on-hits`（14 个）+ `locales/check_untranslated.py`。

## 五、本次大改遵守的纪律

- 只做**读得到的改动**：替换硬编码清单前先打印新旧结果**逐项比对**；先读用途再决定是否"修"
  （两次因先读而避免误改：`session.py` 那处、`grouping.py` 那处）。
- **探针先行**：视图是否保留、异步是否串模式、控件是否显示、守卫是否真会失败，全部用真代码回答。
- 一次一个可提交的步：全量 pytest + 14 守卫 + 翻译**全绿才提交**；宁可回退也不留半成品
  （嵌入搬迁第一次尝试被**主动回退**，第二次带证据重做）。
- 未做的不写成做了：本文档的"遗留"一节如实列出。

## 三、给下一次接手的最小步骤

### 阶段 3 目前的障碍（本轮新增的证据，别再走回头路）

- **已排除：axes 被重建。** 探针显示起始 axes、第一次渲染后、第二次渲染后三者 `id` 全等，
  `_ensure_axes(dimensions=2)` 也返回同一对象。
- **已排除：令牌不一致。** 第二次渲染后 `view_state.drawn_last(ax)` 与
  `context.token(*adapter.token(ctx))` **相等**。
- **仍存在的矛盾（必须先解释，别急着改代码）**：在同一次探测里，`restore_view` 收到正确的
  `captured`（用户的 2.0–4.0）与正确的 token，却**返回 False**；而同一时刻手工比较
  `drawn_last(ax) == token` 又是 **True**。两者不能同时成立 ⇒ 下一步应逐帧记录
  `mark_drawn` / `restore_view` 的**入参对象身份与 token 值**（本轮已写过一次这样的探针，直接复用），
  而不是再猜机制。
- **试验过并已撤销**：在 `restore_view` 里先 `set_autoscale_on(False)` 再设范围——**未被证实有效**，
  按"不加无据补丁"的纪律撤回（当时 2D/3D 测试仍全过，说明该改动无害，但也无益）。

1. 先跑 `uv run pytest tests/test_render_modes_baseline.py -q`（14 模式安全网，必须全绿）；
2. 按 `adapters/two_d.py` 的形态写嵌入适配器（**不要**命名 `embedding.py`，会遮蔽 `rendering/embedding/` 包；
   放在 `adapters/` 下时相对导入要两个点，指向 `visualization/plotting/` 的要三个点）；
   `decorate` 用 `resolve_embedding_params` **解析后**的参数（未解析的是 `None`）；
   `finish` 里的边缘 KDE **必须早于**恢复视图（它会改写主轴范围）；
3. 先解释上面那条矛盾，再动骨架；
4. 每步跑全量：`uv run pytest` + `scripts/check_*.py --fail-on-hits`（14 个）+ `locales/check_untranslated.py`。

## 四、本次大改遵守的纪律

- 只做**读得到的改动**：每次替换硬编码清单前，先打印新旧结果**逐项比对**；先读用途，再决定是否"修"。
- **探针先行**：视图是否保留、异步是否串模式、面板控件是否显示，都用真代码探针回答，不靠推测。
- 一次一个可提交的步：全量 pytest + 14 守卫 + 翻译**全绿才提交**；宁可回退也不留半成品。
- 未做的不写成做了：阶段 3 主体与阶段 4 遗留项在上表明确标注。
