"""Compatibility builder functions extracted from AppStateGateway."""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)
_UNSET = object()


def _compat_handler(
    gateway: Any,
    setter_name: str,
    converter: Callable[[Any], Any] | None = None,
) -> Callable[[Any], None]:
    """Build a set_attr compatibility handler from setter metadata."""
    setter = getattr(gateway, setter_name)
    if converter is None:
        return setter
    return lambda value, _setter=setter, _converter=converter: _setter(_converter(value))


def build_panel_style_allowed_keys() -> set[str]:
    """All accepted keys for panel style updates."""
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


def build_compat_attr_handlers(gateway: Any) -> dict[str, Callable[[Any], None]]:
    """Build compatibility dispatch table for legacy set_attr callers."""
    direct_map = {
        "control_panel_ref": "set_control_panel_ref",
        "legend_update_callback": "set_legend_update_callback",
        "fig": "set_figure",
        "canvas": "set_canvas",
        "ax": "set_axis",
        "legend_ax": "set_legend_ax",
        "current_palette": "set_current_palette",
        "group_marker_map": "set_group_marker_map",
        "annotation": "set_annotation",
        "last_2d_cols": "set_last_2d_cols",
        "recent_files": "set_recent_files",
        "line_styles": "set_line_styles",
        "saved_themes": "set_saved_themes",
        "legend_position": "set_legend_position",
        "legend_location": "set_legend_location",
        "legend_display_mode": "set_legend_display_mode",
        "hidden_groups": "set_hidden_groups",
        "legend_offset": "set_legend_offset",
        "isochron_results": "set_isochron_results",
        "plumbotectonics_group_visibility": "set_plumbotectonics_group_visibility",
        "file_path": "set_file_path",
        "sheet_name": "set_sheet_name",
        "mu_kappa_age_col": "set_mu_kappa_age_col",
        "paleoisochron_ages": "set_paleoisochron_ages",
        "paleoisochron_min_age": "set_paleoisochron_min_age",
        "paleoisochron_max_age": "set_paleoisochron_max_age",
        "model_curve_models": "set_model_curve_models",
        "overlay_artists": "set_overlay_artists",
        "marginal_axes": "set_marginal_axes",
        "overlay_curve_label_data": "set_overlay_curve_label_data",
        "paleoisochron_label_data": "set_paleoisochron_label_data",
        "plumbotectonics_label_data": "set_plumbotectonics_label_data",
        "plumbotectonics_isoage_label_data": "set_plumbotectonics_isoage_label_data",
        "pca_component_indices": "set_pca_component_indices",
        "ternary_manual_limits": "set_ternary_manual_limits",
        "isochron_label_options": "set_isochron_label_options",
        "mixing_endmembers": "set_mixing_endmembers",
        "mixing_mixtures": "set_mixing_mixtures",
        "custom_palettes": "set_custom_palettes",
        "custom_shape_sets": "set_custom_shape_sets",
        "legend_item_order": "set_legend_item_order",
        "ternary_ranges": "set_ternary_ranges",
        "kde_style": "set_kde_style",
        "marginal_kde_style": "set_marginal_kde_style",
        "ml_last_result": "set_ml_last_result",
        "ml_last_model_meta": "set_ml_last_model_meta",
        "equation_overlays": "set_equation_overlays",
        "selected_isochron_data": "set_selected_isochron_data",
        "tooltip_columns": "set_tooltip_columns",
        "selected_indices": "set_selected_indices",
        "active_subset_indices": "set_active_subset_indices",
        "selection_tool": "set_selection_tool",
        "visible_groups": "set_visible_groups",
        "custom_primary_font": "set_custom_primary_font",
        "custom_cjk_font": "set_custom_cjk_font",
        "plot_font_sizes": "set_plot_font_sizes",
        "umap_params": "set_umap_params",
        "tsne_params": "set_tsne_params",
        "pca_params": "set_pca_params",
        "robust_pca_params": "set_robust_pca_params",
        "ml_params": "set_ml_params",
        "v1v2_params": "set_v1v2_params",
        "adjust_text_force_text": "set_adjust_text_force_text",
        "adjust_text_force_static": "set_adjust_text_force_static",
        "adjust_text_expand": "set_adjust_text_expand",
        "group_cols": "_set_group_cols_compat",
        "data_cols": "_set_data_cols_compat",
        "export_image_options": "_set_export_image_options_compat",
        "isochron_error_mode": "_set_isochron_error_mode_compat",
        "isochron_sx_col": "_set_isochron_sx_col_compat",
        "isochron_sy_col": "_set_isochron_sy_col_compat",
        "isochron_rxy_col": "_set_isochron_rxy_col_compat",
        "isochron_sx_value": "_set_isochron_sx_value_compat",
        "isochron_sy_value": "_set_isochron_sy_value_compat",
        "isochron_rxy_value": "_set_isochron_rxy_value_compat",
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
        "show_kde": "set_show_kde",
        "show_marginal_kde": "set_show_marginal_kde",
        "show_equation_overlays": "set_show_equation_overlays",
        "paleo_label_refreshing": "set_paleo_label_refreshing",
        "adjust_text_in_progress": "set_adjust_text_in_progress",
        "overlay_label_refreshing": "set_overlay_label_refreshing",
        "show_model_curves": "set_show_model_curves",
        "show_plumbotectonics_curves": "set_show_plumbotectonics_curves",
        "show_paleoisochrons": "set_show_paleoisochrons",
        "show_model_age_lines": "set_show_model_age_lines",
        "show_growth_curves": "set_show_growth_curves",
        "show_isochrons": "set_show_isochrons",
        "use_real_age_for_mu_kappa": "set_use_real_age_for_mu_kappa",
        "standardize_data": "set_standardize_data",
        "ternary_auto_zoom": "set_ternary_auto_zoom",
        "ternary_manual_limits_enabled": "set_ternary_manual_limits_enabled",
        "marginal_kde_log_transform": "set_marginal_kde_compute_options",
        "show_tooltip": "set_show_tooltip",
        "preserve_import_render_mode": "set_preserve_import_render_mode",
        "selection_mode": "set_selection_mode",
        "draw_selection_ellipse": "set_draw_selection_ellipse",
        "initial_render_done": "set_initial_render_done",
        "embedding_task_running": "set_embedding_task_running",
    }
    int_map = {
        "plot_marker_size": "set_plot_marker_size",
        "plot_dpi": "set_plot_dpi",
        "legend_columns": "set_legend_columns",
        "paleoisochron_step": "set_paleoisochron_step",
        "marginal_kde_max_points": "set_marginal_kde_compute_options",
        "marginal_kde_gridsize": "set_marginal_kde_compute_options",
        "adjust_text_iter_lim": "set_adjust_text_iter_lim",
        "point_size": "set_point_size",
        "data_version": "set_data_version",
        "embedding_task_token": "set_embedding_task_token",
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
        "confidence_level": "set_confidence_level",
        "legend_nudge_step": "set_legend_nudge_step",
        "model_curve_width": "set_model_curve_width",
        "plumbotectonics_curve_width": "set_plumbotectonics_curve_width",
        "paleoisochron_width": "set_paleoisochron_width",
        "model_age_line_width": "set_model_age_line_width",
        "ternary_render_margin": "set_ternary_render_margin",
        "isochron_line_width": "set_isochron_line_width",
        "selected_isochron_line_width": "set_selected_isochron_line_width",
        "marginal_kde_top_size": "set_marginal_kde_layout",
        "marginal_kde_right_size": "set_marginal_kde_layout",
        "marginal_kde_bw_adjust": "set_marginal_kde_compute_options",
        "marginal_kde_bandwidth": "set_marginal_kde_compute_options",
        "marginal_kde_cut": "set_marginal_kde_compute_options",
        "adjust_text_time_lim": "set_adjust_text_time_lim",
    }
    str_map = {
        "algorithm": "set_algorithm",
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
        "geo_model_name": "set_geo_model_name",
        "current_plot_title": "set_current_plot_title",
        "language": "set_language_code",
        "color_scheme": "set_color_scheme",
        "plumbotectonics_variant": "set_plumbotectonics_variant",
        "ternary_limit_mode": "set_ternary_limit_mode",
        "ternary_limit_anchor": "set_ternary_limit_anchor",
        "render_mode": "set_render_mode",
        "ui_theme": "set_ui_theme",
        "marginal_kde_kernel": "set_marginal_kde_compute_options",
        "marginal_kde_auto_bandwidth_method": "set_marginal_kde_compute_options",
    }

    handlers: dict[str, Callable[[Any], None]] = {
        "last_embedding": lambda v: gateway.set_last_embedding(
            v,
            str(getattr(gateway._state, "last_embedding_type", "")),
        ),
        "last_embedding_type": lambda v: gateway.set_last_embedding(
            getattr(gateway._state, "last_embedding", None),
            str(v),
        ),
        "last_pca_variance": lambda v: gateway.set_pca_diagnostics(last_pca_variance=v),
        "last_pca_components": lambda v: gateway.set_pca_diagnostics(last_pca_components=v),
        "current_feature_names": lambda v: gateway.set_pca_diagnostics(current_feature_names=v),
        "marginal_kde_top_size": lambda v: gateway.set_marginal_kde_layout(top_size=float(v)),
        "marginal_kde_right_size": lambda v: gateway.set_marginal_kde_layout(right_size=float(v)),
        "marginal_kde_max_points": lambda v: gateway.set_marginal_kde_compute_options(max_points=int(v)),
        "marginal_kde_bw_adjust": lambda v: gateway.set_marginal_kde_compute_options(bw_adjust=float(v)),
        "marginal_kde_bandwidth": lambda v: gateway.set_marginal_kde_compute_options(
            bandwidth=None if v is None else float(v)
        ),
        "marginal_kde_gridsize": lambda v: gateway.set_marginal_kde_compute_options(gridsize=int(v)),
        "marginal_kde_cut": lambda v: gateway.set_marginal_kde_compute_options(cut=float(v)),
        "marginal_kde_log_transform": lambda v: gateway.set_marginal_kde_compute_options(log_transform=bool(v)),
        "marginal_kde_kernel": lambda v: gateway.set_marginal_kde_compute_options(kernel=str(v)),
        "marginal_kde_auto_bandwidth_method": lambda v: gateway.set_marginal_kde_compute_options(
            auto_bandwidth_method=str(v)
        ),
    }

    for name, setter_name in direct_map.items():
        handlers[name] = _compat_handler(gateway, setter_name)
    for name, setter_name in bool_map.items():
        if name in handlers:
            continue
        handlers[name] = _compat_handler(gateway, setter_name, bool)
    for name, setter_name in int_map.items():
        if name in handlers:
            continue
        handlers[name] = _compat_handler(gateway, setter_name, int)
    for name, setter_name in float_map.items():
        if name in handlers:
            continue
        handlers[name] = _compat_handler(gateway, setter_name, float)
    for name, setter_name in str_map.items():
        if name in handlers:
            continue
        handlers[name] = _compat_handler(gateway, setter_name, str)

    return handlers


def build_overlay_toggle_handlers(gateway: Any) -> dict[str, Callable[[bool], None]]:
    """Build dispatch table for overlay visibility toggle handlers."""
    return {
        "show_model_curves": gateway.set_show_model_curves,
        "show_plumbotectonics_curves": gateway.set_show_plumbotectonics_curves,
        "show_paleoisochrons": gateway.set_show_paleoisochrons,
        "show_model_age_lines": gateway.set_show_model_age_lines,
        "show_growth_curves": gateway.set_show_growth_curves,
        "show_isochrons": gateway.set_show_isochrons,
    }
