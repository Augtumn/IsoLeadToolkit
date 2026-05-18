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

# ── Normalizer functions ───────────────────────────────────────────────


def _normalize_export_options(options: Any) -> dict[str, Any]:
    merged = dict(DEFAULT_EXPORT_IMAGE_OPTIONS)
    if isinstance(options, dict):
        merged.update(options)

    merged["preset_key"] = str(merged.get("preset_key") or "science_single")
    merged["image_ext"] = str(merged.get("image_ext") or "png").lower().strip(".")
    merged["dpi"] = max(MIN_EXPORT_DPI, int(merged.get("dpi", 400)))
    merged["bbox_tight"] = bool(merged.get("bbox_tight", True))
    merged["pad_inches"] = max(0.0, float(merged.get("pad_inches", 0.02)))
    merged["transparent"] = bool(merged.get("transparent", False))

    point_size = merged.get("point_size")
    legend_size = merged.get("legend_size")
    merged["point_size"] = int(point_size) if point_size is not None else None
    merged["legend_size"] = int(legend_size) if legend_size is not None else None
    return merged


def _to_index_set(indices: Any) -> set[int]:
    if indices is None:
        return set()
    if isinstance(indices, set):
        return {int(v) for v in indices}
    if isinstance(indices, Iterable) and not isinstance(indices, (str, bytes)):
        return {int(v) for v in indices}
    return {int(indices)}


def _normalize_visible_groups(groups: Any) -> list[str] | None:
    if groups is None:
        return None
    if isinstance(groups, Iterable) and not isinstance(groups, (str, bytes)):
        out = [str(group) for group in groups]
        return out if out else None
    return [str(groups)]


def _normalize_active_subset_indices(indices: Any) -> set[int] | None:
    if indices is None:
        return None
    if isinstance(indices, Iterable) and not isinstance(indices, (str, bytes)):
        normalized = {int(v) for v in indices}
        return normalized if normalized else set()
    return {int(indices)}


def _normalize_algorithm_params(params: Any) -> dict[str, Any]:
    if isinstance(params, dict):
        return dict(params)
    if params is None:
        return {}
    try:
        return dict(params)
    except Exception:
        return {}


def _normalize_plot_marker_size(value: Any) -> int:
    return max(1, min(int(value), 2000))


def _normalize_plot_marker_alpha(value: Any) -> float:
    return max(0.0, min(float(value), 1.0))


def _normalize_plot_dpi(value: Any) -> int:
    return max(MIN_EXPORT_DPI, min(int(value), 1200))


def _normalize_font_name(value: Any) -> str:
    return str(value or "").strip()


def _normalize_plot_font_sizes(sizes: Any) -> dict[str, int]:
    merged = dict(DEFAULT_PLOT_FONT_SIZES)
    if isinstance(sizes, dict):
        for key in merged:
            if key not in sizes or sizes.get(key) is None:
                continue
            merged[key] = max(6, min(int(sizes[key]), 72))
    return merged


def _normalize_color(value: Any, default: str) -> str:
    text = str(value or "").strip()
    return text if text else default


def _normalize_style_linewidth(value: Any, *, default: float) -> float:
    return max(0.0, min(float(value if value is not None else default), 10.0))


def _normalize_unit_interval(value: Any, *, default: float) -> float:
    return max(0.0, min(float(value if value is not None else default), 1.0))


def _normalize_grid_linestyle(value: Any) -> str:
    text = str(value or "--").strip()
    return text if text in ("-", "--", "-.", ":") else "--"


def _normalize_tick_direction(value: Any) -> str:
    text = str(value or "out").strip().lower()
    return text if text in ("in", "out", "inout") else "out"


def _normalize_tick_length(value: Any, *, default: float) -> float:
    return max(0.0, min(float(value if value is not None else default), 20.0))


def _normalize_text_weight(value: Any, *, default: str) -> str:
    text = str(value or default).strip().lower()
    return text if text in ("normal", "bold") else default


def _normalize_text_pad(value: Any, *, default: float, max_value: float) -> float:
    return max(0.0, min(float(value if value is not None else default), max_value))


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


def _normalize_adjust_text_iter_lim(value: Any) -> int:
    return max(_ADJUST_TEXT_ITER_MIN, min(int(value), _ADJUST_TEXT_ITER_MAX))


def _normalize_adjust_text_time_lim(value: Any) -> float:
    return max(_ADJUST_TEXT_TIME_MIN, min(float(value), _ADJUST_TEXT_TIME_MAX))


