# 开发规划（仅待办）

本文件**只记录尚未开始或尚未完成的工作**。已完成的功能、修复与重构不在此留痕——过程与决策由 git 历史承担（提交信息 + 代码 + 对应模块文档即是最好的记录）。非平凡改动手前在此登记条目；条目完成后**直接删除**，不要新增"已完成/阶段进展"小节。

## 待办

### 插件系统

- [ ] **第三方插件自动发现**：当前只扫描 `plugins/builtins/` 与用户插件目录，pip 安装的外部包无法注册；改为 setuptools entry points（`plugins/manager.py`）。

### 机器学习（`provenance_ml` 插件）

- [ ] **显式 train/valid/test 划分**与固定随机种子的可复现报告（现状只有 StratifiedKFold 交叉验证，无独立测试集）。
- [ ] **per-label 判定阈值**搜索与结果导出。

### 三元图局部放大（待真机验证）

- [ ] **交互式局部放大**：几何纯函数（`similar_subtriangle_limits()` 等）与 Qt 事件过滤器已就位，离屏测试全部通过。2026-09-26 复查真机日志推翻了"零条 release"的旧结论——release 实际可达，症结是**事件双重投递**：应用级过滤器先收到 QWindow 原生副本、后收到画布副本，旧实现把首次不可映射的 release 当作手势取消并清掉 `_press`，导致画布副本变成空操作；另有一个面板 QCheckBox 被全局坐标回退误判为手势起点。两者已在 `ui/main_window_parts/canvas.py` 修复（QWindow 副本走 `globalPos()` 映射、无关 widget 直接拒绝、仅坐标可用时结束手势），并补回归测试（`tests/test_ternary_zoom_qt.py`）。**剩余：真实 GUI 下手工验证拖拽放大与向外拖还原。**

  （原"每 ~0.8 秒整幅重绘"条目已于 2026-09-26 复查注销：最近四次运行日志中无失控循环，密集重绘均为滑块拖动经 350ms 防抖触发；当时伴随的 `ternary_render_margin` 网关外写入告警风暴系 sync 回写清单漏掉该字段所致，已修复。）

### 类型注解收口

- [ ] 按 `docs/dev_conventions.md` §10「新增/重构函数必须标注」逐步补齐 `ui/` 与 `plugins/`。
      当前覆盖率：core / application / utils 100%、data 98%、visualization 88%、plugins 76%、ui 15%。

## 约定

1. **登记时机**：动手前写入本文件对应小节（问题、方案、影响范围）。
2. **完成后删除条目**：历史由 git 保存，本文件不写流水账。
3. 与代码不一致时以代码为准，并先修正本文件。
