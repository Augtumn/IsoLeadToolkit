# 导出模块说明

## 概述

导出能力分为两条主链路：

- 数据导出：将当前选中样本导出为 CSV/Excel，或追加写入已有 Excel。
- 图像导出：对当前图进行离屏重绘并导出为位图/矢量格式。

导出入口位于 `ui/panels/export_panel.py`，具体实现拆分在 `ui/panels/export/` 子包中。

## 模块结构

```text
ui/panels/
├── export_panel.py            # ExportPanel 组装类（薄入口）
└── export/
    ├── __init__.py            # 子包公开 API（mixin 导出）
    ├── build.py               # UI 构建、控件初始化、信号连接
    ├── selection.py           # 选择状态同步、选择工具联动
    ├── data_export.py         # CSV/Excel/追加导出
    ├── image_export.py        # 预览导出、直接导出、离屏重绘
    └── common.py              # 导出公共工具方法
```

## 数据导出实现

### 能力范围

- 导出选中数据到 CSV。
- 导出选中数据到 Excel（新文件）。
- 导出选中数据到 Excel（追加到新工作表）。

### 实现要点

- 导出前根据当前选择构建 DataFrame。
- 若当前渲染模式存在降维结果，会附加对应坐标列与参数元信息。
- 追加导出使用工作表命名冲突处理，避免覆盖已有数据。

## 图像导出实现

### 能力范围

- 直接导出：`Export Image`。
- 预览后导出：`Preview Export`。
- 支持格式：PNG、TIFF、PDF、SVG、EPS。

### 参数控制

- 预设模板（Single Column / Double Column / Presentation）。
- 输出格式。
- DPI。
- 点大小、图例大小。
- `tight bbox` 开关。
- `padding`（inch）。
- 透明背景开关。

### 渲染策略

图像导出采用离屏重绘，不直接保存交互画布：

1. 读取当前数据与分组可见性状态。
2. 构建导出专用 Figure/Axes。
3. 应用预设样式与导出参数。
4. 生成散点、图例与必要叠加层。
5. 调用 `savefig` 按目标格式写出。
6. 清理离屏对象，避免污染当前界面状态。

### 样式来源

- 首选：SciencePlots 样式链（如可用）。
- 回退：内置 `rcParams` 预设（SciencePlots 不可用时自动切换）。

## 依赖包

- PyQt5：导出 UI、文件对话框、预览对话框。
- matplotlib：离屏绘图、样式应用、`savefig` 导出。
- pandas：CSV/Excel 写出。
- openpyxl：Excel 追加写入引擎。
- scienceplots（可选）：期刊样式模板。

## 设计约束

- 导出逻辑不直接改写 UI 控件状态。
- 导出失败需返回可诊断错误信息（日志 + 用户提示）。
- 预览保存与直接导出共享保存参数解析，保证行为一致。
- 所有用户可见文本通过 `translate()` 管理本地化。
