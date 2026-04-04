"""Tests for StateStore-backed gateway mutations."""

from __future__ import annotations

from typing import Any

from core import app_state, state_gateway
from visualization.plotting.core import _build_group_palette


def _snapshot_state() -> dict[str, Any]:
    return {
        "render_mode": getattr(app_state, "render_mode", "UMAP"),
        "algorithm": getattr(app_state, "algorithm", "UMAP"),
        "umap_params": dict(getattr(app_state, "umap_params", {}) or {}),
        "tsne_params": dict(getattr(app_state, "tsne_params", {}) or {}),
        "pca_params": dict(getattr(app_state, "pca_params", {}) or {}),
        "robust_pca_params": dict(getattr(app_state, "robust_pca_params", {}) or {}),
        "ml_params": dict(getattr(app_state, "ml_params", {}) or {}),
        "v1v2_params": dict(getattr(app_state, "v1v2_params", {}) or {}),
        "show_kde": bool(getattr(app_state, "show_kde", False)),
        "show_marginal_kde": bool(getattr(app_state, "show_marginal_kde", True)),
        "show_equation_overlays": bool(getattr(app_state, "show_equation_overlays", False)),
        "geo_model_name": str(getattr(app_state, "geo_model_name", "Stacey & Kramers (2nd Stage)")),
        "paleo_label_refreshing": bool(getattr(app_state, "paleo_label_refreshing", False)),
        "overlay_label_refreshing": bool(getattr(app_state, "overlay_label_refreshing", False)),
        "overlay_curve_label_data": list(getattr(app_state, "overlay_curve_label_data", []) or []),
        "paleoisochron_label_data": list(getattr(app_state, "paleoisochron_label_data", []) or []),
        "plumbotectonics_label_data": list(getattr(app_state, "plumbotectonics_label_data", []) or []),
        "plumbotectonics_isoage_label_data": list(
            getattr(app_state, "plumbotectonics_isoage_label_data", []) or []
        ),
        "overlay_artists": dict(getattr(app_state, "overlay_artists", {}) or {}),
        "last_embedding": getattr(app_state, "last_embedding", None),
        "last_embedding_type": str(getattr(app_state, "last_embedding_type", "") or ""),
        "selected_isochron_data": getattr(app_state, "selected_isochron_data", None),
        "embedding_task_token": int(getattr(app_state, "embedding_task_token", 0)),
        "embedding_task_running": bool(getattr(app_state, "embedding_task_running", False)),
        "marginal_axes": getattr(app_state, "marginal_axes", None),
        "last_pca_variance": getattr(app_state, "last_pca_variance", None),
        "last_pca_components": getattr(app_state, "last_pca_components", None),
        "current_feature_names": getattr(app_state, "current_feature_names", []),
        "adjust_text_in_progress": bool(getattr(app_state, "adjust_text_in_progress", False)),
        "confidence_level": float(getattr(app_state, "confidence_level", 0.95)),
        "current_palette": dict(getattr(app_state, "current_palette", {}) or {}),
        "group_marker_map": dict(getattr(app_state, "group_marker_map", {}) or {}),
        "current_plot_title": str(getattr(app_state, "current_plot_title", "")),
        "last_2d_cols": (
            list(getattr(app_state, "last_2d_cols", []) or [])
            if getattr(app_state, "last_2d_cols", None) is not None
            else None
        ),
        "show_model_curves": bool(getattr(app_state, "show_model_curves", True)),
        "show_plumbotectonics_curves": bool(getattr(app_state, "show_plumbotectonics_curves", True)),
        "show_paleoisochrons": bool(getattr(app_state, "show_paleoisochrons", True)),
        "show_model_age_lines": bool(getattr(app_state, "show_model_age_lines", True)),
        "show_growth_curves": bool(getattr(app_state, "show_growth_curves", True)),
        "show_isochrons": bool(getattr(app_state, "show_isochrons", False)),
        "isochron_error_mode": str(getattr(app_state, "isochron_error_mode", "fixed")),
        "isochron_sx_col": str(getattr(app_state, "isochron_sx_col", "") or ""),
        "isochron_sy_col": str(getattr(app_state, "isochron_sy_col", "") or ""),
        "isochron_rxy_col": str(getattr(app_state, "isochron_rxy_col", "") or ""),
        "isochron_sx_value": float(getattr(app_state, "isochron_sx_value", 0.001)),
        "isochron_sy_value": float(getattr(app_state, "isochron_sy_value", 0.001)),
        "isochron_rxy_value": float(getattr(app_state, "isochron_rxy_value", 0.0)),
        "isochron_results": dict(getattr(app_state, "isochron_results", {}) or {}),
        "plumbotectonics_group_visibility": dict(
            getattr(app_state, "plumbotectonics_group_visibility", {}) or {}
        ),
        "use_real_age_for_mu_kappa": bool(getattr(app_state, "use_real_age_for_mu_kappa", False)),
        "mu_kappa_age_col": getattr(app_state, "mu_kappa_age_col", None),
        "plumbotectonics_variant": str(getattr(app_state, "plumbotectonics_variant", "0")),
        "paleoisochron_step": int(getattr(app_state, "paleoisochron_step", 1000)),
        "paleoisochron_ages": list(getattr(app_state, "paleoisochron_ages", []) or []),
        "draw_selection_ellipse": bool(getattr(app_state, "draw_selection_ellipse", False)),
        "marginal_kde_top_size": float(getattr(app_state, "marginal_kde_top_size", 15.0)),
        "marginal_kde_right_size": float(getattr(app_state, "marginal_kde_right_size", 15.0)),
        "marginal_kde_max_points": int(getattr(app_state, "marginal_kde_max_points", 5000)),
        "marginal_kde_bw_adjust": float(getattr(app_state, "marginal_kde_bw_adjust", 1.0)),
        "marginal_kde_gridsize": int(getattr(app_state, "marginal_kde_gridsize", 256)),
        "marginal_kde_cut": float(getattr(app_state, "marginal_kde_cut", 1.0)),
        "marginal_kde_log_transform": bool(getattr(app_state, "marginal_kde_log_transform", False)),
        "selected_indices": set(getattr(app_state, "selected_indices", set()) or set()),
        "active_subset_indices": (
            set(getattr(app_state, "active_subset_indices", set()) or set())
            if getattr(app_state, "active_subset_indices", None) is not None
            else None
        ),
        "selection_mode": bool(getattr(app_state, "selection_mode", False)),
        "df_global": getattr(app_state, "df_global", None),
        "file_path": getattr(app_state, "file_path", None),
        "sheet_name": getattr(app_state, "sheet_name", None),
        "data_version": int(getattr(app_state, "data_version", 0)),
        "group_cols": list(getattr(app_state, "group_cols", []) or []),
        "data_cols": list(getattr(app_state, "data_cols", []) or []),
        "last_group_col": getattr(app_state, "last_group_col", None),
        "selection_tool": getattr(app_state, "selection_tool", None),
        "plot_style_grid": bool(getattr(app_state, "plot_style_grid", False)),
        "plot_marker_size": int(getattr(app_state, "plot_marker_size", 60)),
        "plot_marker_alpha": float(getattr(app_state, "plot_marker_alpha", 0.8)),
        "show_plot_title": bool(getattr(app_state, "show_plot_title", False)),
        "plot_dpi": int(getattr(app_state, "plot_dpi", 130)),
        "custom_primary_font": str(getattr(app_state, "custom_primary_font", "")),
        "custom_cjk_font": str(getattr(app_state, "custom_cjk_font", "")),
        "plot_font_sizes": dict(getattr(app_state, "plot_font_sizes", {}) or {}),
        "plot_facecolor": str(getattr(app_state, "plot_facecolor", "#ffffff")),
        "axes_facecolor": str(getattr(app_state, "axes_facecolor", "#ffffff")),
        "grid_color": str(getattr(app_state, "grid_color", "#e2e8f0")),
        "grid_linewidth": float(getattr(app_state, "grid_linewidth", 0.6)),
        "grid_alpha": float(getattr(app_state, "grid_alpha", 0.7)),
        "grid_linestyle": str(getattr(app_state, "grid_linestyle", "--")),
        "tick_direction": str(getattr(app_state, "tick_direction", "out")),
        "tick_color": str(getattr(app_state, "tick_color", "#1f2937")),
        "tick_length": float(getattr(app_state, "tick_length", 4.0)),
        "tick_width": float(getattr(app_state, "tick_width", 0.8)),
        "axis_linewidth": float(getattr(app_state, "axis_linewidth", 1.0)),
        "axis_line_color": str(getattr(app_state, "axis_line_color", "#1f2937")),
        "minor_ticks": bool(getattr(app_state, "minor_ticks", False)),
        "minor_tick_length": float(getattr(app_state, "minor_tick_length", 2.5)),
        "minor_tick_width": float(getattr(app_state, "minor_tick_width", 0.6)),
        "show_top_spine": bool(getattr(app_state, "show_top_spine", True)),
        "show_right_spine": bool(getattr(app_state, "show_right_spine", True)),
        "minor_grid": bool(getattr(app_state, "minor_grid", False)),
        "minor_grid_color": str(getattr(app_state, "minor_grid_color", "#e2e8f0")),
        "minor_grid_linewidth": float(getattr(app_state, "minor_grid_linewidth", 0.4)),
        "minor_grid_alpha": float(getattr(app_state, "minor_grid_alpha", 0.4)),
        "minor_grid_linestyle": str(getattr(app_state, "minor_grid_linestyle", ":")),
        "scatter_show_edge": bool(getattr(app_state, "scatter_show_edge", True)),
        "scatter_edgecolor": str(getattr(app_state, "scatter_edgecolor", "#1e293b")),
        "scatter_edgewidth": float(getattr(app_state, "scatter_edgewidth", 0.4)),
        "label_color": str(getattr(app_state, "label_color", "#1f2937")),
        "label_weight": str(getattr(app_state, "label_weight", "normal")),
        "label_pad": float(getattr(app_state, "label_pad", 6.0)),
        "title_color": str(getattr(app_state, "title_color", "#111827")),
        "title_weight": str(getattr(app_state, "title_weight", "bold")),
        "title_pad": float(getattr(app_state, "title_pad", 20.0)),
        "legend_frame_on": bool(getattr(app_state, "legend_frame_on", True)),
        "legend_frame_alpha": float(getattr(app_state, "legend_frame_alpha", 0.95)),
        "legend_frame_facecolor": str(getattr(app_state, "legend_frame_facecolor", "#ffffff")),
        "legend_frame_edgecolor": str(getattr(app_state, "legend_frame_edgecolor", "#cbd5f5")),
        "adjust_text_force_text": tuple(getattr(app_state, "adjust_text_force_text", (0.8, 1.0)) or (0.8, 1.0)),
        "adjust_text_force_static": tuple(getattr(app_state, "adjust_text_force_static", (0.4, 0.6)) or (0.4, 0.6)),
        "adjust_text_expand": tuple(getattr(app_state, "adjust_text_expand", (1.08, 1.20)) or (1.08, 1.20)),
        "adjust_text_iter_lim": int(getattr(app_state, "adjust_text_iter_lim", 120)),
        "adjust_text_time_lim": float(getattr(app_state, "adjust_text_time_lim", 0.25)),
        "point_size": int(getattr(app_state, "point_size", 60)),
        "show_tooltip": bool(getattr(app_state, "show_tooltip", False)),
        "tooltip_columns": list(getattr(app_state, "tooltip_columns", []) or []),
        "ui_theme": str(getattr(app_state, "ui_theme", "Modern Light")),
        "language": str(getattr(app_state, "language", "zh")),
        "color_scheme": str(getattr(app_state, "color_scheme", "vibrant")),
        "legend_position": getattr(app_state, "legend_position", None),
        "legend_location": getattr(app_state, "legend_location", "outside_left"),
        "legend_columns": int(getattr(app_state, "legend_columns", 0)),
        "legend_nudge_step": float(getattr(app_state, "legend_nudge_step", 0.02)),
        "legend_offset": tuple(getattr(app_state, "legend_offset", (0.0, 0.0)) or (0.0, 0.0)),
        "legend_last_title": getattr(app_state, "legend_last_title", None),
        "legend_last_handles": getattr(app_state, "legend_last_handles", None),
        "legend_last_labels": getattr(app_state, "legend_last_labels", None),
        "recent_files": list(getattr(app_state, "recent_files", []) or []),
        "line_styles": dict(getattr(app_state, "line_styles", {}) or {}),
        "saved_themes": dict(getattr(app_state, "saved_themes", {}) or {}),
        "custom_palettes": dict(getattr(app_state, "custom_palettes", {}) or {}),
        "custom_shape_sets": dict(getattr(app_state, "custom_shape_sets", {}) or {}),
        "legend_item_order": list(getattr(app_state, "legend_item_order", []) or []),
        "mixing_endmembers": dict(getattr(app_state, "mixing_endmembers", {}) or {}),
        "mixing_mixtures": dict(getattr(app_state, "mixing_mixtures", {}) or {}),
        "ternary_ranges": dict(getattr(app_state, "ternary_ranges", {}) or {}),
        "kde_style": dict(getattr(app_state, "kde_style", {}) or {}),
        "marginal_kde_style": dict(getattr(app_state, "marginal_kde_style", {}) or {}),
        "ml_last_result": getattr(app_state, "ml_last_result", None),
        "ml_last_model_meta": getattr(app_state, "ml_last_model_meta", None),
        "preserve_import_render_mode": bool(getattr(app_state, "preserve_import_render_mode", False)),
        "available_groups": list(getattr(app_state, "available_groups", []) or []),
        "visible_groups": list(getattr(app_state, "visible_groups", []) or []) if getattr(app_state, "visible_groups", None) else None,
        "selected_2d_cols": list(getattr(app_state, "selected_2d_cols", []) or []),
        "selected_3d_cols": list(getattr(app_state, "selected_3d_cols", []) or []),
        "selected_ternary_cols": list(getattr(app_state, "selected_ternary_cols", []) or []),
        "selected_2d_confirmed": bool(getattr(app_state, "selected_2d_confirmed", False)),
        "selected_3d_confirmed": bool(getattr(app_state, "selected_3d_confirmed", False)),
        "selected_ternary_confirmed": bool(getattr(app_state, "selected_ternary_confirmed", False)),
        "standardize_data": bool(getattr(app_state, "standardize_data", True)),
        "initial_render_done": bool(getattr(app_state, "initial_render_done", False)),
        "pca_component_indices": list(getattr(app_state, "pca_component_indices", [0, 1]) or [0, 1]),
        "ternary_auto_zoom": bool(getattr(app_state, "ternary_auto_zoom", True)),
        "ternary_limit_mode": str(getattr(app_state, "ternary_limit_mode", "min")),
        "ternary_limit_anchor": str(getattr(app_state, "ternary_limit_anchor", "min")),
        "ternary_boundary_percent": float(getattr(app_state, "ternary_boundary_percent", 5.0)),
        "ternary_manual_limits_enabled": bool(getattr(app_state, "ternary_manual_limits_enabled", False)),
        "ternary_manual_limits": dict(getattr(app_state, "ternary_manual_limits", {}) or {}),
        "ternary_stretch_mode": str(getattr(app_state, "ternary_stretch_mode", "power")),
        "ternary_stretch": bool(getattr(app_state, "ternary_stretch", False)),
        "ternary_factors": list(getattr(app_state, "ternary_factors", [1.0, 1.0, 1.0]) or [1.0, 1.0, 1.0]),
        "model_curve_width": float(getattr(app_state, "model_curve_width", 1.2)),
        "plumbotectonics_curve_width": float(getattr(app_state, "plumbotectonics_curve_width", 1.2)),
        "paleoisochron_width": float(getattr(app_state, "paleoisochron_width", 0.9)),
        "model_age_line_width": float(getattr(app_state, "model_age_line_width", 0.7)),
        "isochron_line_width": float(getattr(app_state, "isochron_line_width", 1.5)),
        "selected_isochron_line_width": float(getattr(app_state, "selected_isochron_line_width", 2.0)),
        "isochron_label_options": dict(getattr(app_state, "isochron_label_options", {}) or {}),
        "equation_overlays": list(getattr(app_state, "equation_overlays", []) or []),
        "export_image_options": dict(getattr(app_state, "export_image_options", {}) or {}),
    }


