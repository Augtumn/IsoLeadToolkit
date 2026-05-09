"""Application use case exports (lazy)."""

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
	"export_to_origin",
	"fallback_export_rc",
	"normalize_export_target",
	"resolve_image_save_options",
	"RenderPlotUseCase",
	"SelectionInteractionUseCase",
	"SelectedIsochronUseCase",
	"TooltipContentUseCase",
	"load_dataset",
	"save_export_figure",
]

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
	"append_selected_data_to_excel": ("export_data", "append_selected_data_to_excel"),
	"build_export_dataframe": ("export_data", "build_export_dataframe"),
	"export_dataframe_to_file": ("export_data", "export_dataframe_to_file"),
	"export_selected_data_to_file": ("export_data", "export_selected_data_to_file"),
	"build_image_export_profile": ("export_image", "build_image_export_profile"),
	"collect_geochem_curve_data": ("export_data", "collect_geochem_curve_data"),
	"fallback_export_rc": ("export_image", "fallback_export_rc"),
	"normalize_export_target": ("export_image", "normalize_export_target"),
	"resolve_image_save_options": ("export_image", "resolve_image_save_options"),
	"save_export_figure": ("export_image", "save_export_figure"),
	"export_to_origin": ("export_origin", "export_to_origin"),
	"RenderPlotUseCase": ("render_plot", "RenderPlotUseCase"),
	"load_dataset": ("load_dataset", "load_dataset"),
	"SelectionInteractionUseCase": ("selection_interaction", "SelectionInteractionUseCase"),
	"SelectedIsochronUseCase": ("selected_isochron", "SelectedIsochronUseCase"),
	"TooltipContentUseCase": ("tooltip_content", "TooltipContentUseCase"),
}


def __getattr__(name: str) -> Any:
	try:
		module_name, attr_name = _LAZY_EXPORTS[name]
	except KeyError as exc:
		raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

	module = import_module(f".{module_name}", __name__)
	value = getattr(module, attr_name)
	globals()[name] = value
	return value


def __dir__() -> list[str]:
	return sorted(set(globals().keys()) | set(__all__))
