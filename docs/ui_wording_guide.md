# UI 文案规范

本文件是**面向用户文案**的唯一约定。新增或修改文案前先读它；`locales/check_untranslated.py` 与
`tests/test_guards.py` 会守住其中的机械部分（缺键、无引用键、zh 值等于英文键）。

## 一、句式

- **短命令句**：按钮、菜单项、tooltip 一律用祈使句，不用名词堆叠。
  - ✓ `Fit to data…` · `Clear isochron results` · `Import data…`
  - ✗ `Fit to Data...` · `Hide Isochron`（行为是清空 ✗）· `Lay the panels out: …`
- **准确优先于简短**：文案必须描述**实际行为**。破坏性动作用破坏性动词
  （`Clear isochron results` 而不是 `Hide Isochron`）；无法区分的情形不要谎称
  （导入流程分不清"取消"与"失败"⇒ 说 `Nothing was imported.`）。
- 不使用营销式词汇（`unlock` ✗）。不出现**内部标识符**（`PB_EVOL_76` ✗、matplotlib 位置码
  `upper left` ✗、`\x1f` ✗、异常原文 ✗）——这些进日志，界面说人话。

## 二、大小写与标点

| 项目 | 规则 | 例 |
|---|---|---|
| 英文大小写 | **Sentence case**（首词与专有名词大写） | `Point transparency` ✓ · `Point Transparency` ✗ |
| 完整句 | **句尾加句号** | `Data imported.` |
| 短语式 tooltip | **不加句号** | `Hover tooltip` |
| 省略号 | 一律 **U+2026 `…`** | `Browse…` ✓ · `Browse...` ✗ |
| 标签冒号 | 与控件同行的行首标签**带冒号** | `Figure resolution (DPI):` |
| 独立/分组标题 | **不带冒号** | `Marker Settings` |
| 中文标点 | **全角** | `导入数据…` · `编辑线条样式` · `：` |
| 中文空格 | 拉丁缩写与中文之间**留空格** | `稳健 PCA 参数` ✓ · `稳健PCA参数` ✗ |

## 三、tooltip

tooltip **必须解释控件**，不能复述标签（英文尤其容易犯 ✗）：

- ✓ `Image resolution in dots per inch. A higher value gives a sharper figure and a larger file.`
- ✗ `Figure resolution (DPI)`（复述标签）
- 含范围的控件**保留占位符**：`Point size in square points, from {min} to {max}. …`

## 四、术语表（同一概念只用一种说法）

| 概念 | 英文 | 中文 | 禁用 |
|---|---|---|---|
| 绘图类型 | `Plot type` | 绘图类型 | Render Mode（下拉里是图本身，不是渲染管线 ✗） |
| 分组 | `Grouping` | 分组 | Coloring / Grouping（该页没有着色，配色在图例面板 ✗） |
| 框选 / 套索 | `Box Select` / `Lasso Select` | 框选 / 套索选择 | Enable Selection · Custom Shape |
| μ / κ | `μ` `κ` | μ / κ | Mu / Kappa（正文中） |
| 边缘密度 | `marginal KDE` | 边缘核密度 | 边际核密度 |
| 稳健主成分 | `Robust PCA` | 稳健 PCA | RobustPCA（显示名） |
| 分解 | `decomposition` / `Decompose by…` | 分解 | Collapse（行为是撤销 ✗） |
| 分组列 | `grouping column` | 分组列 | 分组字段 |
| 面板 | `panel` | 面板 | 子窗口 |

**写入数据列的常量保持英文**（`Unknown` / `Other` / `Cluster {n}` / `N/A` / `<Default>`）：
它们会进入导出数据，翻译会破坏用户脚本与跨语言数据交换。

## 五、改中文译文的机制（重要 ✓）

`locales/sync_locales.py` 里的**映射表会覆盖** `zh.json`：

- 键**在映射表里** ⇒ 必须改**映射表**（改 zh.json 会被下一次 sync 覆盖 ✗）；
- 键**不在映射表里** ⇒ 改 `zh.json`（sync 只补缺、不覆盖 ✓）；
- 新增键 ⇒ 加进任一表并跑 `uv run python locales/sync_locales.py`（会自动补齐 en/zh ✓）。

改完必须跑：`uv run python locales/check_untranslated.py`（须 exit=0，它同时报告"无代码引用的陈旧键"）。

## 六、验证方式

1. `uv run pytest tests/test_display_panel_themes.py tests/test_entry_workbook_dialog.py -q`（断言文案的测试）；
2. 真代码探针打印中英对照（`core.translate` + `core.localization.set_language`）；
3. 全量：`uv run pytest -q` + `Get-ChildItem scripts\check_*.py | % { uv run python $_ --fail-on-hits }` + 翻译检查。