def _restore_state(snapshot: dict[str, Any]) -> None:
    state_gateway.set_algorithm(str(snapshot["algorithm"]))
    state_gateway.set_umap_params(snapshot["umap_params"])
    state_gateway.set_tsne_params(snapshot["tsne_params"])
    state_gateway.set_pca_params(snapshot["pca_params"])
    state_gateway.set_robust_pca_params(snapshot["robust_pca_params"])
    state_gateway.set_ml_params(snapshot["ml_params"])
    state_gateway.set_v1v2_params(snapshot["v1v2_params"])
    state_gateway.set_selection_mode(bool(snapshot["selection_mode"]))
    state_gateway.set_render_mode(str(snapshot["render_mode"]))
    state_gateway.set_plot_style_grid(bool(snapshot["plot_style_grid"]))
    state_gateway.set_plot_marker_size(int(snapshot["plot_marker_size"]))
    state_gateway.set_plot_marker_alpha(float(snapshot["plot_marker_alpha"]))
    state_gateway.set_show_plot_title(bool(snapshot["show_plot_title"]))
    state_gateway.set_plot_dpi(int(snapshot["plot_dpi"]))
    state_gateway.set_custom_primary_font(str(snapshot["custom_primary_font"]))
    state_gateway.set_custom_cjk_font(str(snapshot["custom_cjk_font"]))
    state_gateway.set_plot_font_sizes(snapshot["plot_font_sizes"])
    state_gateway.set_plot_facecolor(str(snapshot["plot_facecolor"]))
    state_gateway.set_axes_facecolor(str(snapshot["axes_facecolor"]))
    state_gateway.set_grid_color(str(snapshot["grid_color"]))
    state_gateway.set_grid_linewidth(float(snapshot["grid_linewidth"]))
    state_gateway.set_grid_alpha(float(snapshot["grid_alpha"]))
    state_gateway.set_grid_linestyle(str(snapshot["grid_linestyle"]))
    state_gateway.set_tick_direction(str(snapshot["tick_direction"]))
    state_gateway.set_tick_color(str(snapshot["tick_color"]))
    state_gateway.set_tick_length(float(snapshot["tick_length"]))
    state_gateway.set_tick_width(float(snapshot["tick_width"]))
    state_gateway.set_axis_linewidth(float(snapshot["axis_linewidth"]))
    state_gateway.set_axis_line_color(str(snapshot["axis_line_color"]))
    state_gateway.set_minor_ticks(bool(snapshot["minor_ticks"]))
    state_gateway.set_minor_tick_length(float(snapshot["minor_tick_length"]))
    state_gateway.set_minor_tick_width(float(snapshot["minor_tick_width"]))
    state_gateway.set_show_top_spine(bool(snapshot["show_top_spine"]))
    state_gateway.set_show_right_spine(bool(snapshot["show_right_spine"]))
    state_gateway.set_minor_grid(bool(snapshot["minor_grid"]))
    state_gateway.set_minor_grid_color(str(snapshot["minor_grid_color"]))
    state_gateway.set_minor_grid_linewidth(float(snapshot["minor_grid_linewidth"]))
    state_gateway.set_minor_grid_alpha(float(snapshot["minor_grid_alpha"]))
    state_gateway.set_minor_grid_linestyle(str(snapshot["minor_grid_linestyle"]))
    state_gateway.set_scatter_show_edge(bool(snapshot["scatter_show_edge"]))
    state_gateway.set_scatter_edgecolor(str(snapshot["scatter_edgecolor"]))
    state_gateway.set_scatter_edgewidth(float(snapshot["scatter_edgewidth"]))
    state_gateway.set_label_color(str(snapshot["label_color"]))
    state_gateway.set_label_weight(str(snapshot["label_weight"]))
    state_gateway.set_label_pad(float(snapshot["label_pad"]))
    state_gateway.set_title_color(str(snapshot["title_color"]))
    state_gateway.set_title_weight(str(snapshot["title_weight"]))
    state_gateway.set_title_pad(float(snapshot["title_pad"]))
    state_gateway.set_legend_frame_on(bool(snapshot["legend_frame_on"]))
    state_gateway.set_legend_frame_alpha(float(snapshot["legend_frame_alpha"]))
    state_gateway.set_legend_frame_facecolor(str(snapshot["legend_frame_facecolor"]))
    state_gateway.set_legend_frame_edgecolor(str(snapshot["legend_frame_edgecolor"]))
    state_gateway.set_adjust_text_force_text(snapshot["adjust_text_force_text"])
    state_gateway.set_adjust_text_force_static(snapshot["adjust_text_force_static"])
    state_gateway.set_adjust_text_expand(snapshot["adjust_text_expand"])
    state_gateway.set_adjust_text_iter_lim(int(snapshot["adjust_text_iter_lim"]))
    state_gateway.set_adjust_text_time_lim(float(snapshot["adjust_text_time_lim"]))
    state_gateway.set_point_size(int(snapshot["point_size"]))
    state_gateway.set_show_tooltip(bool(snapshot["show_tooltip"]))
    state_gateway.set_show_kde(bool(snapshot["show_kde"]))
    state_gateway.set_show_marginal_kde(bool(snapshot["show_marginal_kde"]))
    state_gateway.set_show_equation_overlays(bool(snapshot["show_equation_overlays"]))
    state_gateway.set_geo_model_name(str(snapshot["geo_model_name"]))
    state_gateway.set_paleo_label_refreshing(bool(snapshot["paleo_label_refreshing"]))
    state_gateway.set_overlay_label_refreshing(bool(snapshot["overlay_label_refreshing"]))
    state_gateway.set_overlay_curve_label_data(snapshot["overlay_curve_label_data"])
    state_gateway.set_paleoisochron_label_data(snapshot["paleoisochron_label_data"])
    state_gateway.set_plumbotectonics_label_data(snapshot["plumbotectonics_label_data"])
    state_gateway.set_plumbotectonics_isoage_label_data(snapshot["plumbotectonics_isoage_label_data"])
    state_gateway.set_overlay_artists(snapshot["overlay_artists"])
    state_gateway.set_last_embedding(snapshot["last_embedding"], snapshot["last_embedding_type"])
    state_gateway.set_selected_isochron_data(snapshot["selected_isochron_data"])
    state_gateway.set_embedding_task_token(snapshot["embedding_task_token"])
    state_gateway.set_embedding_task_running(snapshot["embedding_task_running"])
    state_gateway.set_marginal_axes(snapshot["marginal_axes"])
    state_gateway.set_pca_diagnostics(
        last_pca_variance=snapshot["last_pca_variance"],
        last_pca_components=snapshot["last_pca_components"],
        current_feature_names=snapshot["current_feature_names"],
    )
    state_gateway.set_adjust_text_in_progress(bool(snapshot["adjust_text_in_progress"]))
    state_gateway.set_confidence_level(float(snapshot["confidence_level"]))
    state_gateway.set_current_palette(snapshot["current_palette"])
    state_gateway.set_group_marker_map(snapshot["group_marker_map"])
    state_gateway.set_current_plot_title(str(snapshot["current_plot_title"]))
    state_gateway.set_last_2d_cols(snapshot["last_2d_cols"])
    state_gateway.set_show_model_curves(bool(snapshot["show_model_curves"]))
    state_gateway.set_show_plumbotectonics_curves(bool(snapshot["show_plumbotectonics_curves"]))
    state_gateway.set_show_paleoisochrons(bool(snapshot["show_paleoisochrons"]))
    state_gateway.set_show_model_age_lines(bool(snapshot["show_model_age_lines"]))
    state_gateway.set_show_growth_curves(bool(snapshot["show_growth_curves"]))
    state_gateway.set_show_isochrons(bool(snapshot["show_isochrons"]))
    state_gateway.set_isochron_error_columns(
        str(snapshot["isochron_sx_col"]),
        str(snapshot["isochron_sy_col"]),
        str(snapshot["isochron_rxy_col"]),
    )
    state_gateway.set_isochron_error_fixed(
        float(snapshot["isochron_sx_value"]),
        float(snapshot["isochron_sy_value"]),
        float(snapshot["isochron_rxy_value"]),
    )
    if str(snapshot["isochron_error_mode"]).strip().lower() == "columns":
        state_gateway.set_isochron_error_columns(
            str(snapshot["isochron_sx_col"]),
            str(snapshot["isochron_sy_col"]),
            str(snapshot["isochron_rxy_col"]),
        )
    else:
        state_gateway.set_isochron_error_fixed(
            float(snapshot["isochron_sx_value"]),
            float(snapshot["isochron_sy_value"]),
            float(snapshot["isochron_rxy_value"]),
        )
    state_gateway.set_isochron_results(snapshot["isochron_results"])
    state_gateway.set_plumbotectonics_group_visibility(snapshot["plumbotectonics_group_visibility"])
    state_gateway.set_use_real_age_for_mu_kappa(bool(snapshot["use_real_age_for_mu_kappa"]))
    state_gateway.set_mu_kappa_age_col(snapshot["mu_kappa_age_col"])
    state_gateway.set_plumbotectonics_variant(str(snapshot["plumbotectonics_variant"]))
    state_gateway.set_paleoisochron_step(int(snapshot["paleoisochron_step"]))
    state_gateway.set_paleoisochron_ages(snapshot["paleoisochron_ages"])
    state_gateway.set_draw_selection_ellipse(bool(snapshot["draw_selection_ellipse"]))
    state_gateway.set_marginal_kde_layout(
        top_size=float(snapshot["marginal_kde_top_size"]),
        right_size=float(snapshot["marginal_kde_right_size"]),
    )
    state_gateway.set_marginal_kde_compute_options(
        max_points=int(snapshot["marginal_kde_max_points"]),
        bw_adjust=float(snapshot["marginal_kde_bw_adjust"]),
        gridsize=int(snapshot["marginal_kde_gridsize"]),
        cut=float(snapshot["marginal_kde_cut"]),
        log_transform=bool(snapshot["marginal_kde_log_transform"]),
    )
    state_gateway.set_tooltip_columns(snapshot["tooltip_columns"])
    state_gateway.set_ui_theme(str(snapshot["ui_theme"]))
    state_gateway.set_language_code(str(snapshot["language"]))
    state_gateway.set_color_scheme(str(snapshot["color_scheme"]))
    state_gateway.set_legend_position(snapshot["legend_position"])
    state_gateway.set_legend_location(snapshot["legend_location"])
    state_gateway.set_legend_columns(int(snapshot["legend_columns"]))
    state_gateway.set_legend_nudge_step(float(snapshot["legend_nudge_step"]))
    state_gateway.set_legend_offset(snapshot["legend_offset"])
    state_gateway.set_legend_snapshot(
        snapshot["legend_last_title"],
        snapshot["legend_last_handles"],
        snapshot["legend_last_labels"],
    )
    state_gateway.set_recent_files(snapshot["recent_files"])
    state_gateway.set_line_styles(snapshot["line_styles"])
    state_gateway.set_saved_themes(snapshot["saved_themes"])
    state_gateway.set_custom_palettes(snapshot["custom_palettes"])
    state_gateway.set_custom_shape_sets(snapshot["custom_shape_sets"])
    state_gateway.set_legend_item_order(snapshot["legend_item_order"])
    state_gateway.set_mixing_endmembers(snapshot["mixing_endmembers"])
    state_gateway.set_mixing_mixtures(snapshot["mixing_mixtures"])
    state_gateway.set_ternary_ranges(snapshot["ternary_ranges"])
    state_gateway.set_kde_style(snapshot["kde_style"])
    state_gateway.set_marginal_kde_style(snapshot["marginal_kde_style"])
    state_gateway.set_ml_last_result(snapshot["ml_last_result"])
    state_gateway.set_ml_last_model_meta(snapshot["ml_last_model_meta"])
    state_gateway.set_preserve_import_render_mode(bool(snapshot["preserve_import_render_mode"]))
    state_gateway.set_selection_mode(snapshot["selection_mode"])
    state_gateway.set_selection_tool(snapshot["selection_tool"])
    state_gateway.set_dataframe_and_source(
        snapshot["df_global"],
        file_path=snapshot["file_path"],
        sheet_name=snapshot["sheet_name"],
    )
    state_gateway.set_data_version(snapshot["data_version"])
    state_gateway.set_group_data_columns(snapshot["group_cols"], snapshot["data_cols"])
    state_gateway.set_last_group_col(snapshot["last_group_col"])
    state_gateway.set_selected_indices(snapshot["selected_indices"])
    state_gateway.set_active_subset_indices(snapshot["active_subset_indices"])
    state_gateway.set_selected_2d_columns(snapshot["selected_2d_cols"], confirmed=snapshot["selected_2d_confirmed"])
    state_gateway.set_selected_3d_columns(snapshot["selected_3d_cols"], confirmed=snapshot["selected_3d_confirmed"])
    state_gateway.set_selected_ternary_columns(snapshot["selected_ternary_cols"], confirmed=snapshot["selected_ternary_confirmed"])
    state_gateway.set_standardize_data(snapshot["standardize_data"])
    state_gateway.set_initial_render_done(snapshot["initial_render_done"])
    state_gateway.set_pca_component_indices(snapshot["pca_component_indices"])
    state_gateway.set_ternary_auto_zoom(snapshot["ternary_auto_zoom"])
    state_gateway.set_ternary_limit_mode(snapshot["ternary_limit_mode"])
    state_gateway.set_ternary_limit_anchor(snapshot["ternary_limit_anchor"])
    state_gateway.set_ternary_boundary_percent(snapshot["ternary_boundary_percent"])
    state_gateway.set_ternary_manual_limits_enabled(snapshot["ternary_manual_limits_enabled"])
    state_gateway.set_ternary_manual_limits(snapshot["ternary_manual_limits"])
    state_gateway.set_ternary_stretch_mode(snapshot["ternary_stretch_mode"])
    state_gateway.set_ternary_stretch(snapshot["ternary_stretch"])
    state_gateway.set_ternary_factors(snapshot["ternary_factors"])
    state_gateway.set_model_curve_width(snapshot["model_curve_width"])
    state_gateway.set_plumbotectonics_curve_width(snapshot["plumbotectonics_curve_width"])
    state_gateway.set_paleoisochron_width(snapshot["paleoisochron_width"])
    state_gateway.set_model_age_line_width(snapshot["model_age_line_width"])
    state_gateway.set_isochron_line_width(snapshot["isochron_line_width"])
    state_gateway.set_selected_isochron_line_width(snapshot["selected_isochron_line_width"])
    state_gateway.set_isochron_label_options(snapshot["isochron_label_options"])
    state_gateway.set_equation_overlays(snapshot["equation_overlays"])
    state_gateway.sync_available_and_visible_groups(snapshot["available_groups"])
    state_gateway.set_visible_groups(snapshot["visible_groups"])
    state_gateway.set_export_image_options(**snapshot["export_image_options"])


