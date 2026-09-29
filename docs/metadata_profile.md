# 铅同位素元数据档案（TerraLID）与数据录入

## 1. 这是什么

`reference/metadata` 是 **TerraLID Metadata Profile** —— 一份面向铅同位素数据的社区元数据
报告格式（CC-BY-4.0，Zenodo DOI [10.5281/zenodo.18069848](https://doi.org/10.5281/zenodo.18069848)，
文档站 <https://terralid.github.io/metadata/>）。它不是数据库 schema，而是"数据模型 + 报告格式"，
目标是让不同来源的铅同位素数据可以合并复用，与最初测量的动机无关。

档案以 mkdocs 站点形式维护：字段定义在 `docs/metadata_*.md`，可复用块在
`includes/metadata_blocks.md`，靠 `include-markdown` 插件内联到各表。

本模块（`data/metadata_profile/`）把那批 markdown 定义**代码化**，使字段清单可校验、
可生成录入工作簿、可与本工程既有的扁平列互转。

## 2. 数据模型

```
Site (遗址/矿区) ──▶ Assemblage (堆积单位) ──▶ Object (器物) ──▶ Sample (样品) ──▶ Analysis (分析)
```

**不是严格层级**：档案明确允许 Object 或 Analysis 直接挂到 Site；单个器物要记地层信息时
须建成"单器物 assemblage"。实现上父外键只作默认建议，校验对 `assemblage_id` / `sample_id`
缺失只报 WARNING（`validate.validate_references` 的宽松规则）。

### 2.1 字段规模（实测，有测试断言）

| 模块 | ID 前缀 | 自有字段 | 表格 |
|------|---------|--------:|-----:|
| Sites | `SI` | 31 | 遗址/矿区 |
| Assemblages | `AS` | 16 | 堆积单位 |
| Objects | `O` | **36** | 器物 |
| Samples | `S` | 24 | 样品 |
| Analyses | `A` | 41 | 分析 |
| Ore | `OO` | 20 | 矿石 |
| Glass | `OG` | 25 | 玻璃 |
| Metal | `OM` | 7 | 金属器 |
| Metal: Coins | `OM.C` | 11 | 钱币 |
| Pigments | `OP` | 36 | 颜料 |
| By-products | — | **0** | 空壳文档（"Coming soon"） |
| **自有合计** | | **247** | |
| 可复用块 B1–B6 | `B` | 61 | 6 个块根 + 55 个成员 |

`len(profile.fields)` = **497** = 自有 247 + 各表内联块字段展开 250。逐表 fields（自有 + 内联）：
sites 60、assemblages 23、objects 102、samples 57、analyses 102、ore 50、glass 33、metal 15、
metal-coins 11、pigment 44、by-products 0。

### 2.2 六个可复用块

模块文档用 `{% include-markdown ... start="<!--relation-start-->" %}` 把块内联进字段，因此同一批
字段会在多个模块重复出现（例如 `B5 Relation` 在 Analyses 里被内联 **4 次**）。实现上块字段
**保留原 OID**，靠 `block_owner`（宿主字段 OID）区分 —— 所以块字段的身份是
**`(table, block_owner, oid)` 三元组**，不是 `oid` 单键。

| 块 | 名称 | 字段数 | 内联到 |
|----|------|-------:|--------|
| B1 | Person | 11 | Objects（O1 收集者、O2 贡献者）、Samples（S13）、Analyses（A11） |
| B2 | Status | 7 | Objects（O17）、Samples（S14） |
| B3 | Dating | 15 | Sites（SI7）、Objects（O14）、Ore |
| B4 | Chemical composition | 8 | Analyses（A7）、Objects（O13）、Samples（S12）、Glass、Metal、Pigment |
| B5 | Relation | 7 | Sites ×2、Assemblages、Objects ×2、Samples、Analyses ×4、Ore |
| B6 | Lead isotope ratio | 7 | Analyses（A9.3 标样实测、A14 样品比值） |

### 2.3 字段的元信息

每个字段固定 7 项，正是"数据驱动表单"的输入：

```
**ID and name:** A14 analysis_lia_ratio          ← 机器可读键名
**Provided by:** data provider, TerraLID system   ← 谁填
**Obligation:** mandatory                         ← mandatory / recommended / optional
**Occurrences:** 1–n                              ← 出现次数，决定标量 or 可重复组
**Definition:** ...
**Allowed values and other constraints:** ...
**Example:** ...
```

- **obligation** 只有三档，作者刻意压低必填量以兼容历史数据。
- **occurrence** 是分表的唯一依据：`0-1`/`1` 可拍平，`0-n`/`1-n` 必须走子表。
- **provided_by** 三种：`data provider`（录入者）、`TerraLID system`（系统计算）、`API`。
  `is_required_from_provider = mandatory 且 data provider` —— 只有这种字段会在工作簿里标红/
  报必填错；系统提供的字段（如 `B6.7 Source`、`A15.*`）留空**不算错**。
- **`value_kind` 的富化提升**：解析层只按文本推断类型；`profile.py` 富化时，若
  `vocab.vocab_id_for(spec)` 命中词表而类型仍是 `FREE_TEXT`/`MIXED`，则提升为
  `CONTROLLED_VOCAB`。这样"是否有受控词表"以 `vocab.py` 登记为**唯一真源**，不必让解析层
  从散文里猜（`A15.1` 就是靠这条才真正生效的）。

## 3. 铅同位素核心

### 3.1 A14 → B6 铅同位素比值（mandatory，1–n）

> "Mass-bias corrected lead isotope ratios and analytical uncertainty.
> **The TerraLID system will calculate all ratios not reported in the original publication.**"

B6 的 8 个允许比值：

| 实测（主比值） | 推导 |
|----------------|------|
| `206Pb/204Pb`、`207Pb/204Pb`、`208Pb/204Pb` | 录入者提供 |
| `204Pb/206Pb`、`207Pb/206Pb`、`208Pb/206Pb`、`207Pb/208Pb`、`206Pb/208Pb` | 工具补齐，`source=calculated` |

推导走 `spec.derived_ratio_expression()` 给出的**因子链**（把每个比值表达为
`∏ (N_mass/N_204) ** exp`），而不是硬编码 5 个除法 —— 档案新增比值时自动生效。

不确定度口径：

- 实测值 `source=original`；派生值 `source=calculated`。
- 派生比值的不确定度按**一阶相对误差传播**：`(σ_r/r)² = Σ (e_i · σ_{p_i}/p_i)²`，
  忽略协方差（档案未提供比值间协方差，`ratios.py` docstring 已写明这是近似）。
- **任一派生因子的主比值缺不确定度时，该派生值的不确定度记为 `None`，不按 0 参与传播** ——
  把未知当 0 会系统性低估不确定度，而低估在地球化学解释里是危险方向。
- B6.6 相对不确定度（%）与 B6.5 绝对不确定度可互相换算（档案明说"提供相对值时系统会算绝对值"）。

### 3.2 A15 年龄模型参数（recommended，0–n，全部由系统提供）

| 字段 | 说明 |
|------|------|
| A15.1 模型名 | `SK75` / `CR75` / `AJ84`（封闭词表） |
| A15.2–A15.3 | 模式年龄 Tmod (Ma) ± 不确定度 |
| A15.4–A15.5 | μ ± 不确定度 |
| A15.6–A15.7 | κ ± 不确定度 |
| A15.8–A15.9 | ω ± 不确定度 |

三个模型分别对应 Stacey & Kramers (1975)、Cumming & Richards (1975)、Albarède & Juteau (1984)，
在本工程 `data/geochemistry/engine.py::PRESET_MODELS` 中**均有实现**，故 A15 可由既有地球化学
引擎从主比值反演补齐（导入时执行；失败只记 warning，不影响导入）。实际调用点：

```python
from data.geochemistry import calculate_all_parameters, engine   # 函数内延迟导入
results = calculate_all_parameters(pb206, pb207, pb208)          # 3 个位置参数，标量 float
# A15.2 <- results["t_Model (Ma)"]    A15.4 <- results["mu_model"]
# A15.6 <- results["kappa_model"]     A15.8 <- results["omega"]
# A15.1 <- engine.current_model_name → SK75/CR75/AJ84（子串映射；映射不上则整个 A15 不写并记 warning）
```

只写模型名、不写参数，或参数为非有限值时跳过；单条求解异常只 warning 不中断导入。
**宁可不写也不给参数配一个错的模型名** —— 模型名与参数不一致会让下游解释直接出错。

### 3.3 分析链路其余与 Pb 有关的字段

`A2` 分析类型、`A3` 制样流程(+文献)、`A4` 分析对象、`A5` 分离流程(+文献)、`A6` 仪器
(类型/型号/**PIDinst**)、`A7` Pb 浓度(→B4)、`A8` 平均总强度+单位、`A9` 标准物质
（**A9.1** Pb 标样名 → **A9.3** 实测值(→B6)、**A9.4** Tl 标样名、**A9.5** ²⁰⁵Tl/²⁰³Tl、**A9.6** Tl 浓度）、
`A10` 质量歧视校正模型、`A11` 实验室(→B1)、`A12` 分析日期、`A13` 描述、`A16` 关联。

## 4. 包结构

| 模块 | 职责 |
|------|------|
| `spec.py` | 数据结构与常量（契约层，**不得**导入 PyQt5/pandas/openpyxl，不做 IO） |
| `parse.py` | `docs/metadata_*.md` + `includes/metadata_blocks.md` → `FieldSpec` |
| `profile.py` | 组装 `Profile`；缓存入口 `load_profile()`；`vocab`/`labels` 富化 |
| `vocab.py` | 80 张受控词表（85 个 OID、930 条术语）：`VOCABULARIES` / `vocabulary` / `terms` / `open_ended` / `contains` / `vocab_id_for` |
| `labels.py` | 字段中文标签 `FIELD_LABELS_ZH`（OID 键）+ 兜底 `EN_LABELS_ZH` + `label_for` |
| `layout.py` | 注册表 → 工作簿工作表/列映射（生成器与导入器**共用**，避免两侧漂移） |
| `ratios.py` | 8 个比值的因子链推导、一阶误差传播、绝对↔相对换算、格式化 |
| `validate.py` | 字段级/条件联动/主外键校验 → `ValidationIssue` 清单 |
| `validate_sheets.py` | 工作表辅助列与块表归属校验（单向依赖 `validate.py`） |
| `io_xlsx.py` | 工作簿读写：原子写 + 覆盖前备份 + 只写布局内的表与列 |

`__init__.py` 按 PEP 562 惰性导出（照 `data/__init__.py` 的既有做法）：只 `import data.metadata_profile`
不会拉入 `openpyxl` 或 930 条词表数据。

外围：

| 位置 | 职责 |
|------|------|
| `scripts/build_entry_workbook.py` + `scripts/entry_workbook_info.py` | 由注册表生成录入工作簿（CLI） |
| `application/use_cases/entry_workbook.py` | 用例层：`generate_template` / `validate_entry_workbook` / `import_entry_workbook` |
| `ui/dialogs/entry_workbook.py` | Qt 对话框：生成 / 校验 / 导入 + 报告视图（菜单「文件 → 数据录入（Excel）...」，`Ctrl+N`） |
| `locales/runtime_keys.py` | 登记运行时才确定键名的校验消息模板（静态扫描看不到，否则会被判为"未被引用的键"） |

## 5. 录入工作簿的结构

### 5.1 为什么是 Excel

档案本质是**关系型表格**（每模块字段集固定 + 主外键链路 + 1–n 重复组），而本工程的数据本来
就住在 xlsx 里。所以分工是：**Excel = 录入面与存储形态；Python = 守门人（校验 → 推导 → 映射）；
PyQt = 薄启动器**。

Excel 有两个硬边界，必须由 Python 补上，否则会变成陷阱：

| Excel 能做 | Excel 做不到 |
|---|---|
| 受控词表下拉、日期/数值格式、必填条件着色（提示性） | **硬性阻止**缺必填、错词表、悬空外键 |
| 长表存 1–n 组 | 在单张宽表里表达 1–n（A14 的 8 比值 × 不确定度、A9 的 n 个标样） |
| 熟悉、可从文献直接粘贴 | 推导其余 5 个比值、绝对↔相对换算、反演 A15 |

### 5.2 分表规则（三条）

> **① 分组节点不建列；② 可重复的组独立成表，一个模块最多两张录入表（主表 + 明细行表）；
> ③ 只能有一个家 —— 每个承值字段恰好被一张表的一列承载。**

1. **分组节点不建列。** 一个字段若是别的字段的 `parent`，或是某个内联块的宿主
   （`block_owner`），它自身就不携带取值 —— 它的内容是子字段或整个块。给它们建列只会产生
   "永远填不上、却因 mandatory 一直标红"的幽灵列（`A9`/`A15`/`SI5`/`A6`/`O10`/`OP4`…）。
   实测档案里这类字段**全部既无 `allowed` 也无 `example`（0 例外）**，因此这条规则是安全的。
   块表内部同样适用（去掉 `B1.4`/`B2.1`/`B3.1`/`B3.3`/`B3.4`/`B5.1`）。
   由此主表少了 30 个幽灵列（如 `5_Analysis` 19 → 13）。
2. **可重复的组独立成表。** 6 个可复用块（B1–B6）各自成表 —— 它们全部含 `0-n`/`1-n` 字段，
   是档案所说的"可复用块"落到 Excel 的自然形态：**一张长表服务多个宿主**，用
   `owner_sheet` + `owner_id` 定位宿主行。模块**自有**的可重复组（如 `O5 object_identifiers`）
   不各成一表，而是**合并进该模块唯一一张明细行表**，用 `group` 列标明该行属于哪个组。
   组根有两类：
   - **容器组根** —— 可重复且有子字段（`A9` 标样、`O5` 器物标识符…），内容由子字段承载；
   - **单列组根** —— 可重复**且没有子字段**的叶子字段（`SI8 site_type` 1–n、`OO3.1` 0–n…），
     它本身就是可重复的值。实测有 **14 个**这样的字段；早期规则漏掉它们会让字段**静默丢失**。
   只为**最外层**组根建行：嵌套重复组（`O5` 里的 `O5.1`、`SI5.4.1` 之类）随外层走，
   否则同一批字段会出现两次。纯粹的可复用块宿主（如 `A7`、`OG3`）不建组 —— 它们的内容归块表。
3. **只能有一个家。** 每个承值字段恰好被一张表的一列承载，既不丢失也不重复。
   `tests/test_metadata_layout.py` 在**真实档案**上断言这一条（`homeless == []` 且
   `duplicated == {}`），因为前两类 bug 都曾以"字段静默消失"的形式出现过。

实测结果：**30 张表** = 4 张信息表 + 11 张主表 + 6 张块表 + 9 张明细行表；26 张需要填写。

```
README            使用说明
0_SCHEMA          全部字段定义（生成，勿改）—— 497 行 = 自有 247 + 内联块展开 250
0_VOCAB           受控词表（生成，勿改）—— 80 张词表、930 条术语
1_Site  (14 列)   SI5/SI6/SI10 等分组节点不建列，其子字段直接入列
1_Site_Rows (10)  明细行：row_id | parent_id | group(SI4,SI5.4.1,SI8,SI10.1,SI10.2) + 成员列
2_Assemblage (11) 2_Assemblage_Rows (5)   group=AS3
3_Object (17)     3_Object_Rows (11)      group=O5,O8,O9,O15
4_Sample (13)     4_Sample_Rows (7)       group=S1,S3
5_Analysis (13)   5_Analysis_Rows (18)    group=A1,A9,A10,A15
6_Person (12)     块表 B1   owner_sheet ∈ 主表 + 明细行表
7_Dating (14)     B3      8_Chemistry (10) B4     9_Relation (8) B5
10_Status (8)     B2      17_LIA-Ratio (10) B6（额外有 ratio_host 列）
11_Ore (7)   11_Ore_Rows (9)        group=OO1,OO2,OO3.1,OO4
12_Glass (9) 12_Glass_Rows (13)     group=OG9..OG13
13_Metal (4) 13_Metal_Rows (4)      group=OM1
14_Coins (11)
15_Pigment (10) 15_Pigment_Rows (19) group=OP1,OP3,OP4.2,OP4.3,OP5.2,OP7.1,OP7.2,OP11,OP12,OP13
16_ByProducts (1)  档案空壳文档，无明细行表
99_CHECK          校验报告（生成，勿改）
```

### 5.2.1 `columns_for_record()`：两条筛列规则

校验必须先按记录筛列，`SheetSpec` 提供两个方法：

```python
SheetSpec.columns_for_record(record)        # 该行适用的列（两条规则，见下）
SheetSpec.stray_columns_for_record(record)  # 本行填了别的组的列（多半是填错行）
```

**规则 1 —— 明细行表按 `group` 筛列。** 明细行表把多个重复组合并到一张表里，用 `group`
（取值 = 组根 OID）标明该行属于哪个组。不筛的话 `group=A15` 的行会被要求填 A9 组的必填字段
（`A9.1` 标样名），产生一批永远消不掉的假错。

**规则 2 —— 未启用的可选分组不施必填。** 档案把 `SI5.1 Point`、`SI5.2 Boundary box`、
`SI6 Registry`、`A8 强度`、`O10 重量`、`O11 尺寸`、`S4 取样位置`、`S6 样品重量` 这类组声明为
`0–1`，而组内子字段是 mandatory —— 该 mandatory **只在该组被使用时成立**：

- 整组一格未填 → 组内字段全部不作要求；
- 填了组里任意一格 → 组内必填项照常要求（只填西边界、不填东西南北，仍报缺三边）；
- 明细行表里**填了 `group` 本身就是"这组在用"的声明** —— 否则用户选好 `group=A15` 还没填值时，
  整组列会被自己"未填"这一事实抹掉，必填永不触发。

判据字段是 `ColumnSpec.optional_ancestors`（`occurrence ∈ {0–1, 0–n}` 的祖先分组）。
**必填容器不在此列**：`A6`（仪器，`occurrence = 1`）若算进来，`A6.1` 会因自己为空而"自我抑制"
永不被要求 —— 而档案明确要求它。工作簿里"红底"条件格式用的是同一个字段、同一个判据。

实测效果：只填"一看就该填"的字段时，ERROR 从 **23 条降到 3 条**，剩下 3 条是真必填
（`O12` 材质、`S5` 样品类型、`S8` 分析后状态）。

### 5.3 双层表头与下拉

- **第 1 行** = 机器键名（`A14 analysis_lia_ratio`），**第 2 行** = 中文标签 + 级别标记
  （`铅同位素比值 ★必填`），冻结窗格 `A3`。同一张表内重名标签自动追加 `[OID]` ——
  档案里 `SI5.1.1` 与 `SI5.4.1.1` 都叫 "Longitude"，不消歧会填错列。
- 第 2 行每列带批注：定义 / 允许值 / 示例 / 来源（`source_doc:source_line`，可回溯到 `reference/metadata`）。
- 下拉：受控词表走 `0_VOCAB` 的命名区域 `Vocab_<id>`（`open_ended=True` 时设
  `showErrorMessage=False`，允许自由文本，因为档案明说词表可能不全）；`σ` = `1,2,3`；
  `ratio_host` = `A9.3,A14`；`owner_sheet` = 11 张主表 + 9 张明细行表；`group` = 该表的组根 OID。
- 必填条件格式**只标 `is_required_from_provider` 为真的列**；系统提供的列（`B6.7` 等）不标红。
- 数值格式：比值 `0.00000`、不确定度 `0.00000000`、日期 `yyyy-mm-dd`。

### 5.4 报告表 `99_CHECK`

单一表头（第 1 行，非双层）：`severity / sheet / record_id / column / message / value`。
导入器在校验后回写，用户不必翻对话框就能看到要改哪一格。

## 6. 三步流程

```bash
# 1) 生成模板（也可在应用里「文件 → 数据录入（Excel）...」或 Ctrl+N）
.venv\Scripts\python.exe scripts/build_entry_workbook.py --output 数据\entry_template.xlsx

# 2) 在 Excel 里填写需要的表（★必填，红底 = 必填未填）

# 3) 校验（只读）与导入（补齐比值并回写，写前自动备份）
```

```python
from application.use_cases.entry_workbook import (
    generate_template, validate_entry_workbook, import_entry_workbook,
)

generate_template("数据/entry_template.xlsx")          # 目标已存在时抛 FileExistsError
report = validate_entry_workbook("数据/entry_template.xlsx")   # 只读，不写盘
print(report.error_count, report.warning_count, report.ok)

report = import_entry_workbook("数据/entry_template.xlsx")      # 补齐、回写、备份
print(report.derived_ratios, report.backup)
```

导入的行为约束：

1. 先校验；**有 ERROR 时只写 `99_CHECK` 报告，不改数据行**（避免半截数据落盘），并在日志里说明。
2. `derive=True` 时按 `(owner_sheet, owner_id, ratio_host)` 分组补齐派生比值与不确定度换算。
   归档时回填 `B6.7 Source`：录入者提供的行写 `original`，工具推导的行写 `calculated`；
   **用户显式填过的值一律保留**（那是他的声明）。
   `report.derived_ratios` 的语义是**实际写回的条数**（被 ERROR 阻断时为 0，算出多少条另记日志）。
3. 写盘前由 `io_xlsx` 自动生成带时间戳的备份 `<name>.bak-<YYYYMMDD-HHMMSS>.xlsx`，
   并以"临时文件 + 原子替换"落盘，中途失败不会留下半截文件。
4. 永远只写布局内的表与列；用户在布局外自己加的备注列会被忽略而不是清掉。
5. **只写被改动的表**（`17_LIA-Ratio` 与 A15 的目标表），不把"读出来又原样写回"的表交给写入器；
   日期列写前还原为真正的日期值，避免日期单元格变成文本。
6. `derive=False` 且无需回写时**文件字节不变**（有幂等性测试守住）。

### 6.1 主键与挂接口径（重要）

档案里主键 `SI0/AS0/O0/S0/A0`（TerraLID ID）的 `Provided by` 是 `TerraLID system`，而
`Allowed values` 与 `Example` 全是 `t.b.d.`。**本工具不代为生成这些 ID** —— 发明一套主键规则并
写进用户的文件，比让用户自己填更糟。

| 你要做的事 | 需要填的 |
|------------|----------|
| 仅填主表（如只要 `1_Site` 一类数据） | 主键可留空（因此这些列**不标红**，档案语义如此） |
| 用块表挂接（`6_Person`…`17_LIA-Ratio` 的 `owner_id`） | 宿主的**主键必须填**，且同表内唯一 |
| 用明细行表挂接（`*_Rows` 的 `parent_id`） | 同上 |

留空却又要挂接时不会静默失败：导入器会给出显式 warning
（如 `A14 ratio rows reference analysis id(s) [...] which no row on 5_Analysis carries`）。
实验室自己的编号请填 `A1 analysis_lab_id` / `S1.1 Laboratory ID` 等专门字段，不要与主键混用。

#### 必填容器：`A9` 与 `SI5` 是例外

"可选分组豁免"（§6.3）只适用于 `occurrence = 0–1 / 0–n` 的容器。档案把
**`A9 Reference materials` 声明为 `mandatory` + `1–n`**、**`SI5 Geolocation` 声明为
`occurrence = 1`**，所以：

- `A9.1`（Pb 标样名）等子字段**不受豁免** —— 只要 `5_Analysis_Rows` 有行，它们就按组规则校验；
- `SI5.3`（地理位置描述）始终在 Site 行的校验范围内（它是"建议"级，不会拦你）。

也就是说，**档案要求每个分析至少有一个 Pb 标准物质**。工具不会因为你"一张
`5_Analysis_Rows` 都没建"而报错（原因见 §9 第 8 条），但按档案本意应当补一行 `group=A9`。

### 6.2 没有自动补齐的系统提供列

`A15.*` 与 `B6.*` 之外的"系统提供"列里，还有两类**刻意留空**：

- `B3.3.4 Unit of date`：档案给了确定性派生规则（`B3.2=geological → Ma`；`archaeological → a`），
  但该规则已写在列批注里，工具暂不代填；
- `OO4.2 Abundance category` / `OM1.2 Major elements`：档案只说"由化学组成推断"，**未给阈值与
  元素集合**，需要领域规则，导入器不该猜。

这三项见 `docs/development_plan.md` 的待办。

### 6.3 填写指导：不要试图填满 497 个字段

档案是为了**数据可复用**而设计的完整字段集，不是录入清单。实测：一口气只填"一看就该填"的
字段会得到 23 条 ERROR —— 其中只有 3 条是真必填。区别在于一条关键语义：

> **分组字段的"必填"是条件性的。** 档案把 `SI5.1 Point`、`SI5.2 Boundary box`、`SI6 Registry`、
> `A8 Mean total intensity`、`O10 Weight`、`O11 Dimensions`、`S4 Sampling location`、`S6 Sample weight`
> 这类组声明为 `0–1`，组内子字段（经纬度 / 四至 / 强度值+单位 / 重量值+单位 …）是 mandatory。
> **这个 mandatory 只在"该组被使用时"成立**：整组一格不填 → 组内字段全部不作要求；
> 只要填了组里任意一格 → 组内必填项必须补齐（只填西边界不填东西南北，会报缺三边）。

`SheetSpec.columns_for_record()` 实现了这条规则（见 §5.2.1），"红底"提醒也按此条件给出。

#### 三条路线，按需要选

| 路线 | 要填的表与列 | 结果 |
|------|--------------|------|
| **① 绝对最小** | `5_Analysis`：`A2` 分析类型、`A6.1` 仪器类型（+`A0` 若要被挂接）<br>`17_LIA-Ratio`：`owner_sheet`/`owner_id`/`ratio_host` + 逐行 `B6.1` 比值名、`B6.2` 比值值 | 2 张表、约 7 格 + 3 行比值 → 校验 **0 error**，导入自动补齐 5 个派生比值与 A15 |
| **② 推荐最小**（数据将来能解释） | 在 ① 之上再填：`1_Site` 的 `SI1` 遗址名；`3_Object` 的 `O3` 器物名、`O12` 材质；`4_Sample` 的 `S5` 样品类型、`S8` 分析后状态 | 5 张表、约 12 格。这 5 格是**无条件必填**，缺了会被校验挡下 |
| **③ 完整档案** | 需要什么补什么：年代→`7_Dating`、人员→`6_Person`、文献→`9_Relation`、化学→`8_Chemistry`、保存→`10_Status`、标样→`5_Analysis_Rows`(group=A9) + `17_LIA-Ratio`(ratio_host=A9.3)、材料专属→`11–16` | 依研究目的而定 |

**先不用管的表**：`0_SCHEMA`、`0_VOCAB`、`99_CHECK` 是生成物，一律不填；
`*_Rows` 明细行表**只有**在同一父记录需要多组值时才用（多个坐标点/多个标识符/多个标样/多个年龄模型）；
`11_Ore`…`16_ByProducts` 只在 `O12 Material` 指定了对应材质时才有意义。

#### 每张录入表什么时候才需要填

| 表 | 需要它的条件 | 无条件必填列 |
|----|--------------|--------------|
| `1_Site` | 数据要有遗址/矿区上下文 | `SI1`（且 `SI1=unknown` 时必须给 `SI2`） |
| `2_Assemblage` | 要记录地层/堆积单位 | 无（`AS4`/`AS5` 都是可选组） |
| `3_Object` | 有器物 | `O3` 器物名、`O12` 材质 |
| `4_Sample` | 有样品 | `S5` 样品类型、`S8` 分析后状态 |
| `5_Analysis` | **录铅同位素必填** | `A2` 分析类型、`A6.1` 仪器类型 |
| `6_Person` | 有收集者/贡献者/取样人/实验室信息 | `B1.1` 角色、`B1.3` 姓、`B1.5` 单位 |
| `7_Dating` | 有年代信息 | `B3.2` 年代类型 |
| `8_Chemistry` | 有化学组成数据 | `B4.1` 分析方法、`B4.2` 分析对象、`B4.3` 值、`B4.4` 单位 |
| `9_Relation` | 有参考文献/关联资源 | `B5.1.1`+`B5.1.2` PID、`B5.3` 关系种类、`B5.4` 资源类型 |
| `10_Status` | 有保存机构/可获取性 | `B2.1.1` 机构名、`B2.1.5` 联系人 |
| `17_LIA-Ratio` | **录铅同位素必填** | `B6.1` 比值名、`B6.2` 比值值 |
| `11_Ore` / `12_Glass` / `13_Metal` / `14_Coins` / `15_Pigment` | `O12 Material` 指定了该材质 | 见 `0_SCHEMA` 该表 ★ 列 |
| `*_Rows` | 该模块需要多组值 | `group` + `parent_id`（+ `row_id` 若要被块表引用） |

**只需给 3 个主比值**（`206/204`、`207/204`、`208/204`）：其余 5 个由工具按因子链推导，
`B6.3`–`B6.6` 不确定度可留空，`B6.7` 由工具填 `original`/`calculated`。
**填完一定要跑一次校验**（应用内「校验录入表…」或 `validate_entry_workbook()`），
以 `99_CHECK` 的结论为准；红底只是提醒。

## 7. 与既有扁平列口径的对应

本工程既有 `数据/lead_isotopes.xlsx`（`青铜器铅同位素` 11 列、`地质铅同位素` 30 列）是**扁平
宽表**，与录入工作簿的规范化多表结构不同形。两者的字段对应关系：

| TerraLID | 既有列 |
|----------|--------|
| `A14/B6` 的 3 个主比值 | `206Pb/204Pb`、`207Pb/204Pb`、`208Pb/204Pb` |
| `A6` 仪器 | `Instrument ` |
| `A11` 实验室 | `Lab_Cn`、`Lab_En` |
| `A16/B5` 关联文献 | `Reference` / `Reference `、`Year` |
| `B3` 年代 | `Period`（青铜器）、`Age`（地质） |
| `SI5` 地理位置 | `LAT`、`LON` |
| `O12` 材质 / 材料专属 | `Specimen` |
| `SI1`/`S1.1` 标识 | `Lab No.`、`Original No.`、`ID`、`Sample No` |

**缺口**：既有扁平表没有任何 obligation/occurrence/不确定度结构；除 3 个主比值外的 5 个导出
比值不存；`B6.3–B6.6` 的不确定度完全不存；`A15` 参数只有 `Age`/`U/Pb`/`Th/U` 三个裸数值，
无模型名、无不确定度。录入工作簿正是为补齐这些缺口而设计。

> 扁平列 ↔ TerraLID 记录的自动互转（`mapping.py`）**尚未实现** —— 当前录入工作簿是独立口径，
> 不与既有表自动合并。这是刻意的最小可用范围，见 §9。

## 8. 已知易错点（字段名与定义不符）

词表最容易写错的位置就在这类字段上。以下均已在 `vocab.py` 的对应 `source` 里注明"**字段名虽为 X，
档案定义实为 Y**"：

| 字段 | 字段名/标题 | 档案定义实为 | 词表 id |
|------|-------------|--------------|---------|
| `OO3.1` | mineralisation type | 矿石矿物的**结构构造**（texture） | `ore_texture` |
| `OO5` | alteration | 蚀变**程度**（不是蚀变类型） | `alteration_extent` |
| `AS4.3` | Context | 堆积时/后期是否受**扰动** | `stratigraphy_context` |
| `S8` | sample condition | **分析之后**样品的状态（消耗/留存） | `sample_condition` |
| `SI4.2` / `B3.1.2` | 标题都只叫 "Type" | 数据**基础设施名称** | `site_pid_type` / `period_pid_type` |
| `OP3.2` | Occurrence | 天然 / 合成 | `pigment_origin` |
| `OM1` 与 `OM1.1` | **键名完全相同**（`material_metal_chemistry`） | 一个组、一个化学组成 | — |

**因此解析与查表只能按 OID，不能按 key。** `layout.py` 与 `validate.py` 全部按 OID/`header_key`
（含 OID）工作，正是为了避开这一坑。

档案自身的格式瑕疵（解析层已容错并记入 `Profile.warnings`，共 3 条）：

1. `metadata_objects.md:66-70` 的 `O5.1` 整块用 `**ID and name**:`（**冒号在粗体外**）。
   全档扫描后这类变体只此一处；解析器按宽松正则容忍（只对 7 个已知元信息键生效，
   正文里偶然出现的 `**Note**:` 不会被误吃）。
2. `metadata_analyses.md:385` 的 `A16` Occurrences 写作 `–n`（缺前半段），无法解析 → 回退 `0-1`。
3. `metadata_blocks.md:200` 的 `B3.1` 缺 `**Definition:**` → 定义记为空串。

## 9. 已知限制

1. **受控词表是本地补充，不是档案内容。** 档案声明"能控则控"，但**仓库内并未枚举词表** ——
   绝大多数只写 `controlled vocabulary`，权威来源指向外部（Nomisma 钱币、IMA/Mindat 矿物、
   ORCID、ROR、PIDinst）。`vocab.py` 的 80 张词表是基于领域常识 + 权威体系补的一版，
   因此 73 张设 `open_ended=True`（词表外取值只报 WARNING），只有 7 张档案已穷举的设
   `open_ended=False`（词表外报 ERROR）。个别条目待考，例如 `A9.1` 的 `Pb-1` 经 4 轮检索
   无法核实为认证标样，故未收录并在 `source` 里留了补录说明。
2. **`metadata_by-products.md` 是空壳**（3 行 "Coming soon"），工作簿里 `16_ByProducts` 只有
   1 列，无明细行表。
3. **`mappings.md` 尚未发布**（"Coming soon"），与其它元数据档案/基础设施的映射需等上游。
4. **块表的宿主引用完整性只做一半**：`(owner_sheet, owner_id)` 会校验"非空 + `owner_sheet` 在候选内"，
   以及"被引用的 ID 是否真的出现在目标表的 ID 列"（导入时 warning），但不做完整跨表外键校验
   （`validate_sheets.validate_sheet_helpers` docstring 已写明"不做"）。
5. **扁平列 ↔ TerraLID 的自动互转未实现**（§7）。录入工作簿与 `数据/lead_isotopes.xlsx`
   目前是两条并行口径，不自动合并。
6. **版本号口径**：首页引用 v0.3，而 `docs/changelog.md` 已到 **v0.3.4**，`exports/pdf/` 有
   v0.3 / 0.3.2 / 0.3.3 三个 PDF。本模块读 changelog 顶部版本号（当前 `0.3.4`），
   读不到时回退 `spec.PROFILE_VERSION_FALLBACK`。
7. **三类系统提供列刻意不代填**（见 §6.2）：`B3.3.4` 单位、`OO4.2` 丰度类别、`OM1.2` 主量元素。
   前者的规则可确定性实现，后两者需要领域阈值；三项都在 `docs/development_plan.md` 待办里。
8. **"至少出现一次"（`1–n`）只在表内存在行时才可校验**：档案把 `A9`（标样）、`A14`（比值）、
   `B5`（关联资源）等声明为 `1–n`，但工具无法从"另一张表一行都没有"推出违规 —— 因此
   **不会因为你没建 `5_Analysis_Rows` 就报"缺标样"**。§6.3 的"绝对最小 = 2 张表"因此在
   校验上成立，但按档案本意仍应补一行 `group=A9`（见 §6.1）。

## 10. 维护须知

- **字段清单来自 `reference/metadata`，不要手改生成物。** `0_SCHEMA` / `0_VOCAB` / `99_CHECK`
  与所有双层表头都由脚本生成；档案升版后重跑生成器即可，模板不会漂移。
- 改校验规则时同步更新 `locales/runtime_keys.py`，否则 `locales/check_untranslated.py` 会把
  新的消息键判为"未被引用的键"而失败。
- 新增可复用块或改分表规则只动 `layout.py`；生成器与导入器都按它的产出工作，不需要各改一份。
- 测试组织（按子系统，不按修复批次）：
  `tests/test_metadata_profile_parse.py`、`test_metadata_vocab.py`、`test_metadata_ratios_validate.py`、
  `test_metadata_layout.py`、`test_metadata_io_xlsx.py`、`test_metadata_workbook_build.py`、
  `test_entry_workbook_use_case.py`；合成注册表夹具在 `tests/conftest.py`
  （`synthetic_profile` / `synthetic_layout`）。
