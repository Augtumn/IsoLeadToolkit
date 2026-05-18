"""StateStore for managed AppState domains."""

from __future__ import annotations

import logging
from typing import Any

from ._dispatch_handlers import dispatch_action
from ._normalizers import (
    _normalize_active_subset_indices,
    _normalize_adjust_text_iter_lim,
    _normalize_adjust_text_pair,
    _normalize_adjust_text_time_lim,
    _normalize_algorithm_params,
    _normalize_color,
    _normalize_export_options,
    _normalize_font_name,
    _normalize_grid_linestyle,
    _normalize_kde_auto_bandwidth_method,
    _normalize_kde_bandwidth,
    _normalize_kde_kernel,
    _normalize_pca_component_indices,
    _normalize_plot_dpi,
    _normalize_plot_font_sizes,
    _normalize_plot_marker_alpha,
    _normalize_plot_marker_size,
    _normalize_style_linewidth,
    _normalize_ternary_boundary_percent,
    _normalize_ternary_limit_anchor,
    _normalize_ternary_limit_mode,
    _normalize_ternary_manual_limits,
    _normalize_ternary_render_margin,
    _normalize_text_pad,
    _normalize_text_weight,
    _normalize_tick_direction,
    _normalize_tick_length,
    _normalize_unit_interval,
    _normalize_visible_groups,
    sync_state_store_to_app,
)

logger = logging.getLogger(__name__)