def test_state_store_set_render_mode_syncs_algorithm() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_render_mode("PCA")

        assert app_state.render_mode == "PCA"
        assert app_state.algorithm == "PCA"
        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["render_mode"] == "PCA"
    finally:
        _restore_state(snapshot)


def test_state_store_plot_style_domains() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_plot_style_grid(True)
        state_gateway.set_plot_marker_size(88)
        state_gateway.set_plot_marker_alpha(0.57)
        state_gateway.set_show_plot_title(True)
        state_gateway.set_plot_dpi(180)
        state_gateway.set_custom_primary_font("Calibri")
        state_gateway.set_custom_cjk_font("SimHei")
        state_gateway.set_plot_font_sizes({"title": 18, "label": 13, "tick": 11, "legend": 12})
        state_gateway.set_plot_facecolor("#fdf6e3")
        state_gateway.set_axes_facecolor("#f8fafc")
        state_gateway.set_grid_color("#334155")
        state_gateway.set_grid_linewidth(1.2)
        state_gateway.set_grid_alpha(0.65)
        state_gateway.set_grid_linestyle(":")
        state_gateway.set_tick_direction("in")
        state_gateway.set_tick_color("#0f172a")
        state_gateway.set_tick_length(5.5)
        state_gateway.set_tick_width(1.1)
        state_gateway.set_axis_linewidth(1.4)
        state_gateway.set_axis_line_color("#111827")
        state_gateway.set_minor_ticks(True)
        state_gateway.set_minor_tick_length(3.2)
        state_gateway.set_minor_tick_width(0.9)
        state_gateway.set_show_top_spine(False)
        state_gateway.set_show_right_spine(False)
        state_gateway.set_minor_grid(True)
        state_gateway.set_minor_grid_color("#94a3b8")
        state_gateway.set_minor_grid_linewidth(0.8)
        state_gateway.set_minor_grid_alpha(0.5)
        state_gateway.set_minor_grid_linestyle("-.")
        state_gateway.set_scatter_show_edge(False)
        state_gateway.set_scatter_edgecolor("#334155")
        state_gateway.set_scatter_edgewidth(0.7)
        state_gateway.set_label_color("#1e293b")
        state_gateway.set_label_weight("bold")
        state_gateway.set_label_pad(10.0)
        state_gateway.set_title_color("#0f172a")
        state_gateway.set_title_weight("normal")
        state_gateway.set_title_pad(24.0)
        state_gateway.set_legend_frame_on(False)
        state_gateway.set_legend_frame_alpha(0.7)
        state_gateway.set_legend_frame_facecolor("#f8fafc")
        state_gateway.set_legend_frame_edgecolor("#94a3b8")
        state_gateway.set_adjust_text_force_text((1.2, 1.4))
        state_gateway.set_adjust_text_force_static((0.7, 0.9))
        state_gateway.set_adjust_text_expand((1.3, 1.5))
        state_gateway.set_adjust_text_iter_lim(240)
        state_gateway.set_adjust_text_time_lim(0.75)

        assert app_state.plot_style_grid is True
        assert app_state.plot_marker_size == 88
        assert app_state.plot_marker_alpha == 0.57
        assert app_state.show_plot_title is True
        assert app_state.plot_dpi == 180
        assert app_state.custom_primary_font == "Calibri"
        assert app_state.custom_cjk_font == "SimHei"
        assert app_state.plot_font_sizes == {
            "title": 18,
            "label": 13,
            "tick": 11,
            "legend": 12,
        }
        assert app_state.plot_facecolor == "#fdf6e3"
        assert app_state.axes_facecolor == "#f8fafc"
        assert app_state.grid_color == "#334155"
        assert app_state.grid_linewidth == 1.2
        assert app_state.grid_alpha == 0.65
        assert app_state.grid_linestyle == ":"
        assert app_state.tick_direction == "in"
        assert app_state.tick_color == "#0f172a"
        assert app_state.tick_length == 5.5
        assert app_state.tick_width == 1.1
        assert app_state.axis_linewidth == 1.4
        assert app_state.axis_line_color == "#111827"
        assert app_state.minor_ticks is True
        assert app_state.minor_tick_length == 3.2
        assert app_state.minor_tick_width == 0.9
        assert app_state.show_top_spine is False
        assert app_state.show_right_spine is False
        assert app_state.minor_grid is True
        assert app_state.minor_grid_color == "#94a3b8"
        assert app_state.minor_grid_linewidth == 0.8
        assert app_state.minor_grid_alpha == 0.5
        assert app_state.minor_grid_linestyle == "-."
        assert app_state.scatter_show_edge is False
        assert app_state.scatter_edgecolor == "#334155"
        assert app_state.scatter_edgewidth == 0.7
        assert app_state.label_color == "#1e293b"
        assert app_state.label_weight == "bold"
        assert app_state.label_pad == 10.0
        assert app_state.title_color == "#0f172a"
        assert app_state.title_weight == "normal"
        assert app_state.title_pad == 24.0
        assert app_state.legend_frame_on is False
        assert app_state.legend_frame_alpha == 0.7
        assert app_state.legend_frame_facecolor == "#f8fafc"
        assert app_state.legend_frame_edgecolor == "#94a3b8"
        assert app_state.adjust_text_force_text == (1.2, 1.4)
        assert app_state.adjust_text_force_static == (0.7, 0.9)
        assert app_state.adjust_text_expand == (1.3, 1.5)
        assert app_state.adjust_text_iter_lim == 240
        assert app_state.adjust_text_time_lim == 0.75

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["plot_style_grid"] is True
        assert store_snapshot["plot_marker_size"] == 88
        assert store_snapshot["plot_marker_alpha"] == 0.57
        assert store_snapshot["show_plot_title"] is True
        assert store_snapshot["plot_dpi"] == 180
        assert store_snapshot["custom_primary_font"] == "Calibri"
        assert store_snapshot["custom_cjk_font"] == "SimHei"
        assert store_snapshot["plot_font_sizes"] == {
            "title": 18,
            "label": 13,
            "tick": 11,
            "legend": 12,
        }
        assert store_snapshot["plot_facecolor"] == "#fdf6e3"
        assert store_snapshot["axes_facecolor"] == "#f8fafc"
        assert store_snapshot["grid_color"] == "#334155"
        assert store_snapshot["grid_linewidth"] == 1.2
        assert store_snapshot["grid_alpha"] == 0.65
        assert store_snapshot["grid_linestyle"] == ":"
        assert store_snapshot["tick_direction"] == "in"
        assert store_snapshot["tick_color"] == "#0f172a"
        assert store_snapshot["tick_length"] == 5.5
        assert store_snapshot["tick_width"] == 1.1
        assert store_snapshot["axis_linewidth"] == 1.4
        assert store_snapshot["axis_line_color"] == "#111827"
        assert store_snapshot["minor_ticks"] is True
        assert store_snapshot["minor_tick_length"] == 3.2
        assert store_snapshot["minor_tick_width"] == 0.9
        assert store_snapshot["show_top_spine"] is False
        assert store_snapshot["show_right_spine"] is False
        assert store_snapshot["minor_grid"] is True
        assert store_snapshot["minor_grid_color"] == "#94a3b8"
        assert store_snapshot["minor_grid_linewidth"] == 0.8
        assert store_snapshot["minor_grid_alpha"] == 0.5
        assert store_snapshot["minor_grid_linestyle"] == "-."
        assert store_snapshot["scatter_show_edge"] is False
        assert store_snapshot["scatter_edgecolor"] == "#334155"
        assert store_snapshot["scatter_edgewidth"] == 0.7
        assert store_snapshot["label_color"] == "#1e293b"
        assert store_snapshot["label_weight"] == "bold"
        assert store_snapshot["label_pad"] == 10.0
        assert store_snapshot["title_color"] == "#0f172a"
        assert store_snapshot["title_weight"] == "normal"
        assert store_snapshot["title_pad"] == 24.0
        assert store_snapshot["legend_frame_on"] is False
        assert store_snapshot["legend_frame_alpha"] == 0.7
        assert store_snapshot["legend_frame_facecolor"] == "#f8fafc"
        assert store_snapshot["legend_frame_edgecolor"] == "#94a3b8"
        assert store_snapshot["adjust_text_force_text"] == (1.2, 1.4)
        assert store_snapshot["adjust_text_force_static"] == (0.7, 0.9)
        assert store_snapshot["adjust_text_expand"] == (1.3, 1.5)
        assert store_snapshot["adjust_text_iter_lim"] == 240
        assert store_snapshot["adjust_text_time_lim"] == 0.75
    finally:
        _restore_state(snapshot)


