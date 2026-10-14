"""Adapters - file IO at the edge of the domain.

These modules read and write the outside world: dataset workbooks/spreadsheets, the galena
reference workbook.  They are infrastructure, not domain, so they live outside ``data/``
(docs/dev_conventions.md §18.1): ``data/`` holds the pure registry and calculations and must
not depend on pandas, openpyxl or Qt.

Exports are lazy (PEP 562) so importing this package does not pull pandas in.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["loader", "read_data_frame", "silverquest", "xlsx_io"]

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "read_data_frame": ("loader", "read_data_frame"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        module_name, attr_name = _LAZY_EXPORTS[name]
        value = getattr(import_module(f".{module_name}", __name__), attr_name)
        globals()[name] = value
        return value
    if name in __all__:
        module = import_module(f".{name}", __name__)
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals().keys()) | set(__all__))
