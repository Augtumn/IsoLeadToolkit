"""工作表辅助列校验：父外键 / 明细行 parent_id·group / 块表 owner_* / ratio_host。

`validate.py` 校验**档案字段**；本模块校验**工作表结构列** —— 那些不对应任何档案字段、
却决定"这一行挂到哪里"的辅助列（`layout.py` 的 ``helper_columns``）：

- **实体表**：父外键列（``SheetSpec.fk_column``）在本行有其它值时必填；``assemblage_id`` 与
  ``sample_id`` 依档案"允许跨级直挂"的宽松原则降为 WARNING。
- **明细行表**（``SheetKind.GROUP``）：``parent_id`` 指向主表主键、``group`` 指明重复组，
  且 ``group`` 必须落在 ``SheetSpec.host_oids`` 内。
- **块表**（``SheetKind.BLOCK``）：``owner_sheet`` 必须是合法宿主表名（主表或明细行表），
  本行有档案字段值时 ``owner_id`` 必填。
- **``17_LIA-Ratio``**：``ratio_host`` 只能是 ``A14``（分析自身比值）或 ``A9.3``
  （标样实测比值）。

**明确不做**：块表 ``(owner_sheet, owner_id)`` 指向的记录是否真实存在（跨表完整性）。那需要
整本工作簿一起核对，属于导入层职责（`docs/metadata_profile.md` 记为已知限制）；本模块只看
单行内辅助列的自洽性。

依赖方向：本模块**单向** ``from .validate import ...``（`validate.py` 不反向 import，故无循环）。
按 `docs/dev_conventions.md` §9.1，模块内 helper 以 ``_`` 前缀且不导出；此处是**显式例外**：
复用了 `validate.py` 的私有 helper（``_RecordContext`` / ``_text`` / ``_is_blank`` /
``_generic_record_id``）—— 两者同属"元数据校验"子域，**改动必须同步**。

设计约束：不得导入 PyQt5 / pandas / openpyxl，不做文件 IO，无全局可变状态。
"""
from __future__ import annotations

import logging
from typing import Mapping, Sequence

from .layout import (
    ENTITY_SHEET_BY_TABLE,
    GROUP_COLUMN,
    OWNER_ID_COLUMN,
    OWNER_SHEET_COLUMN,
    RATIO_HOST_COLUMN,
    ROWS_ID_COLUMN,
    ROWS_SHEET_SUFFIX,
    SheetKind,
    SheetSpec,
    WorkbookLayout,
    owner_sheet_options,
)
from .spec import Block
from .validate import (
    Severity,
    ValidationIssue,
    _RecordContext,
    _generic_record_id,
    _is_blank,
    _text,
)

logger = logging.getLogger(__name__)

# 消息键：稳定英文原文，含 {} 占位符；locales/zh.json 与 locales/en.json 登记同一套键。
MSG_HELPER_REQUIRED = "Required column '{column}' is empty on sheet '{sheet}'"
MSG_HELPER_INVALID_VALUE = (
    "'{value}' is not an allowed value for column '{column}' on sheet '{sheet}'; "
    "allowed values: {allowed}"
)

#: 本模块的消息键（`validate.MESSAGE_KEYS` 之外的补充清单）。
MESSAGE_KEYS: tuple[str, ...] = (MSG_HELPER_REQUIRED, MSG_HELPER_INVALID_VALUE)

#: 明细行表的父键列名（`layout._module_rows_sheet` 写入 ``fk_column``；仅作兜底）。
PARENT_ID_COLUMN = "parent_id"

#: 父外键降为 WARNING 的列：档案允许 Object / Analysis / Sample 直接挂上级，
#: 且 ``assemblage_id`` 在工作簿标签里是 ☆建议 —— 故不用 ERROR 阻断录入。
_SOFT_PARENT_FKS = frozenset({"assemblage_id", "sample_id"})

#: ``ratio_host`` 的两个合法宿主字段 OID（A14 分析自身比值 / A9.3 标样实测比值）。
_RATIO_HOSTS = frozenset({"A14", "A9.3"})


