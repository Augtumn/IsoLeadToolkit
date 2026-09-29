"""元数据校验规则：必填 / 词表 / 值域 / 格式 / 条件联动 / 外键完整性。

`validate_columns()` 是**唯一的规则实现层**：按一组显式字段校验一条记录，工作簿里的
"实体表"（模块字段）与"可复用块表"（B1–B6 字段）都走它；`validate_record()` 只是
"取出某模块字段再委托"的薄包装。`validate_conditionals()` 管档案显式写出的字段联动，
`validate_references()` 管主外键完整性，`validate_workbook()` 把三者串成一次工作簿校验，
`summarize()` 给出报告页眉计数。

规则只报告、不改数据：返回 :class:`ValidationIssue` 列表，`message_key` 是稳定英文原文
（含 ``{}`` 占位符，供 `core.translate()` 渲染；中英对照登记在 `locales/*.json`）。

档案依据（`reference/metadata`）：B3.2 / B3.3.4 / B3.5 / B3.6、B6.1 / B6.4 / B6.7、
SI1 / SI2、SI5.*、O12、A12 / A14。"必填"只针对 **mandatory 且由 data provider 提供**的字段
（系统提供的 B6.7 / A15.* 留空不算错，否则用户永远无法通过校验）。

设计约束：不得导入 PyQt5 / pandas / openpyxl，不做文件 IO，无全局可变状态。
"""
from __future__ import annotations

import datetime
import logging
import math
import re
from dataclasses import dataclass, field, replace
from enum import Enum
from types import MappingProxyType, ModuleType
from typing import TYPE_CHECKING, Collection, Mapping, Sequence
from urllib.parse import urlparse

from .layout import material_table_for
from .spec import (
    LIA_RATIO_NAMES,
    PARENT_FK_COLUMN,
    RATIO_SOURCES,
    SIGMA_LEVELS,
    FieldSpec,
    Profile,
    TableKey,
    TableSpec,
    ValueKind,
)

if TYPE_CHECKING:  # 仅用于类型标注：运行期不硬依赖布局模块
    from .layout import ColumnSpec

logger = logging.getLogger(__name__)

# 消息键：稳定英文原文，含 {} 占位符；locales/zh.json 与 locales/en.json 登记同一套键。
MSG_REQUIRED = "Required field '{field}' ({oid}) is empty"
MSG_VOCAB_UNKNOWN = "'{value}' is not an allowed value for '{field}' ({oid})"
MSG_VOCAB_UNKNOWN_OPEN = (
    "'{value}' is not a known value for '{field}' ({oid}); "
    "the controlled vocabulary may be incomplete"
)
MSG_NOT_NUMERIC = "'{value}' is not a valid {kind} for '{field}' ({oid})"
MSG_NOT_INTEGER = "'{value}' is not a whole number for '{field}' ({oid})"
MSG_INVALID_DATE = "'{value}' is not a date in YYYY-MM-DD format for '{field}' ({oid})"
MSG_INVALID_SIGMA = (
    "'{value}' is not a valid confidence level for '{field}' ({oid}); allowed values are 1, 2, 3"
)
MSG_INVALID_RATIO_NAME = "'{value}' is not a known lead isotope ratio for '{field}' ({oid})"
MSG_INVALID_RATIO_SOURCE = (
    "'{value}' is not a valid lead isotope ratio source for '{field}' ({oid}); "
    "allowed values are original, calculated"
)
MSG_OUT_OF_RANGE = (
    "'{value}' is outside the allowed range {minimum} to {maximum} for '{field}' ({oid})"
)
MSG_INVALID_URL = "'{value}' is not a valid http(s) URL for '{field}' ({oid})"
MSG_SUSPECT_EMAIL = "'{value}' does not look like a valid email address for '{field}' ({oid})"
MSG_SUSPECT_PID = "'{value}' does not look like a valid persistent identifier for '{field}' ({oid})"
MSG_DATE_KIND_CONFLICT = (
    "'{field}' is only available when Date type is '{expected_type}'; this record has '{date_type}'"
)
MSG_DATE_UNIT_MISMATCH = (
    "Unit of date '{value}' does not match Date type '{date_type}'; expected '{expected}'"
)
MSG_UNKNOWN_SITE_REQUIRES_PROJECT = "Site name 'unknown' requires '{field}' to be provided"
MSG_MATERIAL_MODULE_MISSING = "Material '{material}' is set but no {module} record is provided"
MSG_UNKNOWN_MATERIAL = "Unknown material '{material}'"
MSG_DANGLING_REFERENCE = "'{value}' in '{field}' does not reference an existing {parent} record"

