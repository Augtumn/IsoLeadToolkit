"""Normalizer functions and sync logic extracted from StateStore."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────

DEFAULT_EXPORT_IMAGE_OPTIONS = {
    "preset_key": "science_single",
    "image_ext": "png",
    "dpi": 400,
    "bbox_tight": True,
    "pad_inches": 0.02,
    "transparent": False,
    "point_size": None,
    "legend_size": None,
    "embed_fonts": True,
    "white_background": True,
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
_KDE_THRESH_DEFAULT = 0.05
_KDE_THRESH_MIN = 0.001
_KDE_THRESH_MAX = 1.0

MARGINAL_KDE_DEFAULT_AUTO_BANDWIDTH_METHOD = "scott"
MARGINAL_KDE_ALLOWED_AUTO_BANDWIDTH_METHODS = ("scott", "silverman")

# Normalizer clamp bounds

# ── Normalizer functions ───────────────────────────────────────────────


def _to_index_set(indices: Any) -> set[int]:
    if indices is None:
        return set()
    if isinstance(indices, set):
        return {int(v) for v in indices}
    if isinstance(indices, Iterable) and not isinstance(indices, (str, bytes)):
        return {int(v) for v in indices}
    return {int(indices)}


# The ternary coercers live with their declarations in core/state/fields.py;
# they stay importable from here for the dispatch handlers.
from core.state.fields import (  # noqa: E402  (re-export)
    sync_fields,
    _normalize_ternary_boundary_percent,
    _normalize_ternary_manual_limits,
    _normalize_ternary_render_margin,
)

# The coercion helpers live in core/state/coercers.py so the field registry and the
# normalizers can share them; re-exported here for existing importers.
from .coercers import (  # noqa: F401  (re-export)
    _ADJUST_TEXT_ITER_MIN,
    _ADJUST_TEXT_ITER_MAX,
    _ADJUST_TEXT_TIME_MIN,
    _ADJUST_TEXT_TIME_MAX,
    _MARGINAL_SIZE_MIN,
    _MARGINAL_SIZE_MAX,
    _MAX_POINTS_MIN,
    _MAX_POINTS_MAX,
    _BW_ADJUST_MIN,
    _BW_ADJUST_MAX,
    _KDE_BW_MIN,
    _KDE_BW_MAX,
    _normalize_active_subset_indices,
    _normalize_adjust_text_iter_lim,
    _normalize_adjust_text_pair,
    _normalize_adjust_text_time_lim,
    _normalize_algorithm_params,
    _normalize_bw_adjust,
    _normalize_clip_bound,
    _normalize_color,
    _normalize_cut,
    _normalize_export_options,
    _normalize_font_name,
    _normalize_grid_linestyle,
    _normalize_gridsize,
    _normalize_kde_auto_bandwidth_method,
    _normalize_kde_bandwidth,
    _normalize_kde_kernel,
    _normalize_kde_thresh,
    _normalize_marginal_size,
    _normalize_max_points,
    _normalize_pca_component_indices,
    _normalize_plot_dpi,
    _normalize_plot_font_sizes,
    _normalize_plot_marker_alpha,
    _normalize_plot_marker_size,
    _normalize_style_linewidth,
    _normalize_ternary_limit_anchor,
    _normalize_ternary_limit_mode,
    _normalize_text_pad,
    _normalize_text_weight,
    _normalize_tick_direction,
    _normalize_tick_length,
    _normalize_unit_interval,
    _normalize_visible_groups,
    _normalize_export_options,
    _normalize_visible_groups,
    _normalize_active_subset_indices,
    _normalize_algorithm_params,
    _normalize_plot_marker_size,
    _normalize_plot_marker_alpha,
    _normalize_plot_dpi,
    _normalize_font_name,
    _normalize_plot_font_sizes,
    _normalize_color,
    _normalize_style_linewidth,
    _normalize_unit_interval,
    _normalize_grid_linestyle,
    _normalize_tick_direction,
    _normalize_tick_length,
    _normalize_text_weight,
    _normalize_text_pad,
    _normalize_adjust_text_pair,
    _normalize_adjust_text_iter_lim,
    _normalize_adjust_text_time_lim,
    _normalize_marginal_size,
    _normalize_max_points,
    _normalize_bw_adjust,
    _normalize_kde_bandwidth,
    _normalize_kde_kernel,
    _normalize_kde_auto_bandwidth_method,
    _normalize_gridsize,
    _normalize_kde_thresh,
    _normalize_clip_bound,
    _normalize_cut,
    _normalize_pca_component_indices,
    _normalize_ternary_limit_mode,
    _normalize_ternary_limit_anchor,
)



# ── Sync logic ─────────────────────────────────────────────────────────


def sync_state_store_to_app(state: Any, snapshot: dict[str, Any]) -> None:
    """Write snapshot values back to the live app state object."""
    render_mode = str(snapshot["render_mode"])
    state.render_mode = render_mode
    algorithm = str(snapshot["algorithm"])
    if render_mode in ("UMAP", "tSNE", "PCA", "RobustPCA"):
        algorithm = render_mode
        snapshot["algorithm"] = algorithm
    state.algorithm = algorithm

    # NOTE: parameter dicts are written back below. Bypass detection for
    # in-place mutations happens in StateStore.dispatch (before applying an
    # action), where snapshot vs live comparison has the correct semantics —
    # comparing here (after the handler updated the snapshot but before the
    # write-back) would flag every legitimate parameter change.
    state.umap_params = dict(snapshot["umap_params"])
    state.tsne_params = dict(snapshot["tsne_params"])
    state.pca_params = dict(snapshot["pca_params"])
    state.robust_pca_params = dict(snapshot["robust_pca_params"])
    state.ml_params = dict(snapshot["ml_params"])
    state.v1v2_params = dict(snapshot["v1v2_params"])
    state.plot_style_grid = bool(snapshot["plot_style_grid"])
    state.plot_marker_size = int(snapshot["plot_marker_size"])
    state.plot_marker_alpha = float(snapshot["plot_marker_alpha"])
    state.show_plot_title = bool(snapshot["show_plot_title"])
    state.plot_dpi = int(snapshot["plot_dpi"])
    state.custom_primary_font = str(snapshot["custom_primary_font"])
    state.custom_cjk_font = str(snapshot["custom_cjk_font"])
    state.plot_font_sizes = dict(snapshot["plot_font_sizes"])
    state.plot_facecolor = str(snapshot["plot_facecolor"])
    state.axes_facecolor = str(snapshot["axes_facecolor"])
    state.grid_color = str(snapshot["grid_color"])
    state.grid_linewidth = float(snapshot["grid_linewidth"])
    state.grid_alpha = float(snapshot["grid_alpha"])
    state.grid_linestyle = str(snapshot["grid_linestyle"])
    state.tick_direction = str(snapshot["tick_direction"])
    state.tick_color = str(snapshot["tick_color"])
    state.tick_length = float(snapshot["tick_length"])
    state.tick_width = float(snapshot["tick_width"])
    state.axis_linewidth = float(snapshot["axis_linewidth"])
    state.axis_line_color = str(snapshot["axis_line_color"])
    state.minor_ticks = bool(snapshot["minor_ticks"])
    state.minor_tick_length = float(snapshot["minor_tick_length"])
    state.minor_tick_width = float(snapshot["minor_tick_width"])
    state.show_top_spine = bool(snapshot["show_top_spine"])
    state.show_right_spine = bool(snapshot["show_right_spine"])
    state.minor_grid = bool(snapshot["minor_grid"])
    state.minor_grid_color = str(snapshot["minor_grid_color"])
    state.minor_grid_linewidth = float(snapshot["minor_grid_linewidth"])
    state.minor_grid_alpha = float(snapshot["minor_grid_alpha"])
    state.minor_grid_linestyle = str(snapshot["minor_grid_linestyle"])
    state.scatter_show_edge = bool(snapshot["scatter_show_edge"])
    state.scatter_edgecolor = str(snapshot["scatter_edgecolor"])
    state.scatter_edgewidth = float(snapshot["scatter_edgewidth"])
    state.label_color = str(snapshot["label_color"])
    state.label_weight = str(snapshot["label_weight"])
    state.label_pad = float(snapshot["label_pad"])
    state.title_color = str(snapshot["title_color"])
    state.title_weight = str(snapshot["title_weight"])
    state.title_pad = float(snapshot["title_pad"])
    state.legend.legend_frame_on = bool(snapshot["legend_frame_on"])
    state.legend.legend_frame_alpha = float(snapshot["legend_frame_alpha"])
    state.legend.legend_frame_facecolor = str(snapshot["legend_frame_facecolor"])
    state.legend.legend_frame_edgecolor = str(snapshot["legend_frame_edgecolor"])
    state.adjust_text_force_text = tuple(snapshot["adjust_text_force_text"])
    state.adjust_text_force_static = tuple(snapshot["adjust_text_force_static"])
    state.adjust_text_expand = tuple(snapshot["adjust_text_expand"])
    state.adjust_text_iter_lim = int(snapshot["adjust_text_iter_lim"])
    state.adjust_text_time_lim = float(snapshot["adjust_text_time_lim"])
    state.show_kde = bool(snapshot["show_kde"])
    state.show_marginal_kde = bool(snapshot["show_marginal_kde"])
    state.overlay.show_equation_overlays = bool(snapshot["show_equation_overlays"])
    state.overlay.geo_model_name = str(snapshot["geo_model_name"])
    state.paleo_label_refreshing = bool(snapshot["paleo_label_refreshing"])
    state.overlay_label_refreshing = bool(snapshot["overlay_label_refreshing"])
    state.overlay.overlay_curve_label_data = list(snapshot["overlay_curve_label_data"])
    state.overlay.paleoisochron_label_data = list(snapshot["paleoisochron_label_data"])
    state.overlay.plumbotectonics_label_data = list(
        snapshot["plumbotectonics_label_data"]
    )
    state.overlay.plumbotectonics_isoage_label_data = list(
        snapshot["plumbotectonics_isoage_label_data"]
    )
    state.overlay.overlay_artists = dict(snapshot["overlay_artists"])
    state.last_embedding = snapshot["last_embedding"]
    state.last_embedding_type = str(snapshot["last_embedding_type"])
    state.overlay.selected_isochron_data = snapshot["selected_isochron_data"]
    state.embedding_task_token = int(snapshot["embedding_task_token"])
    state.embedding_task_running = bool(snapshot["embedding_task_running"])
    state.marginal_axes = snapshot["marginal_axes"]
    state.last_pca_variance = snapshot["last_pca_variance"]
    state.last_pca_components = snapshot["last_pca_components"]
    state.current_feature_names = snapshot["current_feature_names"]
    state.adjust_text_in_progress = bool(snapshot["adjust_text_in_progress"])
    state.confidence_level = float(snapshot["confidence_level"])
    state.current_palette = dict(snapshot["current_palette"])
    state.group_marker_map = dict(snapshot["group_marker_map"])
    state.current_plot_title = str(snapshot["current_plot_title"])
    state.last_2d_cols = (
        list(snapshot["last_2d_cols"])
        if snapshot["last_2d_cols"] is not None
        else None
    )
    state.overlay.show_model_curves = bool(snapshot["show_model_curves"])
    state.overlay.show_plumbotectonics_curves = bool(
        snapshot["show_plumbotectonics_curves"]
    )
    state.overlay.show_paleoisochrons = bool(snapshot["show_paleoisochrons"])
    state.overlay.show_model_age_lines = bool(snapshot["show_model_age_lines"])
    state.overlay.show_growth_curves = bool(snapshot["show_growth_curves"])
    state.overlay.show_isochrons = bool(snapshot["show_isochrons"])
    state.overlay.isochron_error_mode = str(snapshot["isochron_error_mode"])
    state.overlay.isochron_sx_col = str(snapshot["isochron_sx_col"])
    state.overlay.isochron_sy_col = str(snapshot["isochron_sy_col"])
    state.overlay.isochron_rxy_col = str(snapshot["isochron_rxy_col"])
    state.overlay.isochron_sx_value = float(snapshot["isochron_sx_value"])
    state.overlay.isochron_sy_value = float(snapshot["isochron_sy_value"])
    state.overlay.isochron_rxy_value = float(snapshot["isochron_rxy_value"])
    state.overlay.isochron_results = dict(snapshot["isochron_results"])
    state.overlay.plumbotectonics_group_visibility = dict(
        snapshot["plumbotectonics_group_visibility"]
    )
    state.overlay.use_real_age_for_mu_kappa = bool(
        snapshot["use_real_age_for_mu_kappa"]
    )
    state.overlay.mu_kappa_age_col = snapshot["mu_kappa_age_col"]
    state.overlay.plumbotectonics_variant = str(snapshot["plumbotectonics_variant"])
    state.overlay.paleoisochron_min_age = int(snapshot["paleoisochron_min_age"])
    state.overlay.paleoisochron_max_age = int(snapshot["paleoisochron_max_age"])
    state.overlay.paleoisochron_step = int(snapshot["paleoisochron_step"])
    state.overlay.paleoisochron_ages = list(snapshot["paleoisochron_ages"])
    state.draw_selection_ellipse = bool(snapshot["draw_selection_ellipse"])
    state.marginal_kde_top_size = float(snapshot["marginal_kde_top_size"])
    state.marginal_kde_right_size = float(snapshot["marginal_kde_right_size"])
    state.marginal_kde_max_points = int(snapshot["marginal_kde_max_points"])
    state.marginal_kde_bw_adjust = float(snapshot["marginal_kde_bw_adjust"])
    state.marginal_kde_bandwidth = float(snapshot["marginal_kde_bandwidth"])
    state.marginal_kde_kernel = str(snapshot["marginal_kde_kernel"])
    state.marginal_kde_auto_bandwidth_method = str(
        snapshot["marginal_kde_auto_bandwidth_method"]
    )
    state.marginal_kde_gridsize = int(snapshot["marginal_kde_gridsize"])
    state.marginal_kde_cut = float(snapshot["marginal_kde_cut"])
    state.marginal_kde_log_transform = bool(snapshot["marginal_kde_log_transform"])
    state.kde_bw_adjust = snapshot["kde_bw_adjust"]
    state.kde_bw_method = snapshot["kde_bw_method"]
    state.kde_gridsize = snapshot["kde_gridsize"]
    state.kde_thresh = snapshot["kde_thresh"]
    state.kde_clip_min = snapshot["kde_clip_min"]
    state.kde_clip_max = snapshot["kde_clip_max"]
    state.kde_common_norm = snapshot["kde_common_norm"]
    state.kde_warn_singular = snapshot["kde_warn_singular"]
    state.marginal_kde_clip_min = snapshot["marginal_kde_clip_min"]
    state.marginal_kde_clip_max = snapshot["marginal_kde_clip_max"]
    state.marginal_kde_cumulative = snapshot["marginal_kde_cumulative"]

    state.selected_indices = set(snapshot["selected_indices"])
    state.active_subset_indices = _normalize_active_subset_indices(
        snapshot["active_subset_indices"]
    )
    state.df_global = snapshot["df_global"]
    state.file_path = snapshot["file_path"]
    state.sheet_name = snapshot["sheet_name"]
    state.data_version = int(snapshot["data_version"])
    state.group_cols = list(snapshot["group_cols"])
    state.data_cols = list(snapshot["data_cols"])
    state.last_group_col = snapshot["last_group_col"]
    state.selection_mode = bool(snapshot["selection_mode"])
    state.selection_tool = snapshot["selection_tool"]
    state.point_size = int(snapshot["point_size"])
    state.show_tooltip = bool(snapshot["show_tooltip"])
    state.tooltip_columns = list(snapshot["tooltip_columns"])
    state.ui_theme = str(snapshot["ui_theme"])
    state.language = str(snapshot["language"])
    state.color_scheme = str(snapshot["color_scheme"])
    state.legend.legend_position = snapshot["legend_position"]
    state.legend.legend_location = snapshot["legend_location"]
    state.legend.legend_display_mode = str(snapshot["legend_display_mode"])
    state.legend.legend_columns = int(snapshot["legend_columns"])
    state.legend.legend_nudge_step = float(snapshot["legend_nudge_step"])
    state.legend.legend_offset = tuple(snapshot["legend_offset"])
    state.legend.hidden_groups = set(snapshot["hidden_groups"])
    state.legend.legend_last_title = snapshot["legend_last_title"]
    state.legend.legend_last_handles = snapshot["legend_last_handles"]
    state.legend.legend_last_labels = snapshot["legend_last_labels"]
    state.recent_files = list(snapshot["recent_files"])
    state.overlay.line_styles = dict(snapshot["line_styles"])
    state.saved_themes = dict(snapshot["saved_themes"])
    state.custom_palettes = dict(snapshot["custom_palettes"])
    state.custom_shape_sets = dict(snapshot["custom_shape_sets"])
    state.legend_item_order = list(snapshot["legend_item_order"])
    state.parent_groups = {
        str(k): list(v or []) for k, v in (snapshot["parent_groups"] or {}).items()
    }
    state.parent_shape_map = {
        str(k): str(v) for k, v in (snapshot["parent_shape_map"] or {}).items()
    }
    state.param_presets = {
        str(k): dict(v or {}) for k, v in (snapshot["param_presets"] or {}).items()
    }
    state.mixing_endmembers = dict(snapshot["mixing_endmembers"])
    state.mixing_mixtures = dict(snapshot["mixing_mixtures"])
    state.ternary_ranges = dict(snapshot["ternary_ranges"])
    state.ml_last_result = snapshot["ml_last_result"]
    state.ml_last_model_meta = snapshot["ml_last_model_meta"]
    state.preserve_import_render_mode = bool(snapshot["preserve_import_render_mode"])
    state.available_groups = list(snapshot["available_groups"])
    state.visible_groups = _normalize_visible_groups(snapshot["visible_groups"])
    state.selected_2d_cols = list(snapshot["selected_2d_cols"])
    state.selected_3d_cols = list(snapshot["selected_3d_cols"])
    state.selected_ternary_cols = list(snapshot["selected_ternary_cols"])
    state.selected_2d_confirmed = bool(snapshot["selected_2d_confirmed"])
    state.selected_3d_confirmed = bool(snapshot["selected_3d_confirmed"])
    state.selected_ternary_confirmed = bool(snapshot["selected_ternary_confirmed"])
    state.standardize_data = bool(snapshot["standardize_data"])
    state.initial_render_done = bool(snapshot["initial_render_done"])
    state.pca_component_indices = list(snapshot["pca_component_indices"])
    sync_fields(state, snapshot)
    state.overlay.model_curve_width = float(snapshot["model_curve_width"])
    state.overlay.plumbotectonics_curve_width = float(
        snapshot["plumbotectonics_curve_width"]
    )
    state.overlay.paleoisochron_width = float(snapshot["paleoisochron_width"])
    state.overlay.model_age_line_width = float(snapshot["model_age_line_width"])
    state.overlay.isochron_line_width = float(snapshot["isochron_line_width"])
    state.selected_isochron_line_width = float(snapshot["selected_isochron_line_width"])
    state.overlay.isochron_label_options = dict(snapshot["isochron_label_options"])
    state.overlay.model_curve_models = (
        list(snapshot["model_curve_models"])
        if snapshot["model_curve_models"] is not None
        else None
    )
    state.overlay.equation_overlays = list(snapshot["equation_overlays"])
    state.export_image_options = dict(snapshot["export_image_options"])
