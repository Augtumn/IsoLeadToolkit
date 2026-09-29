"""运行时才确定键名的本地化键清单。

`data/metadata_profile/validate.py` 与 `validate_sheets.py` 把校验问题的
``message_key`` 作为**数据**返回，而不是直接调用 ``translate()`` —— 这样同一份问题
既能写进 Excel 的 ``99_CHECK`` 表（英文原文），也能在 UI 里按当前语言渲染，
还能在非 UI 场景（脚本、测试、登录日志）直接读出。

代价是这些键在源码里**没有** ``translate("...")`` 字面量，而
``locales/check_untranslated.py`` 正是靠静态扫描 ``translate()`` 实参 +
``locales/*.py`` 里的字符串字面量来判定"哪些键被引用"。若不在本文件登记，
它们会被报成 `unused_keys`（未被引用的键）而使本地化检查失败。

因此：**改动校验规则时必须同步更新本清单**。测试
`tests/test_metadata_vocab.py` 与 `tests/test_metadata_ratios_validate.py` 各自
导出的 ``MESSAGE_KEYS`` 是权威来源，本清单只为静态扫描服务。
"""
from __future__ import annotations

#: `validate.py` 的字段级/联动/外键校验消息模板（19 条）。
FIELD_VALIDATION_MESSAGE_KEYS: tuple[str, ...] = (
    "Required field '{field}' ({oid}) is empty",
    "'{value}' is not an allowed value for '{field}' ({oid})",
    "'{value}' is not a known value for '{field}' ({oid}); "
    "the controlled vocabulary may be incomplete",
    "'{value}' is not a valid {kind} for '{field}' ({oid})",
    "'{value}' is not a whole number for '{field}' ({oid})",
    "'{value}' is not a date in YYYY-MM-DD format for '{field}' ({oid})",
    "'{value}' is not a valid confidence level for '{field}' ({oid}); "
    "allowed values are 1, 2, 3",
    "'{value}' is not a known lead isotope ratio for '{field}' ({oid})",
    "'{value}' is not a valid lead isotope ratio source for '{field}' ({oid}); "
    "allowed values are original, calculated",
    "'{value}' is outside the allowed range {minimum} to {maximum} for '{field}' ({oid})",
    "'{value}' is not a valid http(s) URL for '{field}' ({oid})",
    "'{value}' does not look like a valid email address for '{field}' ({oid})",
    "'{value}' does not look like a valid persistent identifier for '{field}' ({oid})",
    "'{field}' is only available when Date type is '{expected_type}'; "
    "this record has '{date_type}'",
    "Unit of date '{value}' does not match Date type '{date_type}'; expected '{expected}'",
    "Site name 'unknown' requires '{field}' to be provided",
    "Material '{material}' is set but no {module} record is provided",
    "Unknown material '{material}'",
    "'{value}' in '{field}' does not reference an existing {parent} record",
)

#: `validate_sheets.py` 的工作表辅助列校验消息模板（2 条）。
SHEET_HELPER_MESSAGE_KEYS: tuple[str, ...] = (
    "Required column '{column}' is empty on sheet '{sheet}'",
    "'{value}' is not an allowed value for column '{column}' on sheet '{sheet}'; "
    "allowed values: {allowed}",
)

#: 用例层在导入时产生的提示（明细行填了别的组的列）。
#: 由 `application/use_cases/entry_workbook.py::MSG_STRAY_GROUP_COLUMN` 提供。
STRAY_GROUP_MESSAGE_KEYS: tuple[str, ...] = (
    "'{value}' in '{column}' belongs to another group on sheet '{sheet}'",
)

#: 全部运行时消息键。
MESSAGE_KEYS: tuple[str, ...] = (
    FIELD_VALIDATION_MESSAGE_KEYS
    + SHEET_HELPER_MESSAGE_KEYS
    + STRAY_GROUP_MESSAGE_KEYS
)

__all__ = [
    "FIELD_VALIDATION_MESSAGE_KEYS",
    "MESSAGE_KEYS",
    "SHEET_HELPER_MESSAGE_KEYS",
    "STRAY_GROUP_MESSAGE_KEYS",
]