MESSAGE_KEYS: tuple[str, ...] = (  # 全部消息键（去重清单，供本地化登记）
    MSG_REQUIRED, MSG_VOCAB_UNKNOWN, MSG_VOCAB_UNKNOWN_OPEN, MSG_NOT_NUMERIC, MSG_NOT_INTEGER,
    MSG_INVALID_DATE, MSG_INVALID_SIGMA, MSG_INVALID_RATIO_NAME, MSG_INVALID_RATIO_SOURCE,
    MSG_OUT_OF_RANGE, MSG_INVALID_URL, MSG_SUSPECT_EMAIL, MSG_SUSPECT_PID,
    MSG_DATE_KIND_CONFLICT, MSG_DATE_UNIT_MISMATCH, MSG_UNKNOWN_SITE_REQUIRES_PROJECT,
    MSG_MATERIAL_MODULE_MISSING, MSG_UNKNOWN_MATERIAL, MSG_DANGLING_REFERENCE,
)


class Severity(str, Enum):
    """问题的严重级别：ERROR 阻断录入，WARNING 只提示。"""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True)
class ValidationIssue:
    """一条校验问题。

    Attributes:
        severity: ERROR 阻断录入；WARNING 只提示。
        table: 模块键（``TableKey.value``）；由工作表名调用时回落为工作表名。
        record_id: 记录主键值；无法确定时为空串。
        field_oid: 档案字段 ID（如 ``"SI5.1.1"``）；非字段级问题填列名。
        field_key: 机器可读键名（如 ``"site_geolocation_point_longitude"``）。
        message_key: 英文原文消息，含 ``{}`` 占位符，供 `core.translate()` 渲染。
        params: 消息占位符取值；另含 ``sheet``（工作表名，便于报表定位）。
        value: 触发问题的原始值。
    """

    severity: Severity
    table: str
    record_id: str
    field_oid: str
    field_key: str
    message_key: str
    params: Mapping[str, object] = field(default_factory=dict)
    value: object | None = None

    def __hash__(self) -> int:
        """按定位信息哈希：``params`` 是映射不可哈希，但问题本身应能放进集合去重。"""
        return hash((self.severity, self.table, self.record_id, self.field_oid,
                     self.field_key, self.message_key))


def format_message(issue: ValidationIssue) -> str:
    """渲染问题的英文消息（日志与非 UI 场景直接可读）。

    Args:
        issue: 校验问题。

    Returns:
        ``message_key.format(**params)``；格式化失败时原样返回 ``message_key`` 并记警告
        （报表不该因一条消息炸掉）。
    """
    try:
        return issue.message_key.format(**issue.params)
    except (KeyError, IndexError, ValueError) as err:
        logger.warning(
            "Cannot format validation message %r with params %s: %s",
            issue.message_key, dict(issue.params), err,
        )
        return issue.message_key


@dataclass(frozen=True)
class _RecordContext:
    """一条记录的问题工厂：把 table / record_id / 词表模块收在一处，规则代码只描述规则。"""

    table: str
    record_id: str
    vocab: ModuleType | None = None

    def issue(self, severity: Severity, oid: str, key: str, message_key: str,
              params: Mapping[str, object] | None = None,
              value: object | None = None) -> ValidationIssue:
        """构造一条问题。"""
        return ValidationIssue(
            severity, self.table, self.record_id, oid, key, message_key, dict(params or {}), value
        )

    def error(self, column: FieldSpec | ColumnSpec, message_key: str,
              params: Mapping[str, object] | None = None,
              value: object | None = None) -> ValidationIssue:
        """构造一条字段级 ERROR。"""
        return self.issue(Severity.ERROR, column.oid, column.key, message_key, params, value)

    def warning(self, column: FieldSpec | ColumnSpec, message_key: str,
                params: Mapping[str, object] | None = None,
                value: object | None = None) -> ValidationIssue:
        """构造一条字段级 WARNING。"""
        return self.issue(Severity.WARNING, column.oid, column.key, message_key, params, value)