class StateStore:
    """Manage selected AppState domains through action dispatch."""

    DEFAULT_EXPORT_IMAGE_OPTIONS = {
        "preset_key": "science_single",
        "image_ext": "png",
        "dpi": 400,
        "bbox_tight": True,
        "pad_inches": 0.02,
        "transparent": False,
        "point_size": None,
        "legend_size": None,
    }
    DEFAULT_PLOT_FONT_SIZES = {
        "title": 14,
        "label": 12,
        "tick": 10,
        "legend": 10,
    }
    MIN_EXPORT_DPI = 72
    DEFAULT_LEGEND_FRAME_ALPHA = 0.95
    DEFAULT_CONFIDENCE_LEVEL = 0.95
    MARGINAL_KDE_DEFAULT_KERNEL = "gaussian"
    MARGINAL_KDE_ALLOWED_KERNELS = (
        "gaussian",
        "tophat",
        "epanechnikov",
        "exponential",
        "linear",
        "cosine",
    )
    MARGINAL_KDE_DEFAULT_AUTO_BANDWIDTH_METHOD = "scott"
    MARGINAL_KDE_ALLOWED_AUTO_BANDWIDTH_METHODS = ("scott", "silverman")

    # Normalizer clamp bounds
    _ADJUST_TEXT_ITER_MIN: int = 10
    _ADJUST_TEXT_ITER_MAX: int = 1000
    _ADJUST_TEXT_TIME_MIN: float = 0.05
    _ADJUST_TEXT_TIME_MAX: float = 2.0
    _MARGINAL_SIZE_MIN: float = 5.0
    _MARGINAL_SIZE_MAX: float = 40.0
    _MAX_POINTS_MIN: int = 200
    _MAX_POINTS_MAX: int = 50000
    _BW_ADJUST_MIN: float = 0.05
    _BW_ADJUST_MAX: float = 5.0
    _KDE_BW_MIN: float = 0.0
    _KDE_BW_MAX: float = 10.0

    def __init__(self, state: Any) -> None:
        self._state = state
        self._snapshot: dict[str, Any] = {
            "render_mode": str(getattr(state, "render_mode", "UMAP")),
            "algorithm": str(getattr(state, "algorithm", "UMAP")),
            "umap_params": _normalize_algorithm_params(
                getattr(state, "umap_params", None)
            ),
            "tsne_params": _normalize_algorithm_params(
                getattr(state, "tsne_params", None)
            ),
            "pca_params": _normalize_algorithm_params(
                getattr(state, "pca_params", None)
            ),
            "robust_pca_params": _normalize_algorithm_params(
                getattr(state, "robust_pca_params", None)
            ),
            "ml_params": _normalize_algorithm_params(
                getattr(state, "ml_params", None)
            ),
            "v1v2_params": _normalize_algorithm_params(
                getattr(state, "v1v2_params", None)
            ),
            "plot_style_grid": bool(getattr(state, "plot_style_grid", False)),
            "plot_marker_size": _normalize_plot_marker_size(
                getattr(state, "plot_marker_size", 60)
            ),
            "plot_marker_alpha": _normalize_plot_marker_alpha(
                getattr(state, "plot_marker_alpha", 0.8)
            ),
            "show_plot_title": bool(getattr(state, "show_plot_title", False)),
            "plot_dpi": _normalize_plot_dpi(getattr(state, "plot_dpi", 130)),
            "custom_primary_font": _normalize_font_name(
                getattr(state, "custom_primary_font", "")
            ),
            "custom_cjk_font": _normalize_font_name(
                getattr(state, "custom_cjk_font", "")
            ),
            "plot_font_sizes": _normalize_plot_font_sizes(
                getattr(state, "plot_font_sizes", None)
            ),
            "plot_facecolor": _normalize_color(
                getattr(state, "plot_facecolor", "#ffffff"),
                "#ffffff",
            ),
            "axes_facecolor": _normalize_color(
                getattr(state, "axes_facecolor", "#ffffff"),
                "#ffffff",
            ),
            "grid_color": _normalize_color(
                getattr(state, "grid_color", "#e2e8f0"),
                "#e2e8f0",
            ),
            "grid_linewidth": _normalize_style_linewidth(
                getattr(state, "grid_linewidth", 0.6),
                default=0.6,
            ),
            "grid_alpha": _normalize_unit_interval(
                getattr(state, "grid_alpha", 0.7),
                default=0.7,
            ),
            "grid_linestyle": _normalize_grid_linestyle(
                getattr(state, "grid_linestyle", "--")
            ),
            "tick_direction": _normalize_tick_direction(
                getattr(state, "tick_direction", "out")
            ),
            "tick_color": _normalize_color(
                getattr(state, "tick_color", "#1f2937"),
                "#1f2937",
            ),
            "tick_length": _normalize_tick_length(
                getattr(state, "tick_length", 4.0),
                default=4.0,
            ),
            "tick_width": _normalize_style_linewidth(
                getattr(state, "tick_width", 0.8),
                default=0.8,
            ),
            "axis_linewidth": _normalize_style_linewidth(
                getattr(state, "axis_linewidth", 1.0),
                default=1.0,
            ),
            "axis_line_color": _normalize_color(
                getattr(state, "axis_line_color", "#1f2937"),
                "#1f2937",
            ),
            "minor_ticks": bool(getattr(state, "minor_ticks", False)),
            "minor_tick_length": _normalize_tick_length(
                getattr(state, "minor_tick_length", 2.5),
                default=2.5,
            ),
            "minor_tick_width": _normalize_style_linewidth(
                getattr(state, "minor_tick_width", 0.6),
                default=0.6,
            ),
            "show_top_spine": bool(getattr(state, "show_top_spine", True)),
            "show_right_spine": bool(getattr(state, "show_right_spine", True)),
            "minor_grid": bool(getattr(state, "minor_grid", False)),
            "minor_grid_color": _normalize_color(
                getattr(state, "minor_grid_color", "#e2e8f0"),
                "#e2e8f0",
            ),
            "minor_grid_linewidth": _normalize_style_linewidth(
                getattr(state, "minor_grid_linewidth", 0.4),
                default=0.4,
            ),
            "minor_grid_alpha": _normalize_unit_interval(
                getattr(state, "minor_grid_alpha", 0.4),
                default=0.4,
            ),
            "minor_grid_linestyle": _normalize_grid_linestyle(
                getattr(state, "minor_grid_linestyle", ":")
            ),
            "scatter_show_edge": bool(getattr(state, "scatter_show_edge", True)),
            "scatter_edgecolor": _normalize_color(
                getattr(state, "scatter_edgecolor", "#1e293b"),
                "#1e293b",
            ),
            "scatter_edgewidth": _normalize_style_linewidth(
                getattr(state, "scatter_edgewidth", 0.4),
                default=0.4,
            ),
            "label_color": _normalize_color(
                getattr(state, "label_color", "#1f2937"),
                "#1f2937",
            ),
            "label_weight": _normalize_text_weight(
                getattr(state, "label_weight", "normal"),
                default="normal",
            ),
            "label_pad": _normalize_text_pad(
                getattr(state, "label_pad", 6.0),
                default=6.0,
                max_value=60.0,
            ),
            "title_color": _normalize_color(
                getattr(state, "title_color", "#111827"),
                "#111827",
            ),
            "title_weight": _normalize_text_weight(
                getattr(state, "title_weight", "bold"),
                default="bold",
            ),
            "title_pad": _normalize_text_pad(
                getattr(state, "title_pad", 20.0),
                default=20.0,
                max_value=80.0,
            ),
            "legend_frame_on": bool(getattr(state, "legend_frame_on", True)),
            "legend_frame_alpha": _normalize_unit_interval(
                getattr(state, "legend_frame_alpha", self.DEFAULT_LEGEND_FRAME_ALPHA),
                default=self.DEFAULT_LEGEND_FRAME_ALPHA,
            ),
            "legend_frame_facecolor": _normalize_color(
                getattr(state, "legend_frame_facecolor", "#ffffff"),
                "#ffffff",
            ),
            "legend_frame_edgecolor": _normalize_color(
                getattr(state, "legend_frame_edgecolor", "#cbd5f5"),
                "#cbd5f5",
            ),
            "adjust_text_force_text": _normalize_adjust_text_pair(
                getattr(state, "adjust_text_force_text", (0.8, 1.0)),
                default=(0.8, 1.0),
                min_value=0.0,
                max_value=3.0,
            ),
            "adjust_text_force_static": _normalize_adjust_text_pair(
                getattr(state, "adjust_text_force_static", (0.4, 0.6)),
                default=(0.4, 0.6),
                min_value=0.0,
                max_value=3.0,
            ),
            "adjust_text_expand": _normalize_adjust_text_pair(
                getattr(state, "adjust_text_expand", (1.08, 1.20)),
                default=(1.08, 1.20),
                min_value=1.0,
                max_value=2.5,
            ),
            "adjust_text_iter_lim": _normalize_adjust_text_iter_lim(
                getattr(state, "adjust_text_iter_lim", 120)
            ),
            "adjust_text_time_lim": _normalize_adjust_text_time_lim(
                getattr(state, "adjust_text_time_lim", 0.25)
            ),
            "show_kde": bool(getattr(state, "show_kde", False)),
            "show_marginal_kde": bool(getattr(state, "show_marginal_kde", True)),
            "show_equation_overlays": bool(getattr(state, "show_equation_overlays", False)),
            "geo_model_name": str(getattr(state, "geo_model_name", "Stacey & Kramers (2nd Stage)")),
            "paleo_label_refreshing": bool(getattr(state, "paleo_label_refreshing", False)),
            "overlay_label_refreshing": bool(getattr(state, "overlay_label_refreshing", False)),
            "overlay_curve_label_data": list(getattr(state, "overlay_curve_label_data", []) or []),
            "paleoisochron_label_data": list(getattr(state, "paleoisochron_label_data", []) or []),
            "plumbotectonics_label_data": list(
                getattr(state, "plumbotectonics_label_data", []) or []
            ),
            "plumbotectonics_isoage_label_data": list(
                getattr(state, "plumbotectonics_isoage_label_data", []) or []
            ),
            "overlay_artists": dict(getattr(state, "overlay_artists", {}) or {}),
            "last_embedding": getattr(state, "last_embedding", None),
            "last_embedding_type": str(getattr(state, "last_embedding_type", "") or ""),
            "selected_isochron_data": getattr(state, "selected_isochron_data", None),
            "embedding_task_token": int(getattr(state, "embedding_task_token", 0)),
            "embedding_task_running": bool(getattr(state, "embedding_task_running", False)),
            "marginal_axes": getattr(state, "marginal_axes", None),
            "last_pca_variance": getattr(state, "last_pca_variance", None),
            "last_pca_components": getattr(state, "last_pca_components", None),
            "current_feature_names": getattr(state, "current_feature_names", []),
            "adjust_text_in_progress": bool(getattr(state, "adjust_text_in_progress", False)),
            "confidence_level": float(
                getattr(state, "confidence_level", self.DEFAULT_CONFIDENCE_LEVEL)
            ),
            "current_palette": dict(getattr(state, "current_palette", {}) or {}),
            "group_marker_map": dict(getattr(state, "group_marker_map", {}) or {}),
            "current_plot_title": str(getattr(state, "current_plot_title", "")),
            "last_2d_cols": (
                list(getattr(state, "last_2d_cols", []) or [])
                if getattr(state, "last_2d_cols", None) is not None
                else None
            ),
            "show_model_curves": bool(getattr(state, "show_model_curves", True)),
            "show_plumbotectonics_curves": bool(
                getattr(state, "show_plumbotectonics_curves", True)
            ),
            "show_paleoisochrons": bool(getattr(state, "show_paleoisochrons", True)),
            "show_model_age_lines": bool(getattr(state, "show_model_age_lines", True)),
            "show_growth_curves": bool(getattr(state, "show_growth_curves", True)),
            "show_isochrons": bool(getattr(state, "show_isochrons", False)),
            "isochron_error_mode": (
                "columns"
                if str(getattr(state, "isochron_error_mode", "fixed") or "fixed").strip().lower()
                == "columns"
                else "fixed"
            ),
            "isochron_sx_col": str(getattr(state, "isochron_sx_col", "") or ""),
            "isochron_sy_col": str(getattr(state, "isochron_sy_col", "") or ""),
            "isochron_rxy_col": str(getattr(state, "isochron_rxy_col", "") or ""),
            "isochron_sx_value": float(getattr(state, "isochron_sx_value", 0.001)),
            "isochron_sy_value": float(getattr(state, "isochron_sy_value", 0.001)),
            "isochron_rxy_value": float(getattr(state, "isochron_rxy_value", 0.0)),
            "isochron_results": dict(getattr(state, "isochron_results", {}) or {}),
            "plumbotectonics_group_visibility": dict(
                getattr(state, "plumbotectonics_group_visibility", {}) or {}
            ),
            "use_real_age_for_mu_kappa": bool(getattr(state, "use_real_age_for_mu_kappa", False)),
            "mu_kappa_age_col": getattr(state, "mu_kappa_age_col", None),
            "plumbotectonics_variant": str(getattr(state, "plumbotectonics_variant", "0")),
            "paleoisochron_min_age": int(getattr(state, "paleoisochron_min_age", 0)),
            "paleoisochron_max_age": int(getattr(state, "paleoisochron_max_age", 3000)),
            "paleoisochron_step": int(getattr(state, "paleoisochron_step", 1000)),
            "paleoisochron_ages": list(getattr(state, "paleoisochron_ages", []) or []),
            "draw_selection_ellipse": bool(getattr(state, "draw_selection_ellipse", False)),
            "marginal_kde_top_size": float(getattr(state, "marginal_kde_top_size", 15.0)),
            "marginal_kde_right_size": float(getattr(state, "marginal_kde_right_size", 15.0)),
            "marginal_kde_max_points": int(getattr(state, "marginal_kde_max_points", 5000)),
            "marginal_kde_bw_adjust": float(getattr(state, "marginal_kde_bw_adjust", 1.0)),
            "marginal_kde_bandwidth": _normalize_kde_bandwidth(
                getattr(state, "marginal_kde_bandwidth", 0.0)
            ),
            "marginal_kde_kernel": _normalize_kde_kernel(
                getattr(state, "marginal_kde_kernel", self.MARGINAL_KDE_DEFAULT_KERNEL)
            ),
            "marginal_kde_auto_bandwidth_method": _normalize_kde_auto_bandwidth_method(
                getattr(
                    state,
                    "marginal_kde_auto_bandwidth_method",
                    self.MARGINAL_KDE_DEFAULT_AUTO_BANDWIDTH_METHOD,
                )
            ),
            "marginal_kde_gridsize": int(getattr(state, "marginal_kde_gridsize", 256)),
            "marginal_kde_cut": float(getattr(state, "marginal_kde_cut", 1.0)),
            "marginal_kde_log_transform": bool(getattr(state, "marginal_kde_log_transform", False)),
            "selected_indices": set(getattr(state, "selected_indices", set()) or set()),
            "active_subset_indices": _normalize_active_subset_indices(
                getattr(state, "active_subset_indices", None)
            ),
            "df_global": getattr(state, "df_global", None),
            "file_path": getattr(state, "file_path", None),
            "sheet_name": getattr(state, "sheet_name", None),
            "data_version": int(getattr(state, "data_version", 0)),
            "group_cols": list(getattr(state, "group_cols", []) or []),
            "data_cols": list(getattr(state, "data_cols", []) or []),
            "last_group_col": getattr(state, "last_group_col", None),
            "selection_mode": bool(getattr(state, "selection_mode", False)),
            "selection_tool": getattr(state, "selection_tool", None),
            "point_size": int(getattr(state, "point_size", 60)),
            "show_tooltip": bool(getattr(state, "show_tooltip", False)),
            "tooltip_columns": list(getattr(state, "tooltip_columns", []) or []),
            "ui_theme": str(getattr(state, "ui_theme", "Modern Light")),
            "language": str(getattr(state, "language", "zh")),
            "color_scheme": str(getattr(state, "color_scheme", "vibrant")),
            "legend_position": getattr(state, "legend_position", None),
            "legend_location": getattr(state, "legend_location", "outside_left"),
            "legend_display_mode": str(getattr(state, "legend_display_mode", "inline")),
            "legend_columns": int(getattr(state, "legend_columns", 0)),
            "legend_nudge_step": float(getattr(state, "legend_nudge_step", 0.02)),
            "legend_offset": tuple(getattr(state, "legend_offset", (0.0, 0.0)) or (0.0, 0.0)),
            "hidden_groups": set(getattr(state, "hidden_groups", set()) or set()),
            "legend_last_title": getattr(state, "legend_last_title", None),
            "legend_last_handles": getattr(state, "legend_last_handles", None),
            "legend_last_labels": getattr(state, "legend_last_labels", None),
            "recent_files": list(getattr(state, "recent_files", []) or []),
            "line_styles": dict(getattr(state, "line_styles", {}) or {}),
            "saved_themes": dict(getattr(state, "saved_themes", {}) or {}),
            "custom_palettes": dict(getattr(state, "custom_palettes", {}) or {}),
            "custom_shape_sets": dict(getattr(state, "custom_shape_sets", {}) or {}),
            "legend_item_order": list(getattr(state, "legend_item_order", []) or []),
            "mixing_endmembers": dict(getattr(state, "mixing_endmembers", {}) or {}),
            "mixing_mixtures": dict(getattr(state, "mixing_mixtures", {}) or {}),
            "ternary_ranges": dict(getattr(state, "ternary_ranges", {}) or {}),
            "kde_style": dict(getattr(state, "kde_style", {}) or {}),
            "marginal_kde_style": dict(getattr(state, "marginal_kde_style", {}) or {}),
            "ml_last_result": getattr(state, "ml_last_result", None),
            "ml_last_model_meta": getattr(state, "ml_last_model_meta", None),
            "preserve_import_render_mode": bool(getattr(state, "preserve_import_render_mode", False)),
            "available_groups": list(getattr(state, "available_groups", []) or []),
            "visible_groups": _normalize_visible_groups(getattr(state, "visible_groups", None)),
            "selected_2d_cols": list(getattr(state, "selected_2d_cols", []) or []),
            "selected_3d_cols": list(getattr(state, "selected_3d_cols", []) or []),
            "selected_ternary_cols": list(getattr(state, "selected_ternary_cols", []) or []),
            "selected_2d_confirmed": bool(getattr(state, "selected_2d_confirmed", False)),
            "selected_3d_confirmed": bool(getattr(state, "selected_3d_confirmed", False)),
            "selected_ternary_confirmed": bool(getattr(state, "selected_ternary_confirmed", False)),
            "standardize_data": bool(getattr(state, "standardize_data", True)),
            "initial_render_done": bool(getattr(state, "initial_render_done", False)),
            "pca_component_indices": _normalize_pca_component_indices(
                getattr(state, "pca_component_indices", None)
            ),
            "ternary_auto_zoom": bool(getattr(state, "ternary_auto_zoom", True)),
            "ternary_limit_mode": _normalize_ternary_limit_mode(
                getattr(state, "ternary_limit_mode", "min")
            ),
            "ternary_limit_anchor": _normalize_ternary_limit_anchor(
                getattr(state, "ternary_limit_anchor", "min")
            ),
            "ternary_boundary_percent": _normalize_ternary_boundary_percent(
                getattr(state, "ternary_boundary_percent", 5.0)
            ),
            "ternary_manual_limits_enabled": bool(
                getattr(state, "ternary_manual_limits_enabled", False)
            ),
            "ternary_manual_limits": _normalize_ternary_manual_limits(
                getattr(state, "ternary_manual_limits", None)
            ),
            "ternary_render_margin": _normalize_ternary_render_margin(
                getattr(state, "ternary_render_margin", 0.002)
            ),
            "ternary_stretch_mode": str(getattr(state, "ternary_stretch_mode", "power") or "power"),
            "ternary_stretch": bool(getattr(state, "ternary_stretch", False)),
            "ternary_factors": list(getattr(state, "ternary_factors", [1.0, 1.0, 1.0]) or [1.0, 1.0, 1.0]),
            "model_curve_width": float(getattr(state, "model_curve_width", 1.2)),
            "plumbotectonics_curve_width": float(getattr(state, "plumbotectonics_curve_width", 1.2)),
            "paleoisochron_width": float(getattr(state, "paleoisochron_width", 0.9)),
            "model_age_line_width": float(getattr(state, "model_age_line_width", 0.7)),
            "isochron_line_width": float(getattr(state, "isochron_line_width", 1.5)),
            "selected_isochron_line_width": float(getattr(state, "selected_isochron_line_width", 2.0)),
            "isochron_label_options": dict(getattr(state, "isochron_label_options", {}) or {}),
            "model_curve_models": (
                list(getattr(state, "model_curve_models", []) or [])
                if getattr(state, "model_curve_models", None) is not None
                else None
            ),
            "equation_overlays": list(getattr(state, "equation_overlays", []) or []),
            "export_image_options": _normalize_export_options(
                getattr(state, "export_image_options", None)
            ),
        }
        self._sync_state()

    def dispatch(self, action: dict[str, Any]) -> dict[str, Any]:
        """Dispatch an action and return a snapshot copy."""
        dispatch_action(self, action)
        self._sync_state()
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        """Return shallow-copied tracked domains."""
        return {
            "render_mode": str(self._snapshot["render_mode"]),
            "algorithm": str(self._snapshot["algorithm"]),
            "umap_params": dict(self._snapshot["umap_params"]),
            "tsne_params": dict(self._snapshot["tsne_params"]),
            "pca_params": dict(self._snapshot["pca_params"]),
            "robust_pca_params": dict(self._snapshot["robust_pca_params"]),
            "ml_params": dict(self._snapshot["ml_params"]),
            "v1v2_params": dict(self._snapshot["v1v2_params"]),
            "plot_style_grid": bool(self._snapshot["plot_style_grid"]),
            "plot_marker_size": int(self._snapshot["plot_marker_size"]),
            "plot_marker_alpha": float(self._snapshot["plot_marker_alpha"]),
            "show_plot_title": bool(self._snapshot["show_plot_title"]),
            "plot_dpi": int(self._snapshot["plot_dpi"]),
            "custom_primary_font": str(self._snapshot["custom_primary_font"]),
            "custom_cjk_font": str(self._snapshot["custom_cjk_font"]),
            "plot_font_sizes": dict(self._snapshot["plot_font_sizes"]),
            "plot_facecolor": str(self._snapshot["plot_facecolor"]),
            "axes_facecolor": str(self._snapshot["axes_facecolor"]),
            "grid_color": str(self._snapshot["grid_color"]),
            "grid_linewidth": float(self._snapshot["grid_linewidth"]),
            "grid_alpha": float(self._snapshot["grid_alpha"]),
            "grid_linestyle": str(self._snapshot["grid_linestyle"]),
            "tick_direction": str(self._snapshot["tick_direction"]),
            "tick_color": str(self._snapshot["tick_color"]),
            "tick_length": float(self._snapshot["tick_length"]),
            "tick_width": float(self._snapshot["tick_width"]),
            "axis_linewidth": float(self._snapshot["axis_linewidth"]),
            "axis_line_color": str(self._snapshot["axis_line_color"]),
            "minor_ticks": bool(self._snapshot["minor_ticks"]),
            "minor_tick_length": float(self._snapshot["minor_tick_length"]),
            "minor_tick_width": float(self._snapshot["minor_tick_width"]),
            "show_top_spine": bool(self._snapshot["show_top_spine"]),
            "show_right_spine": bool(self._snapshot["show_right_spine"]),
            "minor_grid": bool(self._snapshot["minor_grid"]),
            "minor_grid_color": str(self._snapshot["minor_grid_color"]),
            "minor_grid_linewidth": float(self._snapshot["minor_grid_linewidth"]),
            "minor_grid_alpha": float(self._snapshot["minor_grid_alpha"]),
            "minor_grid_linestyle": str(self._snapshot["minor_grid_linestyle"]),
            "scatter_show_edge": bool(self._snapshot["scatter_show_edge"]),
            "scatter_edgecolor": str(self._snapshot["scatter_edgecolor"]),
            "scatter_edgewidth": float(self._snapshot["scatter_edgewidth"]),
            "label_color": str(self._snapshot["label_color"]),
            "label_weight": str(self._snapshot["label_weight"]),
            "label_pad": float(self._snapshot["label_pad"]),
            "title_color": str(self._snapshot["title_color"]),
            "title_weight": str(self._snapshot["title_weight"]),
            "title_pad": float(self._snapshot["title_pad"]),
            "legend_frame_on": bool(self._snapshot["legend_frame_on"]),
            "legend_frame_alpha": float(self._snapshot["legend_frame_alpha"]),
            "legend_frame_facecolor": str(self._snapshot["legend_frame_facecolor"]),
            "legend_frame_edgecolor": str(self._snapshot["legend_frame_edgecolor"]),
            "adjust_text_force_text": tuple(self._snapshot["adjust_text_force_text"]),
            "adjust_text_force_static": tuple(self._snapshot["adjust_text_force_static"]),
            "adjust_text_expand": tuple(self._snapshot["adjust_text_expand"]),
            "adjust_text_iter_lim": int(self._snapshot["adjust_text_iter_lim"]),
            "adjust_text_time_lim": float(self._snapshot["adjust_text_time_lim"]),
            "show_kde": bool(self._snapshot["show_kde"]),
            "show_marginal_kde": bool(self._snapshot["show_marginal_kde"]),
            "show_equation_overlays": bool(self._snapshot["show_equation_overlays"]),
            "geo_model_name": str(self._snapshot["geo_model_name"]),
            "paleo_label_refreshing": bool(self._snapshot["paleo_label_refreshing"]),
            "overlay_label_refreshing": bool(self._snapshot["overlay_label_refreshing"]),
            "overlay_curve_label_data": list(self._snapshot["overlay_curve_label_data"]),
            "paleoisochron_label_data": list(self._snapshot["paleoisochron_label_data"]),
            "plumbotectonics_label_data": list(self._snapshot["plumbotectonics_label_data"]),
            "plumbotectonics_isoage_label_data": list(
                self._snapshot["plumbotectonics_isoage_label_data"]
            ),
            "overlay_artists": dict(self._snapshot["overlay_artists"]),
            "last_embedding": self._snapshot["last_embedding"],
            "last_embedding_type": str(self._snapshot["last_embedding_type"]),
            "selected_isochron_data": self._snapshot["selected_isochron_data"],
            "embedding_task_token": int(self._snapshot["embedding_task_token"]),
            "embedding_task_running": bool(self._snapshot["embedding_task_running"]),
            "marginal_axes": self._snapshot["marginal_axes"],
            "last_pca_variance": self._snapshot["last_pca_variance"],
            "last_pca_components": self._snapshot["last_pca_components"],
            "current_feature_names": self._snapshot["current_feature_names"],
            "adjust_text_in_progress": bool(self._snapshot["adjust_text_in_progress"]),
            "confidence_level": float(self._snapshot["confidence_level"]),
            "current_palette": dict(self._snapshot["current_palette"]),
            "group_marker_map": dict(self._snapshot["group_marker_map"]),
            "current_plot_title": str(self._snapshot["current_plot_title"]),
            "last_2d_cols": (
                list(self._snapshot["last_2d_cols"])
                if self._snapshot["last_2d_cols"] is not None
                else None
            ),
            "show_model_curves": bool(self._snapshot["show_model_curves"]),
            "show_plumbotectonics_curves": bool(self._snapshot["show_plumbotectonics_curves"]),
            "show_paleoisochrons": bool(self._snapshot["show_paleoisochrons"]),
            "show_model_age_lines": bool(self._snapshot["show_model_age_lines"]),
            "show_growth_curves": bool(self._snapshot["show_growth_curves"]),
            "show_isochrons": bool(self._snapshot["show_isochrons"]),
            "isochron_error_mode": str(self._snapshot["isochron_error_mode"]),
            "isochron_sx_col": str(self._snapshot["isochron_sx_col"]),
            "isochron_sy_col": str(self._snapshot["isochron_sy_col"]),
            "isochron_rxy_col": str(self._snapshot["isochron_rxy_col"]),
            "isochron_sx_value": float(self._snapshot["isochron_sx_value"]),
            "isochron_sy_value": float(self._snapshot["isochron_sy_value"]),
            "isochron_rxy_value": float(self._snapshot["isochron_rxy_value"]),
            "isochron_results": dict(self._snapshot["isochron_results"]),
            "plumbotectonics_group_visibility": dict(
                self._snapshot["plumbotectonics_group_visibility"]
            ),
            "use_real_age_for_mu_kappa": bool(self._snapshot["use_real_age_for_mu_kappa"]),
            "mu_kappa_age_col": self._snapshot["mu_kappa_age_col"],
            "plumbotectonics_variant": str(self._snapshot["plumbotectonics_variant"]),
            "paleoisochron_min_age": int(self._snapshot["paleoisochron_min_age"]),
            "paleoisochron_max_age": int(self._snapshot["paleoisochron_max_age"]),
            "paleoisochron_step": int(self._snapshot["paleoisochron_step"]),
            "paleoisochron_ages": list(self._snapshot["paleoisochron_ages"]),
            "draw_selection_ellipse": bool(self._snapshot["draw_selection_ellipse"]),
            "marginal_kde_top_size": float(self._snapshot["marginal_kde_top_size"]),
            "marginal_kde_right_size": float(self._snapshot["marginal_kde_right_size"]),
            "marginal_kde_max_points": int(self._snapshot["marginal_kde_max_points"]),
            "marginal_kde_bw_adjust": float(self._snapshot["marginal_kde_bw_adjust"]),
            "marginal_kde_bandwidth": float(self._snapshot["marginal_kde_bandwidth"]),
            "marginal_kde_kernel": str(self._snapshot["marginal_kde_kernel"]),
            "marginal_kde_auto_bandwidth_method": str(
                self._snapshot["marginal_kde_auto_bandwidth_method"]
            ),
            "marginal_kde_gridsize": int(self._snapshot["marginal_kde_gridsize"]),
            "marginal_kde_cut": float(self._snapshot["marginal_kde_cut"]),
            "marginal_kde_log_transform": bool(self._snapshot["marginal_kde_log_transform"]),
            "selected_indices": set(self._snapshot["selected_indices"]),
            "active_subset_indices": _normalize_active_subset_indices(
                self._snapshot["active_subset_indices"]
            ),
            "df_global": self._snapshot["df_global"],
            "file_path": self._snapshot["file_path"],
            "sheet_name": self._snapshot["sheet_name"],
            "data_version": int(self._snapshot["data_version"]),
            "group_cols": list(self._snapshot["group_cols"]),
            "data_cols": list(self._snapshot["data_cols"]),
            "last_group_col": self._snapshot["last_group_col"],
            "selection_mode": bool(self._snapshot["selection_mode"]),
            "selection_tool": self._snapshot["selection_tool"],
            "point_size": int(self._snapshot["point_size"]),
            "show_tooltip": bool(self._snapshot["show_tooltip"]),
            "tooltip_columns": list(self._snapshot["tooltip_columns"]),
            "ui_theme": str(self._snapshot["ui_theme"]),
            "language": str(self._snapshot["language"]),
            "color_scheme": str(self._snapshot["color_scheme"]),
            "legend_position": self._snapshot["legend_position"],
            "legend_location": self._snapshot["legend_location"],
            "legend_display_mode": str(self._snapshot["legend_display_mode"]),
            "legend_columns": int(self._snapshot["legend_columns"]),
            "legend_nudge_step": float(self._snapshot["legend_nudge_step"]),
            "legend_offset": tuple(self._snapshot["legend_offset"]),
            "hidden_groups": set(self._snapshot["hidden_groups"]),
            "legend_last_title": self._snapshot["legend_last_title"],
            "legend_last_handles": self._snapshot["legend_last_handles"],
            "legend_last_labels": self._snapshot["legend_last_labels"],
            "recent_files": list(self._snapshot["recent_files"]),
            "line_styles": dict(self._snapshot["line_styles"]),
            "saved_themes": dict(self._snapshot["saved_themes"]),
            "custom_palettes": dict(self._snapshot["custom_palettes"]),
            "custom_shape_sets": dict(self._snapshot["custom_shape_sets"]),
            "legend_item_order": list(self._snapshot["legend_item_order"]),
            "mixing_endmembers": dict(self._snapshot["mixing_endmembers"]),
            "mixing_mixtures": dict(self._snapshot["mixing_mixtures"]),
            "ternary_ranges": dict(self._snapshot["ternary_ranges"]),
            "kde_style": dict(self._snapshot["kde_style"]),
            "marginal_kde_style": dict(self._snapshot["marginal_kde_style"]),
            "ml_last_result": self._snapshot["ml_last_result"],
            "ml_last_model_meta": self._snapshot["ml_last_model_meta"],
            "preserve_import_render_mode": bool(self._snapshot["preserve_import_render_mode"]),
            "available_groups": list(self._snapshot["available_groups"]),
            "visible_groups": _normalize_visible_groups(self._snapshot["visible_groups"]),
            "selected_2d_cols": list(self._snapshot["selected_2d_cols"]),
            "selected_3d_cols": list(self._snapshot["selected_3d_cols"]),
            "selected_ternary_cols": list(self._snapshot["selected_ternary_cols"]),
            "selected_2d_confirmed": bool(self._snapshot["selected_2d_confirmed"]),
            "selected_3d_confirmed": bool(self._snapshot["selected_3d_confirmed"]),
            "selected_ternary_confirmed": bool(self._snapshot["selected_ternary_confirmed"]),
            "standardize_data": bool(self._snapshot["standardize_data"]),
            "initial_render_done": bool(self._snapshot["initial_render_done"]),
            "pca_component_indices": list(self._snapshot["pca_component_indices"]),
            "ternary_auto_zoom": bool(self._snapshot["ternary_auto_zoom"]),
            "ternary_limit_mode": str(self._snapshot["ternary_limit_mode"]),
            "ternary_limit_anchor": str(self._snapshot["ternary_limit_anchor"]),
            "ternary_boundary_percent": float(self._snapshot["ternary_boundary_percent"]),
            "ternary_manual_limits_enabled": bool(self._snapshot["ternary_manual_limits_enabled"]),
            "ternary_manual_limits": dict(self._snapshot["ternary_manual_limits"]),
            "ternary_stretch_mode": str(self._snapshot["ternary_stretch_mode"]),
            "ternary_stretch": bool(self._snapshot["ternary_stretch"]),
            "ternary_factors": list(self._snapshot["ternary_factors"]),
            "model_curve_width": float(self._snapshot["model_curve_width"]),
            "plumbotectonics_curve_width": float(self._snapshot["plumbotectonics_curve_width"]),
            "paleoisochron_width": float(self._snapshot["paleoisochron_width"]),
            "model_age_line_width": float(self._snapshot["model_age_line_width"]),
            "isochron_line_width": float(self._snapshot["isochron_line_width"]),
            "selected_isochron_line_width": float(self._snapshot["selected_isochron_line_width"]),
            "isochron_label_options": dict(self._snapshot["isochron_label_options"]),
            "model_curve_models": (
                list(self._snapshot["model_curve_models"])
                if self._snapshot["model_curve_models"] is not None
                else None
            ),
            "equation_overlays": list(self._snapshot["equation_overlays"]),
            "export_image_options": dict(self._snapshot["export_image_options"]),
        }

    def _sync_state(self) -> None:
        sync_state_store_to_app(self._state, self._snapshot)



