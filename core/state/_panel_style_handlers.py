"""Panel style handlers: field name -> gateway setter.

Only the fields AppStateGateway.set_panel_style_updates() accepts are mapped;
every other state change goes through its explicit gateway action.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)
_UNSET = object()


def _converted_handler(
    gateway: Any,
    setter_name: str,
    converter: Callable[[Any], Any] | None = None,
) -> Callable[[Any], None]:
    """Bind a gateway setter with an optional value converter."""
    setter = getattr(gateway, setter_name)
    if converter is None:
        return setter
    return lambda value, _setter=setter, _converter=converter: _setter(_converter(value))


def panel_style_keys() -> set[str]:
    """Field names accepted by panel style updates."""
    return {
        "plot_style_grid",
        "plot_marker_size",
        "plot_marker_alpha",
        "show_plot_title",
        "plot_dpi",
        "custom_primary_font",
        "custom_cjk_font",
        "plot_font_sizes",
        "plot_facecolor",
        "axes_facecolor",
        "grid_color",
        "grid_linewidth",
        "grid_alpha",
        "grid_linestyle",
        "tick_direction",
        "tick_color",
        "tick_length",
        "tick_width",
        "axis_linewidth",
        "axis_line_color",
        "minor_ticks",
        "minor_tick_length",
        "minor_tick_width",
        "show_top_spine",
        "show_right_spine",
        "minor_grid",
        "minor_grid_color",
        "minor_grid_linewidth",
        "minor_grid_alpha",
        "minor_grid_linestyle",
        "scatter_show_edge",
        "scatter_edgecolor",
        "scatter_edgewidth",
        "label_color",
        "label_weight",
        "label_pad",
        "title_color",
        "title_weight",
        "title_pad",
        "legend_frame_on",
        "legend_frame_alpha",
        "legend_frame_facecolor",
        "legend_frame_edgecolor",
        "adjust_text_force_text",
        "adjust_text_force_static",
        "adjust_text_expand",
        "adjust_text_iter_lim",
        "adjust_text_time_lim",
        "color_scheme",
        "model_curve_width",
        "paleoisochron_width",
        "model_age_line_width",
        "isochron_line_width",
    }


def build_panel_style_handlers(gateway: Any) -> dict[str, Callable[[Any], None]]:
    """Build the field-name -> setter table for panel style updates."""
    direct_map = {
        "custom_primary_font": "set_custom_primary_font",
        "custom_cjk_font": "set_custom_cjk_font",
        "plot_font_sizes": "set_plot_font_sizes",
        "adjust_text_force_text": "set_adjust_text_force_text",
        "adjust_text_force_static": "set_adjust_text_force_static",
        "adjust_text_expand": "set_adjust_text_expand",
    }
    bool_map = {
        "plot_style_grid": "set_plot_style_grid",
        "show_plot_title": "set_show_plot_title",
        "minor_ticks": "set_minor_ticks",
        "show_top_spine": "set_show_top_spine",
        "show_right_spine": "set_show_right_spine",
        "minor_grid": "set_minor_grid",
        "scatter_show_edge": "set_scatter_show_edge",
        "legend_frame_on": "set_legend_frame_on",
    }
    int_map = {
        "plot_marker_size": "set_plot_marker_size",
        "plot_dpi": "set_plot_dpi",
        "adjust_text_iter_lim": "set_adjust_text_iter_lim",
    }
    float_map = {
        "plot_marker_alpha": "set_plot_marker_alpha",
        "grid_linewidth": "set_grid_linewidth",
        "grid_alpha": "set_grid_alpha",
        "tick_length": "set_tick_length",
        "tick_width": "set_tick_width",
        "axis_linewidth": "set_axis_linewidth",
        "minor_tick_length": "set_minor_tick_length",
        "minor_tick_width": "set_minor_tick_width",
        "minor_grid_linewidth": "set_minor_grid_linewidth",
        "minor_grid_alpha": "set_minor_grid_alpha",
        "scatter_edgewidth": "set_scatter_edgewidth",
        "label_pad": "set_label_pad",
        "title_pad": "set_title_pad",
        "legend_frame_alpha": "set_legend_frame_alpha",
        "model_curve_width": "set_model_curve_width",
        "paleoisochron_width": "set_paleoisochron_width",
        "model_age_line_width": "set_model_age_line_width",
        "isochron_line_width": "set_isochron_line_width",
        "adjust_text_time_lim": "set_adjust_text_time_lim",
    }
    str_map = {
        "plot_facecolor": "set_plot_facecolor",
        "axes_facecolor": "set_axes_facecolor",
        "grid_color": "set_grid_color",
        "grid_linestyle": "set_grid_linestyle",
        "tick_direction": "set_tick_direction",
        "tick_color": "set_tick_color",
        "axis_line_color": "set_axis_line_color",
        "minor_grid_color": "set_minor_grid_color",
        "minor_grid_linestyle": "set_minor_grid_linestyle",
        "scatter_edgecolor": "set_scatter_edgecolor",
        "label_color": "set_label_color",
        "label_weight": "set_label_weight",
        "title_color": "set_title_color",
        "title_weight": "set_title_weight",
        "legend_frame_facecolor": "set_legend_frame_facecolor",
        "legend_frame_edgecolor": "set_legend_frame_edgecolor",
        "color_scheme": "set_color_scheme",
    }

    handlers: dict[str, Callable[[Any], None]] = {
    }

    for name, setter_name in direct_map.items():
        handlers[name] = _converted_handler(gateway, setter_name)
    for name, setter_name in bool_map.items():
        if name in handlers:
            continue
        handlers[name] = _converted_handler(gateway, setter_name, bool)
    for name, setter_name in int_map.items():
        if name in handlers:
            continue
        handlers[name] = _converted_handler(gateway, setter_name, int)
    for name, setter_name in float_map.items():
        if name in handlers:
            continue
        handlers[name] = _converted_handler(gateway, setter_name, float)
    for name, setter_name in str_map.items():
        if name in handlers:
            continue
        handlers[name] = _converted_handler(gateway, setter_name, str)

    return handlers


def build_overlay_toggle_handlers(gateway: Any) -> dict[str, Callable[[bool], None]]:
    """Build dispatch table for overlay visibility toggles."""
    return {
        "show_model_curves": gateway.set_show_model_curves,
        "show_plumbotectonics_curves": gateway.set_show_plumbotectonics_curves,
        "show_paleoisochrons": gateway.set_show_paleoisochrons,
        "show_model_age_lines": gateway.set_show_model_age_lines,
        "show_growth_curves": gateway.set_show_growth_curves,
        "show_isochrons": gateway.set_show_isochrons,
    }