def validate_columns(
    columns: Sequence[FieldSpec | ColumnSpec],
    record: Mapping[str, object],
    *,
    sheet_name: str = "",
    table: str = "",
    record_id: str = "",
) -> list[ValidationIssue]:
    """按一组显式字段校验一条记录（实体表与可复用块表共用本入口）。

    取值键优先级为 ``ID 键名``（``FieldSpec.qualified_key`` / ``ColumnSpec.header_key``）→
    键名 → ``ID``：工作簿读出的记录与手工构造的字典都能直接校验。

    已实现的规则：必填（``is_required_from_provider``）、受控词表、数值/整数可解析性、
    ``YYYY-MM-DD`` 日期、σ 置信水平、比值名、比值来源、经纬度值域、URL / 邮箱 / PID 形态。
    空值只触发"必填"规则，其余类型规则一律跳过（空 ≠ 类型错误）。

    Args:
        columns: 字段定义（`spec.FieldSpec` 或 `layout.ColumnSpec`，按属性鸭子类型访问）。
        record: 一条记录；键为上述三种形式之一。
        sheet_name: 工作表名；非空时写入每条问题的 ``params["sheet"]``。
        table: 问题的 ``table`` 归属（通常是模块键）；为空时回落为 ``sheet_name``。
        record_id: 记录主键值；为空时按常见 ``terralid_*_id`` 列推断。

    Returns:
        问题列表（可能为空）；同一字段的多条规则命中会各产出一条问题。
    """
    ctx = _RecordContext(
        table=table or sheet_name,
        record_id=record_id or _generic_record_id(record),
        vocab=_load_vocab_module(),
    )
    issues: list[ValidationIssue] = []
    for column in columns:
        raw = _record_value(record, column)
        if _is_blank(raw):
            if column.is_required_from_provider:
                issues.append(ctx.error(column, MSG_REQUIRED, _base_params(column), raw))
            continue
        issues.extend(_check_value(column, raw, ctx))
    return _annotate_sheet(issues, sheet_name)


def validate_record(
    profile: Profile,
    table_key: str,
    record: Mapping[str, object],
    *,
    record_id: str = "",
) -> list[ValidationIssue]:
    """按模块字段校验一条记录（`validate_columns` 的薄包装）。

    Args:
        profile: 档案注册表。
        table_key: 模块键（``TableKey`` 或其 ``value``）。
        record: 一条记录。
        record_id: 记录主键值；为空时取该模块主键字段（如 ``SI0 terralid_site_id``）。

    Returns:
        问题列表；``table_key`` 未知时记 ``logger.warning`` 并返回空列表。
    """
    table_spec = profile.table(table_key)
    if table_spec is None:
        logger.warning("Unknown table key %r; nothing to validate", table_key)
        return []
    return validate_columns(
        table_spec.fields, record, table=table_spec.key.value,
        record_id=record_id or _table_record_id(table_spec, record),
    )


def validate_conditionals(
    table_key: str,
    record: Mapping[str, object],
    *,
    material_tables: Collection[str] | None = None,
) -> list[ValidationIssue]:
    """校验档案显式写出的字段联动。

    1. ``B3.2 Date type`` 与 B3.5 / B3.6 冲突：geological 时 ``B3.5 Cultural unit`` 有值
       → WARNING（B3.5 仅 archaeological 可用），archaeological 时 ``B3.6 Orogenesis`` 有值
       → WARNING。
    2. ``B3.3.4 Unit of date`` 与 ``B3.2`` 派生结果不一致（geological → ``Ma``，
       archaeological → ``a``）→ WARNING；该字段由系统派生，不一致说明是旧值。
    3. ``SI1 Site name == "unknown"`` 且 ``SI2 Project name`` 为空 → ERROR。
    4. ``O12 Material`` 有值但对应材料专属模块没有记录 → WARNING；取值无法识别
       （``layout.material_table_for`` 返回 ``None``）→ WARNING。

    第 4 条需要跨表信息：``material_tables`` 是"本次校验中存在记录的模块键集合"
    （`validate_workbook` 会传全部工作表对应的模块键）；为 ``None`` 时**跳过**该规则并记
    ``logger.debug`` —— 拿不到事实就不猜，避免对只校验单表的调用方误报。

    Args:
        table_key: 模块键，写入问题的 ``table``。
        record: 一条记录。
        material_tables: 已有记录的模块键集合；``None`` 表示未知（跳过 O12 分派规则）。

    Returns:
        问题列表。
    """
    ctx = _RecordContext(table=table_key, record_id=_generic_record_id(record))
    issues: list[ValidationIssue] = []
    date_type = _text(_lookup(record, *_candidates("date_type", "B3.2")))
    if date_type:
        kind = date_type.lower()
        cultural = _lookup(record, *_candidates("date_archaeo_cultural", "B3.5"))
        orogenesis = _lookup(record, *_candidates("date_geol_orogensis", "B3.6"))
        if kind == "geological" and cultural is not None:
            issues.append(ctx.issue(
                Severity.WARNING, "B3.5", "date_archaeo_cultural", MSG_DATE_KIND_CONFLICT,
                {"field": "Cultural unit", "expected_type": "archaeological",
                 "date_type": date_type},
                cultural,
            ))
        if kind == "archaeological" and orogenesis is not None:
            issues.append(ctx.issue(
                Severity.WARNING, "B3.6", "date_geol_orogensis", MSG_DATE_KIND_CONFLICT,
                {"field": "Orogenesis", "expected_type": "geological", "date_type": date_type},
                orogenesis,
            ))
        unit = _text(_lookup(record, *_candidates("date_absolute_unit", "B3.3.4")))
        expected = _DATE_UNIT_BY_TYPE.get(kind, "")
        if unit and expected and unit != expected:
            issues.append(ctx.issue(
                Severity.WARNING, "B3.3.4", "date_absolute_unit", MSG_DATE_UNIT_MISMATCH,
                {"value": unit, "date_type": date_type, "expected": expected}, unit,
            ))
    site_name = _text(_lookup(record, *_candidates("site_name", "SI1")))
    if site_name.lower() == _UNKNOWN_SITE:
        project = _lookup(record, *_candidates("project_name", "SI2"))
        if project is None:
            issues.append(ctx.issue(
                Severity.ERROR, "SI2", "project_name", MSG_UNKNOWN_SITE_REQUIRES_PROJECT,
                {"field": "Project name"}, site_name,
            ))
    material = _text(_lookup(record, *_candidates("object_material", "O12")))
    if material:
        issues.extend(_check_material(ctx, material, material_tables))
    return issues


