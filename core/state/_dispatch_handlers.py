"""Action dispatch handlers for StateStore.

This module is extracted from store.py to keep the store class under 800 lines.
The single entry point is ``dispatch_action(store, action)`` — it receives the
full StateStore instance so it can access ``store._snapshot``, ``store._state``,
and ``store.DEFAULT_*`` class attributes.
"""

from __future__ import annotations

import logging
from typing import Any

from ._normalizers import (
    _normalize_active_subset_indices,
    _normalize_adjust_text_iter_lim,
    _normalize_adjust_text_pair,
    _normalize_adjust_text_time_lim,
    _normalize_algorithm_params,
    _normalize_bw_adjust,
    _normalize_color,
    _normalize_cut,
    _normalize_export_options,
    _normalize_font_name,
    _normalize_grid_linestyle,
    _normalize_gridsize,
    _normalize_kde_auto_bandwidth_method,
    _normalize_kde_bandwidth,
    _normalize_kde_kernel,
    _normalize_marginal_size,
    _normalize_max_points,
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
    _to_index_set,
)

logger = logging.getLogger(__name__)


def dispatch_action(store: Any, action: dict[str, Any]) -> None:
    """Apply *action* mutations to *store._snapshot* in-place.

    This function contains the full if/elif chain that was previously the body
    of ``StateStore.dispatch()``.  It does **not** call ``_sync_state()`` or
    return a snapshot — those responsibilities remain in the store method.
    """
    action_type = str(action.get("type", "")).upper().strip()

    if action_type == "SET_RENDER_MODE":
        render_mode = str(action.get("render_mode", "UMAP") or "UMAP")
        store._snapshot["render_mode"] = render_mode
        if render_mode in ("UMAP", "tSNE", "PCA", "RobustPCA"):
            store._snapshot["algorithm"] = render_mode

    elif action_type == "SET_ALGORITHM":
        store._snapshot["algorithm"] = str(action.get("algorithm", "UMAP") or "UMAP")

    elif action_type == "SET_UMAP_PARAMS":
        store._snapshot["umap_params"] = _normalize_algorithm_params(action.get("params"))

    elif action_type == "SET_TSNE_PARAMS":
        store._snapshot["tsne_params"] = _normalize_algorithm_params(action.get("params"))

    elif action_type == "SET_PCA_PARAMS":
        store._snapshot["pca_params"] = _normalize_algorithm_params(action.get("params"))

    elif action_type == "SET_ROBUST_PCA_PARAMS":
        store._snapshot["robust_pca_params"] = _normalize_algorithm_params(
            action.get("params")
        )

    elif action_type == "SET_ML_PARAMS":
        store._snapshot["ml_params"] = _normalize_algorithm_params(action.get("params"))

    elif action_type == "SET_V1V2_PARAMS":
        store._snapshot["v1v2_params"] = _normalize_algorithm_params(action.get("params"))

    elif action_type == "SET_PLOT_STYLE_GRID":
        store._snapshot["plot_style_grid"] = bool(action.get("enabled", False))

    elif action_type == "SET_PLOT_MARKER_SIZE":
        store._snapshot["plot_marker_size"] = _normalize_plot_marker_size(
            action.get("size", 60)
        )

    elif action_type == "SET_PLOT_MARKER_ALPHA":
        store._snapshot["plot_marker_alpha"] = _normalize_plot_marker_alpha(
            action.get("alpha", 0.8)
        )

    elif action_type == "SET_SHOW_PLOT_TITLE":
        store._snapshot["show_plot_title"] = bool(action.get("show", False))

    elif action_type == "SET_PLOT_DPI":
        store._snapshot["plot_dpi"] = _normalize_plot_dpi(action.get("dpi", 130))

    elif action_type == "SET_CUSTOM_PRIMARY_FONT":
        store._snapshot["custom_primary_font"] = _normalize_font_name(
            action.get("font_name", "")
        )

    elif action_type == "SET_CUSTOM_CJK_FONT":
        store._snapshot["custom_cjk_font"] = _normalize_font_name(
            action.get("font_name", "")
        )

    elif action_type == "SET_PLOT_FONT_SIZES":
        store._snapshot["plot_font_sizes"] = _normalize_plot_font_sizes(
            action.get("sizes")
        )

    elif action_type == "SET_PLOT_FACECOLOR":
        store._snapshot["plot_facecolor"] = _normalize_color(
            action.get("color", "#ffffff"),
            "#ffffff",
        )

    elif action_type == "SET_AXES_FACECOLOR":
        store._snapshot["axes_facecolor"] = _normalize_color(
            action.get("color", "#ffffff"),
            "#ffffff",
        )

    elif action_type == "SET_GRID_COLOR":
        store._snapshot["grid_color"] = _normalize_color(
            action.get("color", "#e2e8f0"),
            "#e2e8f0",
        )

    elif action_type == "SET_GRID_LINEWIDTH":
        store._snapshot["grid_linewidth"] = _normalize_style_linewidth(
            action.get("width", 0.6),
            default=0.6,
        )

    elif action_type == "SET_GRID_ALPHA":
        store._snapshot["grid_alpha"] = _normalize_unit_interval(
            action.get("alpha", 0.7),
            default=0.7,
        )

    elif action_type == "SET_GRID_LINESTYLE":
        store._snapshot["grid_linestyle"] = _normalize_grid_linestyle(
            action.get("linestyle", "--")
        )

    elif action_type == "SET_TICK_DIRECTION":
        store._snapshot["tick_direction"] = _normalize_tick_direction(
            action.get("direction", "out")
        )

    elif action_type == "SET_TICK_COLOR":
        store._snapshot["tick_color"] = _normalize_color(
            action.get("color", "#1f2937"),
            "#1f2937",
        )

    elif action_type == "SET_TICK_LENGTH":
        store._snapshot["tick_length"] = _normalize_tick_length(
            action.get("length", 4.0),
            default=4.0,
        )

    elif action_type == "SET_TICK_WIDTH":
        store._snapshot["tick_width"] = _normalize_style_linewidth(
            action.get("width", 0.8),
            default=0.8,
        )

    elif action_type == "SET_AXIS_LINEWIDTH":
        store._snapshot["axis_linewidth"] = _normalize_style_linewidth(
            action.get("width", 1.0),
            default=1.0,
        )

    elif action_type == "SET_AXIS_LINE_COLOR":
        store._snapshot["axis_line_color"] = _normalize_color(
            action.get("color", "#1f2937"),
            "#1f2937",
        )

    elif action_type == "SET_MINOR_TICKS":
        store._snapshot["minor_ticks"] = bool(action.get("enabled", False))

    elif action_type == "SET_MINOR_TICK_LENGTH":
        store._snapshot["minor_tick_length"] = _normalize_tick_length(
            action.get("length", 2.5),
            default=2.5,
        )

    elif action_type == "SET_MINOR_TICK_WIDTH":
        store._snapshot["minor_tick_width"] = _normalize_style_linewidth(
            action.get("width", 0.6),
            default=0.6,
        )

    elif action_type == "SET_SHOW_TOP_SPINE":
        store._snapshot["show_top_spine"] = bool(action.get("show", True))

    elif action_type == "SET_SHOW_RIGHT_SPINE":
        store._snapshot["show_right_spine"] = bool(action.get("show", True))

    elif action_type == "SET_MINOR_GRID":
        store._snapshot["minor_grid"] = bool(action.get("enabled", False))

    elif action_type == "SET_MINOR_GRID_COLOR":
        store._snapshot["minor_grid_color"] = _normalize_color(
            action.get("color", "#e2e8f0"),
            "#e2e8f0",
        )

    elif action_type == "SET_MINOR_GRID_LINEWIDTH":
        store._snapshot["minor_grid_linewidth"] = _normalize_style_linewidth(
            action.get("width", 0.4),
            default=0.4,
        )

    elif action_type == "SET_MINOR_GRID_ALPHA":
        store._snapshot["minor_grid_alpha"] = _normalize_unit_interval(
            action.get("alpha", 0.4),
            default=0.4,
        )

    elif action_type == "SET_MINOR_GRID_LINESTYLE":
        store._snapshot["minor_grid_linestyle"] = _normalize_grid_linestyle(
            action.get("linestyle", ":")
        )

    elif action_type == "SET_SCATTER_SHOW_EDGE":
        store._snapshot["scatter_show_edge"] = bool(action.get("show", True))

    elif action_type == "SET_SCATTER_EDGECOLOR":
        store._snapshot["scatter_edgecolor"] = _normalize_color(
            action.get("color", "#1e293b"),
            "#1e293b",
        )

    elif action_type == "SET_SCATTER_EDGEWIDTH":
        store._snapshot["scatter_edgewidth"] = _normalize_style_linewidth(
            action.get("width", 0.4),
            default=0.4,
        )

    elif action_type == "SET_LABEL_COLOR":
        store._snapshot["label_color"] = _normalize_color(
            action.get("color", "#1f2937"),
            "#1f2937",
        )

    elif action_type == "SET_LABEL_WEIGHT":
        store._snapshot["label_weight"] = _normalize_text_weight(
            action.get("weight", "normal"),
            default="normal",
        )

    elif action_type == "SET_LABEL_PAD":
        store._snapshot["label_pad"] = _normalize_text_pad(
            action.get("pad", 6.0),
            default=6.0,
            max_value=60.0,
        )

    elif action_type == "SET_TITLE_COLOR":
        store._snapshot["title_color"] = _normalize_color(
            action.get("color", "#111827"),
            "#111827",
        )

    elif action_type == "SET_TITLE_WEIGHT":
        store._snapshot["title_weight"] = _normalize_text_weight(
            action.get("weight", "bold"),
            default="bold",
        )

    elif action_type == "SET_TITLE_PAD":
        store._snapshot["title_pad"] = _normalize_text_pad(
            action.get("pad", 20.0),
            default=20.0,
            max_value=80.0,
        )

    elif action_type == "SET_LEGEND_FRAME_ON":
        store._snapshot["legend_frame_on"] = bool(action.get("enabled", True))

    elif action_type == "SET_LEGEND_FRAME_ALPHA":
        store._snapshot["legend_frame_alpha"] = _normalize_unit_interval(
            action.get("alpha", store.DEFAULT_LEGEND_FRAME_ALPHA),
            default=store.DEFAULT_LEGEND_FRAME_ALPHA,
        )

    elif action_type == "SET_LEGEND_FRAME_FACECOLOR":
        store._snapshot["legend_frame_facecolor"] = _normalize_color(
            action.get("color", "#ffffff"),
            "#ffffff",
        )

    elif action_type == "SET_LEGEND_FRAME_EDGECOLOR":
        store._snapshot["legend_frame_edgecolor"] = _normalize_color(
            action.get("color", "#cbd5f5"),
            "#cbd5f5",
        )

    elif action_type == "SET_ADJUST_TEXT_FORCE_TEXT":
        store._snapshot["adjust_text_force_text"] = _normalize_adjust_text_pair(
            action.get("force", (0.8, 1.0)),
            default=(0.8, 1.0),
            min_value=0.0,
            max_value=3.0,
        )

    elif action_type == "SET_ADJUST_TEXT_FORCE_STATIC":
        store._snapshot["adjust_text_force_static"] = _normalize_adjust_text_pair(
            action.get("force", (0.4, 0.6)),
            default=(0.4, 0.6),
            min_value=0.0,
            max_value=3.0,
        )

    elif action_type == "SET_ADJUST_TEXT_EXPAND":
        store._snapshot["adjust_text_expand"] = _normalize_adjust_text_pair(
            action.get("expand", (1.08, 1.20)),
            default=(1.08, 1.20),
            min_value=1.0,
            max_value=2.5,
        )

    elif action_type == "SET_ADJUST_TEXT_ITER_LIM":
        store._snapshot["adjust_text_iter_lim"] = _normalize_adjust_text_iter_lim(
            action.get("iter_lim", 120)
        )

    elif action_type == "SET_ADJUST_TEXT_TIME_LIM":
        store._snapshot["adjust_text_time_lim"] = _normalize_adjust_text_time_lim(
            action.get("time_lim", 0.25)
        )

    elif action_type == "SET_SHOW_KDE":
        store._snapshot["show_kde"] = bool(action.get("show", False))

    elif action_type == "SET_SHOW_MARGINAL_KDE":
        store._snapshot["show_marginal_kde"] = bool(action.get("show", False))

    elif action_type == "SET_SHOW_EQUATION_OVERLAYS":
        store._snapshot["show_equation_overlays"] = bool(action.get("show", False))

    elif action_type == "SET_GEO_MODEL_NAME":
        store._snapshot["geo_model_name"] = str(
            action.get("model_name", "Stacey & Kramers (2nd Stage)")
        )

    elif action_type == "SET_PALEO_LABEL_REFRESHING":
        store._snapshot["paleo_label_refreshing"] = bool(action.get("refreshing", False))

    elif action_type == "SET_OVERLAY_LABEL_REFRESHING":
        store._snapshot["overlay_label_refreshing"] = bool(action.get("refreshing", False))

    elif action_type == "SET_OVERLAY_CURVE_LABEL_DATA":
        store._snapshot["overlay_curve_label_data"] = list(action.get("data") or [])

    elif action_type == "SET_PALEOISOCHRON_LABEL_DATA":
        store._snapshot["paleoisochron_label_data"] = list(action.get("data") or [])

    elif action_type == "SET_PLUMBOTECTONICS_LABEL_DATA":
        store._snapshot["plumbotectonics_label_data"] = list(action.get("data") or [])

    elif action_type == "SET_PLUMBOTECTONICS_ISOAGE_LABEL_DATA":
        store._snapshot["plumbotectonics_isoage_label_data"] = list(action.get("data") or [])

    elif action_type == "SET_OVERLAY_ARTISTS":
        store._snapshot["overlay_artists"] = dict(action.get("artists") or {})

    elif action_type == "SET_LAST_EMBEDDING":
        store._snapshot["last_embedding"] = action.get("embedding")
        store._snapshot["last_embedding_type"] = str(action.get("embedding_type", "") or "")

    elif action_type == "SET_SELECTED_ISOCHRON_DATA":
        store._snapshot["selected_isochron_data"] = action.get("data")

    elif action_type == "SET_EMBEDDING_TASK_TOKEN":
        store._snapshot["embedding_task_token"] = int(action.get("task_token", 0))

    elif action_type == "SET_EMBEDDING_TASK_RUNNING":
        store._snapshot["embedding_task_running"] = bool(action.get("running", False))

    elif action_type == "SET_MARGINAL_AXES":
        store._snapshot["marginal_axes"] = action.get("marginal_axes")

    elif action_type == "SET_PCA_DIAGNOSTICS":
        if "last_pca_variance" in action:
            store._snapshot["last_pca_variance"] = action.get("last_pca_variance")
        if "last_pca_components" in action:
            store._snapshot["last_pca_components"] = action.get("last_pca_components")
        if "current_feature_names" in action:
            store._snapshot["current_feature_names"] = action.get("current_feature_names")

    elif action_type == "SET_ADJUST_TEXT_IN_PROGRESS":
        store._snapshot["adjust_text_in_progress"] = bool(action.get("in_progress", False))

    elif action_type == "SET_CONFIDENCE_LEVEL":
        store._snapshot["confidence_level"] = float(
            action.get("level", store.DEFAULT_CONFIDENCE_LEVEL)
        )

    elif action_type == "SET_CURRENT_PALETTE":
        store._snapshot["current_palette"] = dict(action.get("palette") or {})

    elif action_type == "SET_GROUP_MARKER_MAP":
        store._snapshot["group_marker_map"] = dict(action.get("marker_map") or {})

    elif action_type == "SET_CURRENT_PLOT_TITLE":
        store._snapshot["current_plot_title"] = str(action.get("title", ""))

    elif action_type == "SET_LAST_2D_COLS":
        columns = action.get("columns")
        store._snapshot["last_2d_cols"] = list(columns or []) if columns is not None else None

    elif action_type == "SET_SHOW_MODEL_CURVES":
        store._snapshot["show_model_curves"] = bool(action.get("show", False))

    elif action_type == "SET_SHOW_PLUMBOTECTONICS_CURVES":
        store._snapshot["show_plumbotectonics_curves"] = bool(action.get("show", False))

    elif action_type == "SET_SHOW_PALEOISOCHRONS":
        store._snapshot["show_paleoisochrons"] = bool(action.get("show", False))

    elif action_type == "SET_SHOW_MODEL_AGE_LINES":
        store._snapshot["show_model_age_lines"] = bool(action.get("show", False))

    elif action_type == "SET_SHOW_GROWTH_CURVES":
        store._snapshot["show_growth_curves"] = bool(action.get("show", False))

    elif action_type == "SET_SHOW_ISOCHRONS":
        store._snapshot["show_isochrons"] = bool(action.get("show", False))

    elif action_type == "SET_ISOCHRON_ERROR_COLUMNS":
        store._snapshot["isochron_error_mode"] = "columns"
        store._snapshot["isochron_sx_col"] = str(action.get("sx_col", "") or "")
        store._snapshot["isochron_sy_col"] = str(action.get("sy_col", "") or "")
        store._snapshot["isochron_rxy_col"] = str(action.get("rxy_col", "") or "")

    elif action_type == "SET_ISOCHRON_ERROR_FIXED":
        store._snapshot["isochron_error_mode"] = "fixed"
        store._snapshot["isochron_sx_value"] = float(action.get("sx_value", 0.001))
        store._snapshot["isochron_sy_value"] = float(action.get("sy_value", 0.001))
        store._snapshot["isochron_rxy_value"] = float(action.get("rxy_value", 0.0))

    elif action_type == "SET_ISOCHRON_RESULTS":
        store._snapshot["isochron_results"] = dict(action.get("results") or {})

    elif action_type == "SET_PLUMBOTECTONICS_GROUP_VISIBILITY":
        store._snapshot["plumbotectonics_group_visibility"] = dict(
            action.get("visibility") or {}
        )

    elif action_type == "SET_USE_REAL_AGE_FOR_MU_KAPPA":
        store._snapshot["use_real_age_for_mu_kappa"] = bool(action.get("enabled", False))

    elif action_type == "SET_MU_KAPPA_AGE_COL":
        store._snapshot["mu_kappa_age_col"] = action.get("column")

    elif action_type == "SET_PLUMBOTECTONICS_VARIANT":
        store._snapshot["plumbotectonics_variant"] = str(action.get("variant", "0"))

    elif action_type == "SET_PALEOISOCHRON_MIN_AGE":
        store._snapshot["paleoisochron_min_age"] = int(action.get("age", 0))

    elif action_type == "SET_PALEOISOCHRON_MAX_AGE":
        store._snapshot["paleoisochron_max_age"] = int(action.get("age", 3000))

    elif action_type == "SET_PALEOISOCHRON_STEP":
        store._snapshot["paleoisochron_step"] = int(action.get("step", 1000))

    elif action_type == "SET_PALEOISOCHRON_AGES":
        store._snapshot["paleoisochron_ages"] = list(action.get("ages") or [])

    elif action_type == "SET_DRAW_SELECTION_ELLIPSE":
        store._snapshot["draw_selection_ellipse"] = bool(action.get("enabled", False))

    elif action_type == "SET_MARGINAL_KDE_LAYOUT":
        top_size = action.get("top_size")
        right_size = action.get("right_size")
        if top_size is not None:
            store._snapshot["marginal_kde_top_size"] = _normalize_marginal_size(top_size)
        if right_size is not None:
            store._snapshot["marginal_kde_right_size"] = _normalize_marginal_size(right_size)

    elif action_type == "SET_MARGINAL_KDE_COMPUTE_OPTIONS":
        max_points = action.get("max_points")
        bw_adjust = action.get("bw_adjust")
        bandwidth = action.get("bandwidth")
        kernel = action.get("kernel")
        auto_bandwidth_method = action.get("auto_bandwidth_method")
        gridsize = action.get("gridsize")
        cut = action.get("cut")
        log_transform = action.get("log_transform")

        if max_points is not None:
            store._snapshot["marginal_kde_max_points"] = _normalize_max_points(max_points)
        if bw_adjust is not None:
            store._snapshot["marginal_kde_bw_adjust"] = _normalize_bw_adjust(bw_adjust)
        if bandwidth is not None:
            store._snapshot["marginal_kde_bandwidth"] = _normalize_kde_bandwidth(bandwidth)
        if kernel is not None:
            store._snapshot["marginal_kde_kernel"] = _normalize_kde_kernel(kernel)
        if auto_bandwidth_method is not None:
            store._snapshot["marginal_kde_auto_bandwidth_method"] = (
                _normalize_kde_auto_bandwidth_method(auto_bandwidth_method)
            )
        if gridsize is not None:
            store._snapshot["marginal_kde_gridsize"] = _normalize_gridsize(gridsize)
        if cut is not None:
            store._snapshot["marginal_kde_cut"] = _normalize_cut(cut)
        if log_transform is not None:
            store._snapshot["marginal_kde_log_transform"] = bool(log_transform)

    elif action_type == "SET_POINT_SIZE":
        store._snapshot["point_size"] = max(1, int(action.get("point_size", 60)))

    elif action_type == "SET_SHOW_TOOLTIP":
        store._snapshot["show_tooltip"] = bool(action.get("show", False))

    elif action_type == "SET_TOOLTIP_COLUMNS":
        store._snapshot["tooltip_columns"] = [str(col) for col in list(action.get("columns") or [])]

    elif action_type == "SET_UI_THEME":
        store._snapshot["ui_theme"] = str(action.get("theme", "Modern Light") or "Modern Light")

    elif action_type == "SET_LANGUAGE_CODE":
        store._snapshot["language"] = str(action.get("code"))

    elif action_type == "SET_COLOR_SCHEME":
        store._snapshot["color_scheme"] = str(action.get("color_scheme"))

    elif action_type == "SET_LEGEND_POSITION":
        store._snapshot["legend_position"] = action.get("position")

    elif action_type == "SET_LEGEND_LOCATION":
        store._snapshot["legend_location"] = action.get("location")

    elif action_type == "SET_LEGEND_DISPLAY_MODE":
        store._snapshot["legend_display_mode"] = str(action.get("mode", "inline"))

    elif action_type == "SET_LEGEND_COLUMNS":
        store._snapshot["legend_columns"] = int(action.get("columns", 0))

    elif action_type == "SET_LEGEND_NUDGE_STEP":
        store._snapshot["legend_nudge_step"] = float(action.get("step", 0.02))

    elif action_type == "SET_LEGEND_OFFSET":
        offset = action.get("offset")
        store._snapshot["legend_offset"] = tuple(offset) if offset is not None else (0.0, 0.0)

    elif action_type == "SET_HIDDEN_GROUPS":
        store._snapshot["hidden_groups"] = set(action.get("groups") or set())

    elif action_type == "SET_LEGEND_SNAPSHOT":
        store._snapshot["legend_last_title"] = action.get("title")
        store._snapshot["legend_last_handles"] = action.get("handles")
        store._snapshot["legend_last_labels"] = action.get("labels")

    elif action_type == "SET_RECENT_FILES":
        store._snapshot["recent_files"] = list(action.get("files") or [])

    elif action_type == "SET_LINE_STYLES":
        store._snapshot["line_styles"] = dict(action.get("line_styles") or {})

    elif action_type == "SET_SAVED_THEMES":
        store._snapshot["saved_themes"] = dict(action.get("themes") or {})

    elif action_type == "SET_CUSTOM_PALETTES":
        store._snapshot["custom_palettes"] = dict(action.get("palettes") or {})

    elif action_type == "SET_CUSTOM_SHAPE_SETS":
        store._snapshot["custom_shape_sets"] = dict(action.get("shape_sets") or {})

    elif action_type == "SET_LEGEND_ITEM_ORDER":
        store._snapshot["legend_item_order"] = list(action.get("order") or [])

    elif action_type == "SET_MIXING_ENDMEMBERS":
        store._snapshot["mixing_endmembers"] = dict(action.get("mapping") or {})

    elif action_type == "SET_MIXING_MIXTURES":
        store._snapshot["mixing_mixtures"] = dict(action.get("mapping") or {})

    elif action_type == "SET_TERNARY_RANGES":
        store._snapshot["ternary_ranges"] = dict(action.get("ranges") or {})

    elif action_type == "SET_KDE_STYLE":
        store._snapshot["kde_style"] = dict(action.get("style") or {})

    elif action_type == "SET_MARGINAL_KDE_STYLE":
        store._snapshot["marginal_kde_style"] = dict(action.get("style") or {})

    elif action_type == "SET_ML_LAST_RESULT":
        store._snapshot["ml_last_result"] = action.get("result")

    elif action_type == "SET_ML_LAST_MODEL_META":
        store._snapshot["ml_last_model_meta"] = action.get("meta")

    elif action_type == "SET_PRESERVE_IMPORT_RENDER_MODE":
        store._snapshot["preserve_import_render_mode"] = bool(action.get("enabled", False))

    elif action_type == "SET_SELECTED_INDICES":
        indices = _to_index_set(action.get("indices", []))
        store._snapshot["selected_indices"] = indices

    elif action_type == "SET_ACTIVE_SUBSET_INDICES":
        store._snapshot["active_subset_indices"] = _normalize_active_subset_indices(
            action.get("indices")
        )

    elif action_type == "ADD_SELECTED_INDICES":
        indices = _to_index_set(action.get("indices", []))
        store._snapshot["selected_indices"].update(indices)

    elif action_type == "REMOVE_SELECTED_INDICES":
        indices = _to_index_set(action.get("indices", []))
        for index in indices:
            store._snapshot["selected_indices"].discard(index)

    elif action_type == "CLEAR_SELECTED_INDICES":
        store._snapshot["selected_indices"].clear()

    elif action_type == "CLEAR_SELECTION":
        store._snapshot["selected_indices"].clear()
        store._snapshot["selection_mode"] = False

    elif action_type == "SET_SELECTION_MODE":
        store._snapshot["selection_mode"] = bool(action.get("enabled", False))

    elif action_type == "SET_SELECTION_TOOL":
        tool = action.get("tool")
        store._snapshot["selection_tool"] = str(tool) if tool is not None else None
        store._snapshot["selection_mode"] = tool is not None

    elif action_type == "SET_DATAFRAME_SOURCE":
        store._snapshot["df_global"] = action.get("df")
        store._snapshot["file_path"] = action.get("file_path")
        store._snapshot["sheet_name"] = action.get("sheet_name")

    elif action_type == "SET_FILE_PATH":
        store._snapshot["file_path"] = str(action.get("file_path"))

    elif action_type == "SET_SHEET_NAME":
        store._snapshot["sheet_name"] = action.get("sheet_name")

    elif action_type == "BUMP_DATA_VERSION":
        store._snapshot["data_version"] = int(store._snapshot.get("data_version", 0)) + 1
        cache = getattr(store._state, "embedding_cache", None)
        if cache is not None and hasattr(cache, "clear"):
            try:
                cache.clear()
            except Exception:
                pass

    elif action_type == "SET_DATA_VERSION":
        store._snapshot["data_version"] = int(action.get("version", 0))

    elif action_type == "SET_GROUP_DATA_COLUMNS":
        store._snapshot["group_cols"] = [str(col) for col in list(action.get("group_cols") or [])]
        store._snapshot["data_cols"] = [str(col) for col in list(action.get("data_cols") or [])]

    elif action_type == "SET_LAST_GROUP_COL":
        group_col = action.get("group_col")
        store._snapshot["last_group_col"] = str(group_col) if group_col is not None else None

    elif action_type == "SET_SELECTED_2D_COLUMNS":
        store._snapshot["selected_2d_cols"] = list(action.get("columns") or [])
        store._snapshot["selected_2d_confirmed"] = bool(action.get("confirmed", False))

    elif action_type == "SET_SELECTED_3D_COLUMNS":
        store._snapshot["selected_3d_cols"] = list(action.get("columns") or [])
        store._snapshot["selected_3d_confirmed"] = bool(action.get("confirmed", False))

    elif action_type == "SET_SELECTED_TERNARY_COLUMNS":
        store._snapshot["selected_ternary_cols"] = list(action.get("columns") or [])
        store._snapshot["selected_ternary_confirmed"] = bool(action.get("confirmed", False))

    elif action_type == "SET_STANDARDIZE_DATA":
        store._snapshot["standardize_data"] = bool(action.get("enabled", False))

    elif action_type == "SET_INITIAL_RENDER_DONE":
        store._snapshot["initial_render_done"] = bool(action.get("done", False))

    elif action_type == "SET_PCA_COMPONENT_INDICES":
        store._snapshot["pca_component_indices"] = _normalize_pca_component_indices(
            action.get("indices")
        )

    elif action_type == "SET_TERNARY_AUTO_ZOOM":
        store._snapshot["ternary_auto_zoom"] = bool(action.get("enabled", False))

    elif action_type == "SET_TERNARY_LIMIT_MODE":
        store._snapshot["ternary_limit_mode"] = _normalize_ternary_limit_mode(
            action.get("mode")
        )

    elif action_type == "SET_TERNARY_LIMIT_ANCHOR":
        store._snapshot["ternary_limit_anchor"] = _normalize_ternary_limit_anchor(
            action.get("anchor")
        )

    elif action_type == "SET_TERNARY_BOUNDARY_PERCENT":
        store._snapshot["ternary_boundary_percent"] = _normalize_ternary_boundary_percent(
            action.get("percent")
        )

    elif action_type == "SET_TERNARY_MANUAL_LIMITS_ENABLED":
        store._snapshot["ternary_manual_limits_enabled"] = bool(action.get("enabled", False))

    elif action_type == "SET_TERNARY_MANUAL_LIMITS":
        store._snapshot["ternary_manual_limits"] = _normalize_ternary_manual_limits(
            action.get("limits")
        )

    elif action_type == "SET_TERNARY_RENDER_MARGIN":
        store._snapshot["ternary_render_margin"] = _normalize_ternary_render_margin(
            action.get("margin")
        )

    elif action_type == "SET_TERNARY_STRETCH_MODE":
        store._snapshot["ternary_stretch_mode"] = str(action.get("mode", "power") or "power")

    elif action_type == "SET_TERNARY_STRETCH":
        store._snapshot["ternary_stretch"] = bool(action.get("stretch", False))

    elif action_type == "SET_TERNARY_FACTORS":
        store._snapshot["ternary_factors"] = list(action.get("factors") or [1.0, 1.0, 1.0])

    elif action_type == "SET_MODEL_CURVE_WIDTH":
        store._snapshot["model_curve_width"] = float(action.get("width", 1.2))

    elif action_type == "SET_PLUMBOTECTONICS_CURVE_WIDTH":
        store._snapshot["plumbotectonics_curve_width"] = float(action.get("width", 1.2))

    elif action_type == "SET_PALEOISOCHRON_WIDTH":
        store._snapshot["paleoisochron_width"] = float(action.get("width", 0.9))

    elif action_type == "SET_MODEL_AGE_LINE_WIDTH":
        store._snapshot["model_age_line_width"] = float(action.get("width", 0.7))

    elif action_type == "SET_ISOCHRON_LINE_WIDTH":
        store._snapshot["isochron_line_width"] = float(action.get("width", 1.5))

    elif action_type == "SET_SELECTED_ISOCHRON_LINE_WIDTH":
        store._snapshot["selected_isochron_line_width"] = float(action.get("width", 2.0))

    elif action_type == "SET_ISOCHRON_LABEL_OPTIONS":
        store._snapshot["isochron_label_options"] = dict(action.get("options") or {})

    elif action_type == "SET_MODEL_CURVE_MODELS":
        models = action.get("models")
        store._snapshot["model_curve_models"] = list(models or []) if models is not None else None

    elif action_type == "SET_EQUATION_OVERLAYS":
        store._snapshot["equation_overlays"] = list(action.get("overlays") or [])

    elif action_type == "RESET_COLUMN_SELECTION":
        store._snapshot["selected_2d_cols"] = []
        store._snapshot["selected_3d_cols"] = []
        store._snapshot["selected_ternary_cols"] = []
        store._snapshot["selected_2d_confirmed"] = False
        store._snapshot["selected_3d_confirmed"] = False
        store._snapshot["selected_ternary_confirmed"] = False
        store._snapshot["available_groups"] = []
        store._snapshot["visible_groups"] = None

    elif action_type == "SYNC_AVAILABLE_VISIBLE_GROUPS":
        groups = [str(group) for group in list(action.get("all_groups") or [])]
        store._snapshot["available_groups"] = groups
        visible_groups = store._snapshot["visible_groups"]
        if visible_groups:
            filtered = [group for group in visible_groups if group in groups]
            store._snapshot["visible_groups"] = filtered if filtered else None

    elif action_type == "SET_VISIBLE_GROUPS":
        store._snapshot["visible_groups"] = _normalize_visible_groups(action.get("groups"))

    elif action_type == "SET_EXPORT_IMAGE_OPTIONS":
        merged = dict(store._snapshot["export_image_options"])
        payload = dict(action.get("options") or {})
        for key, value in payload.items():
            if value is not None:
                merged[key] = value
        store._snapshot["export_image_options"] = _normalize_export_options(merged)