def test_state_store_active_subset_indices_domain() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_active_subset_indices([3, 1, 1, 2])

        assert app_state.active_subset_indices == {1, 2, 3}
        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["active_subset_indices"] == {1, 2, 3}

        state_gateway.set_active_subset_indices(None)
        assert app_state.active_subset_indices is None
        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["active_subset_indices"] is None
    finally:
        _restore_state(snapshot)


def test_compatibility_views_dispatch_to_state_store() -> None:
    snapshot = _snapshot_state()
    original_df_global = getattr(app_state, "df_global", None)
    try:
        state_gateway.set_render_mode("2D")
        app_state.data_state.active_subset_indices = [9, 7, 7]
        app_state.data_state.group_cols = ["G1"]
        app_state.data_state.data_cols = ["X", "Y"]
        app_state.data_state.df_global = original_df_global
        app_state.algorithm_state.algorithm = "PCA"
        app_state.algorithm_state.umap_params = {"n_neighbors": 27, "min_dist": 0.4}
        app_state.algorithm_state.tsne_params = {"perplexity": 33, "learning_rate": 110}
        app_state.algorithm_state.pca_params = {"n_components": 3, "random_state": 11}
        app_state.algorithm_state.robust_pca_params = {
            "n_components": 3,
            "random_state": 11,
            "support_fraction": 0.8,
        }
        app_state.algorithm_state.ml_params = {
            "xgb_params": {"n_estimators": 120, "max_depth": 4},
            "smote_sampling_strategy": 0.9,
        }
        app_state.algorithm_state.v1v2_params = {
            "a": 0.1,
            "b": 2.1,
            "c": -6.0,
            "scale": 1.2,
        }
        app_state.style_state.current_palette = {"G1": "#112233"}
        app_state.style_state.color_scheme = "vibrant"
        app_state.style_state.custom_primary_font = "Calibri"
        app_state.style_state.custom_cjk_font = "SimHei"
        app_state.style_state.plot_font_sizes = {
            "title": 18,
            "label": 13,
            "tick": 11,
            "legend": 12,
        }
        app_state.interaction_state.selection_tool = "lasso"
        app_state.interaction_state.selected_indices = {1, 4}

        assert app_state.active_subset_indices == {7, 9}
        assert app_state.group_cols == ["G1"]
        assert app_state.data_cols == ["X", "Y"]
        assert app_state.algorithm == "PCA"
        assert app_state.umap_params == {"n_neighbors": 27, "min_dist": 0.4}
        assert app_state.tsne_params == {"perplexity": 33, "learning_rate": 110}
        assert app_state.pca_params == {"n_components": 3, "random_state": 11}
        assert app_state.robust_pca_params == {
            "n_components": 3,
            "random_state": 11,
            "support_fraction": 0.8,
        }
        assert app_state.ml_params == {
            "xgb_params": {"n_estimators": 120, "max_depth": 4},
            "smote_sampling_strategy": 0.9,
        }
        assert app_state.v1v2_params == {
            "a": 0.1,
            "b": 2.1,
            "c": -6.0,
            "scale": 1.2,
        }
        assert app_state.current_palette == {"G1": "#112233"}
        assert app_state.custom_primary_font == "Calibri"
        assert app_state.custom_cjk_font == "SimHei"
        assert app_state.plot_font_sizes == {
            "title": 18,
            "label": 13,
            "tick": 11,
            "legend": 12,
        }
        assert app_state.selection_tool == "lasso"
        assert app_state.selected_indices == {1, 4}

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["active_subset_indices"] == {7, 9}
        assert store_snapshot["group_cols"] == ["G1"]
        assert store_snapshot["data_cols"] == ["X", "Y"]
        assert store_snapshot["algorithm"] == "PCA"
        assert store_snapshot["umap_params"] == {"n_neighbors": 27, "min_dist": 0.4}
        assert store_snapshot["tsne_params"] == {"perplexity": 33, "learning_rate": 110}
        assert store_snapshot["pca_params"] == {"n_components": 3, "random_state": 11}
        assert store_snapshot["robust_pca_params"] == {
            "n_components": 3,
            "random_state": 11,
            "support_fraction": 0.8,
        }
        assert store_snapshot["ml_params"] == {
            "xgb_params": {"n_estimators": 120, "max_depth": 4},
            "smote_sampling_strategy": 0.9,
        }
        assert store_snapshot["v1v2_params"] == {
            "a": 0.1,
            "b": 2.1,
            "c": -6.0,
            "scale": 1.2,
        }
        assert store_snapshot["current_palette"] == {"G1": "#112233"}
        assert store_snapshot["custom_primary_font"] == "Calibri"
        assert store_snapshot["custom_cjk_font"] == "SimHei"
        assert store_snapshot["plot_font_sizes"] == {
            "title": 18,
            "label": 13,
            "tick": 11,
            "legend": 12,
        }
        assert store_snapshot["selection_tool"] == "lasso"
        assert store_snapshot["selected_indices"] == {1, 4}
    finally:
        _restore_state(snapshot)


