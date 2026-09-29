"""录入工作簿的表结构定义（注册表 → 工作表/列的映射）。

本模块把 `Profile` 里的字段分配到一个具体的 Excel 工作簿布局上。**生成器
（`scripts/build_entry_workbook.py`）与导入器（`application/use_cases/`）共用本模块**，
避免两侧各写一份表名与列序而互相漂移。

分表规则（只有一条，便于解释与测试）：

1. **可重复的组独立成表**。一个可复用块（B1–B6）只要含任一 ``occurrence.is_repeatable``
   的字段（实测六块全部如此），就在工作簿里拥有一张自己的表，按
   ``(owner_sheet, owner_id)`` 定位宿主行 —— 即档案所说的"可复用块"落到 Excel 就是
   **一张长表服务多个宿主**。
2. **不可重复的字段拍平进所属模块的实体表**。
3. **模块自有的可重复组**（如 ``OO1.1 Minerals``）也独立成表，表名由该组的
   OID 派生，宿主为所属实体表。
4. **材料专属模块各自成表**，由 ``O12 Material`` 的值分派。

实体表的列序固定为：主键 → 父外键 → 其余按文档出现顺序。块表的列序固定为：
``owner_sheet`` / ``owner_id`` → 块字段按文档出现顺序。

设计约束：本模块不得导入 PyQt5 / pandas / openpyxl，也不做文件 IO —— 它是纯布局数据，
生成器与导入器各自负责读写。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Mapping

from .spec import (
    AGE_MODEL_PARAMETERS,
    Block,
    FieldSpec,
    Obligation,
    Occurrence,
    Profile,
    TableKey,
    ValueKind,
)

#: Excel 工作表名上限 31 字符，且不得含 ``[]:*?/\``。
MAX_SHEET_NAME_LENGTH = 31

#: 块表用于定位宿主行的两列。
OWNER_SHEET_COLUMN = "owner_sheet"
OWNER_ID_COLUMN = "owner_id"

#: 模块"明细行"表的表名后缀：一个模块最多两张表（主表 + 明细行表）。
ROWS_SHEET_SUFFIX = "_Rows"

#: 明细行表里标识该行属于哪个重复组的列。
GROUP_COLUMN = "group"

#: 明细行表里该行自身的 ID（可被块表的 ``owner_id`` 引用，如 A9.3 的实测比值）。
ROWS_ID_COLUMN = "row_id"

#: A14（样品自身比值）与 A9.3（标样实测比值）共用 B6 块表，用该列区分。
RATIO_HOST_COLUMN = "ratio_host"

#: 材料专属模块的 ``O12 Material`` 取值 → 材料表名。
MATERIAL_SHEET_BY_VALUE: dict[str, str] = {
    "ore": "11_Ore",
    "glass": "12_Glass",
    "metal": "13_Metal",
    "coin": "14_Coins",
    "pigment": "15_Pigment",
    "by-product": "16_ByProducts",
}

#: ``O12 Material`` 取值 → 模块键（``TableKey.value``）。注意两处命名不同：
#: ``coin`` → ``metal-coins``、``by-product`` → ``by-products``。
#: 校验层用本表判断"O12 有值但对应材料模块无记录"，与表名映射共用同一套取值。
MATERIAL_TABLE_BY_VALUE: dict[str, str] = {
    "ore": TableKey.ORE.value,
    "glass": TableKey.GLASS.value,
    "metal": TableKey.METAL.value,
    "coin": TableKey.COINS.value,
    "pigment": TableKey.PIGMENT.value,
    "by-product": TableKey.BY_PRODUCTS.value,
}

#: 实体表名（模块 → 表名），按层级顺序，同时作为编号依据。
ENTITY_SHEET_BY_TABLE: dict[str, str] = {
    "sites": "1_Site",
    "assemblages": "2_Assemblage",
    "objects": "3_Object",
    "samples": "4_Sample",
    "analyses": "5_Analysis",
    "ore": "11_Ore",
    "glass": "12_Glass",
    "metal": "13_Metal",
    "metal-coins": "14_Coins",
    "pigment": "15_Pigment",
    "by-products": "16_ByProducts",
}

#: 可复用块 → 块表名。
BLOCK_SHEET_BY_BLOCK: dict[Block, str] = {
    Block.PERSON: "6_Person",
    Block.DATING: "7_Dating",
    Block.CHEMISTRY: "8_Chemistry",
    Block.RELATION: "9_Relation",
    Block.STATUS: "10_Status",
    Block.LIA_RATIO: "17_LIA-Ratio",
}

#: 前后置信息表。
SHEET_README = "README"
SHEET_SCHEMA = "0_SCHEMA"
SHEET_VOCAB = "0_VOCAB"
SHEET_CHECK = "99_CHECK"

#: 需要用户填写的表不包含这几个。
_NON_ENTRY_SHEETS = frozenset({SHEET_README, SHEET_SCHEMA, SHEET_VOCAB, SHEET_CHECK})

#: Excel 数值格式：比值 5 位小数（档案示例 18.59123），不确定度 8 位小数（示例 0.00008）。
RATIO_NUMBER_FORMAT = "0.00000"
UNCERTAINTY_NUMBER_FORMAT = "0.00000000"
DATE_NUMBER_FORMAT = "yyyy-mm-dd"

#: 比值本身（B6.2）用 5 位小数。
_RATIO_FIELD_OIDS = frozenset({"B6.2"})

#: 不确定度列用 8 位小数（档案示例 0.00008）：B6.5 绝对 / B6.6 相对，
#: 以及 A15 的四个参数不确定度 —— A15 子字段编号 1 模型名、2 Tmod、3 Tmod 不确定度、
#: 4 μ、5 μ 不确定度、6 κ、7 κ 不确定度、8 ω、9 ω 不确定度，故不确定度落在奇数位。
_UNCERTAINTY_FIELD_OIDS = frozenset({"B6.5", "B6.6"}) | frozenset(
    {f"A15.{2 * index + 1}" for index in range(1, len(AGE_MODEL_PARAMETERS) + 1)}
)

#: 列宽启发式（按取值类型）；命中 ``_WIDTH_BY_OID`` 时优先。
_WIDTH_BY_KIND: dict[ValueKind, int] = {
    ValueKind.DATE: 13,
    ValueKind.DECIMAL: 14,
    ValueKind.NUMBER: 14,
    ValueKind.INTEGER: 10,
    ValueKind.CONTROLLED_VOCAB: 24,
    ValueKind.PID: 26,
    ValueKind.URL: 30,
    ValueKind.EMAIL: 26,
    ValueKind.FILE_PATH: 30,
    ValueKind.YES_NO_UNCLEAR: 12,
    ValueKind.GEOL_TYPE: 15,
    ValueKind.UNIT_AGE: 10,
    ValueKind.SIGMA: 8,
    ValueKind.RATIO_NAME: 15,
    ValueKind.RATIO_SOURCE: 12,
    ValueKind.MIXED: 24,
    ValueKind.FREE_TEXT: 34,
}

_WIDTH_BY_OID: dict[str, int] = {
    "A0": 14,
    "SI0": 14,
    "AS0": 16,
    "O0": 14,
    "S0": 14,
    "B6.1": 15,
    "B6.2": 15,
    "B6.5": 18,
    "B6.6": 18,
}

#: 默认列宽。
DEFAULT_COLUMN_WIDTH = 18


class SheetKind(str, Enum):
    """工作表的角色。"""

    README = "readme"
    SCHEMA = "schema"
    VOCAB = "vocab"
    ENTITY = "entity"
    BLOCK = "block"
    GROUP = "group"
    CHECK = "check"


@dataclass(frozen=True)
class ColumnSpec:
    """工作表里的一列（对应档案的一个字段）。"""

    #: 档案字段 ID；块表里的列可能在多个宿主间重复。
    oid: str
    #: 机器可读键名。
    key: str
    #: 中英标签。
    label_en: str
    label_zh: str
    #: 强制级别与出现次数。
    obligation: Obligation
    #: 取值类型，决定控件与校验。
    value_kind: ValueKind
    #: 受控词表 ID；自由文本为 ``None``。
    vocab_id: str | None
    #: 档案原文：定义 / 允许值 / 示例。
    definition: str
    allowed: str
    example: str
    #: 源文档与行号，便于回溯到 `reference/metadata`。
    source_doc: str
    source_line: int
    #: 该字段所属的可复用块；模块自有字段为 ``None``。
    block: Block | None
    #: 内联该块的宿主字段 OID（如 ``A14`` / ``A9.3``）。
    host_oid: str | None
    #: 父字段 OID（档案的 OID 层级）；顶层字段为 ``None``。
    #: 用于判断"必填"是否受限于某个可选分组（见 `SheetSpec.columns_for_record`）。
    parent: str | None
    #: Excel 列宽与数值格式。
    width: int
    number_format: str | None
    #: 是否由工具补齐（录入者可留空，校验时不报必填错）。
    is_system_provided: bool = False
    #: 自近及远的祖先 OID 链（**含非列的分组节点**，如 ``A8``）。
    #: 由注册表的 ``FieldSpec.parent`` 推出，不能靠字符串截断 —— 钱币表的
    #: ``OM.C7.1`` 截断会得到并不存在的 ``OM.C``。
    ancestors: tuple[str, ...] = ()
    #: ``ancestors`` 中**可选的**分组节点（``occurrence`` 为 ``0-1``/``0-n``）。
    #: 只有它们才允许"整组未填 → 子字段不作要求"；必填容器（如 ``A6`` 仪器，
    #: ``occurrence = 1``）不在此列，否则 ``A6.1`` 会被自己的空值"自我抑制"而永不被要求。
    optional_ancestors: tuple[str, ...] = ()

    @property
    def qualified_key(self) -> str:
        """``ID 键名``，用作校验报告里的列定位。"""
        return f"{self.oid} {self.key}"

    @property
    def header_key(self) -> str:
        """表头第 1 行文本（机器可读）。"""
        return self.qualified_key

    @property
    def header_label(self) -> str:
        """表头第 2 行文本（人读，带级别标记）。"""
        return f"{self.label_zh or self.label_en} {self.obligation.marker}"

    @property
    def is_required_from_provider(self) -> bool:
        """必填且须由录入者提供 —— 只有这种列会在 Excel 里标红。"""
        return self.obligation is Obligation.MANDATORY and not self.is_system_provided


@dataclass(frozen=True)
class SheetSpec:
    """一张工作表及其列。"""

    #: 工作表名（已满足 Excel 命名限制）。
    name: str
    #: 表标题（中英），用于 README 与提示。
    title_en: str
    title_zh: str
    #: 角色。
    kind: SheetKind
    #: 承载的模块（实体表）；块表与信息表为 ``None``。
    table: str | None
    #: 宿主表名（块表/组表指向实体表）；实体表为 ``None``。
    parent_sheet: str | None
    #: 关联父行的列名（块表为 ``owner_id`` 语义的列）。
    fk_column: str | None
    #: 该表承载的可复用块。
    block: Block | None
    #: 该表承载的所有宿主字段 OID（块被多次内联时会有多个）。
    host_oids: tuple[str, ...]
    #: 用户填写的列。
    columns: tuple[ColumnSpec, ...]
    #: 前置辅助列名（如 ``owner_sheet`` / ``owner_id``），在 ``columns`` 之前。
    helper_columns: tuple[str, ...] = ()
    #: 该表是否由用户填写。
    is_entry: bool = True

    @property
    def field_columns(self) -> tuple[ColumnSpec, ...]:
        """档案字段列（不含前置辅助列）。"""
        return self.columns

    @property
    def all_header_keys(self) -> tuple[str, ...]:
        """全部表头键（辅助列在前）。"""
        return tuple(self.helper_columns) + tuple(c.header_key for c in self.columns)

    @property
    def all_header_labels(self) -> tuple[str, ...]:
        """全部表头标签（辅助列在前）。

        同一张表内出现重名标签时追加 ``[OID]`` 消歧 —— 档案里确有重名，例如
        ``SI5.1.1`` 与 ``SI5.4.1.1`` 都叫 "Longitude"。人工填表时两张同名列表头
        必须能分辨，否则会填错列。
        """
        helpers = [_HELPER_LABELS.get(name, name) for name in self.helper_columns]
        labels = [c.header_label for c in self.columns]
        duplicates = {
            label for label in labels if labels.count(label) > 1
        }
        resolved = [
            f"{label} [{column.oid}]" if label in duplicates else label
            for label, column in zip(labels, self.columns)
        ]
        return tuple(helpers) + tuple(resolved)

    @property
    def mandatory_columns(self) -> tuple[ColumnSpec, ...]:
        """必填列。"""
        return tuple(c for c in self.columns if c.obligation is Obligation.MANDATORY)

    @property
    def column_count(self) -> int:
        """总列数（含辅助列）。"""
        return len(self.helper_columns) + len(self.columns)

    def column(self, oid: str) -> ColumnSpec | None:
        """按字段 OID 取列（块表内可能有多列同 OID，取首个）。"""
        for spec in self.columns:
            if spec.oid == oid:
                return spec
        return None

    def column_by_key(self, key: str) -> ColumnSpec | None:
        """按键名取列。"""
        for spec in self.columns:
            if spec.key == key:
                return spec
        return None

    def columns_for_record(self, record: Mapping[str, object]) -> tuple[ColumnSpec, ...]:
        """按记录筛出**适用**的列，供校验使用。

        两条筛选规则，都源自档案语义：

        1. **明细行表按 ``group`` 筛列。** 明细行表把多个重复组合并到一张表里，用 ``group``
           列（取值 = 组根 OID）标明该行属于哪个组。不筛的话 ``group=A15`` 的行会被要求填
           A9 组的必填字段（``A9.1`` 标样名等），产生一批永远消不掉的假错。
        2. **未启用的可选分组不施必填。** 档案把 ``SI5.2 Boundary box``、``A8 Mean total
           intensity`` 这类组声明为 ``0–1``，而组内子字段（四至、强度值/单位）是 mandatory ——
           这个 mandatory 只在**该组被使用时**才成立。若整组一格未填，就不该要求它的子字段，
           否则用户只填"遗址名 + 分析类型 + 三个比值"就会被 23 条 ERROR 挡住，误以为必须填满
           全部 497 个字段。
           "启用"的判据：该组的**后代中有任意一格有值**。于是只填了西边界而不填东西南北，
           仍然会报缺三边；一格不填则整组跳过。

        Args:
            record: 一行记录（键为表头机器键名）。

        Returns:
            该行适用的列。本表没有 ``group`` 列、或该行未填/填了未知 ``group`` 时，
            只应用规则 2（``group`` 自身的必填错由 `validate_sheets` 负责）。
        """
        applicable = self._columns_for_group(record)
        return self._drop_unused_optional_groups(applicable, record)

    def _columns_for_group(
        self, record: Mapping[str, object]
    ) -> tuple[ColumnSpec, ...]:
        """规则 1：明细行表按 ``group`` 只保留该组根及其后代的列。"""
        if GROUP_COLUMN not in self.helper_columns:
            return self.columns
        group = record.get(GROUP_COLUMN)
        root = str(group).strip() if group is not None else ""
        if not root or root not in self.host_oids:
            return self.columns
        prefix = f"{root}."
        return tuple(
            column
            for column in self.columns
            if column.oid == root or column.oid.startswith(prefix)
        )

    def _drop_unused_optional_groups(
        self,
        columns: tuple[ColumnSpec, ...],
        record: Mapping[str, object],
    ) -> tuple[ColumnSpec, ...]:
        """规则 2：丢弃"祖先分组一格未填"的那些列。

        祖先分组 = 该列 ``optional_ancestors`` 里的那些 OID（纯分组节点，如 ``A8``、``SI5.2``）。
        只要某个这样的祖先的后代**全为空**，就把该祖先整棵子树从校验列里去掉。

        **只对可选分组生效**：``A6 Measurement device`` 是 ``occurrence = 1`` 的必填容器，
        若也算进来，``A6.1 Instrument type`` 会因自己为空而"自我抑制"永不被要求 —— 而档案
        明确要求它。这条判据与工作簿里"红底"条件格式的因子保持一致。
        """
        group_prefixes = {
            ancestor
            for column in columns
            for ancestor in column.optional_ancestors
        }
        if not group_prefixes:
            return columns

        # 明细行表里"填了 group"本身就是"这组在用"的声明：用户选好 group 还没填值时，
        # 该组的必填项必须照常报出来（否则整组列会被自己"未填"这一事实抹掉，必填永不触发）。
        declared = ""
        if GROUP_COLUMN in self.helper_columns:
            raw = record.get(GROUP_COLUMN)
            candidate = str(raw).strip() if raw is not None else ""
            if candidate in self.host_oids:
                declared = candidate

        def _group_has_value(oid: str) -> bool:
            """该分组是否已启用：被 ``group`` 声明为**它自己**，或其自身/后代至少填了一格。

            声明只对**该组自身**（以及它的祖先）算数，**不向下传递**：行上写
            ``group=O5`` 只说明"器物标识符这一组在用"，不代表其中嵌套的 ``O5.1``
            持久标识符子组也在用 —— 否则 ``O5.1.1``/``O5.1.2`` 会被无条件要求。
            """
            if declared and (
                declared == oid or declared.startswith(f"{oid}.")
            ):
                return True
            prefix = f"{oid}."
            for column in self.columns:
                if column.oid != oid and not column.oid.startswith(prefix):
                    continue
                value = record.get(column.header_key)
                if value is None:
                    continue
                if isinstance(value, str) and not value.strip():
                    continue
                return True
            return False

        disabled = {oid for oid in group_prefixes if not _group_has_value(oid)}
        if not disabled:
            return columns
        return tuple(
            column
            for column in columns
            if disabled.isdisjoint(column.optional_ancestors)
        )

    def stray_columns_for_record(
        self, record: Mapping[str, object]
    ) -> tuple[ColumnSpec, ...]:
        """本行**不属于**其 ``group``、却填了值的列（多半是填错行的信号）。"""
        applicable = {column.oid for column in self.columns_for_record(record)}
        strays: list[ColumnSpec] = []
        for column in self.columns:
            if column.oid in applicable:
                continue
            value = record.get(column.header_key)
            if value is None or (isinstance(value, str) and not value.strip()):
                continue
            strays.append(column)
        return tuple(strays)


#: 辅助列的表头标签（中文 + 级别）。
_HELPER_LABELS: dict[str, str] = {
    OWNER_SHEET_COLUMN: "所属表 ★必填",
    OWNER_ID_COLUMN: "所属记录ID ★必填",
    RATIO_HOST_COLUMN: "比值来源 ★必填",
    ROWS_ID_COLUMN: "行ID ☆建议（被引用时必填）",
    GROUP_COLUMN: "重复组 ★必填",
    "site_id": "遗址ID ★必填",
    "assemblage_id": "堆积单位ID ☆建议",
    "object_id": "器物ID ★必填",
    "sample_id": "样品ID ★必填",
    "parent_id": "所属行ID ★必填",
}


@dataclass(frozen=True)
class WorkbookLayout:
    """整本录入工作簿的布局。"""

    sheets: tuple[SheetSpec, ...]

    @property
    def entry_sheets(self) -> tuple[SheetSpec, ...]:
        """需要用户填写的工作表。"""
        return tuple(s for s in self.sheets if s.is_entry)

    @property
    def sheet_names(self) -> tuple[str, ...]:
        """全部工作表名（保持定义顺序）。"""
        return tuple(s.name for s in self.sheets)

    def sheet(self, name: str) -> SheetSpec | None:
        """按表名取表。"""
        for spec in self.sheets:
            if spec.name == name:
                return spec
        return None

    def sheet_for_table(self, table: TableKey | str) -> SheetSpec | None:
        """按模块键取实体表。"""
        target = table.value if isinstance(table, TableKey) else str(table)
        for spec in self.sheets:
            if spec.table == target and spec.kind in (
                SheetKind.ENTITY,
                SheetKind.GROUP,
            ):
                return spec
        return None

    def sheet_for_block(self, block: Block) -> SheetSpec | None:
        """按可复用块取块表。"""
        for spec in self.sheets:
            if spec.block is block:
                return spec
        return None

    def columns_for(self, sheet_name: str) -> tuple[ColumnSpec, ...]:
        """取某表的字段列；表不存在时返回空元组。"""
        found = self.sheet(sheet_name)
        return found.columns if found is not None else ()

    def table_key_for_sheet(self, sheet_name: str) -> str | None:
        """工作表 → 模块键（导入器用于决定校验哪张表的规则）。"""
        found = self.sheet(sheet_name)
        return found.table if found is not None else None


def _column_width(spec: FieldSpec) -> int:
    """按字段 OID / 取值类型给出列宽。"""
    if spec.oid in _WIDTH_BY_OID:
        return _WIDTH_BY_OID[spec.oid]
    return _WIDTH_BY_KIND.get(spec.value_kind, DEFAULT_COLUMN_WIDTH)


def _number_format(spec: FieldSpec) -> str | None:
    """按字段给出 Excel 数值格式。"""
    if spec.oid in _RATIO_FIELD_OIDS:
        return RATIO_NUMBER_FORMAT
    if spec.oid in _UNCERTAINTY_FIELD_OIDS:
        return UNCERTAINTY_NUMBER_FORMAT
    if spec.value_kind is ValueKind.DATE:
        return DATE_NUMBER_FORMAT
    return None

def _ancestor_oids(
    by_oid: Mapping[str, FieldSpec], oid: str
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """由注册表的 ``parent`` 链推出祖先 OID。

    不能靠字符串截断 OID：钱币表 ``OM.C7.1`` 截断会得到不存在的 ``OM.C``，而它会因"没有
    后代列"被误判为未启用的分组，把 ``OM.C7.1``/``OM.C7.2`` 整棵子树错误地跳过校验。

    Returns:
        ``(全部祖先, 其中的可选分组祖先)``。可选 = ``occurrence`` 为 ``0-1``/``0-n``；
        祖先在表内查不到时按可选处理（保守：宁可少要求，也不要凭空要求用户填不出来源的值）。

        **块根不算可选分组**：块表的字段（``B6.1``）其祖先链首项就是块根（``B6``），而块根不在
        块自己的字段集合里、会被上面那条"查不到 ⇒ 可选"命中。若照此处理，空着的比值行会因
        "B6 组未启用"而把 ``B6.1``/``B6.2`` 从必填里抹掉 —— 但**块表里有一行本身就已经声明
        了这一组在用**。故显式跳过等于该字段所属块号的祖先（块内部的嵌套可选组，如 ``B1.4``，
        仍照常计入）。
    """
    chain: list[str] = []
    optional: list[str] = []
    seen: set[str] = set()
    spec = by_oid.get(oid)
    own_block = spec.block.value if spec is not None and spec.block is not None else None
    cursor = spec.parent if spec is not None else None
    while cursor and cursor not in seen:
        seen.add(cursor)
        chain.append(cursor)
        parent_spec = by_oid.get(cursor)
        if cursor != own_block and (
            parent_spec is None
            or parent_spec.occurrence
            in (Occurrence.ZERO_TO_ONE, Occurrence.ZERO_TO_N)
        ):
            optional.append(cursor)
        cursor = parent_spec.parent if parent_spec is not None else None
    return tuple(chain), tuple(optional)


def make_column(
    spec: FieldSpec,
    *,
    host_oid: str | None = None,
    ancestors: tuple[str, ...] = (),
    optional_ancestors: tuple[str, ...] = (),
) -> ColumnSpec:
    """把注册表字段转成工作表列。

    Args:
        spec: 档案字段定义。
        host_oid: 内联该块字段的宿主字段 OID（块字段专用）。
        ancestors: 祖先 OID 链（含分组节点），由 ``_ancestor_oids`` 得到。
        optional_ancestors: 其中可选的（``0-1``/``0-n``）分组节点。

    Returns:
        对应的列定义。
    """
    effective_host = host_oid if host_oid is not None else spec.block_owner
    return ColumnSpec(
        oid=spec.oid,
        key=spec.key,
        label_en=spec.label_en,
        label_zh=spec.label_zh or spec.label_en,
        obligation=spec.obligation,
        value_kind=spec.value_kind,
        vocab_id=spec.vocab_id,
        definition=spec.definition,
        allowed=spec.allowed,
        example=spec.example,
        source_doc=spec.source_doc,
        source_line=spec.source_line,
        block=spec.block,
        host_oid=effective_host,
        parent=spec.parent,
        ancestors=ancestors,
        optional_ancestors=optional_ancestors,
        width=_column_width(spec),
        number_format=_number_format(spec),
        is_system_provided=spec.is_system_provided,
    )


def _container_oids(table) -> frozenset[str]:
    """模块内**分组节点**字段的 OID 集合。

    一个字段是分组节点，当且仅当它不携带任何取值：它的内容是别的字段（有子字段），
    或它的内容是某个内联的可复用块（是某个块字段的 `block_owner`）。

    实测档案里"有子字段的字段"全部既无 `allowed` 也无 `example`（0 例外），因此给它们
    建列只会产生永远填不上、却因 mandatory 而被标红的幽灵列（如 `A9`/`A15`/`SI5`/`A6`）。
    """
    parents = {f.parent for f in table.fields if f.parent}
    block_hosts = {f.block_owner for f in table.fields if f.block_owner}
    return frozenset(parents | block_hosts)


def _entity_columns(
    table, group_owned: frozenset[str] = frozenset()
) -> tuple[ColumnSpec, ...]:
    """实体表的字段列：主键 → 剩余字段按文档顺序。

    排除四类字段：

    1. **分组节点**（`_container_oids`）—— 它们没有自己的值，只作层级分组；
    2. **可复用块字段** —— 一律由各自的块表承载，无论其自身是否可重复；
    3. **可重复的自有组字段** —— 由明细行表承载；
    4. **组内成员**（``group_owned``）—— 即使自身不可重复也随组走，
       否则同一字段会在主表与明细行表里各出现一次。
    """
    containers = _container_oids(table)
    plain = [
        f
        for f in table.fields
        if f.block is None
        and not f.is_repeatable
        and f.oid not in group_owned
        and f.oid not in containers
    ]
    id_field = table.id_field
    ordered: list[FieldSpec] = []
    if id_field is not None and id_field in plain:
        ordered.append(id_field)
    ordered.extend(f for f in plain if f is not id_field)
    by_oid = {f.oid: f for f in table.fields}
    return tuple(
        make_column(
            f,
            ancestors=_ancestor_oids(by_oid, f.oid)[0],
            optional_ancestors=_ancestor_oids(by_oid, f.oid)[1],
        )
        for f in ordered
    )


def _block_columns(
    profile: Profile,
    block: Block,
    hosts: Iterable[tuple[str, str | None]],
) -> tuple[ColumnSpec, ...]:
    """块表的字段列。

    块字段在多个宿主内联时 oid 相同、标签相同，故只保留一份列；宿主信息通过
    ``helper_columns`` 与 ``host_oids`` 表达，不重复列。

    块内部的分组节点同样不建列（如 `B1.4` Persistent Identifier 的内容是
    `B1.4.1`/`B1.4.2`），否则块表也会出现填不上的幽灵必填列。
    """
    del hosts  # 宿主信息由 SheetSpec.host_oids 承载
    fields = profile.fields_owned_by(block)
    if not fields:
        # 回退：从任意内联了该块的模块里取（块定义缺失时仍能出表）
        for table in profile.tables:
            taken = [f for f in table.fields if f.block is block]
            if taken:
                fields = tuple(taken)
                break

    containers = {f.parent for f in fields if f.parent}
    ordered = [
        f
        for f in sorted(fields, key=lambda f: (f.order, f.depth))
        if f.oid not in containers
    ]
    by_oid = {f.oid: f for f in fields}
    return tuple(
        make_column(
            f,
            host_oid=None,
            ancestors=_ancestor_oids(by_oid, f.oid)[0],
            optional_ancestors=_ancestor_oids(by_oid, f.oid)[1],
        )
        for f in ordered
    )


def _has_repeatable_ancestor(table, spec: FieldSpec) -> bool:
    """判断字段的祖先链上是否存在可重复字段（即它是否嵌套在别的重复组里）。"""
    by_oid = {f.oid: f for f in table.fields}
    seen: set[str] = set()
    cursor = spec.parent
    while cursor and cursor not in seen:
        seen.add(cursor)
        ancestor = by_oid.get(cursor)
        if ancestor is None:
            return False
        if ancestor.is_repeatable:
            return True
        cursor = ancestor.parent
    return False


def _iter_repeatable_group_roots(table) -> tuple[FieldSpec, ...]:
    """找出模块自有的**最外层**可重复组根字段。

    两类都算组根：

    1. **容器组根** —— 可重复、有子字段（如 ``A9`` 标样、``O5`` 器物标识符）；
       其内容由子字段承载。
    2. **单列组根** —— 可重复**且没有子字段**的叶子字段（如 ``SI8 site_type`` 1–n、
       ``OO3.1`` 0–n、``A1`` 实验室编号 0–n）。这类字段本身就是可重复的值，
       若不单独成组就会无处安放 —— 实测有 14 个这样的字段。

    排除：

    - **可复用块的宿主**（``block_owner``）：其内容在块表里（如 ``A7`` → ``8_Chemistry``），
      不能重复计一张明细行表；
    - **有可重复祖先**的字段：档案存在嵌套重复组（``O5`` 1–n 之下有 ``O5.1`` 0–n），
      嵌套组随最外层组走，否则同一批字段会出现两次、工作簿也会碎成几十张近空表。
    """
    own = [f for f in table.fields if f.block is None]
    child_parents = {f.parent for f in own if f.parent}
    containers = _container_oids(table)
    block_hosts = {f.block_owner for f in table.fields if f.block_owner}

    roots: list[FieldSpec] = []
    for candidate in sorted(own, key=lambda f: (f.order, f.depth)):
        if not candidate.is_repeatable:
            continue
        if candidate.oid in block_hosts and candidate.oid not in child_parents:
            continue  # 纯块宿主：内容归块表
        if candidate.oid in containers and candidate.oid not in child_parents:
            continue  # 既非父又非叶子，理论上不存在；保守跳过以免建空组
        if _has_repeatable_ancestor(table, candidate):
            continue
        roots.append(candidate)
    return tuple(roots)


def _descendants(all_fields: Iterable[FieldSpec], root_oid: str) -> tuple[FieldSpec, ...]:
    """返回以 ``root_oid`` 为祖先的全部字段（含自身），按**文档顺序**。

    排序以 ``FieldSpec.order`` 为准（解析器按出现序赋值，内联块字段也连续编号），
    ``depth`` 仅作稳定的次要键。不用 ``(depth, order)`` 排序是因为那会产出"按层级"
    的顺序（``X1, X1.1, X1.2, X1.1.1``），列名相邻性变差，人工填表时更易看错。
    """
    ordered = sorted(all_fields, key=lambda f: (f.order, f.depth))
    collected: list[FieldSpec] = []
    prefix = f"{root_oid}."
    for spec in ordered:
        if spec.oid == root_oid or spec.oid.startswith(prefix):
            collected.append(spec)
    return tuple(collected)


def _module_rows_sheet(
    table,
    entity_sheet_name: str,
    group_members: Mapping[str, tuple[FieldSpec, ...]],
) -> SheetSpec | None:
    """为模块自有的全部可重复组合并出一张"明细行"表。

    每一行代表父记录的一个重复项；``parent_id`` 指向主表主键，``group`` 标明该行
    属于哪个重复组（取值即组根字段的 OID，如 ``SI5.1``）。

    Args:
        table: 模块定义。
        entity_sheet_name: 该模块主表的工作表名，用于派生明细行表名。
        group_members: 组根 OID → 组成员（含根与后代）。

    Returns:
        明细行表定义；模块没有自有可重复组时返回 ``None``。
    """
    if not group_members:
        return None

    # 组成员之间可能 OID 重叠（一个组是另一个组的祖先时已被
    # _iter_repeatable_group_roots 排除，但同名字段仍可能因 OID 前缀相近而重复），
    # 按文档顺序去重。**分组节点不建列**（它们没有自己的值，只作层级分组）—— 否则
    # `A9`/`A15`/`O5` 这类组根会因 mandatory 变成永远填不上、却一直标红的幽灵列。
    containers = _container_oids(table)
    seen: set[str] = set()
    columns: list[ColumnSpec] = []
    by_oid = {f.oid: f for f in table.fields}
    for members in group_members.values():
        for spec in members:
            if spec.oid in seen or spec.oid in containers:
                continue
            seen.add(spec.oid)
            ancestors, optional_ancestors = _ancestor_oids(by_oid, spec.oid)
            columns.append(
                make_column(
                    spec,
                    ancestors=ancestors,
                    optional_ancestors=optional_ancestors,
                )
            )

    name = f"{entity_sheet_name}{ROWS_SHEET_SUFFIX}"
    return SheetSpec(
        name=name[:MAX_SHEET_NAME_LENGTH],
        title_en=f"{table.label_en} rows",
        title_zh=f"{table.label_zh}：明细行",
        kind=SheetKind.GROUP,
        table=table.key.value,
        parent_sheet=entity_sheet_name,
        fk_column="parent_id",
        block=None,
        host_oids=tuple(group_members),
        columns=tuple(columns),
        helper_columns=(ROWS_ID_COLUMN, "parent_id", GROUP_COLUMN),
    )


def build_layout(profile: Profile) -> WorkbookLayout:
    """把注册表映射为录入工作簿布局。

    Args:
        profile: 由 ``profile.load_profile()`` 得到的注册表。

    Returns:
        含全部工作表定义（含 README / SCHEMA / VOCAB / CHECK 四张信息表）的布局。
    """
    sheets: list[SheetSpec] = []

    # ── 信息表 ──
    sheets.append(
        SheetSpec(
            name=SHEET_README,
            title_en="How to use this workbook",
            title_zh="使用说明",
            kind=SheetKind.README,
            table=None,
            parent_sheet=None,
            fk_column=None,
            block=None,
            host_oids=(),
            columns=(),
            is_entry=False,
        )
    )
    sheets.append(
        SheetSpec(
            name=SHEET_SCHEMA,
            title_en="Field definitions (generated)",
            title_zh="字段定义（生成，勿改）",
            kind=SheetKind.SCHEMA,
            table=None,
            parent_sheet=None,
            fk_column=None,
            block=None,
            host_oids=(),
            columns=(),
            is_entry=False,
        )
    )
    sheets.append(
        SheetSpec(
            name=SHEET_VOCAB,
            title_en="Controlled vocabularies (generated)",
            title_zh="受控词表（生成，勿改）",
            kind=SheetKind.VOCAB,
            table=None,
            parent_sheet=None,
            fk_column=None,
            block=None,
            host_oids=(),
            columns=(),
            is_entry=False,
        )
    )

    # ── 实体表与组表 ──
    group_sheets: list[SheetSpec] = []
    for table in profile.tables:
        sheet_name = ENTITY_SHEET_BY_TABLE.get(table.key.value)
        if sheet_name is None:
            continue

        # 自有可重复组：只取**最外层**根，成员 = 根及其全部后代。组内成员必须整体
        # 从主表移出，否则同一字段会在主表与明细行表里各出现一次。整个模块的重复组
        # 合并进**一张**明细行表，用 `group` 列区分 —— 避免碎成几十张近空表。
        group_members: dict[str, tuple[FieldSpec, ...]] = {
            root.oid: _descendants(table.fields, root.oid)
            for root in _iter_repeatable_group_roots(table)
        }
        group_owned = frozenset(
            spec.oid for members in group_members.values() for spec in members
        )

        parent_fk = table.parent_fk_column
        sheets.append(
            SheetSpec(
                name=sheet_name,
                title_en=table.label_en,
                title_zh=table.label_zh,
                kind=SheetKind.ENTITY,
                table=table.key.value,
                parent_sheet=(
                    ENTITY_SHEET_BY_TABLE.get(table.parent.value)
                    if table.parent is not None
                    else None
                ),
                fk_column=parent_fk or None,
                block=None,
                host_oids=(),
                columns=_entity_columns(table, group_owned),
                helper_columns=(parent_fk,) if parent_fk else (),
            )
        )

        rows_sheet = _module_rows_sheet(table, sheet_name, group_members)
        if rows_sheet is not None:
            group_sheets.append(rows_sheet)

    # ── 可复用块表 ──
    for block, sheet_name in BLOCK_SHEET_BY_BLOCK.items():
        # 宿主 = 内联该块的字段（`block_owner`），不是块字段自身的 OID。
        # 同一个块可能被同一模块内联多次（如 Analyses 的 B5 relation ×4），故需去重。
        hosts: list[tuple[str, str]] = []
        for table in profile.tables:
            for spec in table.fields:
                if spec.block is not block:
                    continue
                owner = spec.block_owner
                if owner is None:
                    continue
                candidate = (table.key.value, owner)
                if candidate not in hosts:
                    hosts.append(candidate)
        if not hosts:
            continue
        helper_names: tuple[str, ...] = (OWNER_SHEET_COLUMN, OWNER_ID_COLUMN)
        if block is Block.LIA_RATIO:
            helper_names = (OWNER_SHEET_COLUMN, OWNER_ID_COLUMN, RATIO_HOST_COLUMN)
        sheets.append(
            SheetSpec(
                name=sheet_name,
                title_en=block.name.replace("_", " ").title(),
                title_zh=block.label_zh,
                kind=SheetKind.BLOCK,
                table=None,
                parent_sheet=None,
                fk_column=OWNER_ID_COLUMN,
                block=block,
                host_oids=tuple(owner for _, owner in hosts),
                columns=_block_columns(profile, block, hosts),
                helper_columns=helper_names,
            )
        )

    sheets.extend(group_sheets)

    # ── 校验报告表 ──
    sheets.append(
        SheetSpec(
            name=SHEET_CHECK,
            title_en="Validation report (generated)",
            title_zh="校验报告（生成，勿改）",
            kind=SheetKind.CHECK,
            table=None,
            parent_sheet=None,
            fk_column=None,
            block=None,
            host_oids=(),
            columns=(),
            is_entry=False,
        )
    )

    return WorkbookLayout(sheets=tuple(sheets))


def material_sheet_for(material_value: str) -> str | None:
    """``O12 Material`` 取值 → 材料表名。

    Args:
        material_value: 录入值（大小写与空格不敏感）。

    Returns:
        材料表名；无法识别时返回 ``None``。
    """
    table = material_table_for(material_value)
    if table is None:
        return None
    return ENTITY_SHEET_BY_TABLE.get(table)


def material_table_for(material_value: str) -> str | None:
    """``O12 Material`` 取值 → 模块键。

    容忍大小写、前后空白、内部空格（``by product`` → ``by-product``）与常见复数
    （``coins`` / ``ores``）。

    Args:
        material_value: 录入值。

    Returns:
        模块键（``TableKey.value``）；无法识别时返回 ``None``。
    """
    normalized = str(material_value or "").strip().lower().replace(" ", "-")
    if not normalized:
        return None
    if normalized in MATERIAL_TABLE_BY_VALUE:
        return MATERIAL_TABLE_BY_VALUE[normalized]
    # 容忍复数与近义写法（先精确匹配，再按前缀匹配）
    for key, table in MATERIAL_TABLE_BY_VALUE.items():
        if normalized == f"{key}s" or normalized.startswith(key):
            return table
    return None


def owner_sheet_options(layout: WorkbookLayout) -> tuple[str, ...]:
    """块表 ``owner_sheet`` 列允许的取值（供 Excel 下拉）。

    含**实体表**与**明细行表**：前者用主键定位（如 ``1_Site`` → site id），后者用
    ``row_id`` 定位（如 ``5_Analysis_Rows`` → 某个 A9 标样行）。块表据此把
    B1/B2/B3/B4/B5/B6 的重复行挂到具体宿主上。
    """
    return tuple(
        spec.name
        for spec in layout.sheets
        if spec.kind in (SheetKind.ENTITY, SheetKind.GROUP)
    )


__all__ = [
    "BLOCK_SHEET_BY_BLOCK",
    "DEFAULT_COLUMN_WIDTH",
    "ENTITY_SHEET_BY_TABLE",
    "GROUP_COLUMN",
    "MATERIAL_SHEET_BY_VALUE",
    "MATERIAL_TABLE_BY_VALUE",
    "MAX_SHEET_NAME_LENGTH",
    "OWNER_ID_COLUMN",
    "OWNER_SHEET_COLUMN",
    "RATIO_HOST_COLUMN",
    "ROWS_ID_COLUMN",
    "ROWS_SHEET_SUFFIX",
    "SHEET_CHECK",
    "SHEET_README",
    "SHEET_SCHEMA",
    "SHEET_VOCAB",
    "ColumnSpec",
    "SheetKind",
    "SheetSpec",
    "WorkbookLayout",
    "build_layout",
    "make_column",
    "material_sheet_for",
    "material_table_for",
    "owner_sheet_options",
]
