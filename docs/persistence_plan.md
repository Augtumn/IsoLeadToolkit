# 持久化改进方案（Persistence Plan）

状态：**已实施**（2026-08-14）· 日期：2026-08-14 · 范围：缓存 + 会话 + 用户数据

> 实施摘要：新增 `core/persistence/` 包（原子写 / 白名单 schema / 自动保存 / 崩溃标记 / 可选 npz 缓存）；
> `params.json` 保留名 + `ui_state.json` 新增；投影参数预设迁出主题容器为独立 `param_presets`；
> 全套测试与守护脚本通过。详见 `docs/development_plan.md` 对应阶段条目。

## 1. 现状痛点（已核实）

| # | 痛点 | 现状 |
|---|------|------|
| P1 | **崩溃丢失**：仅退出时写一次 params.json；异常退出（崩溃/断电）丢失整个会话 | `closeEvent → save_session_params` 单点写入 |
| P2 | **自定义调色板/形状集重启丢失**：`custom_palettes`/`custom_shape_sets` 只在内存 StateStore | 无落盘（主题 `saved_themes` 有落盘，机制不一致） |
| P3 | **最近文件重启丢失**：`recent_files` 只在内存 | 导入向导的"最近文件"每次启动为空 |
| P4 | **图例顺序/父组布局部分丢失**：`parent_groups`/`parent_shape_map` 已入会话，但 `legend_item_order`/`visible_groups`/`hidden_groups` 不保存 | params.json 键集不全 |
| P5 | **嵌入缓存重启失效**：8 条 LRU 纯内存，重启后 UMAP/t-SNE 首次渲染重新计算（数秒） | 无落盘 |
| P6 | **文件分散、机制不一**：params.json（原子写✓）/ config.json / user_themes.json / QSettings×3（窗口/工具箱/对话框） | 4 种持久化路径，2 套写语义 |
| P7 | **无自动保存**：长会话中手工操作（父组拖拽、样式）不落盘 | — |

## 2. 设计目标

1. **不丢**：关键状态自动保存 + 崩溃恢复（启动时回滚到最近一致性快照）
2. **不重算**：可选持久化嵌入缓存（带签名校验，损坏自动丢弃）
3. **统一**：用户数据文件收敛到 `~/.isotopes_analysis/`，统一原子写 + 版本迁移
4. **兼容**：旧 params.json 自动迁移，QSettings 窗口状态保留（系统习惯）

## 3. 文件布局（`~/.isotopes_analysis/`）

| 文件 | 内容 | 写入时机 | 说明 |
|------|------|----------|------|
| `params.json`（保留名） | 会话：算法/参数/列选择/语言/主题/父组/形状 | 退出 + 自动保存(防抖) | 结构升级：加 `schema_version` 与 `saved_at` |
| `ui_state.json`（新） | 图例顺序/可见组/隐藏组/最近文件/自定义调色板/形状集/工具箱状态 | 变更即时 + 自动保存 | 由 StateStore 快照子集生成 |
| `user_themes.json`（保留） | 主题（现状不动） | 现状 | 保持兼容 |
| `config.json`（保留） | 用户配置 + 新增：`autosave_interval`/`cache_persist`/`max_recent_files` | 现状 | — |
| `embedding_cache.npz`（可选，新） | 嵌入缓存持久化 | 异步、低频 | `cache_persist=true` 时启用 |
| `session.lock` / `last_exit_ok` 标记 | 崩溃检测 | 启动/退出 | 正常退出写标记；启动时无标记 → 提示可恢复 |

## 4. 关键机制

### 4.1 统一原子写
现有 `_atomic_write_json`（tmp + fsync + rename）扩展到所有 JSON 文件；新增 `_atomic_write_npz`（缓存）。损坏文件（JSON 解析失败/校验和不符）→ 自动改名 `.corrupt-<ts>` 并告警，不阻塞启动。

### 4.2 自动保存调度（解决 P1/P7）
- `core/persistence/autosave.py`：QTimer 防抖（默认 30s，`config.json: autosave_interval` 可调），监听 StateStore dispatch 计数变化触发
- 关键操作**即时保存**：数据加载、父组增删、主题/调色板保存、语言切换（现有退出保存保留为最终兜底）
- 保存内容 = `session.json` + `ui_state.json` 的**快照子集**（从 `StateStore.snapshot()` 提取白名单字段，杜绝手写漂移——复用上轮加的 schema 漂移测试思路）

### 4.3 崩溃恢复（P1）
- 启动：读 `last_exit_ok`；缺失 → 上次未正常退出 → 加载最近快照并弹一次"已从崩溃中恢复最近状态"提示（可关）
- 加载策略：`ui_state.json` 优先 → 回退 `params.json`（旧会话）→ 回退默认
- 恢复校验：`saved_at` + `schema_version`；未来版本文件拒绝（沿用现有 version 上限逻辑）

