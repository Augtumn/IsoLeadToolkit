"""StateStore for managed AppState domains."""

from __future__ import annotations

import logging
from typing import Any

from ._dispatch_handlers import dispatch_action
from .fields import snapshot_from_state, snapshot_from_store
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
    _normalize_ternary_limit_anchor,
    _normalize_ternary_limit_mode,
    _normalize_text_pad,
    _normalize_text_weight,
    _normalize_tick_direction,
    _normalize_tick_length,
    _normalize_unit_interval,
    _normalize_visible_groups,
    sync_state_store_to_app,
)

logger = logging.getLogger(__name__)

# Runtime-only snapshot fields that the rendering pipeline legitimately
# writes directly (rebuilt every render / transient artist state); they are
# exempt from the direct-mutation warning below.
_DIFF_WARN_EXCLUDED = frozenset({
    "overlay_artists",
    "overlay_curve_label_data",
    "paleoisochron_label_data",
    "plumbotectonics_label_data",
    "plumbotectonics_isoage_label_data",
    "marginal_axes",
    "legend_last_title",
    "legend_last_handles",
    "legend_last_labels",
    "df_global",
    "last_embedding",
})


def _warn_direct_mutations(state: Any, snapshot: dict[str, Any]) -> None:
    """Warn when snapshot-managed state diverged from the store snapshot.

    Any divergence on a non-exempt field means someone bypassed the gateway;
    the next sync will silently roll that change back. Runtime-only fields
    (render maps, matplotlib objects) are exempt.
    """
    import numpy as np

    for key, snap_value in snapshot.items():
        if key in _DIFF_WARN_EXCLUDED:
            continue
        current = getattr(state, key, None)
        try:
            if isinstance(snap_value, np.ndarray) or isinstance(current, np.ndarray):
                equal = bool(np.array_equal(current, snap_value, equal_nan=True))
            else:
                equal = current == snap_value
        except Exception:
            continue
        if not equal:
            logger.warning(
                "State field '%s' was modified outside the gateway and will "
                "be rolled back on the next sync",
                key,
            )


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
        self._dispatch_hook = None
        self._snapshot: dict[str, Any] = {
            "render_mode": str(getattr(state, "render_mode", "UMAP")),
            "algorithm": str(getattr(state, "algorithm", "UMAP")),
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
            "current_plot_title": str(getattr(state, "current_plot_title", "")),
            "last_2d_cols": (
                list(getattr(state, "last_2d_cols", []) or [])
                if getattr(state, "last_2d_cols", None) is not None
                else None
            ),
            "isochron_results": dict(getattr(state, "isochron_results", {}) or {}),
            "kde_bw_adjust": float(getattr(state, "kde_bw_adjust", 1.0)),
            "kde_bw_method": str(getattr(state, "kde_bw_method", "scott")),
            "kde_gridsize": int(getattr(state, "kde_gridsize", 200)),
            "kde_thresh": float(getattr(state, "kde_thresh", 0.05)),
            "kde_common_norm": bool(getattr(state, "kde_common_norm", False)),
            "kde_warn_singular": bool(getattr(state, "kde_warn_singular", False)),
            "marginal_kde_cumulative": bool(getattr(state, "marginal_kde_cumulative", False)),
            "kde_bw_adjust": float(getattr(state, "kde_bw_adjust", 1.0)),
            "kde_bw_method": str(getattr(state, "kde_bw_method", "scott")),
            "kde_gridsize": int(getattr(state, "kde_gridsize", 200)),
            "kde_thresh": float(getattr(state, "kde_thresh", 0.05)),
            "kde_common_norm": bool(getattr(state, "kde_common_norm", False)),
            "kde_warn_singular": bool(getattr(state, "kde_warn_singular", False)),
            "marginal_kde_cumulative": bool(getattr(state, "marginal_kde_cumulative", False)),
            "kde_bw_adjust": float(getattr(state, "kde_bw_adjust", 1.0)),
            "kde_bw_method": str(getattr(state, "kde_bw_method", "scott")),
            "kde_gridsize": int(getattr(state, "kde_gridsize", 200)),
            "kde_thresh": float(getattr(state, "kde_thresh", 0.05)),
            "kde_common_norm": bool(getattr(state, "kde_common_norm", False)),
            "kde_warn_singular": bool(getattr(state, "kde_warn_singular", False)),
            "marginal_kde_cumulative": bool(getattr(state, "marginal_kde_cumulative", False)),
            "selected_indices": set(getattr(state, "selected_indices", set()) or set()),
            "active_subset_indices": _normalize_active_subset_indices(
                getattr(state, "active_subset_indices", None)
            ),
            "df_global": getattr(state, "df_global", None),
            "data_version": int(getattr(state, "data_version", 0)),
            "selection_mode": bool(getattr(state, "selection_mode", False)),
            "selection_tool": getattr(state, "selection_tool", None),
            "hidden_groups": set(getattr(state, "hidden_groups", set()) or set()),
            "legend_last_title": getattr(state, "legend_last_title", None),
            "legend_last_handles": getattr(state, "legend_last_handles", None),
            "legend_last_labels": getattr(state, "legend_last_labels", None),
            "saved_themes": dict(getattr(state, "saved_themes", {}) or {}),
            "parent_groups": {
                str(k): list(v or []) for k, v in (getattr(state, "parent_groups", {}) or {}).items()
            },
            "parent_shape_map": {
                str(k): str(v) for k, v in (getattr(state, "parent_shape_map", {}) or {}).items()
            },
            "param_presets": {
                str(k): dict(v or {}) for k, v in (getattr(state, "param_presets", {}) or {}).items()
            },
            "ml_last_result": getattr(state, "ml_last_result", None),
            "ml_last_model_meta": getattr(state, "ml_last_model_meta", None),
            "preserve_import_render_mode": bool(getattr(state, "preserve_import_render_mode", False)),
            "available_groups": list(getattr(state, "available_groups", []) or []),
            "selected_ternary_cols": list(getattr(state, "selected_ternary_cols", []) or []),
            "selected_2d_confirmed": bool(getattr(state, "selected_2d_confirmed", False)),
            "selected_3d_confirmed": bool(getattr(state, "selected_3d_confirmed", False)),
            "selected_ternary_confirmed": bool(getattr(state, "selected_ternary_confirmed", False)),
            "initial_render_done": bool(getattr(state, "initial_render_done", False)),
            **snapshot_from_state(state),
            "model_curve_models": (
                list(getattr(state, "model_curve_models", []) or [])
                if getattr(state, "model_curve_models", None) is not None
                else None
            ),
        }
        self._sync_state()

    def dispatch(self, action: dict[str, Any]) -> dict[str, Any]:
        """Dispatch an action and return a snapshot copy."""
        _warn_direct_mutations(self._state, self._snapshot)
        dispatch_action(self, action)
        self._sync_state()
        self._notify_render_mode_if_changed(action)
        hook = self._dispatch_hook
        if callable(hook):
            try:
                hook(str(action.get("type", "")))
            except Exception:
                logger.exception("Dispatch hook failed for action %s", action.get("type"))
        return self.snapshot()

    def _notify_render_mode_if_changed(self, action: dict[str, Any]) -> None:
        """Tell render-mode listeners when the mode actually changed.

        The status bar (and any other follower) refreshes through this
        listener; without it, the bottom-right mode label stays stale after
        switching modes from a panel dialog.
        """
        action_type = str(action.get("type", "")).upper().strip()
        if action_type != "SET_RENDER_MODE":
            return
        notify = getattr(self._state, "notify_render_mode_change", None)
        if callable(notify):
            try:
                notify(str(self._snapshot.get("render_mode", "")))
            except Exception:
                logger.exception("Render-mode listener failed")

    def restore_snapshot(self, payload: dict[str, Any]) -> bool:
        """Bulk-restore persisted fields without going through the gateway.

        Used by the persistence layer on startup (see docs/persistence.md
        §2). Only whitelisted, persisted fields are accepted so a hand-edited
        file can never smuggle junk into the live snapshot. Returns True when
        the payload was applied; a value that breaks the sync is rolled back
        and reported as False instead of raising.
        """
        from ..persistence.schema import SESSION_FIELDS, UI_STATE_FIELDS

        # Metadata keys carried by persisted session payloads that are not
        # snapshot fields; they are expected and silently ignored.
        _META_KEYS = frozenset({"session_version", "saved_at"})

        allowed = SESSION_FIELDS | UI_STATE_FIELDS
        accepted = {key: value for key, value in payload.items() if key in allowed}
        skipped = sorted(set(payload) - allowed - _META_KEYS)
        if skipped:
            logger.warning(
                "Ignored %s non-persisted key(s) during snapshot restore: %s",
                len(skipped),
                ", ".join(skipped),
            )
        if not accepted:
            return False
        # JSON round-trips sets/tuples as lists; restore their native types
        # so the mutation-diff check does not flag a false divergence.
        for key in ("hidden_groups",):
            if key in accepted and accepted[key] is not None:
                accepted[key] = set(accepted[key])
        for key in (
            "legend_offset",
            "adjust_text_force_text",
            "adjust_text_force_static",
            "adjust_text_expand",
        ):
            if key in accepted and accepted[key] is not None:
                accepted[key] = tuple(accepted[key])
        # Values are not schema-validated: a hand-edited file can carry a
        # wrong type that only blows up inside _sync_state (e.g. plot_dpi
        # 'abc'). Apply defensively and roll back on failure so a bad file
        # cannot abort startup.
        previous = {key: self._snapshot.get(key) for key in accepted}
        self._snapshot.update(accepted)
        try:
            self._sync_state()
        except Exception as exc:
            logger.error(
                "Failed to apply restored snapshot (%s); rolling back", exc
            )
            self._snapshot.update(previous)
            try:
                self._sync_state()
            except Exception:
                logger.exception("Rollback after failed restore also failed")
            return False
        return True

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
            "isochron_sx_value": float(self._snapshot["isochron_sx_value"]),
            "isochron_sy_value": float(self._snapshot["isochron_sy_value"]),
            "isochron_rxy_value": float(self._snapshot["isochron_rxy_value"]),
            "isochron_results": dict(self._snapshot["isochron_results"]),
            "use_real_age_for_mu_kappa": bool(self._snapshot["use_real_age_for_mu_kappa"]),
            "plumbotectonics_variant": str(self._snapshot["plumbotectonics_variant"]),
            "paleoisochron_min_age": int(self._snapshot["paleoisochron_min_age"]),
            "paleoisochron_max_age": int(self._snapshot["paleoisochron_max_age"]),
            "paleoisochron_step": int(self._snapshot["paleoisochron_step"]),
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
            "kde_bw_adjust": float(self._snapshot["kde_bw_adjust"]),
            "kde_bw_method": str(self._snapshot["kde_bw_method"]),
            "kde_gridsize": int(self._snapshot["kde_gridsize"]),
            "kde_thresh": float(self._snapshot["kde_thresh"]),
            "kde_common_norm": bool(self._snapshot["kde_common_norm"]),
            "kde_warn_singular": bool(self._snapshot["kde_warn_singular"]),
            "marginal_kde_cumulative": bool(self._snapshot["marginal_kde_cumulative"]),
            "kde_bw_adjust": float(self._snapshot["kde_bw_adjust"]),
            "kde_bw_method": str(self._snapshot["kde_bw_method"]),
            "kde_gridsize": int(self._snapshot["kde_gridsize"]),
            "kde_thresh": float(self._snapshot["kde_thresh"]),
            "kde_common_norm": bool(self._snapshot["kde_common_norm"]),
            "kde_warn_singular": bool(self._snapshot["kde_warn_singular"]),
            "marginal_kde_cumulative": bool(self._snapshot["marginal_kde_cumulative"]),
            "kde_bw_adjust": float(self._snapshot["kde_bw_adjust"]),
            "kde_bw_method": str(self._snapshot["kde_bw_method"]),
            "kde_gridsize": int(self._snapshot["kde_gridsize"]),
            "kde_thresh": float(self._snapshot["kde_thresh"]),
            "kde_common_norm": bool(self._snapshot["kde_common_norm"]),
            "kde_warn_singular": bool(self._snapshot["kde_warn_singular"]),
            "marginal_kde_cumulative": bool(self._snapshot["marginal_kde_cumulative"]),
            "selected_indices": set(self._snapshot["selected_indices"]),
            "active_subset_indices": _normalize_active_subset_indices(
                self._snapshot["active_subset_indices"]
            ),
            "df_global": self._snapshot["df_global"],
            "data_version": int(self._snapshot["data_version"]),
            "selection_mode": bool(self._snapshot["selection_mode"]),
            "selection_tool": self._snapshot["selection_tool"],
            "point_size": int(self._snapshot["point_size"]),
            "show_tooltip": bool(self._snapshot["show_tooltip"]),
            "ui_theme": str(self._snapshot["ui_theme"]),
            "language": str(self._snapshot["language"]),
            "color_scheme": str(self._snapshot["color_scheme"]),
            "legend_display_mode": str(self._snapshot["legend_display_mode"]),
            "legend_columns": int(self._snapshot["legend_columns"]),
            "legend_nudge_step": float(self._snapshot["legend_nudge_step"]),
            "hidden_groups": set(self._snapshot["hidden_groups"]),
            "legend_last_title": self._snapshot["legend_last_title"],
            "legend_last_handles": self._snapshot["legend_last_handles"],
            "legend_last_labels": self._snapshot["legend_last_labels"],
            "saved_themes": dict(self._snapshot["saved_themes"]),
            "parent_groups": {
                str(k): list(v or []) for k, v in (self._snapshot["parent_groups"] or {}).items()
            },
            "parent_shape_map": {
                str(k): str(v) for k, v in (self._snapshot["parent_shape_map"] or {}).items()
            },
            "param_presets": {
                str(k): dict(v or {}) for k, v in (self._snapshot["param_presets"] or {}).items()
            },
            "ml_last_result": self._snapshot["ml_last_result"],
            "ml_last_model_meta": self._snapshot["ml_last_model_meta"],
            "preserve_import_render_mode": bool(self._snapshot["preserve_import_render_mode"]),
            "available_groups": list(self._snapshot["available_groups"]),
            "visible_groups": _normalize_visible_groups(self._snapshot["visible_groups"]),
            "selected_ternary_cols": list(self._snapshot["selected_ternary_cols"]),
            "selected_2d_confirmed": bool(self._snapshot["selected_2d_confirmed"]),
            "selected_3d_confirmed": bool(self._snapshot["selected_3d_confirmed"]),
            "selected_ternary_confirmed": bool(self._snapshot["selected_ternary_confirmed"]),
            "standardize_data": bool(self._snapshot["standardize_data"]),
            "initial_render_done": bool(self._snapshot["initial_render_done"]),
            "pca_component_indices": list(self._snapshot["pca_component_indices"]),
            **snapshot_from_store(self._snapshot),
            "model_curve_width": float(self._snapshot["model_curve_width"]),
            "plumbotectonics_curve_width": float(self._snapshot["plumbotectonics_curve_width"]),
            "paleoisochron_width": float(self._snapshot["paleoisochron_width"]),
            "model_age_line_width": float(self._snapshot["model_age_line_width"]),
            "isochron_line_width": float(self._snapshot["isochron_line_width"]),
            "selected_isochron_line_width": float(self._snapshot["selected_isochron_line_width"]),
            "model_curve_models": (
                list(self._snapshot["model_curve_models"])
                if self._snapshot["model_curve_models"] is not None
                else None
            ),
            "export_image_options": dict(self._snapshot["export_image_options"]),
        }

    def _sync_state(self) -> None:
        sync_state_store_to_app(self._state, self._snapshot)



