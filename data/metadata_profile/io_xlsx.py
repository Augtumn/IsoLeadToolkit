"""录入工作簿的读写。

与 `layout.py` 配套：`layout` 决定表与列，本模块负责把工作簿读成记录、把结果写回。
生成模板是 `scripts/build_entry_workbook.py` 的职责，本模块只做**读写与安全落盘**。

两条安全约定（用户的工作簿可能已填了大量数据）：

1. **覆盖前必先备份**。`write_check_report` / `write_records` 在目标已存在时先复制一份
   ``<name>.bak-<YYYYMMDD-HHMMSS>.xlsx``，再以"临时文件 + 原子替换"落盘；中途失败不会
   留下半截文件。
2. **只写自己知道的列**。读取时忽略布局之外的多余列（用户可能自己加了备注列），
   写入时也只写布局内的表与列。

已知限制：`openpyxl` 往返会保留单元格值、数值格式、数据验证与条件格式，但会丢弃
图表与图片。本工作簿不使用图表/图片，故可安全往返。
"""
from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from .layout import SHEET_CHECK, SheetSpec, WorkbookLayout

logger = logging.getLogger(__name__)

#: 表头占用行数：第 1 行机器键名，第 2 行人读标签，数据从第 3 行开始。
HEADER_ROWS = 2

#: 数据起始行（1 起）。
FIRST_DATA_ROW = HEADER_ROWS + 1

#: `99_CHECK` 的列（与生成器约定一致，表头在第 1 行）。
CHECK_HEADERS: tuple[str, ...] = (
    "severity",
    "sheet",
    "record_id",
    "column",
    "message",
    "value",
)

#: `99_CHECK` 的数据起始行（表头占第 1 行）。
CHECK_FIRST_DATA_ROW = 2

#: 备份文件的时间戳格式。
BACKUP_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"


@dataclass(frozen=True)
class SheetReadResult:
    """一张工作表的读取结果。"""

    #: 工作表名。
    sheet: str
    #: 该表承载的模块键（块表为 ``None``）。
    table: str | None
    #: 逐行记录，键为表头第 1 行的机器键名。
    records: tuple[dict[str, Any], ...]

    @property
    def row_count(self) -> int:
        """记录数。"""
        return len(self.records)