def test_app_state_legend_property_setters_dispatch_to_state_store() -> None:
    snapshot = _snapshot_state()
    try:
        setattr(app_state, "legend_position", "upper left")
        setattr(app_state, "legend_columns", 2)
        setattr(app_state, "legend_offset", (0.1, -0.05))
        setattr(app_state, "legend_nudge_step", 0.03)
        setattr(app_state, "legend_location", "outside_right")
        setattr(app_state, "legend_frame_on", False)
        setattr(app_state, "legend_frame_alpha", 0.66)
        setattr(app_state, "legend_frame_facecolor", "#f8fafc")
        setattr(app_state, "legend_frame_edgecolor", "#94a3b8")

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["legend_position"] == "upper left"
        assert store_snapshot["legend_columns"] == 2
        assert store_snapshot["legend_offset"] == (0.1, -0.05)
        assert store_snapshot["legend_nudge_step"] == 0.03
        assert store_snapshot["legend_location"] == "outside_right"
        assert store_snapshot["legend_frame_on"] is False
        assert store_snapshot["legend_frame_alpha"] == 0.66
        assert store_snapshot["legend_frame_facecolor"] == "#f8fafc"
        assert store_snapshot["legend_frame_edgecolor"] == "#94a3b8"
    finally:
        _restore_state(snapshot)


