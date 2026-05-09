"""Application layer package.

Use lazy exports to avoid importing heavy optional dependencies at
package import time (for example during pytest collection in CI).
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "append_selected_data_to_excel",
    "build_export_dataframe",
    "build_image_export_profile",
    "collect_geochem_curve_data",
    "export_dataframe_to_file",
    "export_selected_data_to_file",
    "fallback_export_rc",
    "normalize_export_target",
    "RenderPlotUseCase",
    "SelectionInteractionUseCase",
    "SelectedIsochronUseCase",
    "TooltipContentUseCase",
    "load_dataset",
    "resolve_image_save_options",
    "save_export_figure",
]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    use_cases = import_module(".use_cases", __name__)
    value = getattr(use_cases, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals().keys()) | set(__all__))
