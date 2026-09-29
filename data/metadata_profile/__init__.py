"""TerraLID 铅同位素元数据档案的机器可读注册表与工具。

对 `reference/metadata`（TerraLID Metadata Profile，CC-BY-4.0）的代码化封装：
把分散在 markdown 里的字段定义变成可校验、可生成录入工作簿、可与既有扁平列互转的
数据结构。

模块分工：

| 模块 | 职责 |
|------|------|
| `spec` | 数据结构与常量（契约层，无 IO） |
| `parse` | 解析 `docs/metadata_*.md` 与 `includes/metadata_blocks.md` |
| `profile` | 组装成 `Profile` 注册表（缓存入口 `load_profile()`） |
| `vocab` | 80 张受控词表（档案未枚举，本地补充，登记为词表的唯一真源） |
| `labels` | 字段中文标签（307 条，兜底英文标题表） |
| `layout` | 注册表 → 录入工作簿的工作表/列映射（生成器与导入器共用） |
| `ratios` | 8 个比值的推导与不确定度换算 |
| `validate` | 字段级/联动/外键校验 → 问题清单 |
| `validate_sheets` | 工作表辅助列与块表归属校验 |
| `io_xlsx` | 工作簿读写（原子写 + 覆盖前备份） |

符号按 PEP 562 懒解析，照 `data/__init__.py` 的既有做法：`spec` 之外的模块会拉入
`openpyxl`（`io_xlsx`）或大块词表数据（`vocab`/`labels`），不该在只想要常量时被牵连。

工作簿的生成在 `scripts/build_entry_workbook.py`，用例编排在
`application/use_cases/entry_workbook.py`，Qt 入口在 `ui/dialogs/entry_workbook.py`。
"""

from __future__ import annotations

import importlib
from typing import Any

from .spec import (
    AGE_MODEL_NAMES,
    AGE_MODEL_PARAMETERS,
    DATE_TYPES,
    DATE_UNITS,
    DERIVED_LIA_RATIO_NAMES,
    LIA_RATIO_MASSES,
    LIA_RATIO_NAMES,
    PRIMARY_LIA_RATIO_NAMES,
    PROFILE_DOI,
    PROFILE_LICENSE,
    PROFILE_SOURCE,
    RATIO_SOURCES,
    SIGMA_LEVELS,
    YES_NO_UNCLEAR,
    Block,
    FieldSpec,
    Obligation,
    Occurrence,
    Profile,
    ProvidedBy,
    TableKey,
    TableSpec,
    ValueKind,
    derived_ratio_expression,
    primary_ratio_for_mass,
)

__all__ = [
    # ── 契约：枚举 ──
    "Block",
    "Obligation",
    "Occurrence",
    "ProvidedBy",
    "TableKey",
    "ValueKind",
    # ── 契约：数据结构 ──
    "FieldSpec",
    "Profile",
    "TableSpec",
    # ── 契约：常量与工具 ──
    "AGE_MODEL_NAMES",
    "AGE_MODEL_PARAMETERS",
    "DATE_TYPES",
    "DATE_UNITS",
    "DERIVED_LIA_RATIO_NAMES",
    "LIA_RATIO_MASSES",
    "LIA_RATIO_NAMES",
    "PRIMARY_LIA_RATIO_NAMES",
    "PROFILE_DOI",
    "PROFILE_LICENSE",
    "PROFILE_SOURCE",
    "RATIO_SOURCES",
    "SIGMA_LEVELS",
    "YES_NO_UNCLEAR",
    "derived_ratio_expression",
    "primary_ratio_for_mass",
    # ── 注册表 ──
    "load_profile",
    # ── 词表与标签 ──
    "VOCABULARIES",
    "Vocabulary",
    "contains",
    "label_for",
    "open_ended",
    "terms",
    "vocab_id_for",
    # ── 工作簿布局 ──
    "ColumnSpec",
    "SheetKind",
    "SheetSpec",
    "WorkbookLayout",
    "build_layout",
    "material_sheet_for",
    "material_table_for",
    "owner_sheet_options",
    # ── 比值 ──
    "SOURCE_CALCULATED",
    "SOURCE_ORIGINAL",
    "RatioValue",
    "absolute_from_relative",
    "derive_all_ratios",
    "format_ratio",
    "format_uncertainty",
    "relative_from_absolute",
    # ── 校验 ──
    "Severity",
    "ValidationIssue",
    "format_message",
    "summarize",
    "validate_columns",
    "validate_conditionals",
    "validate_record",
    "validate_references",
    "validate_sheet_helpers",
    "validate_workbook",
    # ── 工作簿 IO ──
    "CHECK_FIRST_DATA_ROW",
    "CHECK_HEADERS",
    "SheetReadResult",
    "backup_file",
    "read_sheet",
    "read_sheets",
    "write_check_report",
    "write_records",
]

#: 属性名 → 提供它的子模块。``spec`` 的符号已直接导入，不必再绕一层。
_LAZY_ATTRS: dict[str, str] = {}


def _register(module_name: str, names: tuple[str, ...]) -> None:
    """登记一批惰性导出的符号（模块级调用，不产生副作用）。"""
    for name in names:
        _LAZY_ATTRS[name] = module_name


_register("profile", ("load_profile",))
_register(
    "vocab",
    ("VOCABULARIES", "Vocabulary", "contains", "open_ended", "terms", "vocab_id_for"),
)
_register("labels", ("label_for",))
_register(
    "layout",
    (
        "ColumnSpec",
        "SheetKind",
        "SheetSpec",
        "WorkbookLayout",
        "build_layout",
        "material_sheet_for",
        "material_table_for",
        "owner_sheet_options",
    ),
)
_register(
    "ratios",
    (
        "SOURCE_CALCULATED",
        "SOURCE_ORIGINAL",
        "RatioValue",
        "absolute_from_relative",
        "derive_all_ratios",
        "format_ratio",
        "format_uncertainty",
        "relative_from_absolute",
    ),
)
_register(
    "validate",
    (
        "Severity",
        "ValidationIssue",
        "format_message",
        "summarize",
        "validate_columns",
        "validate_conditionals",
        "validate_record",
        "validate_references",
        "validate_workbook",
    ),
)
_register("validate_sheets", ("validate_sheet_helpers",))
_register(
    "io_xlsx",
    (
        "CHECK_FIRST_DATA_ROW",
        "CHECK_HEADERS",
        "SheetReadResult",
        "backup_file",
        "read_sheet",
        "read_sheets",
        "write_check_report",
        "write_records",
    ),
)


def __getattr__(name: str) -> Any:
    """按需导入子模块符号（PEP 562），避免 import 时拉入 openpyxl 与词表数据。"""
    module_name = _LAZY_ATTRS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    # importlib 而非 ``from . import x``：后者会在子模块尚未绑定时重入 __getattr__。
    module = importlib.import_module(f"{__name__}.{module_name}")
    return getattr(module, name)


def __dir__() -> list[str]:
    """让 dir() 同时列出已导入与惰性导出的符号。"""
    return sorted(set(globals().keys()) | set(__all__))