def test_build_group_palette_syncs_state_store_snapshot() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_current_palette({})

        palette = _build_group_palette(["A", "B"])

        assert "A" in palette
        assert "B" in palette
        assert app_state.current_palette.get("A") == palette["A"]
        assert app_state.current_palette.get("B") == palette["B"]

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["current_palette"].get("A") == palette["A"]
        assert store_snapshot["current_palette"].get("B") == palette["B"]
    finally:
        _restore_state(snapshot)


def test_state_store_overlay_label_domains() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_overlay_curve_label_data([{"text": "A"}])
        state_gateway.set_paleoisochron_label_data([{"text": "B"}])
        state_gateway.set_plumbotectonics_label_data([{"text": "C"}])
        state_gateway.set_plumbotectonics_isoage_label_data([{"text": "D"}])

        assert app_state.overlay_curve_label_data == [{"text": "A"}]
        assert app_state.paleoisochron_label_data == [{"text": "B"}]
        assert app_state.plumbotectonics_label_data == [{"text": "C"}]
        assert app_state.plumbotectonics_isoage_label_data == [{"text": "D"}]

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["overlay_curve_label_data"] == [{"text": "A"}]
        assert store_snapshot["paleoisochron_label_data"] == [{"text": "B"}]
        assert store_snapshot["plumbotectonics_label_data"] == [{"text": "C"}]
        assert store_snapshot["plumbotectonics_isoage_label_data"] == [{"text": "D"}]
    finally:
        _restore_state(snapshot)


def test_state_store_overlay_artists_and_marginal_axes_domains() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_overlay_artists({"curves": ["a1", "a2"]})
        state_gateway.set_marginal_axes(("ax_top", "ax_right"))

        assert app_state.overlay_artists == {"curves": ["a1", "a2"]}
        assert app_state.marginal_axes == ("ax_top", "ax_right")

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["overlay_artists"] == {"curves": ["a1", "a2"]}
        assert store_snapshot["marginal_axes"] == ("ax_top", "ax_right")
    finally:
        _restore_state(snapshot)


def test_state_store_embedding_and_selected_isochron_domains() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_last_embedding([[1.0, 2.0], [3.0, 4.0]], "PCA")
        state_gateway.set_selected_isochron_data({"group": "A", "mswd": 1.2})

        assert app_state.last_embedding == [[1.0, 2.0], [3.0, 4.0]]
        assert app_state.last_embedding_type == "PCA"
        assert app_state.selected_isochron_data == {"group": "A", "mswd": 1.2}

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["last_embedding"] == [[1.0, 2.0], [3.0, 4.0]]
        assert store_snapshot["last_embedding_type"] == "PCA"
        assert store_snapshot["selected_isochron_data"] == {"group": "A", "mswd": 1.2}
    finally:
        _restore_state(snapshot)


def test_state_store_embedding_task_state_domains() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_embedding_task_token(42)
        state_gateway.set_embedding_task_running(True)

        assert app_state.embedding_task_token == 42
        assert app_state.embedding_task_running is True

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["embedding_task_token"] == 42
        assert store_snapshot["embedding_task_running"] is True
    finally:
        _restore_state(snapshot)


def test_state_store_pca_diagnostics_and_legend_snapshot_domains() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_pca_diagnostics(
            last_pca_variance=[0.61, 0.39],
            last_pca_components=[[1.0, 0.0], [0.0, 1.0]],
            current_feature_names=["x", "y"],
        )
        state_gateway.set_legend_snapshot("Group", ["h1", "h2"], ["A", "B"])

        assert app_state.last_pca_variance == [0.61, 0.39]
        assert app_state.last_pca_components == [[1.0, 0.0], [0.0, 1.0]]
        assert app_state.current_feature_names == ["x", "y"]
        assert app_state.legend_last_title == "Group"
        assert app_state.legend_last_handles == ["h1", "h2"]
        assert app_state.legend_last_labels == ["A", "B"]

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["last_pca_variance"] == [0.61, 0.39]
        assert store_snapshot["last_pca_components"] == [[1.0, 0.0], [0.0, 1.0]]
        assert store_snapshot["current_feature_names"] == ["x", "y"]
        assert store_snapshot["legend_last_title"] == "Group"
        assert store_snapshot["legend_last_handles"] == ["h1", "h2"]
        assert store_snapshot["legend_last_labels"] == ["A", "B"]
    finally:
        _restore_state(snapshot)