### 4.4 嵌入缓存持久化（可选，解决 P5）
- `config.json: cache_persist`（默认 false，保守）
- 序列化：`{key: (embedding_npz, meta)}`，键含数据签名（**上一轮已加内容指纹**，天然校验）；加载时逐键复算 `build_data_signature` 比对，不匹配即丢弃
- 容量：持久化仅存最近 N 条（默认 4），总大小上限（默认 50MB），异步写不阻塞 UI
- 版本：缓存文件头含 schema 版本；升级即整体作废

### 4.5 统一读写层（P6）
新增 `core/persistence/` 包（约 400 行）：
```
persistence/
├── __init__.py      # 门面：save_all/load_all/register_autosave
├── paths.py         # 文件路径 + 目录管理 + lock/exit 标记
├── atomic.py        # 原子写（json/npz）+ 损坏恢复
├── autosave.py      # 防抖调度 + 即时保存触发器
├── session_store.py # params.json 读写/迁移（现有 io.py 迁移至此或委托）
├── ui_state_store.py# ui_state.json（图例/调色板/最近文件…）
└── cache_store.py   # 可选嵌入缓存持久化
```
`core/session/io.py` 保留为兼容入口，内部委托。

### 4.6 迁移兼容（P7 兼容目标）
- `params.json` 旧结构（无 schema_version 之前）→ 迁移器补 `saved_at`/`schema_version`
- `ui_state.json` 首次生成时从内存 StateStore 播种（不要求旧文件）
- QSettings 窗口几何**保持不动**（用户操作系统习惯，且现有代码稳定）

## 5. 实施步骤（建议顺序）

| 步骤 | 内容 | 工作量 | 风险 |
|------|------|--------|------|
| 1 | `persistence/` 骨架：paths + atomic + 损坏恢复 | 0.5 天 | 低 |
| 2 | 自动保存调度 + dispatch 触发钩子 + 退出兜底 | 0.5 天 | 低 |
| 3 | `ui_state.json`（调色板/形状集/最近文件/图例顺序/可见组）生成与恢复 | 1 天 | 中（StateStore 白名单提取需精确） |
| 4 | params.json 结构升级 + 迁移器 | 0.5 天 | 低 |
| 5 | 崩溃恢复（exit 标记 + 启动提示） | 0.5 天 | 低 |
| 6 | 嵌入缓存持久化（开关默认关） | 1 天 | 中（npz 序列化 + 签名校验） |
| 7 | 测试：原子写/迁移/恢复/缓存失效 + 全量回归 | 0.5 天 | — |

## 6. 风险与权衡

| 项 | 决策 |
|----|------|
| 自动保存写入频率 | 防抖 30s + 关键操作即时；写入量小（<100KB JSON），无性能顾虑 |
| 缓存持久化默认关闭 | 避免大文件与兼容负担；用户按需开启 |
| 多进程并发 | 单实例假设；若需多开，`session.lock` 仅作提示不强制 |
| 迁移破坏 | 所有写入原子 + 损坏自动隔离 + 版本上限拒绝，最坏回退默认 |
| 测试耦合 | 沿用 StateStore.snapshot() 白名单提取，配合已有 schema 漂移测试防手写漂移 |

## 7. 不做（明确排除）

- 不迁移 QSettings 窗口状态（保持系统习惯）
- 不做多用户/云同步/加密
- 不自动保存 ML 模型（体积大、可再训练；保留用户主动导出能力评估）

---

## 8. 应记录状态完整盘点（StateStore 188 键分类）

现状：`params.json` 仅保存约 17 个键；快照中约 100 个用户可配置字段不落盘。

### 8.1 应该记录 —— 第一优先（高频用户价值）

| 组 | 字段 | 理由 |
|----|------|------|
| **显示面板全套样式** | plot_style_grid / plot_marker_size / plot_marker_alpha / show_plot_title / plot_dpi / plot_facecolor / axes_facecolor / custom_primary_font / custom_cjk_font / plot_font_sizes | 用户调好的配色/字体/刻度重启即失 |
| **网格/刻度/坐标轴** | grid_color/linewidth/alpha/linestyle、tick_direction/color/length/width、axis_linewidth/axis_line_color、minor_ticks/minor_tick_length/minor_tick_width、show_top_spine/show_right_spine、minor_grid/minor_grid_*/minor_ticks | 同上 |
| **散点/文本** | scatter_show_edge/edgecolor/edgewidth、label_color/weight/pad、title_color/weight/pad、legend_frame_on/alpha/facecolor/edgecolor、adjust_text_force_text/force_static/expand/iter_lim/time_lim、confidence_level、draw_selection_ellipse | 同上 |
| **混合分组** | mixing_endmembers / mixing_mixtures | **手工圈定的端元/混合分组，丢失代价最高** |
| **用户自定义方程** | equation_overlays | 手工输入的覆盖方程 |
| **覆盖层开关与线宽** | show_model_curves / show_paleoisochrons / show_isochrons / show_model_age_lines / show_growth_curves / show_plumbotectonics_curves / show_equation_overlays / show_kde / show_marginal_kde、model_curve_width / plumbotectonics_curve_width / paleoisochron_width / model_age_line_width / isochron_line_width / selected_isochron_line_width、line_styles | 图层的显隐与样式 |
| **算法参数补齐** | pca_params / robust_pca_params / ml_params / v1v2_params | 现有仅 umap/tsne 入会话，其余 4 组不存 |