def validate_sheet_helpers(
    sheet: SheetSpec,
    record: Mapping[str, object],
    *,
    record_id: str = "",
    layout: WorkbookLayout | None = None,
) -> list[ValidationIssue]:
    """校验一行记录里的工作表辅助列（5 条规则，见模块 docstring）。

    问题对象里 ``table`` 与 ``params["sheet"]`` 都是**工作表名**：辅助列属于工作表而非档案
    模块，报表要能直接定位到 Excel 表。完全空白的行同样会报必需辅助列缺失，调用方应在读表
    阶段先跳过整行空白的行。

    Args:
        sheet: 工作表定义（`layout.SheetSpec`）。
        record: 一行记录；辅助列按列名取值（``owner_sheet`` / ``owner_id`` / ``parent_id`` …）。
        record_id: 记录标识；为空时取 ``row_id``，再退到常见 ``terralid_*_id`` 列。
        layout: 整本工作簿布局；给出时 ``owner_sheet`` 候选取 ``owner_sheet_options(layout)``
            （主表 + 明细行表）。为 ``None`` 时退化为"实体表名 / 实体表名 + ``_Rows``"的
            结构判断并记 ``logger.debug``（只校验单表时拿不到整本布局）。

    Returns:
        问题列表；``SheetKind`` 为信息表（README / SCHEMA / VOCAB / CHECK）时为空列表。
    """
    ctx = _RecordContext(
        sheet.name,
        record_id or _text(record.get(ROWS_ID_COLUMN)) or _generic_record_id(record),
    )
    issues: list[ValidationIssue] = []
    fk_column = sheet.fk_column or ""

    # 规则 1：实体表父外键（assemblage_id / sample_id 降为 WARNING）。
    if sheet.kind is SheetKind.ENTITY and fk_column:
        if _is_blank(record.get(fk_column)) and _row_has_values(record, exclude=fk_column):
            severity = Severity.WARNING if fk_column in _SOFT_PARENT_FKS else Severity.ERROR
            issues.append(_helper_required(ctx, fk_column, severity))

    # 规则 2：明细行表的 parent_id / group。
    if sheet.kind is SheetKind.GROUP:
        parent_column = fk_column or PARENT_ID_COLUMN
        if _is_blank(record.get(parent_column)):
            issues.append(_helper_required(ctx, parent_column))
        group = _text(record.get(GROUP_COLUMN))
        if not group:
            issues.append(_helper_required(ctx, GROUP_COLUMN))
        elif group not in sheet.host_oids:
            issues.append(_helper_invalid(ctx, GROUP_COLUMN, group, sheet.host_oids))

    # 规则 3：块表的宿主定位（owner_sheet 合法 + 有数据时 owner_id 必填）。
    if sheet.kind is SheetKind.BLOCK:
        owner_sheet = _text(record.get(OWNER_SHEET_COLUMN))
        if not owner_sheet:
            issues.append(_helper_required(ctx, OWNER_SHEET_COLUMN))
        elif not _is_owner_sheet(owner_sheet, layout):
            candidates = _owner_sheet_candidates(layout)
            issues.append(_helper_invalid(ctx, OWNER_SHEET_COLUMN, owner_sheet, candidates))
        if _is_blank(record.get(OWNER_ID_COLUMN)) and _has_field_values(sheet, record):
            issues.append(_helper_required(ctx, OWNER_ID_COLUMN))

    # 规则 4：17_LIA-Ratio 的 ratio_host。
    if RATIO_HOST_COLUMN in sheet.helper_columns or sheet.block is Block.LIA_RATIO:
        ratio_host = _text(record.get(RATIO_HOST_COLUMN))
        if not ratio_host:
            issues.append(_helper_required(ctx, RATIO_HOST_COLUMN))
        elif ratio_host not in _RATIO_HOSTS:
            issues.append(
                _helper_invalid(ctx, RATIO_HOST_COLUMN, ratio_host, tuple(sorted(_RATIO_HOSTS)))
            )
    return issues


def _helper_required(
    ctx: _RecordContext, column: str, severity: Severity = Severity.ERROR
) -> ValidationIssue:
    """构造"必需辅助列为空"的问题。"""
    return ctx.issue(
        severity, column, column, MSG_HELPER_REQUIRED, {"column": column, "sheet": ctx.table}
    )


def _helper_invalid(
    ctx: _RecordContext, column: str, value: str, allowed: Sequence[str]
) -> ValidationIssue:
    """构造"辅助列取值不在候选内"的问题。"""
    return ctx.issue(
        Severity.ERROR, column, column, MSG_HELPER_INVALID_VALUE,
        {
            "value": value,
            "column": column,
            "sheet": ctx.table,
            "allowed": ", ".join(str(item) for item in allowed),
        },
    )


def _row_has_values(record: Mapping[str, object], *, exclude: str) -> bool:
    """本行除 ``exclude`` 外是否还有非空值。"""
    return any(key != exclude and not _is_blank(value) for key, value in record.items())


def _has_field_values(sheet: SheetSpec, record: Mapping[str, object]) -> bool:
    """本行的档案字段列是否有值（辅助列不算）。"""
    for column in sheet.columns:
        for key in (column.header_key, column.key, column.oid):
            if key in record and not _is_blank(record[key]):
                return True
    return False


def _owner_sheet_candidates(layout: WorkbookLayout | None) -> tuple[str, ...]:
    """``owner_sheet`` 的候选表名：主表 + 明细行表。"""
    if layout is not None:
        return owner_sheet_options(layout)
    logger.debug("No layout given; owner_sheet candidates come from the sheet-name structure")
    main_sheets = tuple(ENTITY_SHEET_BY_TABLE.values())
    return main_sheets + tuple(f"{name}{ROWS_SHEET_SUFFIX}" for name in main_sheets)


def _is_owner_sheet(value: str, layout: WorkbookLayout | None) -> bool:
    """``owner_sheet`` 是否为合法宿主表名（有布局时以 ``owner_sheet_options`` 为准）。"""
    if layout is not None:
        return value in owner_sheet_options(layout)
    if value in ENTITY_SHEET_BY_TABLE.values():
        return True
    return value.endswith(ROWS_SHEET_SUFFIX) and value[: -len(ROWS_SHEET_SUFFIX)] in set(
        ENTITY_SHEET_BY_TABLE.values()
    )


__all__ = [
    "MESSAGE_KEYS",
    "MSG_HELPER_INVALID_VALUE",
    "MSG_HELPER_REQUIRED",
    "PARENT_ID_COLUMN",
    "validate_sheet_helpers",
]