def _cell_to_value(value: Any) -> Any:
    """把 openpyxl 单元格值归一为可校验的形式。

    Args:
        value: 单元格原始值。

    Returns:
        ``date`` / ``datetime`` 转成 ``YYYY-MM-DD`` 字符串（档案要求该格式）；
        字符串两端空白被去除（``""`` 归一为 ``None``）；其余原样返回。
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _header_map(worksheet: Worksheet, sheet_spec: SheetSpec) -> dict[int, str]:
    """建立"列号 → 机器键名"的映射。

    以**布局**为准（而不是表头文本），这样用户即便改动了第 2 行的人读标签也不影响读取；
    仅当第 1 行文本与布局不一致时记 warning，便于发现表结构被改动。

    Args:
        worksheet: 已打开的工作表。
        sheet_spec: 该表的布局定义。

    Returns:
        列号（1 起）到机器键名的映射；不在布局中的列被忽略。
    """
    expected = list(sheet_spec.all_header_keys)
    mapping: dict[int, str] = {}
    for index, key in enumerate(expected, start=1):
        actual = worksheet.cell(row=1, column=index).value
        actual_text = str(actual).strip() if actual is not None else ""
        if actual_text and actual_text != key:
            logger.warning(
                "Sheet %s column %d header mismatch: expected %r, found %r "
                "(layout is authoritative; 表头可能被改动)",
                sheet_spec.name,
                index,
                key,
                actual_text,
            )
        mapping[index] = key
    return mapping


def _row_has_data(row: Sequence[Any]) -> bool:
    """判断一行是否有任何非空值（用于跳过空行）。"""
    return any(_cell_to_value(value) is not None for value in row)


def read_sheet(worksheet: Worksheet, sheet_spec: SheetSpec) -> SheetReadResult:
    """读取一张工作表。

    Args:
        worksheet: 已打开的工作表。
        sheet_spec: 该表的布局定义。

    Returns:
        含逐行记录的读取结果。完全空白的行被跳过；布局之外的列被忽略。
    """
    columns = _header_map(worksheet, sheet_spec)
    records: list[dict[str, Any]] = []
    max_column = max(columns) if columns else 0

    for row_index in range(FIRST_DATA_ROW, worksheet.max_row + 1):
        raw = [
            worksheet.cell(row=row_index, column=col).value
            for col in range(1, max_column + 1)
        ]
        if not _row_has_data(raw):
            continue
        record: dict[str, Any] = {}
        for col, key in columns.items():
            record[key] = _cell_to_value(raw[col - 1])
        record["__row__"] = row_index
        records.append(record)

    logger.info(
        "Read sheet %s: %d records (table=%s)",
        sheet_spec.name,
        len(records),
        sheet_spec.table,
    )
    return SheetReadResult(
        sheet=sheet_spec.name,
        table=sheet_spec.table,
        records=tuple(records),
    )


def read_sheets(
    layout: WorkbookLayout,
    path: str | Path,
    *,
    sheets: Iterable[str] | None = None,
) -> dict[str, SheetReadResult]:
    """读取录入工作簿中的若干张表。

    Args:
        layout: 工作簿布局。
        path: 工作簿路径。
        sheets: 只读这些表；``None`` 表示全部需要填写的表。

    Returns:
        表名 → 读取结果。目标表不存在时跳过并记 warning（用户可能删了不用的表）。

    Raises:
        FileNotFoundError: 工作簿不存在。
        ValueError: 文件不是可读的 xlsx。
    """
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Workbook not found: {target}")

    wanted = (
        list(sheets)
        if sheets is not None
        else [spec.name for spec in layout.entry_sheets]
    )

    try:
        workbook = load_workbook(target, data_only=True, read_only=False)
    except Exception as err:
        logger.error("Failed to open workbook %s: %s", target, err)
        raise ValueError(f"Not a readable xlsx workbook: {target}") from err

    results: dict[str, SheetReadResult] = {}
    try:
        for name in wanted:
            sheet_spec = layout.sheet(name)
            if sheet_spec is None:
                logger.warning("Sheet %s is not part of the layout; skipped", name)
                continue
            if name not in workbook.sheetnames:
                logger.warning("Sheet %s missing from workbook %s", name, target)
                continue
            results[name] = read_sheet(workbook[name], sheet_spec)
    finally:
        workbook.close()

    return results


def backup_file(path: str | Path, *, timestamp: str | None = None) -> Path | None:
    """为待覆盖的文件建一份带时间戳的备份。

    Args:
        path: 待备份文件。
        timestamp: 时间戳文本（缺省取当前时间），便于测试注入。

    Returns:
        备份文件路径；源文件不存在时返回 ``None``。
    """
    source = Path(path)
    if not source.exists():
        return None
    stamp = timestamp or datetime.now().strftime(BACKUP_TIMESTAMP_FORMAT)
    backup = source.with_name(f"{source.stem}.bak-{stamp}{source.suffix}")
    shutil.copy2(source, backup)
    logger.info("Backed up %s -> %s", source, backup)
    return backup


def _save_atomically(workbook: Any, path: Path) -> Path:
    """以"临时文件 + 原子替换"写入，避免中途失败留下半截文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        workbook.save(temporary)
        temporary.replace(path)
    finally:
        if temporary.exists():
            try:
                temporary.unlink()
            except OSError as err:
                logger.warning("Could not remove temporary file %s: %s", temporary, err)
    return path


