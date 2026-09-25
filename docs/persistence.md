# 持久化（Persistence）

用户数据统一落在 `~/.isotopes_analysis/`，由 `core/persistence/` 提供原子写、崩溃隔离与自动保存。

## 1. 文件布局

| 文件 | 内容 | 写入时机 |
|------|------|----------|
| `params.json` | 会话：算法/参数/列选择/语言/主题/父组/形状，含 `schema_version`、`saved_at` | 退出 + 自动保存（防抖） |
| `ui_state.json` | 图例顺序/可见组/隐藏组/最近文件/自定义调色板与形状集/`param_presets` | 变更即时 + 自动保存 |
| `user_themes.json` | 显示主题（兼容保留；投影参数预设已迁出至 `param_presets`） | 主题保存时 |
| `config.json` | 用户配置覆盖（`autosave_interval`、`cache_persist`、`max_recent_files` 等） | 设置变更时 |
| `embedding_cache.npz` | 可选嵌入缓存（`cache_persist=true` 时启用） | 异步、低频 |
| `last_exit_ok` | 正常退出标记；启动时缺失 → 提示可从最近快照恢复 | 正常退出 |

路径常量见 `core/persistence/paths.py`。损坏文件重命名为 `<name>.corrupt-<时间戳>` 并告警，不阻塞启动。

## 2. 关键机制

- **原子写**（`atomic.py`）：临时文件 + `fsync` + `rename`，JSON 与 npz 统一走同一入口；解析失败的文件隔离为 `.corrupt-<ts>`。
- **自动保存**（`__init__.py`）：QTimer 防抖（`DEFAULT_AUTOSAVE_INTERVAL = 30s`）或 dispatch 计数达到 `DEFAULT_AUTOSAVE_DISPATCHES = 20` 触发；数据加载、父组增删、主题/调色板保存、语言切换等关键操作即时保存；退出保存为最终兜底。
- **快照白名单**（`schema.py`）：落盘字段按白名单从 `StateStore.snapshot()` 程序化提取，避免手写漂移；白名单外的字段保持内存语义。
- **崩溃恢复**：启动读 `last_exit_ok`，缺失则按 `ui_state.json` → `params.json` → 默认 的顺序回退；用 `schema_version`/`saved_at` 校验，未来版本拒绝加载。
- **缓存持久化**（`cache.py`）：仅存最近 N 条（默认 4）、总量上限（默认 50MB）；缓存键含数据签名，加载时复算比对，不匹配即丢弃。
- **迁移**：旧 `saved_themes["projection_presets"]` 一次性迁入 `param_presets` 并清理；QSettings 窗口几何保持不动（系统习惯）。

## 3. 状态白名单口径

**落盘**：

- 显示样式：网格 / 刻度 / 坐标轴 / 散点 / 文本 / 图例框 / 字体与画布 / 置信度
- 混合分组（`mixing_endmembers`、`mixing_mixtures`）与用户自定义方程
- 覆盖层开关与线宽、各算法参数（umap / tsne / pca / robust_pca / ml / v1v2）
- 图例显示、当前调色板与形状映射、等时线误差模式、古等时线年龄、Plumbotectonics、三元图、KDE 样式
- 投影参数预设 `param_presets`（独立存储，不再混入主题）

**不落盘**：

- 数据本体（`df_global`：按 `file_path` / `sheet` 重载）
- 派生诊断与渲染产物（`last_embedding`、`overlay_artists`、各类 label data、`marginal_axes` 等）
- 瞬态标志（`selection_mode`、`selected_indices`、`embedding_task_*` 等）
- 可重算缓存（`isochron_results`、`ml_last_result`）

## 4. 明确排除

- 不迁移 QSettings 窗口状态（保持系统习惯）
- 不做多用户 / 云同步 / 加密
- 不自动保存 ML 模型（体积大且可再训练）