def _check_material(
    ctx: _RecordContext, material: str, material_tables: Collection[str] | None
) -> list[ValidationIssue]:
    """O12 分派检查：材料取值 → 材料专属模块；模块无记录 / 取值未知各记一条 WARNING。"""
    module = material_table_for(material)
    if module is None:
        return [ctx.issue(Severity.WARNING, "O12", "object_material", MSG_UNKNOWN_MATERIAL,
                          {"material": material}, material)]
    if material_tables is None:
        logger.debug(
            "Material %r maps to module %r but no material-module context was provided; "
            "skipping the O12 dispatch check", material, module,
        )
        return []
    if module in material_tables:
        return []
    return [ctx.issue(Severity.WARNING, "O12", "object_material", MSG_MATERIAL_MODULE_MISSING,
                      {"material": material, "module": _table_label(module)}, material)]


def validate_references(
    table_key: str,
    records_by_table: Mapping[str, Sequence[Mapping[str, object]]],
) -> list[ValidationIssue]:
    """校验一张表的父外键：指向不存在的父记录 → ERROR。

    父键列名取自 `spec.PARENT_FK_COLUMN`（``objects`` → ``assemblage_id`` 等）；父记录
    主键值按 ``<前缀>0 terralid_<单数>_id`` / ``terralid_<单数>_id`` / ``<单数>_id`` /
    ``id`` 依次取值（覆盖工作簿表头 ``ID 键名`` 与纯键名两种写法）。

    **宽松规则（档案声明，不是遗漏）**：Object 与 Analysis 可跨级直接挂 Site，因此这两张
    表的父键悬空时，若记录另有非空 ``site_id`` 视为合法；其他模块（如 Sample）不适用该
    豁免。父表缺席或父键为空时无法判定，跳过并记 ``logger.debug``（增量录入不误报）。

    Args:
        table_key: 子表模块键。
        records_by_table: 模块键 → 该模块的全部记录。

    Returns:
        问题列表；``table_key`` 未知或为顶层模块时返回空列表。
    """
    try:
        table = TableKey(table_key)
    except ValueError as err:
        logger.warning("Unknown table key %r (%s); skipping reference validation", table_key, err)
        return []
    fk_column = PARENT_FK_COLUMN.get(table.value, "")
    parent = table.parent
    if not fk_column or parent is None:
        logger.debug("Table %r is top-level; no parent reference to validate", table.value)
        return []
    children = records_by_table.get(table.value) or ()
    if not children:
        return []
    if parent.value not in records_by_table:
        logger.debug(
            "Parent table %r is absent from the validated workbook; %r references are not checked",
            parent.value, table.value,
        )
        return []
    parent_ids = _parent_ids(parent, records_by_table.get(parent.value) or ())
    issues: list[ValidationIssue] = []
    for record in children:
        value = _text(record.get(fk_column))
        if not value or value in parent_ids or _is_cross_level_ok(table, fk_column, record):
            continue
        ctx = _RecordContext(table.value, _generic_record_id(record))
        issues.append(ctx.issue(
            Severity.ERROR, fk_column, fk_column, MSG_DANGLING_REFERENCE,
            {"value": value, "field": fk_column, "parent": parent.label_en,
             "parent_table": parent.value},
            value,
        ))
    return issues