def _normalize_marginal_size(value: Any) -> float:
    return max(_MARGINAL_SIZE_MIN, min(float(value), _MARGINAL_SIZE_MAX))


def _normalize_max_points(value: Any) -> int:
    return max(_MAX_POINTS_MIN, min(int(value), _MAX_POINTS_MAX))


def _normalize_bw_adjust(value: Any) -> float:
    return max(_BW_ADJUST_MIN, min(float(value), _BW_ADJUST_MAX))


def _normalize_kde_bandwidth(value: Any) -> float:
    if value is None:
        return _KDE_BW_MIN
    return max(_KDE_BW_MIN, min(float(value), _KDE_BW_MAX))


def _normalize_kde_kernel(value: Any) -> str:
    text = str(value or MARGINAL_KDE_DEFAULT_KERNEL).strip().lower()
    return text if text in MARGINAL_KDE_ALLOWED_KERNELS else MARGINAL_KDE_DEFAULT_KERNEL


def _normalize_kde_auto_bandwidth_method(value: Any) -> str:
    text = str(value or MARGINAL_KDE_DEFAULT_AUTO_BANDWIDTH_METHOD).strip().lower()
    return (
        text
        if text in MARGINAL_KDE_ALLOWED_AUTO_BANDWIDTH_METHODS
        else MARGINAL_KDE_DEFAULT_AUTO_BANDWIDTH_METHOD
    )


def _normalize_gridsize(value: Any) -> int:
    return max(32, min(int(value), 1024))


def _normalize_cut(value: Any) -> float:
    return max(0.0, min(float(value), 5.0))


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


def _normalize_ternary_limit_mode(mode: Any) -> str:
    text = str(mode or "min").strip().lower()
    return text if text in ("min", "max", "both") else "min"


def _normalize_ternary_limit_anchor(anchor: Any) -> str:
    text = str(anchor or "min").strip().lower()
    return text if text in ("min", "max") else "min"


def _normalize_ternary_boundary_percent(percent: Any) -> float:
    return max(0.0, min(float(percent if percent is not None else 5.0), 30.0))


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


def _normalize_ternary_render_margin(margin: Any) -> float:
    return max(0.0, min(float(margin if margin is not None else 0.002), 0.05))


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

    # Detect unsynchronized in-place dict mutations before overwriting.
    # If any of these differ from the snapshot, a state_gateway.set_*_params()
    # call was missed after an in-place modification — log a warning so the
    # regression is visible in logs before it manifests as a user-facing bug.
    _WATCHED_DICT_FIELDS = (
        ("umap_params", state.umap_params),
        ("tsne_params", state.tsne_params),
        ("pca_params", state.pca_params),
        ("robust_pca_params", state.robust_pca_params),
        ("ml_params", state.ml_params),
        ("v1v2_params", state.v1v2_params),
    )
    for name, current in _WATCHED_DICT_FIELDS:
        snap = snapshot.get(name)
        if isinstance(snap, dict) and isinstance(current, dict):
            if current != snap:
                logger.warning(
                    "_sync_state overwriting %s: snapshot differs from live state. "
                    "Missing state_gateway.set_%s() after in-place mutation?",
                    name, name,
                )

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
    state.mixing_endmembers = dict(snapshot["mixing_endmembers"])
    state.mixing_mixtures = dict(snapshot["mixing_mixtures"])
    state.ternary_ranges = dict(snapshot["ternary_ranges"])
    state.kde_style = dict(snapshot["kde_style"])
    state.marginal_kde_style = dict(snapshot["marginal_kde_style"])
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
    state.ternary_auto_zoom = bool(snapshot["ternary_auto_zoom"])
    state.ternary_limit_mode = str(snapshot["ternary_limit_mode"])
    state.ternary_limit_anchor = str(snapshot["ternary_limit_anchor"])
    state.ternary_boundary_percent = float(snapshot["ternary_boundary_percent"])
    state.ternary_manual_limits_enabled = bool(snapshot["ternary_manual_limits_enabled"])
    state.ternary_manual_limits = dict(snapshot["ternary_manual_limits"])
    state.ternary_stretch_mode = str(snapshot["ternary_stretch_mode"])
    state.ternary_stretch = bool(snapshot["ternary_stretch"])
    state.ternary_factors = list(snapshot["ternary_factors"] or [])
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