def test_state_store_session_preference_domains() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_render_mode("2D")
        state_gateway.set_algorithm("RobustPCA")
        state_gateway.set_point_size(88)
        state_gateway.set_tooltip_columns(["Lab No.", "Period"])
        state_gateway.set_ui_theme("Modern Light")
        state_gateway.set_language_code("en")
        state_gateway.set_color_scheme("vibrant")
        state_gateway.set_legend_position("upper right")
        state_gateway.set_legend_location("outside_right")
        state_gateway.set_legend_columns(3)
        state_gateway.set_legend_nudge_step(0.125)
        state_gateway.set_legend_offset((0.2, -0.1))
        state_gateway.set_recent_files(["d:/tmp/a.xlsx", "d:/tmp/b.csv"])
        state_gateway.set_line_styles({"model_curve": {"linewidth": 2.2, "alpha": 0.5}})
        state_gateway.set_saved_themes({"my_theme": {"color_scheme": "vibrant"}})
        state_gateway.set_custom_palettes({"my_palette": ["#112233", "#445566"]})
        state_gateway.set_custom_shape_sets({"my_shapes": ["o", "s", "^"]})
        state_gateway.set_legend_item_order(["A", "B", "C"])
        state_gateway.set_mixing_endmembers({"EM1": [1, 2, 3]})
        state_gateway.set_mixing_mixtures({"M1": [4, 5]})
        state_gateway.set_ternary_ranges({"tmin": 0.1, "tmax": 0.9})
        state_gateway.set_kde_style({"alpha": 0.5, "linewidth": 1.7, "fill": False, "levels": 8})
        state_gateway.set_marginal_kde_style(
            {
                "alpha": 0.22,
                "linewidth": 1.3,
                "fill": True,
                "bw_adjust": 1.4,
                "gridsize": 320,
                "cut": 0.7,
                "log_transform": True,
            }
        )
        state_gateway.set_ml_last_result({"status": "ok", "score": 0.93})
        state_gateway.set_ml_last_model_meta({"model": "xgb", "classes": 4})
        state_gateway.set_geo_model_name("V1V2 (Zhu 1993)")
        state_gateway.set_paleo_label_refreshing(True)
        state_gateway.set_overlay_label_refreshing(True)
        state_gateway.set_adjust_text_in_progress(True)
        state_gateway.set_confidence_level(0.91)
        state_gateway.set_current_palette({"A": "#112233", "B": "#445566"})
        state_gateway.set_group_marker_map({"A": "o", "B": "s"})
        state_gateway.set_current_plot_title("Batch 64 demo")
        state_gateway.set_last_2d_cols(["x", "y"])
        state_gateway.set_show_model_curves(False)
        state_gateway.set_show_plumbotectonics_curves(False)
        state_gateway.set_show_paleoisochrons(False)
        state_gateway.set_show_model_age_lines(False)
        state_gateway.set_show_growth_curves(False)
        state_gateway.set_show_isochrons(True)
        state_gateway.set_isochron_results({"A": {"mswd": 1.2}})
        state_gateway.set_plumbotectonics_group_visibility({"A": True, "B": False})
        state_gateway.set_use_real_age_for_mu_kappa(True)
        state_gateway.set_mu_kappa_age_col("Age_Ma")
        state_gateway.set_plumbotectonics_variant("2")
        state_gateway.set_paleoisochron_step(250)
        state_gateway.set_paleoisochron_ages([1000, 750, 500, 250])
        state_gateway.set_draw_selection_ellipse(True)
        state_gateway.set_standardize_data(False)
        state_gateway.set_initial_render_done(True)
        state_gateway.set_pca_component_indices([2, 4])
        state_gateway.set_ternary_auto_zoom(False)
        state_gateway.set_ternary_limit_mode("both")
        state_gateway.set_ternary_limit_anchor("max")
        state_gateway.set_ternary_boundary_percent(12.5)
        state_gateway.set_ternary_manual_limits_enabled(True)
        state_gateway.set_ternary_manual_limits({"tmin": 0.2, "tmax": 0.8, "lmin": 0.1, "lmax": 0.9})
        state_gateway.set_ternary_stretch_mode("hybrid")
        state_gateway.set_ternary_stretch(True)
        state_gateway.set_ternary_factors([1.1, 1.2, 0.9])
        state_gateway.set_model_curve_width(2.4)
        state_gateway.set_plumbotectonics_curve_width(2.2)
        state_gateway.set_paleoisochron_width(1.1)
        state_gateway.set_model_age_line_width(0.95)
        state_gateway.set_isochron_line_width(2.0)
        state_gateway.set_selected_isochron_line_width(2.8)
        state_gateway.set_isochron_label_options({"show_age": True, "show_mswd": True, "show_r_squared": False})
        state_gateway.set_equation_overlays(
            [
                {
                    "id": "eq_custom_1",
                    "label": "y=x",
                    "latex": "y=x",
                    "expression": "x",
                    "enabled": True,
                }
            ]
        )
        state_gateway.set_preserve_import_render_mode(True)

        assert app_state.algorithm == "RobustPCA"
        assert app_state.point_size == 88
        assert app_state.tooltip_columns == ["Lab No.", "Period"]
        assert app_state.ui_theme == "Modern Light"
        assert app_state.language == "en"
        assert app_state.color_scheme == "vibrant"
        assert app_state.legend_position == "upper right"
        assert app_state.legend_location == "outside_right"
        assert app_state.legend_columns == 3
        assert app_state.legend_nudge_step == 0.125
        assert app_state.legend_offset == (0.2, -0.1)
        assert app_state.recent_files == ["d:/tmp/a.xlsx", "d:/tmp/b.csv"]
        assert app_state.line_styles["model_curve"]["linewidth"] == 2.2
        assert app_state.saved_themes["my_theme"]["color_scheme"] == "vibrant"
        assert app_state.custom_palettes["my_palette"] == ["#112233", "#445566"]
        assert app_state.custom_shape_sets["my_shapes"] == ["o", "s", "^"]
        assert app_state.legend_item_order == ["A", "B", "C"]
        assert app_state.mixing_endmembers == {"EM1": [1, 2, 3]}
        assert app_state.mixing_mixtures == {"M1": [4, 5]}
        assert app_state.ternary_ranges == {"tmin": 0.1, "tmax": 0.9}
        assert app_state.kde_style["alpha"] == 0.5
        assert app_state.marginal_kde_style["gridsize"] == 320
        assert app_state.ml_last_result == {"status": "ok", "score": 0.93}
        assert app_state.ml_last_model_meta == {"model": "xgb", "classes": 4}
        assert app_state.geo_model_name == "V1V2 (Zhu 1993)"
        assert app_state.paleo_label_refreshing is True
        assert app_state.overlay_label_refreshing is True
        assert app_state.adjust_text_in_progress is True
        assert app_state.confidence_level == 0.91
        assert app_state.current_palette == {"A": "#112233", "B": "#445566"}
        assert app_state.group_marker_map == {"A": "o", "B": "s"}
        assert app_state.current_plot_title == "Batch 64 demo"
        assert app_state.last_2d_cols == ["x", "y"]
        assert app_state.show_model_curves is False
        assert app_state.show_plumbotectonics_curves is False
        assert app_state.show_paleoisochrons is False
        assert app_state.show_model_age_lines is False
        assert app_state.show_growth_curves is False
        assert app_state.show_isochrons is True
        assert app_state.isochron_results == {"A": {"mswd": 1.2}}
        assert app_state.plumbotectonics_group_visibility == {"A": True, "B": False}
        assert app_state.use_real_age_for_mu_kappa is True
        assert app_state.mu_kappa_age_col == "Age_Ma"
        assert app_state.plumbotectonics_variant == "2"
        assert app_state.paleoisochron_step == 250
        assert app_state.paleoisochron_ages == [1000, 750, 500, 250]
        assert app_state.draw_selection_ellipse is True
        assert app_state.standardize_data is False
        assert app_state.initial_render_done is True
        assert app_state.pca_component_indices == [2, 4]
        assert app_state.ternary_auto_zoom is False
        assert app_state.ternary_limit_mode == "both"
        assert app_state.ternary_limit_anchor == "max"
        assert app_state.ternary_boundary_percent == 12.5
        assert app_state.ternary_manual_limits_enabled is True
        assert app_state.ternary_manual_limits["tmin"] == 0.2
        assert app_state.ternary_stretch_mode == "hybrid"
        assert app_state.ternary_stretch is True
        assert app_state.ternary_factors == [1.1, 1.2, 0.9]
        assert app_state.model_curve_width == 2.4
        assert app_state.plumbotectonics_curve_width == 2.2
        assert app_state.paleoisochron_width == 1.1
        assert app_state.model_age_line_width == 0.95
        assert app_state.isochron_line_width == 2.0
        assert app_state.selected_isochron_line_width == 2.8
        assert app_state.isochron_label_options["show_mswd"] is True
        assert app_state.equation_overlays and app_state.equation_overlays[0]["id"] == "eq_custom_1"
        assert app_state.preserve_import_render_mode is True

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["algorithm"] == "RobustPCA"
        assert store_snapshot["point_size"] == 88
        assert store_snapshot["tooltip_columns"] == ["Lab No.", "Period"]
        assert store_snapshot["ui_theme"] == "Modern Light"
        assert store_snapshot["language"] == "en"
        assert store_snapshot["color_scheme"] == "vibrant"
        assert store_snapshot["legend_position"] == "upper right"
        assert store_snapshot["legend_location"] == "outside_right"
        assert store_snapshot["legend_columns"] == 3
        assert store_snapshot["legend_nudge_step"] == 0.125
        assert store_snapshot["legend_offset"] == (0.2, -0.1)
        assert store_snapshot["recent_files"] == ["d:/tmp/a.xlsx", "d:/tmp/b.csv"]
        assert store_snapshot["line_styles"]["model_curve"]["linewidth"] == 2.2
        assert store_snapshot["saved_themes"]["my_theme"]["color_scheme"] == "vibrant"
        assert store_snapshot["custom_palettes"]["my_palette"] == ["#112233", "#445566"]
        assert store_snapshot["custom_shape_sets"]["my_shapes"] == ["o", "s", "^"]
        assert store_snapshot["legend_item_order"] == ["A", "B", "C"]
        assert store_snapshot["mixing_endmembers"] == {"EM1": [1, 2, 3]}
        assert store_snapshot["mixing_mixtures"] == {"M1": [4, 5]}
        assert store_snapshot["ternary_ranges"] == {"tmin": 0.1, "tmax": 0.9}
        assert store_snapshot["kde_style"]["alpha"] == 0.5
        assert store_snapshot["marginal_kde_style"]["gridsize"] == 320
        assert store_snapshot["ml_last_result"] == {"status": "ok", "score": 0.93}
        assert store_snapshot["ml_last_model_meta"] == {"model": "xgb", "classes": 4}
        assert store_snapshot["geo_model_name"] == "V1V2 (Zhu 1993)"
        assert store_snapshot["paleo_label_refreshing"] is True
        assert store_snapshot["overlay_label_refreshing"] is True
        assert store_snapshot["adjust_text_in_progress"] is True
        assert store_snapshot["confidence_level"] == 0.91
        assert store_snapshot["current_palette"] == {"A": "#112233", "B": "#445566"}
        assert store_snapshot["group_marker_map"] == {"A": "o", "B": "s"}
        assert store_snapshot["current_plot_title"] == "Batch 64 demo"
        assert store_snapshot["last_2d_cols"] == ["x", "y"]
        assert store_snapshot["show_model_curves"] is False
        assert store_snapshot["show_plumbotectonics_curves"] is False
        assert store_snapshot["show_paleoisochrons"] is False
        assert store_snapshot["show_model_age_lines"] is False
        assert store_snapshot["show_growth_curves"] is False
        assert store_snapshot["show_isochrons"] is True
        assert store_snapshot["isochron_results"] == {"A": {"mswd": 1.2}}
        assert store_snapshot["plumbotectonics_group_visibility"] == {"A": True, "B": False}
        assert store_snapshot["use_real_age_for_mu_kappa"] is True
        assert store_snapshot["mu_kappa_age_col"] == "Age_Ma"
        assert store_snapshot["plumbotectonics_variant"] == "2"
        assert store_snapshot["paleoisochron_step"] == 250
        assert store_snapshot["paleoisochron_ages"] == [1000, 750, 500, 250]
        assert store_snapshot["draw_selection_ellipse"] is True
        assert store_snapshot["standardize_data"] is False
        assert store_snapshot["initial_render_done"] is True
        assert store_snapshot["pca_component_indices"] == [2, 4]
        assert store_snapshot["ternary_auto_zoom"] is False
        assert store_snapshot["ternary_limit_mode"] == "both"
        assert store_snapshot["ternary_limit_anchor"] == "max"
        assert store_snapshot["ternary_boundary_percent"] == 12.5
        assert store_snapshot["ternary_manual_limits_enabled"] is True
        assert store_snapshot["ternary_manual_limits"]["tmin"] == 0.2
        assert store_snapshot["ternary_stretch_mode"] == "hybrid"
        assert store_snapshot["ternary_stretch"] is True
        assert store_snapshot["ternary_factors"] == [1.1, 1.2, 0.9]
        assert store_snapshot["model_curve_width"] == 2.4
        assert store_snapshot["plumbotectonics_curve_width"] == 2.2
        assert store_snapshot["paleoisochron_width"] == 1.1
        assert store_snapshot["model_age_line_width"] == 0.95
        assert store_snapshot["isochron_line_width"] == 2.0
        assert store_snapshot["selected_isochron_line_width"] == 2.8
        assert store_snapshot["isochron_label_options"]["show_mswd"] is True
        assert store_snapshot["equation_overlays"] and store_snapshot["equation_overlays"][0]["id"] == "eq_custom_1"
        assert store_snapshot["preserve_import_render_mode"] is True
    finally:
        _restore_state(snapshot)