def _is_cross_level_ok(table: TableKey, fk_column: str, record: Mapping[str, object]) -> bool:
    """Object / Analysis 跨级直挂 Site：父键悬空但另有非空 ``site_id`` 时视为合法。"""
    if table.value not in _CROSS_LEVEL_TABLES or fk_column == _CROSS_LEVEL_COLUMN:
        return False
    if not _text(record.get(_CROSS_LEVEL_COLUMN)):
        return False
    logger.debug("Accepting %s=%r in %s as a direct attachment to Site via %s",
                 fk_column, record.get(fk_column), table.value, _CROSS_LEVEL_COLUMN)
    return True


def _parent_ids(table: TableKey, records: Sequence[Mapping[str, object]]) -> frozenset[str]:
    """收集父表记录的主键值（候选列里首个非空命中即为该记录的主键）。"""
    singular = _TABLE_SINGULAR.get(table.value, "")
    columns = ((f"{table.oid_prefix}0 terralid_{singular}_id", f"terralid_{singular}_id",
                f"{singular}_id", "id") if singular else ("id",))
    found: set[str] = set()
    for record in records:
        for column in columns:
            raw = record.get(column)
            if raw is None:
                continue
            text = _text(raw)
            if text:
                found.add(text)
                break
    if not found:
        logger.debug("Parent table %r provided no usable primary key values", table.value)
    return frozenset(found)


def validate_workbook(
    profile: Profile,
    sheeted_records: Mapping[tuple[str, str], Sequence[Mapping[str, object]]],
) -> list[ValidationIssue]:
    """校验整本录入工作簿。

    键是 ``(模块键, 工作表名)``：工作表名到模块的映射由调用方给出，避免本模块猜表名。
    流程：逐记录跑 `validate_record` + `validate_conditionals`，最后统一跑 `validate_references`。

    Args:
        profile: 档案注册表。
        sheeted_records: ``(table_key, sheet_name)`` → 该表记录序列。

    Returns:
        问题列表；顺序为"逐表逐记录的字段/联动问题，然后是外键问题"，便于报表稳定。
    """
    issues: list[ValidationIssue] = []
    records_by_table: dict[str, list[Mapping[str, object]]] = {}
    material_tables = frozenset(table_key for table_key, _sheet in sheeted_records)
    for (table_key, sheet_name), records in sheeted_records.items():
        bucket = records_by_table.setdefault(table_key, [])
        for record in records:
            bucket.append(record)
            issues.extend(_annotate_sheet(validate_record(profile, table_key, record), sheet_name))
            linked = validate_conditionals(table_key, record, material_tables=material_tables)
            issues.extend(_annotate_sheet(linked, sheet_name))
    for table_key in records_by_table:
        issues.extend(validate_references(table_key, records_by_table))
    return issues


def summarize(issues: Sequence[ValidationIssue]) -> dict[str, int]:
    """统计问题数量，供报告页眉。

    Args:
        issues: 校验问题序列。

    Returns:
        ``{"error": n, "warning": n, "records": n}``（``records`` 按出现问题记录去重）。
    """
    return {
        "error": sum(1 for issue in issues if issue.severity is Severity.ERROR),
        "warning": sum(1 for issue in issues if issue.severity is Severity.WARNING),
        "records": len({(issue.table, issue.record_id) for issue in issues}),
    }


# 内部实现
# ─────────────────────────────────────────────────────────────────────────────

#: 需要数值解析的取值类型，及其在 ``{kind}`` 占位符里的描述。
_NUMERIC_KINDS = frozenset({ValueKind.DECIMAL, ValueKind.NUMBER, ValueKind.INTEGER})
_NUMERIC_KIND_LABELS: Mapping[ValueKind, str] = MappingProxyType(
    {ValueKind.DECIMAL: "decimal number", ValueKind.NUMBER: "number", ValueKind.INTEGER: "integer"}
)

#: B3.2 → B3.3.4 的派生关系（档案 B3.3.4 定义原文）；B3.2 = "unknown" 的站点名（SI1）。
_DATE_UNIT_BY_TYPE: Mapping[str, str] = MappingProxyType(
    {"geological": "Ma", "archaeological": "a"}
)
_UNKNOWN_SITE = "unknown"

