"""录入工作簿的用例层：生成模板 / 校验 / 导入（补齐比值与 A15 年龄模型参数）。

`data/metadata_profile/` 提供纯能力（布局、读写、校验、比值推导），`data/geochemistry/`
提供年龄模型反演，本模块只做**编排**：三个入口 + 两个冻结 DTO。

四条口径（`docs/metadata_profile.md` §6）：

1. **先校验、后写盘**：有 ERROR 时只写 `99_CHECK`，数据行一个字节都不改。
2. **只写被补齐的表**：`write_records()` 会先清空目标表的数据行，故不把"读出来又原样写回"的
   表交给它；日期列写前还原成 ``date``，避免把日期写成文本。
3. **地球化学引擎是可选能力**：A15 反演失败只记 ``logger.warning``，不影响导入。
4. **列按行 ``group`` 筛**：`validate_workbook()` 不含辅助列规则，且明细行表把多个重复组合并成
   一张表，故这里逐记录串 `validate_columns(columns_for_record(...))` + `validate_sheet_helpers()`，
   再统一跑条件联动与外键（否则 ``group=A15`` 的行会被要求填 A9 组的必填字段）。

依赖方向：`application/` → `data/`（不得反向）；不导入 PyQt5，也不用 openpyxl —— 所有 Excel
细节经 `data.metadata_profile.io_xlsx`。
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from data.metadata_profile import io_xlsx, ratios, spec, validate, validate_sheets
from data.metadata_profile.layout import (
    GROUP_COLUMN,
    OWNER_ID_COLUMN,
    OWNER_SHEET_COLUMN,
    RATIO_HOST_COLUMN,
    ROWS_ID_COLUMN,
    SheetKind,
    SheetSpec,
    WorkbookLayout,
    build_layout,
)
from data.metadata_profile.profile import Profile, load_profile

logger = logging.getLogger(__name__)

#: 缺省模板文件名；目录沿用生成器的 `DEFAULT_OUTPUT_DIR`（`数据/`），不在这里复写路径。
TEMPLATE_FILENAME = "entry_template_TerraLID_v{version}.xlsx"
#: `io_xlsx` 写进记录里的 Excel 行号键（写回时显式剔除）。
_ROW_NUMBER_KEY = "__row__"
#: ERROR 的字符串口径（DTO 存字符串，便于 Qt 渲染与写 Excel）。
_SEVERITY_ERROR = validate.Severity.ERROR.value
#: 铅同位素比值块（B6）的字段 OID：列名固定为 ``B6.x``，语义取自 `spec`。
_RATIO_NAME_OID, _RATIO_VALUE_OID = "B6.1", "B6.2"
_RATIO_SIGMA_OID, _RATIO_ABSOLUTE_OID = "B6.4", "B6.5"
_RATIO_RELATIVE_OID, _RATIO_SOURCE_OID = "B6.6", "B6.7"
#: A15 参数 → `calculate_all_parameters()` 的结果键：μ/κ 取**模型参考**反演
#: （`calculate_model_mu` / `calculate_model_kappa`），ω 取源区反演，Tmod 取 `t_Model (Ma)`。
_A15_VALUE_KEYS: tuple[tuple[str, str], ...] = (
    ("A15.2", "t_Model (Ma)"),
    ("A15.4", "mu_model"),
    ("A15.6", "kappa_model"),
    ("A15.8", "omega"),
)
#: A15.1 模型名（封闭词表 `spec.AGE_MODEL_NAMES`）；参数没有模型名就无法解释。
_A15_MODEL_NAME_OID = "A15.1"
#: 承载 A15 列的判定列（真实档案在 `5_Analysis_Rows`，合成注册表在主表）。
_A15_MARKER_OID = "A15.2"
#: 明细行表里 A15 组的分组名（`layout.GROUP_COLUMN` 的取值 = 组根字段 OID）。
_A15_GROUP = "A15"
#: 引擎预设模型名 → 档案 A15.1 允许值（小写子串匹配）。Geokit / Zhu93 / Maltese & Mezger 等
#: 预设不在档案三个年龄模型内，此时**不写 A15**并记 warning —— 宁可不写，也不配错模型名。
_AGE_MODEL_NAME_HINTS: tuple[tuple[str, str], ...] = (
    ("stacey", "SK75"),
    ("kramers", "SK75"),
    ("cumming", "CR75"),
    ("richards", "CR75"),
    ("juteau", "AJ84"),
)
#: 只有 `ratio_host=A14` 的比值行描述分析自身，才可用于 A15 反演（A9.3 是标样实测值）。
_OWN_RATIO_HOST = "A14"
#: 系统推导的来源语义（= `ratios.SOURCE_CALCULATED`）与"填错组"提示键（后者对 locales 登记）。
_SYSTEM_SOURCE = ratios.SOURCE_CALCULATED
MSG_STRAY_GROUP_COLUMN = "'{value}' in '{column}' belongs to another group on sheet '{sheet}'"
#: 惰性导入的生成器缓存：``(DEFAULT_OUTPUT_DIR, build_workbook)``。
_generator: tuple[Path, Callable[[Profile, Path], Path]] | None = None


@dataclass(frozen=True)
class EntryIssue:
    """一条录入校验问题（`validate.ValidationIssue` 的 UI / 报表视图）。

    ``sheet`` / ``record_id`` / ``column`` 是定位（``column`` 形如 ``"A14 analysis_lia_ratio"``，
    辅助列即列名本身）；``message`` 是渲染好的英文原文（可直接写 Excel），``message_key`` +
    ``params`` 供 `core.translate()` 本地化；``severity`` 为 ``"error"`` 时阻断导入写盘。
    """
    severity: str
    sheet: str
    record_id: str
    column: str
    message: str
    message_key: str
    params: Mapping[str, object]
    value: object | None


@dataclass(frozen=True)
class EntryWorkbookReport:
    """一次录入工作簿操作的报告：读了多少、改了什么、有哪些问题、备份在哪。

    ``derived_ratios`` 是**实际写回**的派生比值条数（被 ERROR 阻断写盘时为 0）；``backup`` 是
    写盘前的备份路径；``issues`` 顺序为"逐表逐记录的字段/辅助列 → 条件联动 → 外键"。
    """

    workbook: Path
    profile_version: str
    sheets_read: int
    records_read: int
    derived_ratios: int
    issues: tuple[EntryIssue, ...]
    error_count: int
    warning_count: int
    backup: Path | None

    @property
    def ok(self) -> bool:
        """是否没有 ERROR（ERROR 会阻断导入写盘）。"""
        return self.error_count == 0


@dataclass(frozen=True)
class _Scan:
    """一次"读取 + 校验"的中间结果（只读校验与导入共用）；记录是副本，可安全就地补齐。"""

    target: Path
    profile: Profile
    layout: WorkbookLayout
    records_by_sheet: dict[str, list[dict[str, Any]]]
    issues: tuple[EntryIssue, ...]
    sheets_read: int
    records_read: int


@dataclass(frozen=True)
class _RatioColumns:
    """`17_LIA-Ratio` 表里参与推导的列（OID → 表头键名）；缺失的列记 ``None``。"""

    name: str
    value: str
    sigma: str | None
    absolute: str | None
    relative: str | None
    source: str | None


def generate_template(output: str | Path | None = None, *, force: bool = False) -> Path:
    """生成 TerraLID 录入工作簿模板（生成逻辑只在 `scripts/build_entry_workbook.py` 里）。

    Args:
        output: 输出 xlsx 路径；``None`` 时用生成器的缺省口径
            ``数据/entry_template_TerraLID_v<profile.version>.xlsx``。
        force: 目标已存在时是否覆盖；缺省 ``False``（用户的工作簿可能已填数据）。

    Returns:
        实际写入的工作簿路径。

    Raises:
        FileExistsError: ``force=False`` 且目标已存在。
        RuntimeError: 生成器不可用（``scripts/`` 不在导入路径，或缺 openpyxl）。
        FileNotFoundError / OSError: 档案根不可读，或目录不可写 / 落盘失败。
    """
    output_dir, build = _load_generator()
    profile = load_profile()
    target = (
        Path(output)
        if output is not None
        else output_dir / TEMPLATE_FILENAME.format(version=profile.version)
    )
    if target.exists() and not force:
        logger.warning("Entry template already exists, refusing to overwrite: %s", target)
        raise FileExistsError(
            f"录入模板已存在，未覆盖：{target}\n"
            "该文件可能已填写数据；确认可覆盖后请传 force=True，或换一个 output 路径。"
        )
    path = build(profile, target)
    logger.info("Generated entry template %s (profile=%s, force=%s)", path, profile.version, force)
    return path


def validate_entry_workbook(path: str | Path) -> EntryWorkbookReport:
    """只读校验录入工作簿（不写盘、不生成备份）：字段级 → 工作表辅助列 → 条件联动 + 主外键。

    Args:
        path: 录入工作簿路径。

    Returns:
        报告；``report.ok`` 即 ``error_count == 0``。

    Raises:
        FileNotFoundError: 工作簿不存在。
        ValueError: 工作簿不是可读的 xlsx。
    """
    scan = _scan_workbook(path)
    report = _build_report(scan)
    logger.info("Validated entry workbook %s: %d error(s), %d warning(s)",
                scan.target, report.error_count, report.warning_count)
    return report


def import_entry_workbook(
    path: str | Path, *, derive: bool = True, write_check: bool = True
) -> EntryWorkbookReport:
    """导入录入工作簿：校验 → 补齐派生比值与 A15 参数 → 写回（写前自动备份）。

    先按 :func:`validate_entry_workbook` 的口径校验；``derive=True`` 时按
    ``(owner_sheet, owner_id, ratio_host)`` 分组，用 `ratios.derive_all_ratios()` 补齐缺失的
    派生比值（``source="calculated"``）、把 B6.5 绝对 ↔ B6.6 相对不确定度互相换算，并给未填
    B6.7 来源的录入行补 ``original``（用户显式填了别的值则保留）；分析行的 A14 主比值齐全时用
    `calculate_all_parameters()` 反演 Tmod / μ / κ / ω 写入 A15.* 列（失败只记 warning）。
    ``write_check=True`` 时把问题回写 `99_CHECK`（`io_xlsx` 先备份，路径填进 ``backup``）。
    **只有 0 个 ERROR 时才把被改动的表写回**；有 ERROR 时只写报告并在日志里说明原因。

    Args:
        path: 录入工作簿路径。
        derive: 是否补齐派生比值与不确定度换算（``False`` 时工作簿不会被改写）。
        write_check: 是否把校验问题回写 `99_CHECK`。

    Returns:
        报告；``derived_ratios`` 是**实际写回**的派生比值条数。

    Raises:
        FileNotFoundError: 工作簿不存在。
        ValueError: 工作簿不可读，或缺 ``99_CHECK`` 表（``write_check=True``）。
    """
    scan = _scan_workbook(path)
    changed: set[str] = set()
    derived = _supplement_ratios(scan.layout, scan.records_by_sheet, changed) if derive else 0
    try:
        written, target = _apply_age_model(scan.layout, scan.records_by_sheet)
    except Exception as err:  # noqa: BLE001 — 地球化学引擎是可选能力，不能拖垮整次导入
        logger.warning("Age model parameters (A15) were not derived: %s", err)
        written, target = 0, None
    if written and target:
        changed.add(target)

    backup: Path | None = None
    if write_check:
        backup = _rewrite_check_report(scan)
    errors = sum(1 for issue in scan.issues if issue.severity == _SEVERITY_ERROR)
    if errors:
        logger.warning("Entry workbook %s has %d error(s); data rows untouched "
                       "(check report only, %d derived ratio(s) not written)",
                       scan.target, errors, derived)
        return _build_report(scan, derived_ratios=0, backup=backup)
    backup = _write_back(scan, changed, backup)
    report = _build_report(scan, derived_ratios=derived, backup=backup)
    logger.info("Imported %s: %d record(s), %d derived ratio(s), %d error(s), backup=%s",
                scan.target, scan.records_read, report.derived_ratios, report.error_count, backup)
    return report


def _scan_workbook(path: str | Path) -> _Scan:
    """读取录入工作簿并跑完全部校验（只读，不写盘）。"""
    target = Path(path)
    profile = load_profile()
    layout = build_layout(profile)
    read = io_xlsx.read_sheets(layout, target)  # sheets=None → 只读 entry_sheets（26 张）
    records_by_sheet = {
        name: [dict(record) for record in result.records] for name, result in read.items()
    }
    records_read = sum(result.row_count for result in read.values())
    issues = _collect_issues(layout, records_by_sheet)
    logger.info("Read entry workbook %s: profile=%s sheets=%d records=%d issues=%d",
                target, profile.version, len(read), records_read, len(issues))
    return _Scan(
        target=target, profile=profile, layout=layout, records_by_sheet=records_by_sheet,
        issues=issues, sheets_read=len(read), records_read=records_read,
    )


def _collect_issues(
    layout: WorkbookLayout, records_by_sheet: Mapping[str, Sequence[Mapping[str, Any]]]
) -> tuple[EntryIssue, ...]:
    """逐表逐记录跑字段级 + 辅助列校验（列按该行 ``group`` 筛），再统一跑条件联动与外键。

    条件联动的 ``material_tables`` 取"确实有记录"的模块键（空表不算提供，否则 ``O12 Material``
    的分派规则永远不触发）；填了别的组的列只记 WARNING（多半是填错行）。
    """
    collected: list[EntryIssue] = []
    sheeted: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for sheet_name, records in records_by_sheet.items():
        sheet = layout.sheet(sheet_name)
        if sheet is None:
            logger.warning("Sheet %s is not part of the layout; %d record(s) not validated",
                           sheet_name, len(records))
            continue
        table = sheet.table or sheet_name
        for record in records:
            record_id = _record_id(sheet, record)
            issues = validate.validate_columns(
                sheet.columns_for_record(record), record, sheet_name=sheet_name, table=table,
                record_id=record_id,
            )
            issues += validate_sheets.validate_sheet_helpers(
                sheet, record, record_id=record_id, layout=layout
            )
            collected.extend(_to_entry_issue(issue, sheet_name) for issue in issues)
            for column in sheet.stray_columns_for_record(record):
                value = record.get(column.header_key)
                params = {"value": _text(value), "column": column.header_key, "sheet": sheet_name}
                collected.append(EntryIssue(
                    severity=validate.Severity.WARNING.value, sheet=sheet_name,
                    record_id=record_id, column=column.header_key,
                    message=MSG_STRAY_GROUP_COLUMN.format(**params),
                    message_key=MSG_STRAY_GROUP_COLUMN, params=params, value=value,
                ))
        if sheet.table:
            sheeted.setdefault((sheet.table, sheet_name), []).extend(records)

    present = frozenset(key for (key, _name), rows in sheeted.items() if rows)
    records_by_table: dict[str, list[Mapping[str, Any]]] = {}
    for (table_key, sheet_name), records in sheeted.items():
        for record in records:
            for issue in validate.validate_conditionals(table_key, record, material_tables=present):
                collected.append(_to_entry_issue(issue, sheet_name))
        records_by_table.setdefault(table_key, []).extend(records)
    for table_key in records_by_table:
        parent = layout.sheet_for_table(table_key)
        fallback = parent.name if parent is not None else table_key
        for issue in validate.validate_references(table_key, records_by_table):
            collected.append(_to_entry_issue(issue, fallback))
    return tuple(collected)


def _build_report(
    scan: _Scan, *, derived_ratios: int = 0, backup: Path | None = None
) -> EntryWorkbookReport:
    """把中间结果组装成 DTO。"""
    errors = sum(1 for issue in scan.issues if issue.severity == _SEVERITY_ERROR)
    return EntryWorkbookReport(
        workbook=scan.target, profile_version=scan.profile.version,
        sheets_read=scan.sheets_read, records_read=scan.records_read,
        derived_ratios=derived_ratios, issues=scan.issues, error_count=errors,
        warning_count=len(scan.issues) - errors, backup=backup,
    )


def _to_entry_issue(issue: validate.ValidationIssue, fallback_sheet: str) -> EntryIssue:
    """`ValidationIssue` → DTO；列定位给 ``"<OID> <键名>"``（辅助列两者同值只给一次）。"""
    params = dict(issue.params)
    oid, key = _text(issue.field_oid), _text(issue.field_key)
    return EntryIssue(
        severity=issue.severity.value,
        sheet=_text(params.get("sheet")) or fallback_sheet or issue.table,
        record_id=issue.record_id,
        column=f"{oid} {key}" if oid and key and oid != key else (oid or key),
        message=validate.format_message(issue),
        message_key=issue.message_key,
        params=params,
        value=issue.value,
    )


def _record_id(sheet: SheetSpec, record: Mapping[str, Any]) -> str:
    """记录标识：``row_id`` → 主表主键列（``sheet.columns[0]``）→ ``row{Excel 行号}``。"""
    row_id = _text(record.get(ROWS_ID_COLUMN))
    if row_id:
        return row_id
    if sheet.columns:  # 取值口径同 `validate`：ID 键名 → 键名 → ID
        primary = sheet.columns[0]
        for key in (primary.header_key, primary.key, primary.oid):
            text = _text(record.get(key))
            if text:
                return text
    row_number = record.get(_ROW_NUMBER_KEY)
    return f"row{row_number}" if row_number is not None else "row?"


def _supplement_ratios(
    layout: WorkbookLayout, records_by_sheet: dict[str, list[dict[str, Any]]], changed: set[str]
) -> int:
    """补齐比值表的派生比值与不确定度换算；返回新增的派生比值行数。"""
    derived = 0
    for sheet in layout.sheets:
        if sheet.block is not spec.Block.LIA_RATIO or not sheet.is_entry:
            continue
        rows = records_by_sheet.get(sheet.name)
        if not rows:
            logger.debug("Ratio sheet %s has no data row; nothing to supplement", sheet.name)
            continue
        columns = _ratio_columns(sheet)
        if columns is None:
            logger.warning("Ratio sheet %s lacks the %s / %s columns; derivation skipped",
                           sheet.name, _RATIO_NAME_OID, _RATIO_VALUE_OID)
            continue
        groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
        for row in rows:  # 一个 (owner_sheet, owner_id, ratio_host) 就是一组比值
            key = (_text(row.get(OWNER_SHEET_COLUMN)), _text(row.get(OWNER_ID_COLUMN)),
                   _text(row.get(RATIO_HOST_COLUMN)))
            groups.setdefault(key, []).append(row)
        for group_key, group in groups.items():
            converted = _convert_uncertainties(group, columns)
            marked = _mark_reported_source(group, columns)
            new_rows = _derive_missing(group, columns)
            if new_rows:
                rows.extend(new_rows)
                derived += len(new_rows)
            if converted or marked or new_rows:
                changed.add(sheet.name)
                logger.info(
                    "Sheet %s group %s: %d uncertainty conversion(s), %d source mark(s), "
                    "%d derived ratio(s)", sheet.name,
                    "/".join(part or "?" for part in group_key), converted, marked, len(new_rows),
                )
    if not derived:
        logger.info("No derived lead isotope ratio was needed in this workbook")
    return derived


def _ratio_columns(sheet: SheetSpec) -> _RatioColumns | None:
    """按 OID 解析比值表的列名；缺 B6.1 / B6.2 时返回 ``None``（``None`` 键列可安全当哨兵）。"""
    name, value = sheet.column(_RATIO_NAME_OID), sheet.column(_RATIO_VALUE_OID)
    if name is None or value is None:
        return None
    found = {oid: sheet.column(oid) for oid in (
        _RATIO_SIGMA_OID, _RATIO_ABSOLUTE_OID, _RATIO_RELATIVE_OID, _RATIO_SOURCE_OID)}
    return _RatioColumns(
        name=name.header_key, value=value.header_key,
        **{field: found[oid].header_key if found[oid] else None for field, oid in (
            ("sigma", _RATIO_SIGMA_OID), ("absolute", _RATIO_ABSOLUTE_OID),
            ("relative", _RATIO_RELATIVE_OID), ("source", _RATIO_SOURCE_OID))},
    )


def _convert_uncertainties(group: Sequence[dict[str, Any]], columns: _RatioColumns) -> int:
    """B6.5 绝对 ↔ B6.6 相对不确定度互相换算（就地），返回换算条数。

    负值不换算（不确定度为负是录入错误，交给校验层报告）；比值为 0 时无法构成相对量。
    """
    converted = 0
    for row in group:
        value = _as_float(row.get(columns.value))
        if value is None or value == 0:
            continue
        absolute = _as_float(row.get(columns.absolute))
        relative = _as_float(row.get(columns.relative))
        if absolute is None and relative is not None and relative >= 0 and columns.absolute:
            row[columns.absolute] = ratios.absolute_from_relative(value, relative)
            converted += 1
        elif relative is None and absolute is not None and absolute >= 0 and columns.relative:
            computed = ratios.relative_from_absolute(value, absolute)
            if computed is not None:
                row[columns.relative] = computed
                converted += 1
    return converted


def _mark_reported_source(group: Sequence[dict[str, Any]], columns: _RatioColumns) -> int:
    """给填了比值却没填来源的行补 ``B6.7 = original``（该列由系统提供，只补空白、不覆盖用户值）。

    档案：B6.7 说明比值是原文报告的、还是系统算出来的；派生行写 ``calculated``。
    """
    if columns.source is None:
        return 0
    marked = 0
    for row in group:
        if _text(row.get(columns.source)) or not _text(row.get(columns.name)):
            continue
        if _as_float(row.get(columns.value)) is None:
            continue
        row[columns.source] = ratios.SOURCE_ORIGINAL
        marked += 1
    return marked


def _derive_missing(group: Sequence[dict[str, Any]], columns: _RatioColumns) -> list[dict[str, Any]]:
    """用组内已有的实测比值推导缺失的比值行；已有同名行不覆盖，B6.3 不猜测。"""
    measured: dict[str, float] = {}
    uncertainties: dict[str, float] = {}
    reported: set[str] = set()
    levels: list[int] = []
    for row in group:
        name = _text(row.get(columns.name))
        if not name:
            continue
        reported.add(name)
        value = _as_float(row.get(columns.value))
        if value is not None:
            measured[name] = value
        absolute = _as_float(row.get(columns.absolute))
        if absolute is not None and absolute >= 0:
            uncertainties[name] = absolute
        level = _as_int(row.get(columns.sigma))
        if level is not None and level not in levels:
            levels.append(level)
    if not reported:
        return []
    if len(levels) > 1:
        logger.warning("Ratio group has conflicting sigma levels %s; using %d for derived rows",
                       levels, levels[0])
    sigma = levels[0] if levels else None
    computed = ratios.derive_all_ratios(measured, uncertainties=uncertainties, sigma=sigma)
    template = group[0]
    new_rows: list[dict[str, Any]] = []
    for name in spec.LIA_RATIO_NAMES:
        ratio_value = computed.get(name)
        if ratio_value is None or name in reported:
            continue
        row: dict[str, Any] = {
            OWNER_SHEET_COLUMN: template.get(OWNER_SHEET_COLUMN),
            OWNER_ID_COLUMN: template.get(OWNER_ID_COLUMN),
            RATIO_HOST_COLUMN: template.get(RATIO_HOST_COLUMN),
            columns.name: name, columns.value: ratio_value.value,
        }
        for key, value in (
            (columns.sigma, sigma),
            (columns.absolute, ratio_value.uncertainty_absolute),
            (columns.relative, ratio_value.uncertainty_relative_percent),
            (columns.source, ratios.SOURCE_CALCULATED),
        ):
            if key is not None:
                row[key] = value
        new_rows.append(row)
    return new_rows


def _apply_age_model(
    layout: WorkbookLayout, records_by_sheet: Mapping[str, Sequence[Mapping[str, Any]]]
) -> tuple[int, str | None]:
    """A15 反演主流程；返回 ``(写入参数的分析记录数, 承载 A15 的表名)``（失败由调用方收口）。"""
    analysis = layout.sheet_for_table(spec.TableKey.ANALYSIS)
    target = next((sheet for sheet in layout.sheets
                   if sheet.is_entry and sheet.table == spec.TableKey.ANALYSIS.value
                   and sheet.column(_A15_MARKER_OID) is not None), None)
    if analysis is None or target is None:
        logger.warning("Layout has no analyses sheet or no A15 column; A15 not derived")
        return 0, None

    by_owner: dict[str, dict[str, float]] = {}
    for sheet in layout.sheets:
        columns = _ratio_columns(sheet) if sheet.block is spec.Block.LIA_RATIO else None
        for row in records_by_sheet.get(sheet.name, ()) if columns else ():
            if _text(row.get(OWNER_SHEET_COLUMN)) != analysis.name:
                continue
            if _text(row.get(RATIO_HOST_COLUMN)) != _OWN_RATIO_HOST:
                continue
            owner, name = _text(row.get(OWNER_ID_COLUMN)), _text(row.get(columns.name))
            value = _as_float(row.get(columns.value))
            if owner and name and value is not None:
                by_owner.setdefault(owner, {})[name] = value
    if not by_owner:
        logger.debug("No %s ratio row refers to sheet %s; A15 not derived",
                     _OWN_RATIO_HOST, analysis.name)
        return 0, None
    known = {_record_id(analysis, record) for record in records_by_sheet.get(analysis.name, ())}
    orphans = sorted(set(by_owner) - known)
    if orphans:
        logger.warning("A14 ratio rows reference analysis id(s) %s which no row on sheet %s "
                       "carries (fill that sheet's ID column to link them); skipped",
                       orphans[:5], analysis.name)

    from data.geochemistry import calculate_all_parameters, engine  # 大型依赖：函数内延迟导入

    current = getattr(engine, "current_model_name", "")
    model_name = _resolve_age_model_name(current)
    if model_name is None:
        logger.warning("Current geochemistry model %r matches none of %s; A15 not derived",
                       current, spec.AGE_MODEL_NAMES)
        return 0, None

    written = 0
    for record in records_by_sheet.get(analysis.name, ()):
        record_id = _record_id(analysis, record)
        measured = by_owner.get(record_id)
        if not measured or any(name not in measured for name in spec.PRIMARY_LIA_RATIO_NAMES):
            continue
        pb206, pb207, pb208 = (measured[name] for name in spec.PRIMARY_LIA_RATIO_NAMES)
        try:
            results = calculate_all_parameters(pb206, pb207, pb208)
        except Exception as err:  # noqa: BLE001 — 单条记录的求解失败不该中断整次导入
            logger.warning("calculate_all_parameters() failed for analysis %s on sheet %s: %s",
                           record_id, analysis.name, err)
            continue
        values: dict[str, object] = {_A15_MODEL_NAME_OID: model_name}
        values.update({oid: number for oid, key in _A15_VALUE_KEYS
                       if (number := _as_float(results.get(key))) is not None})
        if len(values) == 1:  # 只有模型名、没有任何参数 -> 不写
            continue
        if not _store_age_model(target, layout, records_by_sheet, record_id, values):
            continue
        written += 1
        logger.info("A15 derived for analysis %s on sheet %s: model=%s source=%s values=%s",
                    record_id, target.name, model_name, _SYSTEM_SOURCE,
                    {oid: round(n, 5) for oid, n in sorted(values.items())
                     if oid != _A15_MODEL_NAME_OID})
    return written, target.name


def _store_age_model(
    sheet: SheetSpec,
    layout: WorkbookLayout,
    records_by_sheet: dict[str, list[dict[str, Any]]],
    record_id: str,
    values: Mapping[str, object],
) -> bool:
    """把 A15 取值写进目标行（主表写该行；明细行表定位/新建 ``group=A15`` 行）。

    **写入自检**：新行或新值都先过一次本工具的校验，会引入 ERROR 就不写（新行整行不建、
    已存在行回滚）。把工作簿写脏（下次校验冒出新 ERROR）比不写更糟。
    """
    rows = records_by_sheet.get(sheet.name)
    if rows is None:
        logger.warning("Sheet %s is absent; A15 for %s was not written", sheet.name, record_id)
        return False
    available = {oid: c.header_key for oid in values if (c := sheet.column(oid)) is not None}
    if not available:
        logger.debug("Sheet %s lacks the A15 columns %s; skipped", sheet.name, sorted(values))
        return False

    if sheet.kind is SheetKind.GROUP:
        row = next((item for item in rows
                    if _text(item.get(GROUP_COLUMN)) == _A15_GROUP
                    and _text(item.get(validate_sheets.PARENT_ID_COLUMN)) == record_id), None)
        if row is None:
            used = {_text(item.get(ROWS_ID_COLUMN)) for item in rows}
            base, index = f"{record_id}-{_A15_GROUP}", 1
            while (row_id := base if index == 1 else f"{base}-{index}") in used:
                index += 1
            candidate = {ROWS_ID_COLUMN: row_id, validate_sheets.PARENT_ID_COLUMN: record_id,
                         GROUP_COLUMN: _A15_GROUP}
            blocking = _row_errors(sheet, layout, candidate, record_id)
            if blocking:
                logger.warning(
                    "Not creating a %s row (group=%s, parent_id=%s): it would introduce "
                    "%d error(s): %s", sheet.name, _A15_GROUP, record_id, len(blocking),
                    "; ".join(validate.format_message(i) for i in blocking[:3]),
                )
                return False
            rows.append(candidate)
            row = candidate
            logger.info("Created a %s row (group=%s, parent_id=%s) for A15",
                        sheet.name, _A15_GROUP, record_id)
    else:
        row = next((item for item in rows if _record_id(sheet, item) == record_id), None)
        if row is None:
            logger.warning("No row on sheet %s carries id %r; A15 was not written",
                           sheet.name, record_id)
            return False

    before = len(_row_errors(sheet, layout, row, record_id))
    for oid, key in available.items():
        row[key] = values[oid]
    blocking = _row_errors(sheet, layout, row, record_id)
    if len(blocking) > before:
        for key in available.values():
            row.pop(key, None)
        logger.warning("Rolled back A15 on sheet %s for %s: %d new error(s): %s",
                       sheet.name, record_id, len(blocking) - before,
                       "; ".join(validate.format_message(i) for i in blocking[:3]))
        return False
    return True


def _row_errors(
    sheet: SheetSpec, layout: WorkbookLayout, row: Mapping[str, Any], record_id: str
) -> list[validate.ValidationIssue]:
    """对一行跑"字段 + 辅助列"校验，只返回 ERROR（写入前的自检；列按该行 ``group`` 筛）。"""
    issues = validate.validate_columns(
        sheet.columns_for_record(row), row, sheet_name=sheet.name,
        table=sheet.table or sheet.name, record_id=record_id,
    ) + validate_sheets.validate_sheet_helpers(
        sheet, row, record_id=record_id, layout=layout
    )
    return [issue for issue in issues if issue.severity is validate.Severity.ERROR]


def _resolve_age_model_name(model_name: object) -> str | None:
    """引擎的模型名 → 档案 A15.1 允许值；无法映射时返回 ``None``（不猜）。"""
    text = _text(model_name).lower()
    if not text:
        return None
    if text.upper() in spec.AGE_MODEL_NAMES:
        return text.upper()
    for hint, short_name in _AGE_MODEL_NAME_HINTS:
        if hint in text:
            return short_name
    return None


def _rewrite_check_report(scan: _Scan) -> Path | None:
    """把问题回写 `99_CHECK`（`io_xlsx` 覆盖前自动备份），返回备份路径。"""
    keys = io_xlsx.CHECK_HEADERS
    rows = [dict(zip(keys, (issue.severity, issue.sheet, issue.record_id, issue.column,
                            issue.message, issue.value))) for issue in scan.issues]
    try:
        _, backup = io_xlsx.write_check_report(scan.layout, scan.target, rows)
    except (OSError, ValueError) as err:
        logger.error("Failed to write the check report into %s: %s", scan.target, err)
        raise
    logger.info("Wrote %d validation issue(s) into %s (backup=%s)", len(rows), scan.target, backup)
    return backup


def _write_back(scan: _Scan, changed: set[str], backup: Path | None) -> Path | None:
    """把被补齐的表写回工作簿；没有改动时不碰文件，返回备份路径（优先已有那份）。

    日期列还原成 ``date`` 再写（否则日期单元格变成文本）；``__row__`` 是内部行号键，剔除。
    """
    payload: dict[str, list[dict[str, Any]]] = {}
    for name in sorted(changed):
        rows = scan.records_by_sheet.get(name) or []
        sheet = scan.layout.sheet(name)
        if sheet is None or not rows:
            logger.warning("Sheet %s has nothing to write back; skipped", name)
            continue
        date_keys = [c.header_key for c in sheet.columns
                     if c.value_kind is spec.ValueKind.DATE]
        prepared: list[dict[str, Any]] = []
        for record in rows:
            row = {key: value for key, value in record.items() if key != _ROW_NUMBER_KEY}
            for key in date_keys:
                text = row.get(key)
                if isinstance(text, str):
                    row[key] = _iso_date(text) or text
            prepared.append(row)
        payload[name] = prepared

    if not payload:
        logger.info("Entry workbook %s: no supplemented record to write back", scan.target)
        return backup
    _, data_backup = io_xlsx.write_records(scan.layout, scan.target, payload)
    logger.info("Wrote %d sheet(s) back to %s: %s (backup=%s)",
                len(payload), scan.target, ", ".join(sorted(payload)), data_backup)
    return backup or data_backup


def _iso_date(text: str) -> date | None:
    """``YYYY-MM-DD`` → `date`；不是 ISO 日期时返回 ``None``（校验层已报过格式问题）。"""
    try:
        return date.fromisoformat(text)
    except ValueError as err:
        logger.debug("Keeping %r as text: not an ISO date (%s)", text, err)
        return None


def _load_generator() -> tuple[Path, Callable[[Profile, Path], Path]]:
    """延迟导入生成器（`scripts/` 不在包内，独立运行时可能不可导入）；不可用抛 RuntimeError。"""
    global _generator
    if _generator is not None:
        return _generator
    try:
        from scripts.build_entry_workbook import DEFAULT_OUTPUT_DIR, build_workbook
    except ImportError as err:
        logger.error("Entry workbook generator is unavailable: %s", err)
        raise RuntimeError(
            "无法生成录入模板：scripts/build_entry_workbook.py 不可用"
            f"（scripts 不在导入路径，或缺少 openpyxl）：{err}"
        ) from err
    _generator = (Path(DEFAULT_OUTPUT_DIR), build_workbook)
    return _generator


def _text(value: object) -> str:
    """渲染为去空白字符串（``None`` → 空串）。"""
    return "" if value is None else str(value).strip()


def _as_float(value: object) -> float | None:
    """安全转成有限浮点数（禁止裸 ``float()``，规范 §8.1）；失败只记 debug。"""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)  # type: ignore[arg-type]  # 输入类型不可信，故包裹转换
    except (TypeError, ValueError) as err:
        logger.debug("Ignoring non-numeric value %r: %s", value, err)
        return None
    if not math.isfinite(number):
        logger.debug("Ignoring non-finite value %r", value)
        return None
    return number


def _as_int(value: object) -> int | None:
    """安全转成整数（禁止裸 ``int()``，规范 §8.1）；失败只记 debug。"""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    try:
        return int(value)  # type: ignore[arg-type]  # 输入类型不可信，故包裹转换
    except (TypeError, ValueError) as err:
        logger.debug("Ignoring non-integer value %r: %s", value, err)
        return None


__all__ = [
    "EntryIssue", "EntryWorkbookReport", "TEMPLATE_FILENAME",
    "generate_template", "import_entry_workbook", "validate_entry_workbook",
]
