"""Persistence schemas: which StateStore fields are saved where.

Design (see docs/persistence_plan.md §8):
- ``SESSION_FIELDS``  → params.json  (session-level: algorithm, params, data refs)
- ``UI_STATE_FIELDS`` → ui_state.json (user configuration: styles, overlays,
  legend, ternary/KDE settings, presets, recent files)
- ``EXCLUDED_FIELDS`` → never persisted (runtime/render artifacts, transient)
"""
from __future__ import annotations

from typing import Any

#: Session-level fields saved to params.json.
SESSION_FIELDS: frozenset[str] = frozenset({
    "algorithm",
    "render_mode",
    "umap_params",
    "tsne_params",
    "pca_params",
    "robust_pca_params",
    "ml_params",
    "v1v2_params",
    "point_size",
    "last_group_col",
    "group_cols",
    "data_cols",
    "file_path",
    "sheet_name",
    "selected_2d_cols",
    "selected_3d_cols",
    "language",
    "tooltip_columns",
    "ui_theme",
    "parent_groups",
    "parent_shape_map",
})

#: User-configuration fields saved to ui_state.json.
UI_STATE_FIELDS: frozenset[str] = frozenset({
    # display styles
    "plot_style_grid", "plot_marker_size", "plot_marker_alpha", "show_plot_title",
    "plot_dpi", "plot_facecolor", "axes_facecolor", "custom_primary_font",
    "custom_cjk_font", "plot_font_sizes",
    "grid_color", "grid_linewidth", "grid_alpha", "grid_linestyle",
    "tick_direction", "tick_color", "tick_length", "tick_width",
    "axis_linewidth", "axis_line_color",
    "minor_ticks", "minor_tick_length", "minor_tick_width",
    "show_top_spine", "show_right_spine",
    "minor_grid", "minor_grid_color", "minor_grid_linewidth", "minor_grid_alpha",
    "minor_grid_linestyle",
    "scatter_show_edge", "scatter_edgecolor", "scatter_edgewidth",
    "label_color", "label_weight", "label_pad",
    "title_color", "title_weight", "title_pad",
    "legend_frame_on", "legend_frame_alpha", "legend_frame_facecolor",
    "legend_frame_edgecolor",
    "adjust_text_force_text", "adjust_text_force_static", "adjust_text_expand",
    "adjust_text_iter_lim", "adjust_text_time_lim",
    "confidence_level", "draw_selection_ellipse",
    # analysis / overlays
    "mixing_endmembers", "mixing_mixtures", "equation_overlays",
    "show_model_curves", "show_paleoisochrons", "show_isochrons",
    "show_model_age_lines", "show_growth_curves", "show_plumbotectonics_curves",
    "show_equation_overlays", "show_kde", "show_marginal_kde",
    "model_curve_width", "plumbotectonics_curve_width", "paleoisochron_width",
    "model_age_line_width", "isochron_line_width", "selected_isochron_line_width",
    "line_styles",
    # legend display
    "legend_columns", "legend_display_mode", "legend_position", "legend_location",
    "legend_nudge_step", "legend_offset", "color_scheme",
    "current_palette", "group_marker_map", "legend_item_order",
    "visible_groups", "hidden_groups",
    # isochron / paleoisochron / plumbotectonics
    "isochron_error_mode", "isochron_sx_col", "isochron_sy_col", "isochron_rxy_col",
    "isochron_sx_value", "isochron_sy_value", "isochron_rxy_value",
    "isochron_label_options",
    "paleoisochron_ages", "paleoisochron_min_age", "paleoisochron_max_age",
    "paleoisochron_step",
    "plumbotectonics_variant", "plumbotectonics_group_visibility",
    "geo_model_name", "use_real_age_for_mu_kappa", "mu_kappa_age_col",
    # ternary
    "ternary_auto_zoom", "ternary_limit_mode", "ternary_limit_anchor",
    "ternary_boundary_percent", "ternary_manual_limits",
    "ternary_manual_limits_enabled", "ternary_stretch", "ternary_stretch_mode",
    "ternary_factors", "ternary_ranges",
    # KDE
    "kde_style", "marginal_kde_style",
    "marginal_kde_bandwidth", "marginal_kde_bw_adjust", "marginal_kde_kernel",
    "marginal_kde_auto_bandwidth_method", "marginal_kde_gridsize",
    "marginal_kde_cut", "marginal_kde_log_transform", "marginal_kde_max_points",
    "marginal_kde_top_size", "marginal_kde_right_size",
    # misc configuration
    "standardize_data", "pca_component_indices",
    "export_image_options", "recent_files",
    "show_tooltip",
    "custom_palettes", "custom_shape_sets", "param_presets",
})

#: Snapshot fields that must NEVER be persisted (runtime/render artifacts).
EXCLUDED_FIELDS: frozenset[str] = frozenset({
    "df_global",
    "last_embedding",
    "last_pca_variance",
    "last_pca_components",
    "current_feature_names",
    "overlay_artists",
    "overlay_curve_label_data",
    "paleoisochron_label_data",
    "plumbotectonics_label_data",
    "plumbotectonics_isoage_label_data",
    "legend_last_title",
    "legend_last_handles",
    "legend_last_labels",
    "selected_isochron_data",
    "marginal_axes",
    "isochron_results",
    "ml_last_result",
    "ml_last_model_meta",
    "selection_mode",
    "selection_tool",
    "selected_indices",
    "embedding_task_running",
    "embedding_task_token",
    "initial_render_done",
    "adjust_text_in_progress",
    "overlay_label_refreshing",
    "paleo_label_refreshing",
    "preserve_import_render_mode",
    "data_version",
    "available_groups",
})

_ALL_PERSISTED = SESSION_FIELDS | UI_STATE_FIELDS


def build_payload(snapshot: dict[str, Any], fields: frozenset[str]) -> dict[str, Any]:
    """Extract the given fields from a StateStore snapshot."""
    return {key: snapshot[key] for key in fields if key in snapshot}


def validate_schema(snapshot_keys: set[str]) -> list[str]:
    """Return problems found in the persistence schema vs the live snapshot.

    Called by a guard test so the hand-maintained white lists cannot drift.
    """
    problems: list[str] = []
    overlap = _ALL_PERSISTED & EXCLUDED_FIELDS
    if overlap:
        problems.append(f"fields both persisted and excluded: {sorted(overlap)}")
    missing = _ALL_PERSISTED - snapshot_keys
    if missing:
        problems.append(f"persisted fields missing from snapshot: {sorted(missing)}")
    dead_exclusions = EXCLUDED_FIELDS - snapshot_keys
    if dead_exclusions:
        problems.append(f"excluded fields absent from snapshot: {sorted(dead_exclusions)}")
    return problems
