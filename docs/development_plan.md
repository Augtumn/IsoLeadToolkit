# 开发规划（仅待办）

本文件**只记录尚未开始或尚未完成的工作**。已完成的功能、修复与重构不在此留痕——过程与决策由 git 历史承担（提交信息 + 代码 + 对应模块文档即是最好的记录）。非平凡改动手前在此登记条目；条目完成后**直接删除**，不要新增"已完成/阶段进展"小节。

## 待办

### 兜底与兼容回退清理（按"不静默兜底、该报错就报错"的标准）

规范已改（§9.2 只对真可选依赖探测、§11.2 状态字段直接访问、§14.3 不保留兼容层、§18.6 新准则），
静默异常已清零（`check_silent_exceptions.py` 扫全部生产包，基线为空），状态 `getattr` 默认值已清 41 处。
**剩余**：

- [ ] **可选的"运行时句柄"探测（35 处）**：`last_embedding`、`current_plot_title`、`canvas`、
      `lasso_selector`、`legend_ax`、`show_2d_kde`、`group_reveal_callback` 等属性目前只在真正用到时
      才被赋值，所以读取处仍用 `getattr(..., None)`。要么在 `core/state/bootstrap.py` 里全部初始化为
      `None`（并同步 `check_state_field_coverage.py` 的白名单），然后把探测改成直接访问；要么明确
      把这批属性登记为"可缺省运行时句柄"。二选一，别长期悬着。
- [ ] **`getattr`/`.get` 的其余存量**：非状态目标（Qt 控件、matplotlib 对象、字典载荷）约 325 处，
      逐个判断"是语义默认还是掩盖错误"。语义默认（可选字段的 `.get(key, default)`）保留。
- [ ] **外部数据格式的读取兼容**（会话文件、录入工作簿旧版本）：§14.3 的唯一例外，若发现"旧格式
      静默按新格式读"的路径，改为显式版本分支 + 日志。
### 插件系统

- [ ] **第三方插件自动发现**：当前只扫描 `plugins/builtins/` 与用户插件目录，pip 安装的外部包无法注册；改为 setuptools entry points（`plugins/manager.py`）。

### 机器学习（`provenance_ml` 插件）

- [ ] **显式 train/valid/test 划分**与固定随机种子的可复现报告（现状只有 StratifiedKFold 交叉验证，无独立测试集）。
- [ ] **per-label 判定阈值**搜索与结果导出。

### 类型注解收口

- [ ] 按 `docs/dev_conventions.md` §10「新增/重构函数必须标注」逐步补齐 `ui/` 与 `plugins/`。
      当前覆盖率：core / application / utils 100%、data 98%、visualization 88%、plugins 76%、ui 15%。

## 约定

1. **登记时机**：动手前写入本文件对应小节（问题、方案、影响范围）。
2. **完成后删除条目**：历史由 git 保存，本文件不写流水账。
3. 与代码不一致时以代码为准，并先修正本文件。