def test_state_store_kde_domains() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_show_kde(True)
        state_gateway.set_show_marginal_kde(False)
        state_gateway.set_marginal_kde_layout(top_size=99.0, right_size=2.0)
        state_gateway.set_marginal_kde_compute_options(
            max_points=100000,
            bw_adjust=0.001,
            gridsize=2000,
            cut=-1.0,
            log_transform=True,
        )

        assert app_state.show_kde is True
        assert app_state.show_marginal_kde is False
        assert app_state.marginal_kde_top_size == 40.0
        assert app_state.marginal_kde_right_size == 5.0
        assert app_state.marginal_kde_max_points == 50000
        assert app_state.marginal_kde_bw_adjust == 0.05
        assert app_state.marginal_kde_gridsize == 1024
        assert app_state.marginal_kde_cut == 0.0
        assert app_state.marginal_kde_log_transform is True

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["show_kde"] is True
        assert store_snapshot["show_marginal_kde"] is False
        assert store_snapshot["marginal_kde_top_size"] == 40.0
        assert store_snapshot["marginal_kde_right_size"] == 5.0
        assert store_snapshot["marginal_kde_max_points"] == 50000
        assert store_snapshot["marginal_kde_bw_adjust"] == 0.05
        assert store_snapshot["marginal_kde_gridsize"] == 1024
        assert store_snapshot["marginal_kde_cut"] == 0.0
        assert store_snapshot["marginal_kde_log_transform"] is True
    finally:
        _restore_state(snapshot)


def test_state_store_equation_overlay_domain() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_show_equation_overlays(True)
        assert app_state.show_equation_overlays is True
        assert app_state.state_store.snapshot()["show_equation_overlays"] is True

        state_gateway.set_show_equation_overlays(False)
        assert app_state.show_equation_overlays is False
        assert app_state.state_store.snapshot()["show_equation_overlays"] is False
    finally:
        _restore_state(snapshot)


def test_state_store_geochem_overlay_visibility_domains() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_show_model_curves(False)
        state_gateway.set_show_plumbotectonics_curves(False)
        state_gateway.set_show_paleoisochrons(False)
        state_gateway.set_show_model_age_lines(False)
        state_gateway.set_show_growth_curves(False)
        state_gateway.set_show_isochrons(True)

        assert app_state.show_model_curves is False
        assert app_state.show_plumbotectonics_curves is False
        assert app_state.show_paleoisochrons is False
        assert app_state.show_model_age_lines is False
        assert app_state.show_growth_curves is False
        assert app_state.show_isochrons is True

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["show_model_curves"] is False
        assert store_snapshot["show_plumbotectonics_curves"] is False
        assert store_snapshot["show_paleoisochrons"] is False
        assert store_snapshot["show_model_age_lines"] is False
        assert store_snapshot["show_growth_curves"] is False
        assert store_snapshot["show_isochrons"] is True
    finally:
        _restore_state(snapshot)


def test_state_store_isochron_error_config_domains() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_isochron_error_columns("sx", "sy", "rxy")

        assert app_state.isochron_error_mode == "columns"
        assert app_state.isochron_sx_col == "sx"
        assert app_state.isochron_sy_col == "sy"
        assert app_state.isochron_rxy_col == "rxy"

        columns_snapshot = app_state.state_store.snapshot()
        assert columns_snapshot["isochron_error_mode"] == "columns"
        assert columns_snapshot["isochron_sx_col"] == "sx"
        assert columns_snapshot["isochron_sy_col"] == "sy"
        assert columns_snapshot["isochron_rxy_col"] == "rxy"

        state_gateway.set_isochron_error_fixed(0.01, 0.02, 0.3)

        assert app_state.isochron_error_mode == "fixed"
        assert app_state.isochron_sx_value == 0.01
        assert app_state.isochron_sy_value == 0.02
        assert app_state.isochron_rxy_value == 0.3

        fixed_snapshot = app_state.state_store.snapshot()
        assert fixed_snapshot["isochron_error_mode"] == "fixed"
        assert fixed_snapshot["isochron_sx_value"] == 0.01
        assert fixed_snapshot["isochron_sy_value"] == 0.02
        assert fixed_snapshot["isochron_rxy_value"] == 0.3
    finally:
        _restore_state(snapshot)


def test_state_store_tooltip_visibility_domain() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_show_tooltip(True)
        assert app_state.show_tooltip is True
        assert app_state.state_store.snapshot()["show_tooltip"] is True

        state_gateway.set_show_tooltip(False)
        assert app_state.show_tooltip is False
        assert app_state.state_store.snapshot()["show_tooltip"] is False
    finally:
        _restore_state(snapshot)


def test_state_store_selected_indices_mutations() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_selected_indices({1, 2})
        state_gateway.add_selected_indices([2, 3])
        state_gateway.remove_selected_indices([1])

        assert app_state.selected_indices == {2, 3}
        assert app_state.state_store.snapshot()["selected_indices"] == {2, 3}

        state_gateway.clear_selected_indices()
        assert app_state.selected_indices == set()
    finally:
        _restore_state(snapshot)


def test_state_store_selection_tool_and_mode_domains() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_selection_mode(False)
        assert app_state.selection_mode is False

        state_gateway.set_selection_tool("lasso")
        assert app_state.selection_tool == "lasso"
        assert app_state.selection_mode is True

        state_gateway.clear_selection()
        assert app_state.selected_indices == set()
        assert app_state.selection_mode is False
        # Preserve existing behavior: clear_selection does not clear tool identity.
        assert app_state.selection_tool == "lasso"

        state_gateway.set_selection_tool(None)
        assert app_state.selection_tool is None
        assert app_state.selection_mode is False
    finally:
        _restore_state(snapshot)


def test_state_store_export_image_options_roundtrip() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_export_image_options(
            preset_key="ieee_single",
            image_ext="SVG",
            dpi=50,
            bbox_tight=False,
            pad_inches=-1.0,
            transparent=True,
            point_size=12,
            legend_size=7,
        )
        options = state_gateway.get_export_image_options()

        assert options["preset_key"] == "ieee_single"
        assert options["image_ext"] == "svg"
        assert options["dpi"] == 72
        assert options["bbox_tight"] is False
        assert options["pad_inches"] == 0.0
        assert options["transparent"] is True
        assert options["point_size"] == 12
        assert options["legend_size"] == 7
        assert dict(app_state.export_image_options) == options
    finally:
        _restore_state(snapshot)


def test_state_store_column_selection_domains() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_selected_2d_columns(["x", "y"], confirmed=True)
        state_gateway.set_selected_3d_columns(["x", "y", "z"], confirmed=True)
        state_gateway.set_selected_ternary_columns(["a", "b", "c"], confirmed=False)

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["selected_2d_cols"] == ["x", "y"]
        assert store_snapshot["selected_3d_cols"] == ["x", "y", "z"]
        assert store_snapshot["selected_ternary_cols"] == ["a", "b", "c"]
        assert store_snapshot["selected_2d_confirmed"] is True
        assert store_snapshot["selected_3d_confirmed"] is True
        assert store_snapshot["selected_ternary_confirmed"] is False

        state_gateway.reset_column_selection()
        assert app_state.selected_2d_cols == []
        assert app_state.selected_3d_cols == []
        assert app_state.selected_ternary_cols == []
        assert app_state.selected_2d_confirmed is False
        assert app_state.selected_3d_confirmed is False
        assert app_state.selected_ternary_confirmed is False
    finally:
        _restore_state(snapshot)


def test_state_store_available_visible_groups_sync() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.sync_available_and_visible_groups(["A", "B", "C"])
        state_gateway.set_visible_groups(["A", "C"])
        assert app_state.visible_groups == ["A", "C"]

        state_gateway.sync_available_and_visible_groups(["B", "C"])
        assert app_state.available_groups == ["B", "C"]
        assert app_state.visible_groups == ["C"]

        state_gateway.set_visible_groups(None)
        assert app_state.visible_groups is None
    finally:
        _restore_state(snapshot)


def test_state_store_data_source_and_columns_domains() -> None:
    snapshot = _snapshot_state()
    try:
        mock_df = {"rows": 2}
        state_gateway.set_dataframe_and_source(mock_df, file_path="d:/tmp/a.xlsx", sheet_name="Sheet1")
        state_gateway.set_group_data_columns(["Group"], ["206Pb/204Pb", "207Pb/204Pb"])
        state_gateway.set_last_group_col("Group")

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["df_global"] is mock_df
        assert store_snapshot["file_path"] == "d:/tmp/a.xlsx"
        assert store_snapshot["sheet_name"] == "Sheet1"
        assert store_snapshot["group_cols"] == ["Group"]
        assert store_snapshot["data_cols"] == ["206Pb/204Pb", "207Pb/204Pb"]
        assert store_snapshot["last_group_col"] == "Group"
    finally:
        _restore_state(snapshot)


def test_state_store_bump_data_version_clears_cache() -> None:
    snapshot = _snapshot_state()
    try:
        app_state.embedding_cache.set(("k",), "v")
        before_version = int(app_state.data_version)
        assert len(app_state.embedding_cache) == 1

        state_gateway.bump_data_version()

        assert app_state.data_version == before_version + 1
        assert len(app_state.embedding_cache) == 0
    finally:
        _restore_state(snapshot)