#: 经纬度字段 OID → 区间（档案：经度 -180..180、纬度 -90..90）。
_GEO_BOUNDS_BY_OID: Mapping[str, tuple[float, float]] = MappingProxyType({
    "SI5.1.1": (-180.0, 180.0), "SI5.2.1": (-180.0, 180.0), "SI5.2.2": (-180.0, 180.0),
    "SI5.4.1.1": (-180.0, 180.0), "SI5.1.2": (-90.0, 90.0), "SI5.2.3": (-90.0, 90.0),
    "SI5.2.4": (-90.0, 90.0), "SI5.4.1.2": (-90.0, 90.0)})

#: 跨级直挂：Object / Analysis 可直接挂 Site（档案层级声明）。
_CROSS_LEVEL_TABLES = frozenset({TableKey.OBJECT.value, TableKey.ANALYSIS.value})
_CROSS_LEVEL_COLUMN = "site_id"

#: 层级链路实体表 → 主键列单数词（``terralid_<单数>_id``）。
_TABLE_SINGULAR: Mapping[str, str] = MappingProxyType(
    {"sites": "site", "assemblages": "assemblage", "objects": "object",
     "samples": "sample", "analyses": "analysis"}
)

#: 常见 ``terralid_*_id`` 主键列（无注册表时推断记录 ID）。
_GENERIC_ID_KEYS: tuple[str, ...] = tuple(
    key for table in (TableKey.SITE, TableKey.ASSEMBLAGE, TableKey.OBJECT, TableKey.SAMPLE,
                      TableKey.ANALYSIS)
    for key in (f"{table.oid_prefix}0 terralid_{_TABLE_SINGULAR[table.value]}_id",
                f"terralid_{_TABLE_SINGULAR[table.value]}_id")
)

#: 日期必须形如 ``YYYY-MM-DD``（``date.fromisoformat`` 在 3.11+ 也接受 ``YYYYMMDD``）。
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

#: 邮箱基本形态 ``local@domain.tld``（宽松，避免误伤合法地址）。
_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

#: ORCID ``0000-0002-1825-0097``（末位可为 X）与 DOI ``10.<registrant>/<suffix>``。
_ORCID_PATTERN = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dXx]$")
_DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$")


def _load_vocab_module() -> ModuleType | None:
    """延迟导入受控词表模块；不可用时返回 ``None``（按 open_ended=True 回退）。"""
    try:
        from . import vocab as vocab_module
    except ImportError as err:
        logger.debug("Controlled vocabulary module unavailable (%s); membership not enforced", err)
        return None
    except Exception as err:  # noqa: BLE001 — 词表模块损坏只降级，不让整本工作簿校验崩掉
        logger.warning("Controlled vocabulary module failed to import (%s); not enforced", err)
        return None
    return vocab_module


def _check_value(column: FieldSpec | ColumnSpec, raw: object,
                 ctx: _RecordContext) -> list[ValidationIssue]:
    """非空字段的取值检查（数值 / 词表 / 日期 / σ / 比值 / 值域 / 格式）。"""
    issues: list[ValidationIssue] = []
    text = _text(raw)
    params = _base_params(column)
    number = _coerce_float(raw) if column.value_kind in _NUMERIC_KINDS else None
    if column.value_kind in _NUMERIC_KINDS:
        if number is None:
            kind = _NUMERIC_KIND_LABELS.get(column.value_kind, "number")
            issues.append(ctx.error(column, MSG_NOT_NUMERIC,
                                    {**params, "value": text, "kind": kind}, raw))
        elif column.value_kind is ValueKind.INTEGER and not number.is_integer():
            issues.append(ctx.warning(column, MSG_NOT_INTEGER, {**params, "value": text}, raw))
    if column.value_kind is ValueKind.CONTROLLED_VOCAB:
        issues.extend(_check_vocabulary(column, text, raw, ctx))
    if column.value_kind is ValueKind.DATE and not _is_valid_date(raw):
        issues.append(ctx.error(column, MSG_INVALID_DATE, {**params, "value": text}, raw))
    if column.value_kind is ValueKind.SIGMA:
        level = _coerce_int(raw)
        if level is None or level not in SIGMA_LEVELS:
            issues.append(ctx.error(column, MSG_INVALID_SIGMA, {**params, "value": text}, raw))
    if column.value_kind is ValueKind.RATIO_NAME and text not in LIA_RATIO_NAMES:
        issues.append(ctx.error(column, MSG_INVALID_RATIO_NAME, {**params, "value": text}, raw))
    if column.value_kind is ValueKind.RATIO_SOURCE and text not in RATIO_SOURCES:
        issues.append(ctx.error(column, MSG_INVALID_RATIO_SOURCE, {**params, "value": text}, raw))
    bounds = _GEO_BOUNDS_BY_OID.get(column.oid)
    if bounds is not None:
        parsed = number if number is not None else _coerce_float(raw)
        if parsed is None and column.value_kind not in _NUMERIC_KINDS:
            issues.append(ctx.error(column, MSG_NOT_NUMERIC,
                                    {**params, "value": text, "kind": "decimal number"}, raw))
        elif parsed is not None and not bounds[0] <= parsed <= bounds[1]:
            issues.append(ctx.error(column, MSG_OUT_OF_RANGE,
                                    {**params, "value": text, "minimum": bounds[0],
                                     "maximum": bounds[1]}, raw))
    if column.value_kind is ValueKind.URL and not _is_valid_url(text):
        issues.append(ctx.error(column, MSG_INVALID_URL, {**params, "value": text}, raw))
    if column.value_kind is ValueKind.EMAIL and not _EMAIL_PATTERN.match(text):
        issues.append(ctx.warning(column, MSG_SUSPECT_EMAIL, {**params, "value": text}, raw))
    if column.value_kind is ValueKind.PID and not _is_valid_pid(text):
        issues.append(ctx.warning(column, MSG_SUSPECT_PID, {**params, "value": text}, raw))
    return issues


