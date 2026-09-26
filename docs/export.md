# 导出模块说明

## 概述

导出能力分为两条主链路：

- 数据导出：将当前选中样本导出为 CSV/Excel，或追加写入已有 Excel。
- 图像导出：对当前图进行离屏重绘并导出为位图/矢量格式。

导出入口位于 `ui/panels/export/panel.py`，具体实现采用“UI 交互层 + Application 用例层”的分层结构。

## 模块结构

```text
ui/panels/
├── panel.py                   # ExportPanel 组装类（薄入口）
└── export/
    ├── __init__.py            # 子包公开 API（mixin 导出）
    ├── build.py               # UI 构建、控件初始化、信号连接
    ├── data_export.py         # CSV/Excel/追加导出
    ├── image_export.py        # 预览导出、直接导出、离屏重绘
    ├── origin_export.py       # Origin 工程导出
    └── common.py              # 导出公共工具方法

application/use_cases/
├── export_data.py             # 数据导出用例（构建 DataFrame、写出、追加）
├── export_image.py            # 图像导出用例（预设、格式归一化、savefig 选项）
├── export_origin.py           # Origin 工程导出用例
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
- 文件写出、后缀补全与追加逻辑由 `application/use_cases/export_data.py` 统一处理。

## 图像导出实现

### 能力范围

- 直接导出：`Export Image`。
- 预览后导出：`Preview Export`。
- 支持格式：PNG、TIFF、PDF、SVG、EPS。

### 参数控制

- 预设模板（下拉项由 `available_image_presets()` 单一来源生成）：

  | 预设 | 栏宽 | 适用 |
  |---|---|---|
  | Science Single / Double Column | 85 / 183 mm | Science 单栏 / 双栏 |
  | Nature Single / Double Column | 89 / 180 mm | Nature 单栏 / 双栏 |
  | IEEE Single Column | 88 mm | IEEE |
  | Elsevier Double Column | 190 mm | Elsevier 系（含 Geochimica 等） |
  | GSA Double Column | 190 mm | GSA Bulletin / Geology |
  | Presentation | 240 mm | 幻灯片 |
- 输出格式（PNG / TIFF / PDF / SVG / EPS）。
- DPI（`72–1200`，预设默认 300）。
- 点大小，以及图例 / 标签 / 标题 / 刻度字号。
- `tight bbox` 开关与 `padding`（inch）。
- 透明背景开关。
- **嵌入字体**（默认开）：PDF/EPS 嵌入 TrueType（`pdf.fonttype=42`、`ps.fonttype=42`），
  SVG 保持文本可编辑（`svg.fonttype='none'`）。关闭后 SVG 文本转为路径（`'path'`）。
  多数期刊拒收 Type 3 字体，故默认开启。
- **白色背景**（默认开）：非透明导出统一铺白底，避免深色主题渗入投稿图；
  与"透明背景"互斥（透明时不铺底色；EPS 无 alpha 通道，会退回白底）。

### 格式细化

| 格式 | 处理 |
|---|---|
| PDF | TrueType 字体嵌入 + 文档元数据（Title/Subject 取自当前图标题，Creator=IsotopesAnalyse） |
| SVG | 文本保持可编辑（或按需转路径） |
| EPS | 丢弃 alpha 通道，改用白底 |
| PNG | `pil_kwargs={'optimize': True}` 无损压缩 |
| TIFF | `pil_kwargs={'compression': 'tiff_lzw'}` |

DPI 低于 72 会被钳制；`pad_inches` 仅在 `tight bbox` 开启时传入。


### 用例下沉（2026-04-01）

- 预设解析、导出后缀归一化、保存参数组装已迁移到 `application/use_cases/export_image.py`。
- `savefig` 落盘逻辑由应用层统一封装，UI 层仅负责参数收集和用户反馈。

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

- UI 层只负责交互、参数采集、提示与异常展示；业务规则放在 application use case。
- 导出逻辑不直接改写 UI 控件状态。
- 导出失败需返回可诊断错误信息（日志 + 用户提示）。
- 预览保存与直接导出共享保存参数解析，保证行为一致。
- 所有用户可见文本通过 `translate()` 管理本地化。
