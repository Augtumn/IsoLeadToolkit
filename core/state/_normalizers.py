"""Normalizer functions and sync logic extracted from StateStore."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

# The coercion helpers live in core/state/coercers.py (shared with the field
# registry in core/state/fields.py); re-exported here for the existing
# importers (store, dispatch handlers).
from .coercers import (  # noqa: F401  (re-export)
    _ADJUST_TEXT_ITER_MAX,
    _ADJUST_TEXT_ITER_MIN,
    _ADJUST_TEXT_TIME_MAX,
    _ADJUST_TEXT_TIME_MIN,
    _BW_ADJUST_MAX,
    _BW_ADJUST_MIN,
    _KDE_BW_MAX,
    _KDE_BW_MIN,
    _MARGINAL_SIZE_MAX,
    _MARGINAL_SIZE_MIN,
    _MAX_POINTS_MAX,
    _MAX_POINTS_MIN,
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
    _normalize_locked_axis_limits,
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
)

# The field → snapshot write-back loop lives in core/state/fields.py.
from .fields import sync_fields  # noqa: F401  (re-export)

logger = logging.getLogger(__name__)

# ── Normalizer functions ───────────────────────────────────────────────


def _to_index_set(indices: Any) -> set[int]:
    if indices is None:
        return set()
    if isinstance(indices, set):
        return {int(v) for v in indices}
    if isinstance(indices, Iterable) and not isinstance(indices, (str, bytes)):
        return {int(v) for v in indices}
    return {int(indices)}


# ── Sync logic ─────────────────────────────────────────────────────────


def sync_state_store_to_app(state: Any, snapshot: dict[str, Any]) -> None:
    """Write snapshot values back to the live app state object."""
    render_mode = str(snapshot["render_mode"])
    algorithm = str(snapshot["algorithm"])
    if render_mode in ("UMAP", "tSNE", "PCA", "RobustPCA"):
        algorithm = render_mode
        snapshot["algorithm"] = algorithm

    # NOTE: parameter dicts are written back below. Bypass detection for
    # in-place mutations happens in StateStore.dispatch (before applying an
    # action), where snapshot vs live comparison has the correct semantics —
    # comparing here (after the handler updated the snapshot but before the
    # write-back) would flag every legitimate parameter change.
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
    state.current_plot_title = str(snapshot["current_plot_title"])
    state.last_2d_cols = (
        list(snapshot["last_2d_cols"])
        if snapshot["last_2d_cols"] is not None
        else None
    )
    state.overlay.isochron_results = dict(snapshot["isochron_results"])

    state.selected_indices = set(snapshot["selected_indices"])
    state.active_subset_indices = _normalize_active_subset_indices(
        snapshot["active_subset_indices"]
    )
    state.df_global = snapshot["df_global"]
    state.data_version = int(snapshot["data_version"])
    state.selection_mode = bool(snapshot["selection_mode"])
    state.selection_tool = snapshot["selection_tool"]
    state.legend.legend_last_title = snapshot["legend_last_title"]
    state.legend.legend_last_handles = snapshot["legend_last_handles"]
    state.legend.legend_last_labels = snapshot["legend_last_labels"]
    state.saved_themes = dict(snapshot["saved_themes"])
    state.ml_last_result = snapshot["ml_last_result"]
    state.ml_last_model_meta = snapshot["ml_last_model_meta"]
    state.preserve_import_render_mode = bool(snapshot["preserve_import_render_mode"])
    state.available_groups = list(snapshot["available_groups"])
    state.selected_ternary_cols = list(snapshot["selected_ternary_cols"])
    state.selected_2d_confirmed = bool(snapshot["selected_2d_confirmed"])
    state.selected_3d_confirmed = bool(snapshot["selected_3d_confirmed"])
    state.selected_ternary_confirmed = bool(snapshot["selected_ternary_confirmed"])
    state.initial_render_done = bool(snapshot["initial_render_done"])
    sync_fields(state, snapshot)
    state.overlay.model_curve_models = (
        list(snapshot["model_curve_models"])
        if snapshot["model_curve_models"] is not None
        else None
    )