def write_check_report(
    layout: WorkbookLayout,
    path: str | Path,
    issues: Sequence[Mapping[str, Any]],
) -> tuple[Path, Path | None]:
    """把校验问题写回工作簿的 ``99_CHECK`` 表。

    覆盖前会先备份原文件（用户可能已填数据）。问题行按
    ``CHECK_HEADERS`` 顺序写入：severity / sheet / record_id / column / message / value。

    Args:
        layout: 工作簿布局（用于确认存在 ``99_CHECK``）。
        path: 工作簿路径。
        issues: 问题序列，每项含 ``CHECK_HEADERS`` 中的键。

    Returns:
        ``(工作簿路径, 备份路径或 None)``。

    Raises:
        FileNotFoundError: 工作簿不存在（请先用生成器创建模板）。
        ValueError: 工作簿不可读或缺少 ``99_CHECK`` 表。
    """
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Workbook not found: {target}")
    if layout.sheet(SHEET_CHECK) is None:
        raise ValueError("Layout has no check sheet to write into")

    try:
        workbook = load_workbook(target, data_only=False)
    except Exception as err:
        logger.error("Failed to open workbook %s for report: %s", target, err)
        raise ValueError(f"Not a readable xlsx workbook: {target}") from err

    backup: Path | None = None
    try:
        if SHEET_CHECK not in workbook.sheetnames:
            raise ValueError(f"Workbook missing sheet {SHEET_CHECK}")
        worksheet = workbook[SHEET_CHECK]

        # 表头在第 1 行；清空旧报告行（若有）后重写，保证幂等。
        if worksheet.max_row >= CHECK_FIRST_DATA_ROW:
            worksheet.delete_rows(CHECK_FIRST_DATA_ROW, worksheet.max_row)

        for offset, issue in enumerate(issues, start=CHECK_FIRST_DATA_ROW):
            for column, header in enumerate(CHECK_HEADERS, start=1):
                value = issue.get(header)
                worksheet.cell(row=offset, column=column, value=value)

        backup = backup_file(target)
        _save_atomically(workbook, target)
    finally:
        workbook.close()

    logger.info("Wrote %d validation issues to %s", len(issues), target)
    return target, backup


def write_records(
    layout: WorkbookLayout,
    path: str | Path,
    records_by_sheet: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    include_system_sheets: bool = False,
) -> tuple[Path, Path | None]:
    """把规范化后的记录写回工作簿（导入器落库用）。

    只覆盖 ``records_by_sheet`` 里出现的表：先清空其数据行再写入，其它表保持原样。
    写入值按列定义取记录里对应机器键名的项。

    Args:
        layout: 工作簿布局。
        path: 工作簿路径。
        records_by_sheet: 表名 → 记录序列（键为机器键名）。
        include_system_sheets: 是否允许写入 ``99_CHECK`` 等非录入表（默认禁止，
            以免把手填数据写进生成物）。

    Returns:
        ``(工作簿路径, 备份路径或 None)``。

    Raises:
        FileNotFoundError: 工作簿不存在。
        ValueError: 工作簿不可读，或指定了布局里不存在的表。
    """
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Workbook not found: {target}")

    try:
        workbook = load_workbook(target, data_only=False)
    except Exception as err:
        logger.error("Failed to open workbook %s for write: %s", target, err)
        raise ValueError(f"Not a readable xlsx workbook: {target}") from err

    backup: Path | None = None
    try:
        for sheet_name, records in records_by_sheet.items():
            sheet_spec = layout.sheet(sheet_name)
            if sheet_spec is None:
                raise ValueError(f"Sheet {sheet_name} is not part of the layout")
            if not sheet_spec.is_entry and not include_system_sheets:
                raise ValueError(
                    f"Sheet {sheet_name} is generated content; refusing to write records"
                )
            if sheet_name not in workbook.sheetnames:
                raise ValueError(f"Workbook missing sheet {sheet_name}")

            worksheet = workbook[sheet_name]
            keys = list(sheet_spec.all_header_keys)

            if worksheet.max_row >= FIRST_DATA_ROW:
                worksheet.delete_rows(FIRST_DATA_ROW, worksheet.max_row)

            for offset, record in enumerate(records, start=FIRST_DATA_ROW):
                for column, key in enumerate(keys, start=1):
                    worksheet.cell(row=offset, column=column, value=record.get(key))

        backup = backup_file(target)
        _save_atomically(workbook, target)
    finally:
        workbook.close()

    total = sum(len(rows) for rows in records_by_sheet.values())
    logger.info("Wrote %d records into %s", total, target)
    return target, backup


__all__ = [
    "BACKUP_TIMESTAMP_FORMAT",
    "CHECK_FIRST_DATA_ROW",
    "CHECK_HEADERS",
    "FIRST_DATA_ROW",
    "HEADER_ROWS",
    "SheetReadResult",
    "backup_file",
    "read_sheet",
    "read_sheets",
    "write_check_report",
    "write_records",
]