def _check_vocabulary(column: FieldSpec | ColumnSpec, text: str, raw: object,
                      ctx: _RecordContext) -> list[ValidationIssue]:
    """受控词表规则：``vocab.contains`` 判定，``vocab.open_ended`` 决定级别。

    词表 id 优先取字段的 ``vocab_id``，缺失时按 OID 回落到 ``vocab.vocab_id_for(field)``。
    词表不存在或尚无词条时**不报问题** —— 空词表会把所有值都判成"词表外"，那是假阳性。
    """
    if ctx.vocab is None:
        logger.debug("Vocabulary for %s is not checked: no vocabulary module", column.oid)
        return []
    vocab_id = getattr(column, "vocab_id", None)
    if not vocab_id:
        resolved = _vocab_call(ctx.vocab, "vocab_id_for", column)
        vocab_id = str(resolved) if resolved else None
    if not vocab_id:
        logger.debug("Field %s has no vocabulary id; free text is not checked", column.oid)
        return []
    if not _vocab_call(ctx.vocab, "terms", vocab_id):
        logger.debug("Controlled vocabulary %r has no terms; %r for %s is not checked",
                     vocab_id, text, column.oid)
        return []
    contained = _vocab_call(ctx.vocab, "contains", vocab_id, text)
    if contained is None:
        return []  # 词表查询不可用（``_vocab_call`` 已记日志）：降级为不检查
    if contained:
        return []
    open_ended = _vocab_call(ctx.vocab, "open_ended", vocab_id)
    if open_ended is None or open_ended:
        return [ctx.warning(column, MSG_VOCAB_UNKNOWN_OPEN,
                            {**_base_params(column), "value": text}, raw)]
    return [ctx.error(column, MSG_VOCAB_UNKNOWN, {**_base_params(column), "value": text}, raw)]


def _vocab_call(vocab_module: ModuleType, name: str, *args) -> object | None:
    """调用 vocab 模块的可选函数：缺失/异常时记日志并返回 ``None``（降级不中断）。"""
    function = getattr(vocab_module, name, None)
    if not callable(function):
        logger.debug("vocab.%s() is unavailable; skipping that vocabulary step", name)
        return None
    try:
        return function(*args)
    except Exception as err:  # noqa: BLE001 — 并行模块的失败只降级，不中断整次校验
        logger.warning("vocab.%s%r failed: %s", name, args, err)
        return None


def _is_valid_date(value: object) -> bool:
    """``YYYY-MM-DD`` 且为合法日历日；``datetime`` 对象直接视为合法。"""
    if isinstance(value, datetime.date):  # datetime 是 date 的子类
        return True
    text = _text(value)
    if not _DATE_PATTERN.match(text):
        return False
    try:
        datetime.date.fromisoformat(text)
    except ValueError as err:
        logger.debug("Rejecting date %r: %s", text, err)
        return False
    return True


def _is_valid_url(text: str) -> bool:
    """URL 规则：scheme 必须是 http/https 且带主机名。"""
    parsed = urlparse(text)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        logger.debug("Rejecting URL %r: scheme=%r netloc=%r", text, parsed.scheme, parsed.netloc)
        return False
    return True


