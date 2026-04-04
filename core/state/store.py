"""StateStore for managed AppState domains."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


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

    def __init__(self, state: Any) -> None:
        self._state = state
        self._snapshot: dict[str, Any] = {
            "render_mode": str(getattr(state, "render_mode", "UMAP")),
            "algorithm": str(getattr(state, "algorithm", "UMAP")),
            "umap_params": self._normalize_algorithm_params(
                getattr(state, "umap_params", None)
            ),
            "tsne_params": self._normalize_algorithm_params(
                getattr(state, "tsne_params", None)
            ),
            "pca_params": self._normalize_algorithm_params(
                getattr(state, "pca_params", None)
            ),
            "robust_pca_params": self._normalize_algorithm_params(
                getattr(state, "robust_pca_params", None)
            ),
            "ml_params": self._normalize_algorithm_params(
                getattr(state, "ml_params", None)
            ),
            "v1v2_params": self._normalize_algorithm_params(
                getattr(state, "v1v2_params", None)
            ),
            "plot_style_grid": bool(getattr(state, "plot_style_grid", False)),
            "plot_marker_size": self._normalize_plot_marker_size(
                getattr(state, "plot_marker_size", 60)
            ),
            "plot_marker_alpha": self._normalize_plot_marker_alpha(
                getattr(state, "plot_marker_alpha", 0.8)
            ),
            "show_plot_title": bool(getattr(state, "show_plot_title", False)),
            "plot_dpi": self._normalize_plot_dpi(getattr(state, "plot_dpi", 130)),
            "plot_facecolor": self._normalize_color(
                getattr(state, "plot_facecolor", "#ffffff"),
                "#ffffff",
            ),
            "axes_facecolor": self._normalize_color(
                getattr(state, "axes_facecolor", "#ffffff"),
                "#ffffff",
            ),
            "grid_color": self._normalize_color(
                getattr(state, "grid_color", "#e2e8f0"),
                "#e2e8f0",
            ),
            "grid_linewidth": self._normalize_style_linewidth(
                getattr(state, "grid_linewidth", 0.6),
                default=0.6,
            ),
            "grid_alpha": self._normalize_unit_interval(
                getattr(state, "grid_alpha", 0.7),
                default=0.7,
            ),
            "grid_linestyle": self._normalize_grid_linestyle(
                getattr(state, "grid_linestyle", "--")
            ),
            "tick_direction": self._normalize_tick_direction(
                getattr(state, "tick_direction", "out")
            ),
            "tick_color": self._normalize_color(
                getattr(state, "tick_color", "#1f2937"),
                "#1f2937",
            ),
            "tick_length": self._normalize_tick_length(
                getattr(state, "tick_length", 4.0),
                default=4.0,
            ),
            "tick_width": self._normalize_style_linewidth(
                getattr(state, "tick_width", 0.8),
                default=0.8,
            ),
            "axis_linewidth": self._normalize_style_linewidth(
                getattr(state, "axis_linewidth", 1.0),
                default=1.0,
            ),
            "axis_line_color": self._normalize_color(
                getattr(state, "axis_line_color", "#1f2937"),
                "#1f2937",
            ),
            "minor_ticks": bool(getattr(state, "minor_ticks", False)),
            "minor_tick_length": self._normalize_tick_length(
                getattr(state, "minor_tick_length", 2.5),
                default=2.5,
            ),
            "minor_tick_width": self._normalize_style_linewidth(
                getattr(state, "minor_tick_width", 0.6),
                default=0.6,
            ),
            "show_top_spine": bool(getattr(state, "show_top_spine", True)),
            "show_right_spine": bool(getattr(state, "show_right_spine", True)),
            "minor_grid": bool(getattr(state, "minor_grid", False)),
            "minor_grid_color": self._normalize_color(
                getattr(state, "minor_grid_color", "#e2e8f0"),
                "#e2e8f0",
            ),
            "minor_grid_linewidth": self._normalize_style_linewidth(
                getattr(state, "minor_grid_linewidth", 0.4),
                default=0.4,
            ),
            "minor_grid_alpha": self._normalize_unit_interval(
                getattr(state, "minor_grid_alpha", 0.4),
                default=0.4,
            ),
            "minor_grid_linestyle": self._normalize_grid_linestyle(
                getattr(state, "minor_grid_linestyle", ":")
            ),
            "scatter_show_edge": bool(getattr(state, "scatter_show_edge", True)),
            "scatter_edgecolor": self._normalize_color(
                getattr(state, "scatter_edgecolor", "#1e293b"),
                "#1e293b",
            ),
            "scatter_edgewidth": self._normalize_style_linewidth(
                getattr(state, "scatter_edgewidth", 0.4),
                default=0.4,
            ),
            "label_color": self._normalize_color(
                getattr(state, "label_color", "#1f2937"),
                "#1f2937",
            ),
            "label_weight": self._normalize_text_weight(
                getattr(state, "label_weight", "normal"),
                default="normal",
            ),
            "label_pad": self._normalize_text_pad(
                getattr(state, "label_pad", 6.0),
                default=6.0,
                max_value=60.0,
            ),
            "title_color": self._normalize_color(
                getattr(state, "title_color", "#111827"),
                "#111827",
            ),
            "title_weight": self._normalize_text_weight(
                getattr(state, "title_weight", "bold"),
                default="bold",
            ),
            "title_pad": self._normalize_text_pad(
                getattr(state, "title_pad", 20.0),
                default=20.0,
                max_value=80.0,
            ),
            "legend_frame_on": bool(getattr(state, "legend_frame_on", True)),
            "legend_frame_alpha": self._normalize_unit_interval(
                getattr(state, "legend_frame_alpha", 0.95),
                default=0.95,
            ),
            "legend_frame_facecolor": self._normalize_color(
                getattr(state, "legend_frame_facecolor", "#ffffff"),
                "#ffffff",
            ),
            "legend_frame_edgecolor": self._normalize_color(
                getattr(state, "legend_frame_edgecolor", "#cbd5f5"),
                "#cbd5f5",
            ),
            "adjust_text_force_text": self._normalize_adjust_text_pair(
                getattr(state, "adjust_text_force_text", (0.8, 1.0)),
                default=(0.8, 1.0),
                min_value=0.0,
                max_value=3.0,
            ),
            "adjust_text_force_static": self._normalize_adjust_text_pair(
                getattr(state, "adjust_text_force_static", (0.4, 0.6)),
                default=(0.4, 0.6),
                min_value=0.0,
                max_value=3.0,
            ),
            "adjust_text_expand": self._normalize_adjust_text_pair(
                getattr(state, "adjust_text_expand", (1.08, 1.20)),
                default=(1.08, 1.20),
                min_value=1.0,
                max_value=2.5,
            ),
            "adjust_text_iter_lim": self._normalize_adjust_text_iter_lim(
                getattr(state, "adjust_text_iter_lim", 120)
            ),
            "adjust_text_time_lim": self._normalize_adjust_text_time_lim(
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
            "confidence_level": float(getattr(state, "confidence_level", 0.95)),
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
            "paleoisochron_step": int(getattr(state, "paleoisochron_step", 1000)),
            "paleoisochron_ages": list(getattr(state, "paleoisochron_ages", []) or []),
            "draw_selection_ellipse": bool(getattr(state, "draw_selection_ellipse", False)),
            "marginal_kde_top_size": float(getattr(state, "marginal_kde_top_size", 15.0)),
            "marginal_kde_right_size": float(getattr(state, "marginal_kde_right_size", 15.0)),
            "marginal_kde_max_points": int(getattr(state, "marginal_kde_max_points", 5000)),
            "marginal_kde_bw_adjust": float(getattr(state, "marginal_kde_bw_adjust", 1.0)),
            "marginal_kde_gridsize": int(getattr(state, "marginal_kde_gridsize", 256)),
            "marginal_kde_cut": float(getattr(state, "marginal_kde_cut", 1.0)),
            "marginal_kde_log_transform": bool(getattr(state, "marginal_kde_log_transform", False)),
            "selected_indices": set(getattr(state, "selected_indices", set()) or set()),
            "active_subset_indices": self._normalize_active_subset_indices(
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
            "legend_columns": int(getattr(state, "legend_columns", 0)),
            "legend_nudge_step": float(getattr(state, "legend_nudge_step", 0.02)),
            "legend_offset": tuple(getattr(state, "legend_offset", (0.0, 0.0)) or (0.0, 0.0)),
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
            "visible_groups": self._normalize_visible_groups(getattr(state, "visible_groups", None)),
            "selected_2d_cols": list(getattr(state, "selected_2d_cols", []) or []),
            "selected_3d_cols": list(getattr(state, "selected_3d_cols", []) or []),
            "selected_ternary_cols": list(getattr(state, "selected_ternary_cols", []) or []),
            "selected_2d_confirmed": bool(getattr(state, "selected_2d_confirmed", False)),
            "selected_3d_confirmed": bool(getattr(state, "selected_3d_confirmed", False)),
            "selected_ternary_confirmed": bool(getattr(state, "selected_ternary_confirmed", False)),
            "standardize_data": bool(getattr(state, "standardize_data", True)),
            "initial_render_done": bool(getattr(state, "initial_render_done", False)),
            "pca_component_indices": self._normalize_pca_component_indices(
                getattr(state, "pca_component_indices", None)
            ),
            "ternary_auto_zoom": bool(getattr(state, "ternary_auto_zoom", True)),
            "ternary_limit_mode": self._normalize_ternary_limit_mode(
                getattr(state, "ternary_limit_mode", "min")
            ),
            "ternary_limit_anchor": self._normalize_ternary_limit_anchor(
                getattr(state, "ternary_limit_anchor", "min")
            ),
            "ternary_boundary_percent": self._normalize_ternary_boundary_percent(
                getattr(state, "ternary_boundary_percent", 5.0)
            ),
            "ternary_manual_limits_enabled": bool(
                getattr(state, "ternary_manual_limits_enabled", False)
            ),
            "ternary_manual_limits": self._normalize_ternary_manual_limits(
                getattr(state, "ternary_manual_limits", None)
            ),
            "ternary_stretch_mode": self._normalize_ternary_stretch_mode(
                getattr(state, "ternary_stretch_mode", "power")
            ),
            "ternary_stretch": bool(getattr(state, "ternary_stretch", False)),
            "ternary_factors": self._normalize_ternary_factors(
                getattr(state, "ternary_factors", None)
            ),
            "model_curve_width": float(getattr(state, "model_curve_width", 1.2)),
            "plumbotectonics_curve_width": float(getattr(state, "plumbotectonics_curve_width", 1.2)),
            "paleoisochron_width": float(getattr(state, "paleoisochron_width", 0.9)),
            "model_age_line_width": float(getattr(state, "model_age_line_width", 0.7)),
            "isochron_line_width": float(getattr(state, "isochron_line_width", 1.5)),
            "selected_isochron_line_width": float(getattr(state, "selected_isochron_line_width", 2.0)),
            "isochron_label_options": dict(getattr(state, "isochron_label_options", {}) or {}),
            "equation_overlays": list(getattr(state, "equation_overlays", []) or []),
            "export_image_options": self._normalize_export_options(
                getattr(state, "export_image_options", None)
            ),
        }
        self._sync_state()

    def dispatch(self, action: dict[str, Any]) -> dict[str, Any]:
        """Dispatch an action and return a snapshot copy."""
        action_type = str(action.get("type", "")).upper().strip()

        if action_type == "SET_RENDER_MODE":
            render_mode = str(action.get("render_mode", "UMAP") or "UMAP")
            self._snapshot["render_mode"] = render_mode
            if render_mode in ("UMAP", "tSNE", "PCA", "RobustPCA"):
                self._snapshot["algorithm"] = render_mode

        elif action_type == "SET_ALGORITHM":
            self._snapshot["algorithm"] = str(action.get("algorithm", "UMAP") or "UMAP")

        elif action_type == "SET_UMAP_PARAMS":
            self._snapshot["umap_params"] = self._normalize_algorithm_params(action.get("params"))

        elif action_type == "SET_TSNE_PARAMS":
            self._snapshot["tsne_params"] = self._normalize_algorithm_params(action.get("params"))

        elif action_type == "SET_PCA_PARAMS":
            self._snapshot["pca_params"] = self._normalize_algorithm_params(action.get("params"))

        elif action_type == "SET_ROBUST_PCA_PARAMS":
            self._snapshot["robust_pca_params"] = self._normalize_algorithm_params(
                action.get("params")
            )

        elif action_type == "SET_ML_PARAMS":
            self._snapshot["ml_params"] = self._normalize_algorithm_params(action.get("params"))

        elif action_type == "SET_V1V2_PARAMS":
            self._snapshot["v1v2_params"] = self._normalize_algorithm_params(action.get("params"))

        elif action_type == "SET_PLOT_STYLE_GRID":
            self._snapshot["plot_style_grid"] = bool(action.get("enabled", False))

        elif action_type == "SET_PLOT_MARKER_SIZE":
            self._snapshot["plot_marker_size"] = self._normalize_plot_marker_size(
                action.get("size", 60)
            )

        elif action_type == "SET_PLOT_MARKER_ALPHA":
            self._snapshot["plot_marker_alpha"] = self._normalize_plot_marker_alpha(
                action.get("alpha", 0.8)
            )

        elif action_type == "SET_SHOW_PLOT_TITLE":
            self._snapshot["show_plot_title"] = bool(action.get("show", False))

        elif action_type == "SET_PLOT_DPI":
            self._snapshot["plot_dpi"] = self._normalize_plot_dpi(action.get("dpi", 130))

        elif action_type == "SET_PLOT_FACECOLOR":
            self._snapshot["plot_facecolor"] = self._normalize_color(
                action.get("color", "#ffffff"),
                "#ffffff",
            )

        elif action_type == "SET_AXES_FACECOLOR":
            self._snapshot["axes_facecolor"] = self._normalize_color(
                action.get("color", "#ffffff"),
                "#ffffff",
            )

        elif action_type == "SET_GRID_COLOR":
            self._snapshot["grid_color"] = self._normalize_color(
                action.get("color", "#e2e8f0"),
                "#e2e8f0",
            )

        elif action_type == "SET_GRID_LINEWIDTH":
            self._snapshot["grid_linewidth"] = self._normalize_style_linewidth(
                action.get("width", 0.6),
                default=0.6,
            )

        elif action_type == "SET_GRID_ALPHA":
            self._snapshot["grid_alpha"] = self._normalize_unit_interval(
                action.get("alpha", 0.7),
                default=0.7,
            )

        elif action_type == "SET_GRID_LINESTYLE":
            self._snapshot["grid_linestyle"] = self._normalize_grid_linestyle(
                action.get("linestyle", "--")
            )

        elif action_type == "SET_TICK_DIRECTION":
            self._snapshot["tick_direction"] = self._normalize_tick_direction(
                action.get("direction", "out")
            )

        elif action_type == "SET_TICK_COLOR":
            self._snapshot["tick_color"] = self._normalize_color(
                action.get("color", "#1f2937"),
                "#1f2937",
            )

        elif action_type == "SET_TICK_LENGTH":
            self._snapshot["tick_length"] = self._normalize_tick_length(
                action.get("length", 4.0),
                default=4.0,
            )

        elif action_type == "SET_TICK_WIDTH":
            self._snapshot["tick_width"] = self._normalize_style_linewidth(
                action.get("width", 0.8),
                default=0.8,
            )

        elif action_type == "SET_AXIS_LINEWIDTH":
            self._snapshot["axis_linewidth"] = self._normalize_style_linewidth(
                action.get("width", 1.0),
                default=1.0,
            )

        elif action_type == "SET_AXIS_LINE_COLOR":
            self._snapshot["axis_line_color"] = self._normalize_color(
                action.get("color", "#1f2937"),
                "#1f2937",
            )

        elif action_type == "SET_MINOR_TICKS":
            self._snapshot["minor_ticks"] = bool(action.get("enabled", False))

        elif action_type == "SET_MINOR_TICK_LENGTH":
            self._snapshot["minor_tick_length"] = self._normalize_tick_length(
                action.get("length", 2.5),
                default=2.5,
            )

        elif action_type == "SET_MINOR_TICK_WIDTH":
            self._snapshot["minor_tick_width"] = self._normalize_style_linewidth(
                action.get("width", 0.6),
                default=0.6,
            )

        elif action_type == "SET_SHOW_TOP_SPINE":
            self._snapshot["show_top_spine"] = bool(action.get("show", True))

        elif action_type == "SET_SHOW_RIGHT_SPINE":
            self._snapshot["show_right_spine"] = bool(action.get("show", True))

        elif action_type == "SET_MINOR_GRID":
            self._snapshot["minor_grid"] = bool(action.get("enabled", False))

        elif action_type == "SET_MINOR_GRID_COLOR":
            self._snapshot["minor_grid_color"] = self._normalize_color(
                action.get("color", "#e2e8f0"),
                "#e2e8f0",
            )

        elif action_type == "SET_MINOR_GRID_LINEWIDTH":
            self._snapshot["minor_grid_linewidth"] = self._normalize_style_linewidth(
                action.get("width", 0.4),
                default=0.4,
            )

        elif action_type == "SET_MINOR_GRID_ALPHA":
            self._snapshot["minor_grid_alpha"] = self._normalize_unit_interval(
                action.get("alpha", 0.4),
                default=0.4,
            )

        elif action_type == "SET_MINOR_GRID_LINESTYLE":
            self._snapshot["minor_grid_linestyle"] = self._normalize_grid_linestyle(
                action.get("linestyle", ":")
            )

        elif action_type == "SET_SCATTER_SHOW_EDGE":
            self._snapshot["scatter_show_edge"] = bool(action.get("show", True))

        elif action_type == "SET_SCATTER_EDGECOLOR":
            self._snapshot["scatter_edgecolor"] = self._normalize_color(
                action.get("color", "#1e293b"),
                "#1e293b",
            )

        elif action_type == "SET_SCATTER_EDGEWIDTH":
            self._snapshot["scatter_edgewidth"] = self._normalize_style_linewidth(
                action.get("width", 0.4),
                default=0.4,
            )

        elif action_type == "SET_LABEL_COLOR":
            self._snapshot["label_color"] = self._normalize_color(
                action.get("color", "#1f2937"),
                "#1f2937",
            )

        elif action_type == "SET_LABEL_WEIGHT":
            self._snapshot["label_weight"] = self._normalize_text_weight(
                action.get("weight", "normal"),
                default="normal",
            )

        elif action_type == "SET_LABEL_PAD":
            self._snapshot["label_pad"] = self._normalize_text_pad(
                action.get("pad", 6.0),
                default=6.0,
                max_value=60.0,
            )

        elif action_type == "SET_TITLE_COLOR":
            self._snapshot["title_color"] = self._normalize_color(
                action.get("color", "#111827"),
                "#111827",
            )

        elif action_type == "SET_TITLE_WEIGHT":
            self._snapshot["title_weight"] = self._normalize_text_weight(
                action.get("weight", "bold"),
                default="bold",
            )

        elif action_type == "SET_TITLE_PAD":
            self._snapshot["title_pad"] = self._normalize_text_pad(
                action.get("pad", 20.0),
                default=20.0,
                max_value=80.0,
            )

        elif action_type == "SET_LEGEND_FRAME_ON":
            self._snapshot["legend_frame_on"] = bool(action.get("enabled", True))

        elif action_type == "SET_LEGEND_FRAME_ALPHA":
            self._snapshot["legend_frame_alpha"] = self._normalize_unit_interval(
                action.get("alpha", 0.95),
                default=0.95,
            )

        elif action_type == "SET_LEGEND_FRAME_FACECOLOR":
            self._snapshot["legend_frame_facecolor"] = self._normalize_color(
                action.get("color", "#ffffff"),
                "#ffffff",
            )

        elif action_type == "SET_LEGEND_FRAME_EDGECOLOR":
            self._snapshot["legend_frame_edgecolor"] = self._normalize_color(
                action.get("color", "#cbd5f5"),
                "#cbd5f5",
            )

        elif action_type == "SET_ADJUST_TEXT_FORCE_TEXT":
            self._snapshot["adjust_text_force_text"] = self._normalize_adjust_text_pair(
                action.get("force", (0.8, 1.0)),
                default=(0.8, 1.0),
                min_value=0.0,
                max_value=3.0,
            )

        elif action_type == "SET_ADJUST_TEXT_FORCE_STATIC":
            self._snapshot["adjust_text_force_static"] = self._normalize_adjust_text_pair(
                action.get("force", (0.4, 0.6)),
                default=(0.4, 0.6),
                min_value=0.0,
                max_value=3.0,
            )

        elif action_type == "SET_ADJUST_TEXT_EXPAND":
            self._snapshot["adjust_text_expand"] = self._normalize_adjust_text_pair(
                action.get("expand", (1.08, 1.20)),
                default=(1.08, 1.20),
                min_value=1.0,
                max_value=2.5,
            )

        elif action_type == "SET_ADJUST_TEXT_ITER_LIM":
            self._snapshot["adjust_text_iter_lim"] = self._normalize_adjust_text_iter_lim(
                action.get("iter_lim", 120)
            )

        elif action_type == "SET_ADJUST_TEXT_TIME_LIM":
            self._snapshot["adjust_text_time_lim"] = self._normalize_adjust_text_time_lim(
                action.get("time_lim", 0.25)
            )

        elif action_type == "SET_SHOW_KDE":
            self._snapshot["show_kde"] = bool(action.get("show", False))

        elif action_type == "SET_SHOW_MARGINAL_KDE":
            self._snapshot["show_marginal_kde"] = bool(action.get("show", False))

        elif action_type == "SET_SHOW_EQUATION_OVERLAYS":
            self._snapshot["show_equation_overlays"] = bool(action.get("show", False))

        elif action_type == "SET_GEO_MODEL_NAME":
            self._snapshot["geo_model_name"] = str(
                action.get("model_name", "Stacey & Kramers (2nd Stage)")
            )

        elif action_type == "SET_PALEO_LABEL_REFRESHING":
            self._snapshot["paleo_label_refreshing"] = bool(action.get("refreshing", False))

        elif action_type == "SET_OVERLAY_LABEL_REFRESHING":
            self._snapshot["overlay_label_refreshing"] = bool(action.get("refreshing", False))

        elif action_type == "SET_OVERLAY_CURVE_LABEL_DATA":
            self._snapshot["overlay_curve_label_data"] = list(action.get("data") or [])

        elif action_type == "SET_PALEOISOCHRON_LABEL_DATA":
            self._snapshot["paleoisochron_label_data"] = list(action.get("data") or [])

        elif action_type == "SET_PLUMBOTECTONICS_LABEL_DATA":
            self._snapshot["plumbotectonics_label_data"] = list(action.get("data") or [])

        elif action_type == "SET_PLUMBOTECTONICS_ISOAGE_LABEL_DATA":
            self._snapshot["plumbotectonics_isoage_label_data"] = list(action.get("data") or [])

        elif action_type == "SET_OVERLAY_ARTISTS":
            self._snapshot["overlay_artists"] = dict(action.get("artists") or {})

        elif action_type == "SET_LAST_EMBEDDING":
            self._snapshot["last_embedding"] = action.get("embedding")
            self._snapshot["last_embedding_type"] = str(action.get("embedding_type", "") or "")

        elif action_type == "SET_SELECTED_ISOCHRON_DATA":
            self._snapshot["selected_isochron_data"] = action.get("data")

        elif action_type == "SET_EMBEDDING_TASK_TOKEN":
            self._snapshot["embedding_task_token"] = int(action.get("task_token", 0))

        elif action_type == "SET_EMBEDDING_TASK_RUNNING":
            self._snapshot["embedding_task_running"] = bool(action.get("running", False))

        elif action_type == "SET_MARGINAL_AXES":
            self._snapshot["marginal_axes"] = action.get("marginal_axes")

        elif action_type == "SET_PCA_DIAGNOSTICS":
            if "last_pca_variance" in action:
                self._snapshot["last_pca_variance"] = action.get("last_pca_variance")
            if "last_pca_components" in action:
                self._snapshot["last_pca_components"] = action.get("last_pca_components")
            if "current_feature_names" in action:
                self._snapshot["current_feature_names"] = action.get("current_feature_names")

        elif action_type == "SET_ADJUST_TEXT_IN_PROGRESS":
            self._snapshot["adjust_text_in_progress"] = bool(action.get("in_progress", False))

        elif action_type == "SET_CONFIDENCE_LEVEL":
            self._snapshot["confidence_level"] = float(action.get("level", 0.95))

        elif action_type == "SET_CURRENT_PALETTE":
            self._snapshot["current_palette"] = dict(action.get("palette") or {})

        elif action_type == "SET_GROUP_MARKER_MAP":
            self._snapshot["group_marker_map"] = dict(action.get("marker_map") or {})

        elif action_type == "SET_CURRENT_PLOT_TITLE":
            self._snapshot["current_plot_title"] = str(action.get("title", ""))

        elif action_type == "SET_LAST_2D_COLS":
            columns = action.get("columns")
            self._snapshot["last_2d_cols"] = list(columns or []) if columns is not None else None

        elif action_type == "SET_SHOW_MODEL_CURVES":
            self._snapshot["show_model_curves"] = bool(action.get("show", False))

        elif action_type == "SET_SHOW_PLUMBOTECTONICS_CURVES":
            self._snapshot["show_plumbotectonics_curves"] = bool(action.get("show", False))

        elif action_type == "SET_SHOW_PALEOISOCHRONS":
            self._snapshot["show_paleoisochrons"] = bool(action.get("show", False))

        elif action_type == "SET_SHOW_MODEL_AGE_LINES":
            self._snapshot["show_model_age_lines"] = bool(action.get("show", False))

        elif action_type == "SET_SHOW_GROWTH_CURVES":
            self._snapshot["show_growth_curves"] = bool(action.get("show", False))

        elif action_type == "SET_SHOW_ISOCHRONS":
            self._snapshot["show_isochrons"] = bool(action.get("show", False))

        elif action_type == "SET_ISOCHRON_ERROR_COLUMNS":
            self._snapshot["isochron_error_mode"] = "columns"
            self._snapshot["isochron_sx_col"] = str(action.get("sx_col", "") or "")
            self._snapshot["isochron_sy_col"] = str(action.get("sy_col", "") or "")
            self._snapshot["isochron_rxy_col"] = str(action.get("rxy_col", "") or "")

        elif action_type == "SET_ISOCHRON_ERROR_FIXED":
            self._snapshot["isochron_error_mode"] = "fixed"
            self._snapshot["isochron_sx_value"] = float(action.get("sx_value", 0.001))
            self._snapshot["isochron_sy_value"] = float(action.get("sy_value", 0.001))
            self._snapshot["isochron_rxy_value"] = float(action.get("rxy_value", 0.0))

        elif action_type == "SET_ISOCHRON_RESULTS":
            self._snapshot["isochron_results"] = dict(action.get("results") or {})

        elif action_type == "SET_PLUMBOTECTONICS_GROUP_VISIBILITY":
            self._snapshot["plumbotectonics_group_visibility"] = dict(
                action.get("visibility") or {}
            )

        elif action_type == "SET_USE_REAL_AGE_FOR_MU_KAPPA":
            self._snapshot["use_real_age_for_mu_kappa"] = bool(action.get("enabled", False))

        elif action_type == "SET_MU_KAPPA_AGE_COL":
            self._snapshot["mu_kappa_age_col"] = action.get("column")

        elif action_type == "SET_PLUMBOTECTONICS_VARIANT":
            self._snapshot["plumbotectonics_variant"] = str(action.get("variant", "0"))

        elif action_type == "SET_PALEOISOCHRON_STEP":
            self._snapshot["paleoisochron_step"] = int(action.get("step", 1000))

        elif action_type == "SET_PALEOISOCHRON_AGES":
            self._snapshot["paleoisochron_ages"] = list(action.get("ages") or [])

        elif action_type == "SET_DRAW_SELECTION_ELLIPSE":
            self._snapshot["draw_selection_ellipse"] = bool(action.get("enabled", False))

        elif action_type == "SET_MARGINAL_KDE_LAYOUT":
            top_size = action.get("top_size")
            right_size = action.get("right_size")
            if top_size is not None:
                self._snapshot["marginal_kde_top_size"] = self._normalize_marginal_size(top_size)
            if right_size is not None:
                self._snapshot["marginal_kde_right_size"] = self._normalize_marginal_size(right_size)

        elif action_type == "SET_MARGINAL_KDE_COMPUTE_OPTIONS":
            max_points = action.get("max_points")
            bw_adjust = action.get("bw_adjust")
            gridsize = action.get("gridsize")
            cut = action.get("cut")
            log_transform = action.get("log_transform")

            if max_points is not None:
                self._snapshot["marginal_kde_max_points"] = self._normalize_max_points(max_points)
            if bw_adjust is not None:
                self._snapshot["marginal_kde_bw_adjust"] = self._normalize_bw_adjust(bw_adjust)
            if gridsize is not None:
                self._snapshot["marginal_kde_gridsize"] = self._normalize_gridsize(gridsize)
            if cut is not None:
                self._snapshot["marginal_kde_cut"] = self._normalize_cut(cut)
            if log_transform is not None:
                self._snapshot["marginal_kde_log_transform"] = bool(log_transform)

        elif action_type == "SET_POINT_SIZE":
            self._snapshot["point_size"] = max(1, int(action.get("point_size", 60)))

        elif action_type == "SET_SHOW_TOOLTIP":
            self._snapshot["show_tooltip"] = bool(action.get("show", False))

        elif action_type == "SET_TOOLTIP_COLUMNS":
            self._snapshot["tooltip_columns"] = [str(col) for col in list(action.get("columns") or [])]

        elif action_type == "SET_UI_THEME":
            self._snapshot["ui_theme"] = str(action.get("theme", "Modern Light") or "Modern Light")

        elif action_type == "SET_LANGUAGE_CODE":
            self._snapshot["language"] = str(action.get("code"))

        elif action_type == "SET_COLOR_SCHEME":
            self._snapshot["color_scheme"] = str(action.get("color_scheme"))

        elif action_type == "SET_LEGEND_POSITION":
            self._snapshot["legend_position"] = action.get("position")

        elif action_type == "SET_LEGEND_LOCATION":
            self._snapshot["legend_location"] = action.get("location")

        elif action_type == "SET_LEGEND_COLUMNS":
            self._snapshot["legend_columns"] = int(action.get("columns", 0))

        elif action_type == "SET_LEGEND_NUDGE_STEP":
            self._snapshot["legend_nudge_step"] = float(action.get("step", 0.02))

        elif action_type == "SET_LEGEND_OFFSET":
            offset = action.get("offset")
            self._snapshot["legend_offset"] = tuple(offset) if offset is not None else (0.0, 0.0)

        elif action_type == "SET_LEGEND_SNAPSHOT":
            self._snapshot["legend_last_title"] = action.get("title")
            self._snapshot["legend_last_handles"] = action.get("handles")
            self._snapshot["legend_last_labels"] = action.get("labels")

        elif action_type == "SET_RECENT_FILES":
            self._snapshot["recent_files"] = list(action.get("files") or [])

        elif action_type == "SET_LINE_STYLES":
            self._snapshot["line_styles"] = dict(action.get("line_styles") or {})

        elif action_type == "SET_SAVED_THEMES":
            self._snapshot["saved_themes"] = dict(action.get("themes") or {})

        elif action_type == "SET_CUSTOM_PALETTES":
            self._snapshot["custom_palettes"] = dict(action.get("palettes") or {})

        elif action_type == "SET_CUSTOM_SHAPE_SETS":
            self._snapshot["custom_shape_sets"] = dict(action.get("shape_sets") or {})

        elif action_type == "SET_LEGEND_ITEM_ORDER":
            self._snapshot["legend_item_order"] = list(action.get("order") or [])

        elif action_type == "SET_MIXING_ENDMEMBERS":
            self._snapshot["mixing_endmembers"] = dict(action.get("mapping") or {})

        elif action_type == "SET_MIXING_MIXTURES":
            self._snapshot["mixing_mixtures"] = dict(action.get("mapping") or {})

        elif action_type == "SET_TERNARY_RANGES":
            self._snapshot["ternary_ranges"] = dict(action.get("ranges") or {})

        elif action_type == "SET_KDE_STYLE":
            self._snapshot["kde_style"] = dict(action.get("style") or {})

        elif action_type == "SET_MARGINAL_KDE_STYLE":
            self._snapshot["marginal_kde_style"] = dict(action.get("style") or {})

        elif action_type == "SET_ML_LAST_RESULT":
            self._snapshot["ml_last_result"] = action.get("result")

        elif action_type == "SET_ML_LAST_MODEL_META":
            self._snapshot["ml_last_model_meta"] = action.get("meta")

        elif action_type == "SET_PRESERVE_IMPORT_RENDER_MODE":
            self._snapshot["preserve_import_render_mode"] = bool(action.get("enabled", False))

        elif action_type == "SET_SELECTED_INDICES":
            indices = self._to_index_set(action.get("indices", []))
            self._snapshot["selected_indices"] = indices

        elif action_type == "SET_ACTIVE_SUBSET_INDICES":
            self._snapshot["active_subset_indices"] = self._normalize_active_subset_indices(
                action.get("indices")
            )

        elif action_type == "ADD_SELECTED_INDICES":
            indices = self._to_index_set(action.get("indices", []))
            self._snapshot["selected_indices"].update(indices)

        elif action_type == "REMOVE_SELECTED_INDICES":
            indices = self._to_index_set(action.get("indices", []))
            for index in indices:
                self._snapshot["selected_indices"].discard(index)

        elif action_type == "CLEAR_SELECTED_INDICES":
            self._snapshot["selected_indices"].clear()

        elif action_type == "CLEAR_SELECTION":
            self._snapshot["selected_indices"].clear()
            self._snapshot["selection_mode"] = False

        elif action_type == "SET_SELECTION_MODE":
            self._snapshot["selection_mode"] = bool(action.get("enabled", False))

        elif action_type == "SET_SELECTION_TOOL":
            tool = action.get("tool")
            self._snapshot["selection_tool"] = str(tool) if tool is not None else None
            self._snapshot["selection_mode"] = tool is not None

        elif action_type == "SET_DATAFRAME_SOURCE":
            self._snapshot["df_global"] = action.get("df")
            self._snapshot["file_path"] = action.get("file_path")
            self._snapshot["sheet_name"] = action.get("sheet_name")

        elif action_type == "SET_FILE_PATH":
            self._snapshot["file_path"] = str(action.get("file_path"))

        elif action_type == "SET_SHEET_NAME":
            self._snapshot["sheet_name"] = action.get("sheet_name")

        elif action_type == "BUMP_DATA_VERSION":
            self._snapshot["data_version"] = int(self._snapshot.get("data_version", 0)) + 1
            cache = getattr(self._state, "embedding_cache", None)
            if cache is not None and hasattr(cache, "clear"):
                try:
                    cache.clear()
                except Exception:
                    pass

        elif action_type == "SET_DATA_VERSION":
            self._snapshot["data_version"] = int(action.get("version", 0))

        elif action_type == "SET_GROUP_DATA_COLUMNS":
            self._snapshot["group_cols"] = [str(col) for col in list(action.get("group_cols") or [])]
            self._snapshot["data_cols"] = [str(col) for col in list(action.get("data_cols") or [])]

        elif action_type == "SET_LAST_GROUP_COL":
            group_col = action.get("group_col")
            self._snapshot["last_group_col"] = str(group_col) if group_col is not None else None

        elif action_type == "SET_SELECTED_2D_COLUMNS":
            self._snapshot["selected_2d_cols"] = list(action.get("columns") or [])
            self._snapshot["selected_2d_confirmed"] = bool(action.get("confirmed", False))

        elif action_type == "SET_SELECTED_3D_COLUMNS":
            self._snapshot["selected_3d_cols"] = list(action.get("columns") or [])
            self._snapshot["selected_3d_confirmed"] = bool(action.get("confirmed", False))

        elif action_type == "SET_SELECTED_TERNARY_COLUMNS":
            self._snapshot["selected_ternary_cols"] = list(action.get("columns") or [])
            self._snapshot["selected_ternary_confirmed"] = bool(action.get("confirmed", False))

        elif action_type == "SET_STANDARDIZE_DATA":
            self._snapshot["standardize_data"] = bool(action.get("enabled", False))

        elif action_type == "SET_INITIAL_RENDER_DONE":
            self._snapshot["initial_render_done"] = bool(action.get("done", False))

        elif action_type == "SET_PCA_COMPONENT_INDICES":
            self._snapshot["pca_component_indices"] = self._normalize_pca_component_indices(
                action.get("indices")
            )

        elif action_type == "SET_TERNARY_AUTO_ZOOM":
            self._snapshot["ternary_auto_zoom"] = bool(action.get("enabled", False))

        elif action_type == "SET_TERNARY_LIMIT_MODE":
            self._snapshot["ternary_limit_mode"] = self._normalize_ternary_limit_mode(
                action.get("mode")
            )

        elif action_type == "SET_TERNARY_LIMIT_ANCHOR":
            self._snapshot["ternary_limit_anchor"] = self._normalize_ternary_limit_anchor(
                action.get("anchor")
            )

        elif action_type == "SET_TERNARY_BOUNDARY_PERCENT":
            self._snapshot["ternary_boundary_percent"] = self._normalize_ternary_boundary_percent(
                action.get("percent")
            )

        elif action_type == "SET_TERNARY_MANUAL_LIMITS_ENABLED":
            self._snapshot["ternary_manual_limits_enabled"] = bool(action.get("enabled", False))

        elif action_type == "SET_TERNARY_MANUAL_LIMITS":
            self._snapshot["ternary_manual_limits"] = self._normalize_ternary_manual_limits(
                action.get("limits")
            )

        elif action_type == "SET_TERNARY_STRETCH_MODE":
            self._snapshot["ternary_stretch_mode"] = self._normalize_ternary_stretch_mode(
                action.get("mode")
            )

        elif action_type == "SET_TERNARY_STRETCH":
            self._snapshot["ternary_stretch"] = bool(action.get("enabled", False))

        elif action_type == "SET_TERNARY_FACTORS":
            self._snapshot["ternary_factors"] = self._normalize_ternary_factors(action.get("factors"))

        elif action_type == "SET_MODEL_CURVE_WIDTH":
            self._snapshot["model_curve_width"] = float(action.get("width", 1.2))

        elif action_type == "SET_PLUMBOTECTONICS_CURVE_WIDTH":
            self._snapshot["plumbotectonics_curve_width"] = float(action.get("width", 1.2))

        elif action_type == "SET_PALEOISOCHRON_WIDTH":
            self._snapshot["paleoisochron_width"] = float(action.get("width", 0.9))

        elif action_type == "SET_MODEL_AGE_LINE_WIDTH":
            self._snapshot["model_age_line_width"] = float(action.get("width", 0.7))

        elif action_type == "SET_ISOCHRON_LINE_WIDTH":
            self._snapshot["isochron_line_width"] = float(action.get("width", 1.5))

        elif action_type == "SET_SELECTED_ISOCHRON_LINE_WIDTH":
            self._snapshot["selected_isochron_line_width"] = float(action.get("width", 2.0))

        elif action_type == "SET_ISOCHRON_LABEL_OPTIONS":
            self._snapshot["isochron_label_options"] = dict(action.get("options") or {})

        elif action_type == "SET_EQUATION_OVERLAYS":
            self._snapshot["equation_overlays"] = list(action.get("overlays") or [])

        elif action_type == "RESET_COLUMN_SELECTION":
            self._snapshot["selected_2d_cols"] = []
            self._snapshot["selected_3d_cols"] = []
            self._snapshot["selected_ternary_cols"] = []
            self._snapshot["selected_2d_confirmed"] = False
            self._snapshot["selected_3d_confirmed"] = False
            self._snapshot["selected_ternary_confirmed"] = False
            self._snapshot["available_groups"] = []
            self._snapshot["visible_groups"] = None

        elif action_type == "SYNC_AVAILABLE_VISIBLE_GROUPS":
            groups = [str(group) for group in list(action.get("all_groups") or [])]
            self._snapshot["available_groups"] = groups
            visible_groups = self._snapshot["visible_groups"]
            if visible_groups:
                filtered = [group for group in visible_groups if group in groups]
                self._snapshot["visible_groups"] = filtered if filtered else None

        elif action_type == "SET_VISIBLE_GROUPS":
            self._snapshot["visible_groups"] = self._normalize_visible_groups(action.get("groups"))

        elif action_type == "SET_EXPORT_IMAGE_OPTIONS":
            merged = dict(self._snapshot["export_image_options"])
            payload = dict(action.get("options") or {})
            for key, value in payload.items():
                if value is not None:
                    merged[key] = value
            self._snapshot["export_image_options"] = self._normalize_export_options(merged)

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
            "paleoisochron_step": int(self._snapshot["paleoisochron_step"]),
            "paleoisochron_ages": list(self._snapshot["paleoisochron_ages"]),
            "draw_selection_ellipse": bool(self._snapshot["draw_selection_ellipse"]),
            "marginal_kde_top_size": float(self._snapshot["marginal_kde_top_size"]),
            "marginal_kde_right_size": float(self._snapshot["marginal_kde_right_size"]),
            "marginal_kde_max_points": int(self._snapshot["marginal_kde_max_points"]),
            "marginal_kde_bw_adjust": float(self._snapshot["marginal_kde_bw_adjust"]),
            "marginal_kde_gridsize": int(self._snapshot["marginal_kde_gridsize"]),
            "marginal_kde_cut": float(self._snapshot["marginal_kde_cut"]),
            "marginal_kde_log_transform": bool(self._snapshot["marginal_kde_log_transform"]),
            "selected_indices": set(self._snapshot["selected_indices"]),
            "active_subset_indices": self._normalize_active_subset_indices(
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
            "legend_columns": int(self._snapshot["legend_columns"]),
            "legend_nudge_step": float(self._snapshot["legend_nudge_step"]),
            "legend_offset": tuple(self._snapshot["legend_offset"]),
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
            "visible_groups": self._normalize_visible_groups(self._snapshot["visible_groups"]),
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
            "equation_overlays": list(self._snapshot["equation_overlays"]),
            "export_image_options": dict(self._snapshot["export_image_options"]),
        }

    def _sync_state(self) -> None:
        render_mode = str(self._snapshot["render_mode"])
        self._state.render_mode = render_mode
        algorithm = str(self._snapshot["algorithm"])
        if render_mode in ("UMAP", "tSNE", "PCA", "RobustPCA"):
            algorithm = render_mode
            self._snapshot["algorithm"] = algorithm
        self._state.algorithm = algorithm
        self._state.umap_params = dict(self._snapshot["umap_params"])
        self._state.tsne_params = dict(self._snapshot["tsne_params"])
        self._state.pca_params = dict(self._snapshot["pca_params"])
        self._state.robust_pca_params = dict(self._snapshot["robust_pca_params"])
        self._state.ml_params = dict(self._snapshot["ml_params"])
        self._state.v1v2_params = dict(self._snapshot["v1v2_params"])
        self._state.plot_style_grid = bool(self._snapshot["plot_style_grid"])
        self._state.plot_marker_size = int(self._snapshot["plot_marker_size"])
        self._state.plot_marker_alpha = float(self._snapshot["plot_marker_alpha"])
        self._state.show_plot_title = bool(self._snapshot["show_plot_title"])
        self._state.plot_dpi = int(self._snapshot["plot_dpi"])
        self._state.plot_facecolor = str(self._snapshot["plot_facecolor"])
        self._state.axes_facecolor = str(self._snapshot["axes_facecolor"])
        self._state.grid_color = str(self._snapshot["grid_color"])
        self._state.grid_linewidth = float(self._snapshot["grid_linewidth"])
        self._state.grid_alpha = float(self._snapshot["grid_alpha"])
        self._state.grid_linestyle = str(self._snapshot["grid_linestyle"])
        self._state.tick_direction = str(self._snapshot["tick_direction"])
        self._state.tick_color = str(self._snapshot["tick_color"])
        self._state.tick_length = float(self._snapshot["tick_length"])
        self._state.tick_width = float(self._snapshot["tick_width"])
        self._state.axis_linewidth = float(self._snapshot["axis_linewidth"])
        self._state.axis_line_color = str(self._snapshot["axis_line_color"])
        self._state.minor_ticks = bool(self._snapshot["minor_ticks"])
        self._state.minor_tick_length = float(self._snapshot["minor_tick_length"])
        self._state.minor_tick_width = float(self._snapshot["minor_tick_width"])
        self._state.show_top_spine = bool(self._snapshot["show_top_spine"])
        self._state.show_right_spine = bool(self._snapshot["show_right_spine"])
        self._state.minor_grid = bool(self._snapshot["minor_grid"])
        self._state.minor_grid_color = str(self._snapshot["minor_grid_color"])
        self._state.minor_grid_linewidth = float(self._snapshot["minor_grid_linewidth"])
        self._state.minor_grid_alpha = float(self._snapshot["minor_grid_alpha"])
        self._state.minor_grid_linestyle = str(self._snapshot["minor_grid_linestyle"])
        self._state.scatter_show_edge = bool(self._snapshot["scatter_show_edge"])
        self._state.scatter_edgecolor = str(self._snapshot["scatter_edgecolor"])
        self._state.scatter_edgewidth = float(self._snapshot["scatter_edgewidth"])
        self._state.label_color = str(self._snapshot["label_color"])
        self._state.label_weight = str(self._snapshot["label_weight"])
        self._state.label_pad = float(self._snapshot["label_pad"])
        self._state.title_color = str(self._snapshot["title_color"])
        self._state.title_weight = str(self._snapshot["title_weight"])
        self._state.title_pad = float(self._snapshot["title_pad"])
        self._state.legend_frame_on = bool(self._snapshot["legend_frame_on"])
        self._state.legend_frame_alpha = float(self._snapshot["legend_frame_alpha"])
        self._state.legend_frame_facecolor = str(self._snapshot["legend_frame_facecolor"])
        self._state.legend_frame_edgecolor = str(self._snapshot["legend_frame_edgecolor"])
        self._state.adjust_text_force_text = tuple(self._snapshot["adjust_text_force_text"])
        self._state.adjust_text_force_static = tuple(self._snapshot["adjust_text_force_static"])
        self._state.adjust_text_expand = tuple(self._snapshot["adjust_text_expand"])
        self._state.adjust_text_iter_lim = int(self._snapshot["adjust_text_iter_lim"])
        self._state.adjust_text_time_lim = float(self._snapshot["adjust_text_time_lim"])
        self._state.show_kde = bool(self._snapshot["show_kde"])
        self._state.show_marginal_kde = bool(self._snapshot["show_marginal_kde"])
        self._state.show_equation_overlays = bool(self._snapshot["show_equation_overlays"])
        self._state.geo_model_name = str(self._snapshot["geo_model_name"])
        self._state.paleo_label_refreshing = bool(self._snapshot["paleo_label_refreshing"])
        self._state.overlay_label_refreshing = bool(self._snapshot["overlay_label_refreshing"])
        self._state.overlay_curve_label_data = list(self._snapshot["overlay_curve_label_data"])
        self._state.paleoisochron_label_data = list(self._snapshot["paleoisochron_label_data"])
        self._state.plumbotectonics_label_data = list(self._snapshot["plumbotectonics_label_data"])
        self._state.plumbotectonics_isoage_label_data = list(
            self._snapshot["plumbotectonics_isoage_label_data"]
        )
        self._state.overlay_artists = dict(self._snapshot["overlay_artists"])
        self._state.last_embedding = self._snapshot["last_embedding"]
        self._state.last_embedding_type = str(self._snapshot["last_embedding_type"])
        self._state.selected_isochron_data = self._snapshot["selected_isochron_data"]
        self._state.embedding_task_token = int(self._snapshot["embedding_task_token"])
        self._state.embedding_task_running = bool(self._snapshot["embedding_task_running"])
        self._state.marginal_axes = self._snapshot["marginal_axes"]
        self._state.last_pca_variance = self._snapshot["last_pca_variance"]
        self._state.last_pca_components = self._snapshot["last_pca_components"]
        self._state.current_feature_names = self._snapshot["current_feature_names"]
        self._state.adjust_text_in_progress = bool(self._snapshot["adjust_text_in_progress"])
        self._state.confidence_level = float(self._snapshot["confidence_level"])
        self._state.current_palette = dict(self._snapshot["current_palette"])
        self._state.group_marker_map = dict(self._snapshot["group_marker_map"])
        self._state.current_plot_title = str(self._snapshot["current_plot_title"])
        self._state.last_2d_cols = (
            list(self._snapshot["last_2d_cols"])
            if self._snapshot["last_2d_cols"] is not None
            else None
        )
        self._state.show_model_curves = bool(self._snapshot["show_model_curves"])
        self._state.show_plumbotectonics_curves = bool(self._snapshot["show_plumbotectonics_curves"])
        self._state.show_paleoisochrons = bool(self._snapshot["show_paleoisochrons"])
        self._state.show_model_age_lines = bool(self._snapshot["show_model_age_lines"])
        self._state.show_growth_curves = bool(self._snapshot["show_growth_curves"])
        self._state.show_isochrons = bool(self._snapshot["show_isochrons"])
        self._state.isochron_error_mode = str(self._snapshot["isochron_error_mode"])
        self._state.isochron_sx_col = str(self._snapshot["isochron_sx_col"])
        self._state.isochron_sy_col = str(self._snapshot["isochron_sy_col"])
        self._state.isochron_rxy_col = str(self._snapshot["isochron_rxy_col"])
        self._state.isochron_sx_value = float(self._snapshot["isochron_sx_value"])
        self._state.isochron_sy_value = float(self._snapshot["isochron_sy_value"])
        self._state.isochron_rxy_value = float(self._snapshot["isochron_rxy_value"])
        self._state.isochron_results = dict(self._snapshot["isochron_results"])
        self._state.plumbotectonics_group_visibility = dict(
            self._snapshot["plumbotectonics_group_visibility"]
        )
        self._state.use_real_age_for_mu_kappa = bool(self._snapshot["use_real_age_for_mu_kappa"])
        self._state.mu_kappa_age_col = self._snapshot["mu_kappa_age_col"]
        self._state.plumbotectonics_variant = str(self._snapshot["plumbotectonics_variant"])
        self._state.paleoisochron_step = int(self._snapshot["paleoisochron_step"])
        self._state.paleoisochron_ages = list(self._snapshot["paleoisochron_ages"])
        self._state.draw_selection_ellipse = bool(self._snapshot["draw_selection_ellipse"])
        self._state.marginal_kde_top_size = float(self._snapshot["marginal_kde_top_size"])
        self._state.marginal_kde_right_size = float(self._snapshot["marginal_kde_right_size"])
        self._state.marginal_kde_max_points = int(self._snapshot["marginal_kde_max_points"])
        self._state.marginal_kde_bw_adjust = float(self._snapshot["marginal_kde_bw_adjust"])
        self._state.marginal_kde_gridsize = int(self._snapshot["marginal_kde_gridsize"])
        self._state.marginal_kde_cut = float(self._snapshot["marginal_kde_cut"])
        self._state.marginal_kde_log_transform = bool(self._snapshot["marginal_kde_log_transform"])

        self._state.selected_indices = set(self._snapshot["selected_indices"])
        self._state.active_subset_indices = self._normalize_active_subset_indices(
            self._snapshot["active_subset_indices"]
        )
        self._state.df_global = self._snapshot["df_global"]
        self._state.file_path = self._snapshot["file_path"]
        self._state.sheet_name = self._snapshot["sheet_name"]
        self._state.data_version = int(self._snapshot["data_version"])
        self._state.group_cols = list(self._snapshot["group_cols"])
        self._state.data_cols = list(self._snapshot["data_cols"])
        self._state.last_group_col = self._snapshot["last_group_col"]
        self._state.selection_mode = bool(self._snapshot["selection_mode"])
        self._state.selection_tool = self._snapshot["selection_tool"]
        self._state.point_size = int(self._snapshot["point_size"])
        self._state.show_tooltip = bool(self._snapshot["show_tooltip"])
        self._state.tooltip_columns = list(self._snapshot["tooltip_columns"])
        self._state.ui_theme = str(self._snapshot["ui_theme"])
        self._state.language = str(self._snapshot["language"])
        self._state.color_scheme = str(self._snapshot["color_scheme"])
        self._state.legend_position = self._snapshot["legend_position"]
        self._state.legend_location = self._snapshot["legend_location"]
        self._state.legend_columns = int(self._snapshot["legend_columns"])
        self._state.legend_nudge_step = float(self._snapshot["legend_nudge_step"])
        self._state.legend_offset = tuple(self._snapshot["legend_offset"])
        self._state.legend_last_title = self._snapshot["legend_last_title"]
        self._state.legend_last_handles = self._snapshot["legend_last_handles"]
        self._state.legend_last_labels = self._snapshot["legend_last_labels"]
        self._state.recent_files = list(self._snapshot["recent_files"])
        self._state.line_styles = dict(self._snapshot["line_styles"])
        self._state.saved_themes = dict(self._snapshot["saved_themes"])
        self._state.custom_palettes = dict(self._snapshot["custom_palettes"])
        self._state.custom_shape_sets = dict(self._snapshot["custom_shape_sets"])
        self._state.legend_item_order = list(self._snapshot["legend_item_order"])
        self._state.mixing_endmembers = dict(self._snapshot["mixing_endmembers"])
        self._state.mixing_mixtures = dict(self._snapshot["mixing_mixtures"])
        self._state.ternary_ranges = dict(self._snapshot["ternary_ranges"])
        self._state.kde_style = dict(self._snapshot["kde_style"])
        self._state.marginal_kde_style = dict(self._snapshot["marginal_kde_style"])
        self._state.ml_last_result = self._snapshot["ml_last_result"]
        self._state.ml_last_model_meta = self._snapshot["ml_last_model_meta"]
        self._state.preserve_import_render_mode = bool(self._snapshot["preserve_import_render_mode"])
        self._state.available_groups = list(self._snapshot["available_groups"])
        self._state.visible_groups = self._normalize_visible_groups(self._snapshot["visible_groups"])
        self._state.selected_2d_cols = list(self._snapshot["selected_2d_cols"])
        self._state.selected_3d_cols = list(self._snapshot["selected_3d_cols"])
        self._state.selected_ternary_cols = list(self._snapshot["selected_ternary_cols"])
        self._state.selected_2d_confirmed = bool(self._snapshot["selected_2d_confirmed"])
        self._state.selected_3d_confirmed = bool(self._snapshot["selected_3d_confirmed"])
        self._state.selected_ternary_confirmed = bool(self._snapshot["selected_ternary_confirmed"])
        self._state.standardize_data = bool(self._snapshot["standardize_data"])
        self._state.initial_render_done = bool(self._snapshot["initial_render_done"])
        self._state.pca_component_indices = list(self._snapshot["pca_component_indices"])
        self._state.ternary_auto_zoom = bool(self._snapshot["ternary_auto_zoom"])
        self._state.ternary_limit_mode = str(self._snapshot["ternary_limit_mode"])
        self._state.ternary_limit_anchor = str(self._snapshot["ternary_limit_anchor"])
        self._state.ternary_boundary_percent = float(self._snapshot["ternary_boundary_percent"])
        self._state.ternary_manual_limits_enabled = bool(self._snapshot["ternary_manual_limits_enabled"])
        self._state.ternary_manual_limits = dict(self._snapshot["ternary_manual_limits"])
        self._state.ternary_stretch_mode = str(self._snapshot["ternary_stretch_mode"])
        self._state.ternary_stretch = bool(self._snapshot["ternary_stretch"])
        self._state.ternary_factors = list(self._snapshot["ternary_factors"])
        self._state.model_curve_width = float(self._snapshot["model_curve_width"])
        self._state.plumbotectonics_curve_width = float(self._snapshot["plumbotectonics_curve_width"])
        self._state.paleoisochron_width = float(self._snapshot["paleoisochron_width"])
        self._state.model_age_line_width = float(self._snapshot["model_age_line_width"])
        self._state.isochron_line_width = float(self._snapshot["isochron_line_width"])
        self._state.selected_isochron_line_width = float(self._snapshot["selected_isochron_line_width"])
        self._state.isochron_label_options = dict(self._snapshot["isochron_label_options"])
        self._state.equation_overlays = list(self._snapshot["equation_overlays"])
        self._state.export_image_options = dict(self._snapshot["export_image_options"])

    @classmethod
    def _normalize_export_options(cls, options: Any) -> dict[str, Any]:
        merged = dict(cls.DEFAULT_EXPORT_IMAGE_OPTIONS)
        if isinstance(options, dict):
            merged.update(options)

        merged["preset_key"] = str(merged.get("preset_key") or "science_single")
        merged["image_ext"] = str(merged.get("image_ext") or "png").lower().strip(".")
        merged["dpi"] = max(72, int(merged.get("dpi", 400)))
        merged["bbox_tight"] = bool(merged.get("bbox_tight", True))
        merged["pad_inches"] = max(0.0, float(merged.get("pad_inches", 0.02)))
        merged["transparent"] = bool(merged.get("transparent", False))

        point_size = merged.get("point_size")
        legend_size = merged.get("legend_size")
        merged["point_size"] = int(point_size) if point_size is not None else None
        merged["legend_size"] = int(legend_size) if legend_size is not None else None
        return merged

    @staticmethod
    def _to_index_set(indices: Any) -> set[int]:
        if indices is None:
            return set()
        if isinstance(indices, set):
            return {int(v) for v in indices}
        if isinstance(indices, Iterable) and not isinstance(indices, (str, bytes)):
            return {int(v) for v in indices}
        return {int(indices)}

    @staticmethod
    def _normalize_visible_groups(groups: Any) -> list[str] | None:
        if groups is None:
            return None
        if isinstance(groups, Iterable) and not isinstance(groups, (str, bytes)):
            out = [str(group) for group in groups]
            return out if out else None
        return [str(groups)]

    @staticmethod
    def _normalize_active_subset_indices(indices: Any) -> set[int] | None:
        if indices is None:
            return None
        if isinstance(indices, Iterable) and not isinstance(indices, (str, bytes)):
            normalized = {int(v) for v in indices}
            return normalized if normalized else set()
        return {int(indices)}

    @staticmethod
    def _normalize_algorithm_params(params: Any) -> dict[str, Any]:
        if isinstance(params, dict):
            return dict(params)
        if params is None:
            return {}
        try:
            return dict(params)
        except Exception:
            return {}

    @staticmethod
    def _normalize_plot_marker_size(value: Any) -> int:
        return max(1, min(int(value), 2000))

    @staticmethod
    def _normalize_plot_marker_alpha(value: Any) -> float:
        return max(0.0, min(float(value), 1.0))

    @staticmethod
    def _normalize_plot_dpi(value: Any) -> int:
        return max(72, min(int(value), 1200))

    @staticmethod
    def _normalize_color(value: Any, default: str) -> str:
        text = str(value or "").strip()
        return text if text else default

    @staticmethod
    def _normalize_style_linewidth(value: Any, *, default: float) -> float:
        return max(0.0, min(float(value if value is not None else default), 10.0))

    @staticmethod
    def _normalize_unit_interval(value: Any, *, default: float) -> float:
        return max(0.0, min(float(value if value is not None else default), 1.0))

    @staticmethod
    def _normalize_grid_linestyle(value: Any) -> str:
        text = str(value or "--").strip()
        return text if text in ("-", "--", "-.", ":") else "--"

    @staticmethod
    def _normalize_tick_direction(value: Any) -> str:
        text = str(value or "out").strip().lower()
        return text if text in ("in", "out", "inout") else "out"

    @staticmethod
    def _normalize_tick_length(value: Any, *, default: float) -> float:
        return max(0.0, min(float(value if value is not None else default), 20.0))

    @staticmethod
    def _normalize_text_weight(value: Any, *, default: str) -> str:
        text = str(value or default).strip().lower()
        return text if text in ("normal", "bold") else default

    @staticmethod
    def _normalize_text_pad(value: Any, *, default: float, max_value: float) -> float:
        return max(0.0, min(float(value if value is not None else default), max_value))

    @staticmethod
    def _normalize_adjust_text_pair(
        value: Any,
        *,
        default: tuple[float, float],
        min_value: float,
        max_value: float,
    ) -> tuple[float, float]:
        values: list[float] = []
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            for item in value:
                try:
                    values.append(float(item))
                except Exception:
                    values.append(0.0)
                if len(values) >= 2:
                    break
        if not values:
            values = [default[0], default[1]]
        elif len(values) == 1:
            values = [values[0], default[1]]
        return (
            max(min_value, min(values[0], max_value)),
            max(min_value, min(values[1], max_value)),
        )

    @staticmethod
    def _normalize_adjust_text_iter_lim(value: Any) -> int:
        return max(10, min(int(value), 1000))

    @staticmethod
    def _normalize_adjust_text_time_lim(value: Any) -> float:
        return max(0.05, min(float(value), 2.0))

    @staticmethod
    def _normalize_marginal_size(value: Any) -> float:
        return max(5.0, min(float(value), 40.0))

    @staticmethod
    def _normalize_max_points(value: Any) -> int:
        return max(200, min(int(value), 50000))

    @staticmethod
    def _normalize_bw_adjust(value: Any) -> float:
        return max(0.05, min(float(value), 5.0))

    @staticmethod
    def _normalize_gridsize(value: Any) -> int:
        return max(32, min(int(value), 1024))

    @staticmethod
    def _normalize_cut(value: Any) -> float:
        return max(0.0, min(float(value), 5.0))

    @staticmethod
    def _normalize_pca_component_indices(indices: Any) -> list[int]:
        if indices is None:
            return [0, 1]
        if isinstance(indices, Iterable) and not isinstance(indices, (str, bytes)):
            values = [int(v) for v in indices]
        else:
            values = [int(indices)]
        if len(values) < 2:
            values = (values + [1])[:2]
        return [max(0, values[0]), max(0, values[1])]

    @staticmethod
    def _normalize_ternary_limit_mode(mode: Any) -> str:
        text = str(mode or "min").strip().lower()
        return text if text in ("min", "max", "both") else "min"

    @staticmethod
    def _normalize_ternary_limit_anchor(anchor: Any) -> str:
        text = str(anchor or "min").strip().lower()
        return text if text in ("min", "max") else "min"

    @staticmethod
    def _normalize_ternary_boundary_percent(percent: Any) -> float:
        return max(0.0, min(float(percent if percent is not None else 5.0), 30.0))

    @staticmethod
    def _normalize_ternary_stretch_mode(mode: Any) -> str:
        text = str(mode or "power").strip().lower()
        return text if text in ("power", "minmax", "hybrid") else "power"

    @staticmethod
    def _normalize_ternary_manual_limits(limits: Any) -> dict[str, float]:
        defaults = {
            "tmin": 0.0,
            "tmax": 1.0,
            "lmin": 0.0,
            "lmax": 1.0,
            "rmin": 0.0,
            "rmax": 1.0,
        }
        merged = dict(defaults)
        if isinstance(limits, dict):
            for key, value in limits.items():
                if key in merged and value is not None:
                    merged[key] = max(0.0, min(float(value), 1.0))
        return merged

    @staticmethod
    def _normalize_ternary_factors(factors: Any) -> list[float]:
        values: list[Any]
        if isinstance(factors, dict):
            if all(k in factors for k in ("top", "left", "right")):
                values = [factors.get("top"), factors.get("left"), factors.get("right")]
            elif all(k in factors for k in ("t", "l", "r")):
                values = [factors.get("t"), factors.get("l"), factors.get("r")]
            else:
                values = list(factors.values())
        elif factors is None:
            values = [1.0, 1.0, 1.0]
        elif isinstance(factors, Iterable) and not isinstance(factors, (str, bytes)):
            values = list(factors)
        else:
            values = [factors]

        out: list[float] = []
        for value in values[:3]:
            try:
                out.append(float(value))
            except Exception:
                out.append(1.0)
        while len(out) < 3:
            out.append(1.0)
        return out