### 8.2 应该记录 —— 第二优先（配置类）

| 组 | 字段 |
|----|------|
| 图例显示 | legend_columns / legend_display_mode / legend_position / legend_location / legend_nudge_step / legend_offset / color_scheme |
| 当前映射 | current_palette / group_marker_map（用户手动改过的颜色/形状） |
| 等时线误差 | isochron_error_mode / isochron_sx_col / isochron_sy_col / isochron_rxy_col / isochron_sx_value / isochron_sy_value / isochron_rxy_value、isochron_label_options |
| 古等时线 | paleoisochron_ages / min_age / max_age / step |
| Plumbotectonics | plumbotectonics_variant / plumbotectonics_group_visibility / geo_model_name / use_real_age_for_mu_kappa / mu_kappa_age_col |
| 三元图 | ternary_auto_zoom / limit_mode / limit_anchor / boundary_percent / manual_limits / manual_limits_enabled / stretch / stretch_mode / factors / ranges |
| KDE | kde_style / marginal_kde_style / marginal_kde_*（bandwidth/bw_adjust/kernel/auto_bandwidth_method/gridsize/cut/log_transform/max_points/top_size/right_size） |
| 其他 | standardize_data / pca_component_indices / show_tooltip / tooltip_columns（已存）/ last_group_col（已存） |

### 8.3 不应记录（瞬态/渲染产物/大对象）

| 类别 | 字段 | 说明 |
|------|------|------|
| 数据本体 | df_global | 重、可重载（file_path/sheet 已存） |
| 派生诊断 | last_embedding / last_pca_variance / last_pca_components / current_feature_names | 由缓存/重算机制负责 |
| 渲染产物 | overlay_artists、overlay_curve_label_data / paleoisochron_label_data / plumbotectonics_label_data / plumbotectonics_isoage_label_data、legend_last_title/handles/labels、selected_isochron_data、marginal_axes | 含 artist 引用，重建时重新生成 |
| 瞬态标志 | selection_mode / selection_tool / selected_indices / embedding_task_* / initial_render_done / adjust_text_in_progress / overlay_label_refreshing / paleo_label_refreshing / preserve_import_render_mode / data_version / available_groups | 运行期语义 |
| 计算缓存 | isochron_results / ml_last_result / ml_last_model_meta | 可重算（ml_params 才值得存） |

### 8.4 快照之外的附加建议

- `export_image_options`（导出预设选择）落盘至 `ui_state.json`
- 崩溃前 `render_mode` 已随会话保存；轴缩放（matplotlib 状态）不存（低价值）
- 日志归档/窗口几何已有机制，不重复

### 8.5 参数预设（用户指出的散乱典型）

**现状问题**（`ui/panels/data/_projection.py:418-603`）：
1. 投影参数预设（UMAP/tSNE/PCA/RobustPCA/ml/v1v2 参数 Save/Load）**寄生在主题容器** `saved_themes["projection_presets"]`，与显示主题混存于 `user_themes.json`——语义错位，主题列表可能误显示；
2. **绕过 gateway 原地修改** `saved_themes`（该文件在 guard ALLOWLIST 中豁免）→ store 快照不同步、下次 dispatch 回滚；且**手写 `json.dump` 非原子**；
3. 与自动保存/白名单方案冲突（预设 ≠ 主题）。

**改进**：
- 新增独立 `param_presets` 存储（`ui_state.json`）：`{name: {umap/tsne/pca/robust_pca/ml/v1v2 params}}`
- 经 gateway（`set_param_presets`）读写，纳入自动保存与白名单
- 启动迁移：`saved_themes["projection_presets"]` → `param_presets` 后清空；主题列表不再混入
- 内置预设（地球化学模型/导出期刊/预设方程）为代码常量，不落盘（维持现状，不属于散乱）

**实现要点**：持久化白名单 = 8.1 + 8.2 + 8.5 字段集，从 `StateStore.snapshot()` 程序化提取（复用 schema 漂移测试思路，杜绝手写漂移）；8.3 显式排除并加守卫测试（防止未来把不可序列化字段误入白名单）。