def _is_valid_pid(text: str) -> bool:
    """PID 规则（宽容）：ORCID / DOI / ``prefix/suffix`` 形态之一即可。"""
    if _ORCID_PATTERN.match(text) or _DOI_PATTERN.match(text):
        return True
    prefix, separator, suffix = text.partition("/")
    return bool(separator and prefix.strip() and suffix.strip())


def _is_blank(value: object) -> bool:
    """判断值是否为空（``None`` / 空串 / NaN / 空集合）。``0`` 与 ``False`` 不算空。"""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, float):
        return math.isnan(value)
    if isinstance(value, (Mapping, Sequence, set, frozenset)):
        return len(value) == 0
    return False


def _coerce_float(value: object) -> float | None:
    """安全转成有限浮点数（禁止裸 ``float()``，规范 §8.1）；失败记 debug 并返回 None。"""
    if isinstance(value, bool):
        return None
    try:
        candidate = float(value)  # type: ignore[arg-type]  # 输入类型不可信，故包裹转换
    except (TypeError, ValueError) as err:
        logger.debug("Ignoring non-numeric value %r: %s", value, err)
        return None
    if not math.isfinite(candidate):
        logger.debug("Ignoring non-finite value %r", value)
        return None
    return candidate


def _coerce_int(value: object) -> int | None:
    """安全转成整数（禁止裸 ``int()``）；失败记 debug 并返回 ``None``。"""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    try:
        return int(value)  # type: ignore[arg-type]  # 输入类型不可信，故包裹转换
    except (TypeError, ValueError) as err:
        logger.debug("Ignoring non-integer value %r: %s", value, err)
        return None


def _text(value: object) -> str:
    """把值渲染为去掉首尾空白的字符串（``None`` → 空串）。"""
    return "" if value is None else str(value).strip()


def _base_params(column: FieldSpec | ColumnSpec) -> dict[str, object]:
    """字段级消息的公共占位符（``{field}`` 英文标签 + ``{oid}``）。"""
    return {"field": getattr(column, "label_en", "") or column.key, "oid": column.oid}


def _record_value(record: Mapping[str, object], column: FieldSpec | ColumnSpec) -> object | None:
    """按候选键从记录里取值：``ID 键名`` → 键名 → ``ID``。"""
    header = getattr(column, "header_key", None) or column.qualified_key
    for key in (header, column.key, column.oid):
        if key in record:
            return record[key]
    return None


def _candidates(key: str, oid: str) -> tuple[str, str, str]:
    """条件联动规则的取值键候选（记录可能按表头键或纯键名存放）。"""
    return (f"{oid} {key}", key, oid)


def _lookup(record: Mapping[str, object], *candidates: str) -> object | None:
    """取第一个非空命中值；全部缺失/为空时返回 ``None``。"""
    for candidate in candidates:
        if candidate in record and not _is_blank(record[candidate]):
            return record[candidate]
    return None


def _generic_record_id(record: Mapping[str, object]) -> str:
    """按常见 ``terralid_*_id`` 列推断记录 ID；推断不出返回空串。"""
    for key in _GENERIC_ID_KEYS:
        text = _text(record.get(key))
        if text:
            return text
    return ""


def _table_record_id(table: TableSpec, record: Mapping[str, object]) -> str:
    """按模块主键字段取记录 ID。"""
    id_field = table.id_field
    if id_field is None:
        return _generic_record_id(record)
    return _text(_record_value(record, id_field)) or _generic_record_id(record)


def _table_label(table_key: str) -> str:
    """模块键 → 模块英文名（消息占位符 ``{module}``）。"""
    try:
        return TableKey(table_key).label_en
    except ValueError as err:
        logger.debug("Unknown table key %r (%s); falling back to the raw key", table_key, err)
        return table_key


def _annotate_sheet(issues: Sequence[ValidationIssue], sheet_name: str) -> list[ValidationIssue]:
    """把工作表名写进问题的 ``params["sheet"]``，便于报表定位到具体工作表。"""
    if not sheet_name:
        return list(issues)
    return [replace(issue, params={**issue.params, "sheet": sheet_name}) for issue in issues]


__all__ = [
    "MESSAGE_KEYS",  # 消息键（中英对照登记用；单键常量亦公开）
    "Severity",
    "ValidationIssue",
    "format_message",
    "summarize",
    "validate_columns",
    "validate_conditionals",
    "validate_record",
    "validate_references",
    "validate_workbook",
]
