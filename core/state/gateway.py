"""State gateway for coordinated app_state mutations."""

from __future__ import annotations

import logging
from typing import Any, Callable

from .app_state import app_state
from .store import StateStore
from ._compat_builders import (
    build_compat_attr_handlers,
    build_overlay_toggle_handlers,
    build_panel_style_allowed_keys,
)

logger = logging.getLogger(__name__)
_UNSET = object()


class AppStateGateway:
    """Provide explicit mutation entry points for shared app state."""

    def __init__(self, state: Any) -> None:
        self._state = state
        store = getattr(state, "state_store", None)
        if store is None:
            store = StateStore(state)
            setattr(state, "state_store", store)
        self._store = store
        self._compat_attr_handlers = build_compat_attr_handlers(self)
        self._overlay_toggle_handlers = build_overlay_toggle_handlers(self)
        self._panel_style_allowed_keys = build_panel_style_allowed_keys()

    def _dispatch(self, action_type: str, **payload: Any) -> dict[str, Any]:
        return self._store.dispatch({"type": action_type, **payload})

    def _set_group_cols_compat(self, value: Any) -> None:
        group_cols = [] if value is None else list(value)
        self.set_group_data_columns(group_cols, list(getattr(self._state, "data_cols", []) or []))

    def _set_data_cols_compat(self, value: Any) -> None:
        data_cols = [] if value is None else list(value)
        self.set_group_data_columns(list(getattr(self._state, "group_cols", []) or []), data_cols)

    def _set_export_image_options_compat(self, value: Any) -> None:
        if isinstance(value, dict):
            self.set_export_image_options(**value)
            return
        # Keep legacy callers safe while preventing direct state bypass.
        self.set_export_image_options()

    def _set_isochron_error_mode_compat(self, value: Any) -> None:
        mode = str(value or "fixed").strip().lower()
        if mode == "columns":
            self.set_isochron_error_columns(
                str(getattr(self._state, "isochron_sx_col", "") or ""),
                str(getattr(self._state, "isochron_sy_col", "") or ""),
                str(getattr(self._state, "isochron_rxy_col", "") or ""),
            )
            return
        self.set_isochron_error_fixed(
            float(getattr(self._state, "isochron_sx_value", 0.001) or 0.001),
            float(getattr(self._state, "isochron_sy_value", 0.001) or 0.001),
            float(getattr(self._state, "isochron_rxy_value", 0.0) or 0.0),
        )

    def _set_isochron_sx_col_compat(self, value: Any) -> None:
        self.set_isochron_error_columns(
            str(value or ""),
            str(getattr(self._state, "isochron_sy_col", "") or ""),
            str(getattr(self._state, "isochron_rxy_col", "") or ""),
        )

    def _set_isochron_sy_col_compat(self, value: Any) -> None:
        self.set_isochron_error_columns(
            str(getattr(self._state, "isochron_sx_col", "") or ""),
            str(value or ""),
            str(getattr(self._state, "isochron_rxy_col", "") or ""),
        )

    def _set_isochron_rxy_col_compat(self, value: Any) -> None:
        self.set_isochron_error_columns(
            str(getattr(self._state, "isochron_sx_col", "") or ""),
            str(getattr(self._state, "isochron_sy_col", "") or ""),
            str(value or ""),
        )

    def _set_isochron_sx_value_compat(self, value: Any) -> None:
        self.set_isochron_error_fixed(
            float(value),
            float(getattr(self._state, "isochron_sy_value", 0.001) or 0.001),
            float(getattr(self._state, "isochron_rxy_value", 0.0) or 0.0),
        )

    def _set_isochron_sy_value_compat(self, value: Any) -> None:
        self.set_isochron_error_fixed(
            float(getattr(self._state, "isochron_sx_value", 0.001) or 0.001),
            float(value),
            float(getattr(self._state, "isochron_rxy_value", 0.0) or 0.0),
        )

    def _set_isochron_rxy_value_compat(self, value: Any) -> None:
        self.set_isochron_error_fixed(
            float(getattr(self._state, "isochron_sx_value", 0.001) or 0.001),
            float(getattr(self._state, "isochron_sy_value", 0.001) or 0.001),
            float(value),
        )

    def set_attr(self, name: str, value: Any) -> None:
        """Set a single app_state attribute via gateway."""
        handler = self._compat_attr_handlers.get(name)
        if handler is not None:
            handler(value)
            return
        logger.warning("Ignored unknown set_attr key: %s", name)

    def set_attrs(self, values: dict[str, Any]) -> None:
        """Set multiple app_state attributes via gateway."""
        for name, value in values.items():
            self.set_attr(name, value)

    def set_panel_style_updates(self, updates: dict[str, Any]) -> None:
        """Apply style-control updates collected from panel widgets."""
        for name, value in updates.items():
            if name not in self._panel_style_allowed_keys:
                logger.warning("Ignored unknown panel style update key: %s", name)
                continue
            handler = self._compat_attr_handlers.get(name)
            if handler is not None:
                handler(value)
                continue
            logger.warning("Ignored unsupported panel style update key: %s", name)

    def set_render_mode(self, render_mode: str) -> None:
        self._dispatch("SET_RENDER_MODE", render_mode=render_mode)

    def set_algorithm(self, algorithm: str) -> None:
        self._dispatch("SET_ALGORITHM", algorithm=algorithm)

    def set_umap_params(self, params: Any) -> None:
        self._dispatch("SET_UMAP_PARAMS", params=dict(params or {}))

    def set_tsne_params(self, params: Any) -> None:
        self._dispatch("SET_TSNE_PARAMS", params=dict(params or {}))

    def set_pca_params(self, params: Any) -> None:
        self._dispatch("SET_PCA_PARAMS", params=dict(params or {}))

    def set_robust_pca_params(self, params: Any) -> None:
        self._dispatch("SET_ROBUST_PCA_PARAMS", params=dict(params or {}))

    def set_ml_params(self, params: Any) -> None:
        self._dispatch("SET_ML_PARAMS", params=dict(params or {}))

    def get_ml_params(self) -> dict[str, Any]:
        return dict(self._store.snapshot().get("ml_params", {}))

    def set_v1v2_params(self, params: Any) -> None:
        self._dispatch("SET_V1V2_PARAMS", params=dict(params or {}))

    def get_v1v2_params(self) -> dict[str, Any]:
        return dict(self._store.snapshot().get("v1v2_params", {}))

    def set_plot_style_grid(self, enabled: bool) -> None:
        self._dispatch("SET_PLOT_STYLE_GRID", enabled=bool(enabled))

    def set_plot_marker_size(self, size: int) -> None:
        self._dispatch("SET_PLOT_MARKER_SIZE", size=int(size))

    def set_plot_marker_alpha(self, alpha: float) -> None:
        self._dispatch("SET_PLOT_MARKER_ALPHA", alpha=float(alpha))

    def set_show_plot_title(self, show: bool) -> None:
        self._dispatch("SET_SHOW_PLOT_TITLE", show=bool(show))

    def set_plot_dpi(self, dpi: int) -> None:
        self._dispatch("SET_PLOT_DPI", dpi=int(dpi))

    def set_custom_primary_font(self, font_name: str) -> None:
        self._dispatch("SET_CUSTOM_PRIMARY_FONT", font_name=str(font_name))

    def set_custom_cjk_font(self, font_name: str) -> None:
        self._dispatch("SET_CUSTOM_CJK_FONT", font_name=str(font_name))

    def set_plot_font_sizes(self, sizes: Any) -> None:
        self._dispatch("SET_PLOT_FONT_SIZES", sizes=dict(sizes or {}))

    def set_plot_facecolor(self, color: str) -> None:
        self._dispatch("SET_PLOT_FACECOLOR", color=str(color))

    def set_axes_facecolor(self, color: str) -> None:
        self._dispatch("SET_AXES_FACECOLOR", color=str(color))

    def set_grid_color(self, color: str) -> None:
        self._dispatch("SET_GRID_COLOR", color=str(color))

    def set_grid_linewidth(self, width: float) -> None:
        self._dispatch("SET_GRID_LINEWIDTH", width=float(width))

    def set_grid_alpha(self, alpha: float) -> None:
        self._dispatch("SET_GRID_ALPHA", alpha=float(alpha))

    def set_grid_linestyle(self, linestyle: str) -> None:
        self._dispatch("SET_GRID_LINESTYLE", linestyle=str(linestyle))

    def set_tick_direction(self, direction: str) -> None:
        self._dispatch("SET_TICK_DIRECTION", direction=str(direction))

    def set_tick_color(self, color: str) -> None:
        self._dispatch("SET_TICK_COLOR", color=str(color))

    def set_tick_length(self, length: float) -> None:
        self._dispatch("SET_TICK_LENGTH", length=float(length))

    def set_tick_width(self, width: float) -> None:
        self._dispatch("SET_TICK_WIDTH", width=float(width))

    def set_axis_linewidth(self, width: float) -> None:
        self._dispatch("SET_AXIS_LINEWIDTH", width=float(width))

    def set_axis_line_color(self, color: str) -> None:
        self._dispatch("SET_AXIS_LINE_COLOR", color=str(color))

    def set_minor_ticks(self, enabled: bool) -> None:
        self._dispatch("SET_MINOR_TICKS", enabled=bool(enabled))

    def set_minor_tick_length(self, length: float) -> None:
        self._dispatch("SET_MINOR_TICK_LENGTH", length=float(length))

    def set_minor_tick_width(self, width: float) -> None:
        self._dispatch("SET_MINOR_TICK_WIDTH", width=float(width))

    def set_show_top_spine(self, show: bool) -> None:
        self._dispatch("SET_SHOW_TOP_SPINE", show=bool(show))

    def set_show_right_spine(self, show: bool) -> None:
        self._dispatch("SET_SHOW_RIGHT_SPINE", show=bool(show))

    def set_minor_grid(self, enabled: bool) -> None:
        self._dispatch("SET_MINOR_GRID", enabled=bool(enabled))

    def set_minor_grid_color(self, color: str) -> None:
        self._dispatch("SET_MINOR_GRID_COLOR", color=str(color))

    def set_minor_grid_linewidth(self, width: float) -> None:
        self._dispatch("SET_MINOR_GRID_LINEWIDTH", width=float(width))

    def set_minor_grid_alpha(self, alpha: float) -> None:
        self._dispatch("SET_MINOR_GRID_ALPHA", alpha=float(alpha))

    def set_minor_grid_linestyle(self, linestyle: str) -> None:
        self._dispatch("SET_MINOR_GRID_LINESTYLE", linestyle=str(linestyle))

    def set_scatter_show_edge(self, show: bool) -> None:
        self._dispatch("SET_SCATTER_SHOW_EDGE", show=bool(show))

    def set_scatter_edgecolor(self, color: str) -> None:
        self._dispatch("SET_SCATTER_EDGECOLOR", color=str(color))

    def set_scatter_edgewidth(self, width: float) -> None:
        self._dispatch("SET_SCATTER_EDGEWIDTH", width=float(width))

    def set_label_color(self, color: str) -> None:
        self._dispatch("SET_LABEL_COLOR", color=str(color))

    def set_label_weight(self, weight: str) -> None:
        self._dispatch("SET_LABEL_WEIGHT", weight=str(weight))

    def set_label_pad(self, pad: float) -> None:
        self._dispatch("SET_LABEL_PAD", pad=float(pad))

    def set_title_color(self, color: str) -> None:
        self._dispatch("SET_TITLE_COLOR", color=str(color))

    def set_title_weight(self, weight: str) -> None:
        self._dispatch("SET_TITLE_WEIGHT", weight=str(weight))

    def set_title_pad(self, pad: float) -> None:
        self._dispatch("SET_TITLE_PAD", pad=float(pad))

    def set_legend_frame_on(self, enabled: bool) -> None:
        self._dispatch("SET_LEGEND_FRAME_ON", enabled=bool(enabled))

    def set_legend_frame_alpha(self, alpha: float) -> None:
        self._dispatch("SET_LEGEND_FRAME_ALPHA", alpha=float(alpha))

    def set_legend_frame_facecolor(self, color: str) -> None:
        self._dispatch("SET_LEGEND_FRAME_FACECOLOR", color=str(color))

    def set_legend_frame_edgecolor(self, color: str) -> None:
        self._dispatch("SET_LEGEND_FRAME_EDGECOLOR", color=str(color))

    def set_adjust_text_force_text(self, force: Any) -> None:
        self._dispatch("SET_ADJUST_TEXT_FORCE_TEXT", force=force)

    def set_adjust_text_force_static(self, force: Any) -> None:
        self._dispatch("SET_ADJUST_TEXT_FORCE_STATIC", force=force)

    def set_adjust_text_expand(self, expand: Any) -> None:
        self._dispatch("SET_ADJUST_TEXT_EXPAND", expand=expand)

    def set_adjust_text_iter_lim(self, iter_lim: int) -> None:
        self._dispatch("SET_ADJUST_TEXT_ITER_LIM", iter_lim=int(iter_lim))

    def set_adjust_text_time_lim(self, time_lim: float) -> None:
        self._dispatch("SET_ADJUST_TEXT_TIME_LIM", time_lim=float(time_lim))

    def set_show_kde(self, show: bool) -> None:
        self._dispatch("SET_SHOW_KDE", show=bool(show))

    def set_show_marginal_kde(self, show: bool) -> None:
        self._dispatch("SET_SHOW_MARGINAL_KDE", show=bool(show))

    def set_show_equation_overlays(self, show: bool) -> None:
        self._dispatch("SET_SHOW_EQUATION_OVERLAYS", show=bool(show))

    def set_geo_model_name(self, model_name: str) -> None:
        self._dispatch("SET_GEO_MODEL_NAME", model_name=model_name)

    def set_marginal_kde_layout(
        self,
        *,
        top_size: float | None = None,
        right_size: float | None = None,
    ) -> None:
        self._dispatch(
            "SET_MARGINAL_KDE_LAYOUT",
            top_size=top_size,
            right_size=right_size,
        )

    def set_marginal_kde_compute_options(
        self,
        *,
        max_points: int | None = None,
        bw_adjust: float | None = None,
        bandwidth: float | None = None,
        kernel: str | None = None,
        auto_bandwidth_method: str | None = None,
        gridsize: int | None = None,
        cut: float | None = None,
        log_transform: bool | None = None,
    ) -> None:
        self._dispatch(
            "SET_MARGINAL_KDE_COMPUTE_OPTIONS",
            max_points=max_points,
            bw_adjust=bw_adjust,
            bandwidth=bandwidth,
            kernel=kernel,
            auto_bandwidth_method=auto_bandwidth_method,
            gridsize=gridsize,
            cut=cut,
            log_transform=log_transform,
        )

    def set_point_size(self, point_size: int) -> None:
        self._dispatch("SET_POINT_SIZE", point_size=int(point_size))

    def set_show_tooltip(self, show: bool) -> None:
        self._dispatch("SET_SHOW_TOOLTIP", show=bool(show))

    def set_tooltip_columns(self, columns: Any) -> None:
        if columns is None:
            col_list: list[Any] = []
        elif isinstance(columns, (str, bytes)):
            col_list = [columns]
        else:
            col_list = list(columns)
        self._dispatch("SET_TOOLTIP_COLUMNS", columns=col_list)

    def set_ui_theme(self, theme: str) -> None:
        self._dispatch("SET_UI_THEME", theme=theme)

    def set_selected_indices(self, indices: Any) -> None:
        self._dispatch("SET_SELECTED_INDICES", indices=indices)

    def set_export_image_options(
        self,
        *,
        preset_key: str | None = None,
        image_ext: str | None = None,
        dpi: int | None = None,
        bbox_tight: bool | None = None,
        pad_inches: float | None = None,
        transparent: bool | None = None,
        point_size: int | None = None,
        legend_size: int | None = None,
        label_size: int | None = None,
        title_size: int | None = None,
        tick_size: int | None = None,
    ) -> None:
        self._dispatch(
            "SET_EXPORT_IMAGE_OPTIONS",
            options={
                "preset_key": preset_key,
                "image_ext": image_ext,
                "dpi": dpi,
                "bbox_tight": bbox_tight,
                "pad_inches": pad_inches,
                "transparent": transparent,
                "point_size": point_size,
                "legend_size": legend_size,
                "label_size": label_size,
                "title_size": title_size,
                "tick_size": tick_size,
            },
        )

    def get_export_image_options(self) -> dict[str, Any]:
        return dict(self._store.snapshot().get("export_image_options", {}))

    def set_figure_axes(self, fig: Any, ax: Any) -> None:
        self._state.fig = fig
        self._state.ax = ax

    def set_figure(self, fig: Any) -> None:
        self._state.fig = fig

    def set_canvas(self, canvas: Any) -> None:
        self._state.canvas = canvas

    def set_axis(self, ax: Any) -> None:
        self._state.ax = ax

    def set_legend_ax(self, legend_ax: Any) -> None:
        self._state.legend_ax = legend_ax

    def set_embedding_progress_callback(self, callback: Any) -> None:
        self._state.embedding_progress_callback = callback

    def set_last_embedding(self, embedding: Any, embedding_type: str) -> None:
        self._dispatch(
            "SET_LAST_EMBEDDING",
            embedding=embedding,
            embedding_type=str(embedding_type),
        )

    def set_pca_diagnostics(
        self,
        *,
        last_pca_variance: Any = _UNSET,
        last_pca_components: Any = _UNSET,
        current_feature_names: Any = _UNSET,
    ) -> None:
        payload: dict[str, Any] = {}
        if last_pca_variance is not _UNSET:
            payload["last_pca_variance"] = last_pca_variance
        if last_pca_components is not _UNSET:
            payload["last_pca_components"] = last_pca_components
        if current_feature_names is not _UNSET:
            payload["current_feature_names"] = current_feature_names
        if payload:
            self._dispatch("SET_PCA_DIAGNOSTICS", **payload)

    def set_overlay_label_flags(self, *, refreshing: bool, adjust_in_progress: bool) -> None:
        self.set_overlay_label_refreshing(refreshing)
        self.set_adjust_text_in_progress(adjust_in_progress)

    def set_paleo_label_refreshing(self, refreshing: bool) -> None:
        self._dispatch("SET_PALEO_LABEL_REFRESHING", refreshing=bool(refreshing))

    def set_control_panel_ref(self, panel: Any) -> None:
        self._state.control_panel_ref = panel

    def set_confidence_level(self, level: float) -> None:
        self._dispatch("SET_CONFIDENCE_LEVEL", level=float(level))

    def set_legend_update_callback(self, callback: Any) -> None:
        self._state.legend_update_callback = callback

    def set_overlay_label_state(self, label_state: dict[str, Any]) -> None:
        handlers: dict[str, Callable[[Any], None]] = {
            "paleoisochron_label_data": self.set_paleoisochron_label_data,
            "plumbotectonics_label_data": self.set_plumbotectonics_label_data,
            "plumbotectonics_isoage_label_data": self.set_plumbotectonics_isoage_label_data,
            "overlay_curve_label_data": self.set_overlay_curve_label_data,
        }
        for key, value in label_state.items():
            handler = handlers.get(key)
            if handler is None:
                logger.warning("Ignored unknown overlay label state key: %s", key)
                continue
            handler(value)

    def set_palette_and_marker_map(self, palette: dict[str, Any], marker_map: dict[str, Any]) -> None:
        self._dispatch("SET_CURRENT_PALETTE", palette=dict(palette))
        self._dispatch("SET_GROUP_MARKER_MAP", marker_map=dict(marker_map))

    def set_current_palette(self, palette: Any) -> None:
        self._dispatch("SET_CURRENT_PALETTE", palette=dict(palette or {}))

    def set_group_marker_map(self, marker_map: Any) -> None:
        self._dispatch("SET_GROUP_MARKER_MAP", marker_map=dict(marker_map or {}))

    def set_adjust_text_in_progress(self, in_progress: bool) -> None:
        self._dispatch("SET_ADJUST_TEXT_IN_PROGRESS", in_progress=bool(in_progress))

    def set_overlay_label_refreshing(self, refreshing: bool) -> None:
        self._dispatch("SET_OVERLAY_LABEL_REFRESHING", refreshing=bool(refreshing))

    def set_current_plot_title(self, title: str) -> None:
        self._dispatch("SET_CURRENT_PLOT_TITLE", title=str(title))

    def set_annotation(self, annotation: Any) -> None:
        self._state.annotation = annotation

    def set_last_2d_cols(self, columns: Any) -> None:
        self._dispatch("SET_LAST_2D_COLS", columns=(list(columns or []) if columns is not None else None))

    def set_recent_files(self, files: Any) -> None:
        self._dispatch("SET_RECENT_FILES", files=list(files or []))

    def set_file_path(self, file_path: str) -> None:
        self._dispatch("SET_FILE_PATH", file_path=str(file_path))

    def set_sheet_name(self, sheet_name: Any) -> None:
        self._dispatch("SET_SHEET_NAME", sheet_name=sheet_name)

    def set_language_code(self, code: str) -> None:
        self._dispatch("SET_LANGUAGE_CODE", code=code)

    def set_line_styles(self, line_styles: Any) -> None:
        self._dispatch("SET_LINE_STYLES", line_styles=dict(line_styles or {}))

    def set_saved_themes(self, themes: Any) -> None:
        self._dispatch("SET_SAVED_THEMES", themes=dict(themes or {}))

    def set_color_scheme(self, color_scheme: str) -> None:
        self._dispatch("SET_COLOR_SCHEME", color_scheme=color_scheme)

    def set_legend_position(self, position: Any) -> None:
        self._dispatch("SET_LEGEND_POSITION", position=position)

    def set_legend_location(self, location: Any) -> None:
        self._dispatch("SET_LEGEND_LOCATION", location=location)

    def set_legend_display_mode(self, mode: Any) -> None:
        self._dispatch("SET_LEGEND_DISPLAY_MODE", mode=str(mode))

    def set_hidden_groups(self, groups: Any) -> None:
        self._dispatch("SET_HIDDEN_GROUPS", groups=set(groups or set()))

    def set_legend_columns(self, columns: int) -> None:
        self._dispatch("SET_LEGEND_COLUMNS", columns=columns)

    def set_legend_nudge_step(self, step: float) -> None:
        self._dispatch("SET_LEGEND_NUDGE_STEP", step=step)

    def set_legend_offset(self, offset: Any) -> None:
        self._dispatch("SET_LEGEND_OFFSET", offset=offset)

    def set_legend_snapshot(self, title: Any, handles: Any, labels: Any) -> None:
        self._dispatch(
            "SET_LEGEND_SNAPSHOT",
            title=title,
            handles=handles,
            labels=labels,
        )

    def set_isochron_results(self, results: Any) -> None:
        self._dispatch("SET_ISOCHRON_RESULTS", results=dict(results or {}))

    def set_plumbotectonics_group_visibility(self, visibility: Any) -> None:
        self._dispatch(
            "SET_PLUMBOTECTONICS_GROUP_VISIBILITY",
            visibility=dict(visibility or {}),
        )

    def set_show_model_curves(self, show: bool) -> None:
        self._dispatch("SET_SHOW_MODEL_CURVES", show=bool(show))

    def set_show_plumbotectonics_curves(self, show: bool) -> None:
        self._dispatch("SET_SHOW_PLUMBOTECTONICS_CURVES", show=bool(show))

    def set_show_paleoisochrons(self, show: bool) -> None:
        self._dispatch("SET_SHOW_PALEOISOCHRONS", show=bool(show))

    def set_show_model_age_lines(self, show: bool) -> None:
        self._dispatch("SET_SHOW_MODEL_AGE_LINES", show=bool(show))

    def set_show_growth_curves(self, show: bool) -> None:
        self._dispatch("SET_SHOW_GROWTH_CURVES", show=bool(show))

    def set_use_real_age_for_mu_kappa(self, enabled: bool) -> None:
        self._dispatch("SET_USE_REAL_AGE_FOR_MU_KAPPA", enabled=bool(enabled))

    def set_mu_kappa_age_col(self, column: Any) -> None:
        self._dispatch("SET_MU_KAPPA_AGE_COL", column=column)

    def set_plumbotectonics_variant(self, variant: str) -> None:
        self._dispatch("SET_PLUMBOTECTONICS_VARIANT", variant=variant)

    def set_paleoisochron_min_age(self, age: int) -> None:
        self._dispatch("SET_PALEOISOCHRON_MIN_AGE", age=int(age))

    def set_paleoisochron_max_age(self, age: int) -> None:
        self._dispatch("SET_PALEOISOCHRON_MAX_AGE", age=int(age))

    def set_paleoisochron_step(self, step: int) -> None:
        self._dispatch("SET_PALEOISOCHRON_STEP", step=step)

    def set_paleoisochron_ages(self, ages: Any) -> None:
        self._dispatch("SET_PALEOISOCHRON_AGES", ages=list(ages or []))

    def set_model_curve_models(self, models: Any) -> None:
        normalized = list(models or []) if models is not None else None
        self._dispatch("SET_MODEL_CURVE_MODELS", models=normalized)

    def set_overlay_artists(self, artists: Any) -> None:
        self._dispatch("SET_OVERLAY_ARTISTS", artists=dict(artists or {}))

    def set_overlay_curve_label_data(self, data: Any) -> None:
        self._dispatch("SET_OVERLAY_CURVE_LABEL_DATA", data=list(data or []))

    def set_paleoisochron_label_data(self, data: Any) -> None:
        self._dispatch("SET_PALEOISOCHRON_LABEL_DATA", data=list(data or []))

    def set_plumbotectonics_label_data(self, data: Any) -> None:
        self._dispatch("SET_PLUMBOTECTONICS_LABEL_DATA", data=list(data or []))

    def set_plumbotectonics_isoage_label_data(self, data: Any) -> None:
        self._dispatch("SET_PLUMBOTECTONICS_ISOAGE_LABEL_DATA", data=list(data or []))

    def set_standardize_data(self, enabled: bool) -> None:
        self._dispatch("SET_STANDARDIZE_DATA", enabled=bool(enabled))

    def set_pca_component_indices(self, indices: Any) -> None:
        self._dispatch("SET_PCA_COMPONENT_INDICES", indices=indices)

    def set_ternary_auto_zoom(self, enabled: bool) -> None:
        self._dispatch("SET_TERNARY_AUTO_ZOOM", enabled=bool(enabled))

    def set_ternary_limit_mode(self, mode: str) -> None:
        self._dispatch("SET_TERNARY_LIMIT_MODE", mode=mode)

    def set_ternary_limit_anchor(self, anchor: str) -> None:
        self._dispatch("SET_TERNARY_LIMIT_ANCHOR", anchor=anchor)

    def set_ternary_manual_limits_enabled(self, enabled: bool) -> None:
        self._dispatch("SET_TERNARY_MANUAL_LIMITS_ENABLED", enabled=bool(enabled))

    def set_ternary_manual_limits(self, limits: Any) -> None:
        self._dispatch("SET_TERNARY_MANUAL_LIMITS", limits=dict(limits or {}))

    def set_ternary_boundary_percent(self, percent: Any) -> None:
        self._dispatch("SET_TERNARY_BOUNDARY_PERCENT", percent=percent)

    def set_model_curve_width(self, width: float) -> None:
        self._dispatch("SET_MODEL_CURVE_WIDTH", width=width)

    def set_plumbotectonics_curve_width(self, width: float) -> None:
        self._dispatch("SET_PLUMBOTECTONICS_CURVE_WIDTH", width=width)

    def set_paleoisochron_width(self, width: float) -> None:
        self._dispatch("SET_PALEOISOCHRON_WIDTH", width=width)

    def set_model_age_line_width(self, width: float) -> None:
        self._dispatch("SET_MODEL_AGE_LINE_WIDTH", width=width)

    def set_isochron_line_width(self, width: float) -> None:
        self._dispatch("SET_ISOCHRON_LINE_WIDTH", width=width)

    def set_selected_isochron_line_width(self, width: float) -> None:
        self._dispatch("SET_SELECTED_ISOCHRON_LINE_WIDTH", width=width)

    def set_isochron_label_options(self, options: Any) -> None:
        self._dispatch("SET_ISOCHRON_LABEL_OPTIONS", options=dict(options or {}))

    def set_mixing_endmembers(self, mapping: Any) -> None:
        self._dispatch("SET_MIXING_ENDMEMBERS", mapping=dict(mapping or {}))

    def set_mixing_mixtures(self, mapping: Any) -> None:
        self._dispatch("SET_MIXING_MIXTURES", mapping=dict(mapping or {}))

    def set_custom_palettes(self, palettes: Any) -> None:
        self._dispatch("SET_CUSTOM_PALETTES", palettes=dict(palettes or {}))

    def set_custom_shape_sets(self, shape_sets: Any) -> None:
        self._dispatch("SET_CUSTOM_SHAPE_SETS", shape_sets=dict(shape_sets or {}))

    def set_legend_item_order(self, order: Any) -> None:
        self._dispatch("SET_LEGEND_ITEM_ORDER", order=list(order or []))

    def set_ternary_render_margin(self, margin: float) -> None:
        self._dispatch("SET_TERNARY_RENDER_MARGIN", margin=margin)

    def set_ternary_stretch_mode(self, mode: str) -> None:
        self._dispatch("SET_TERNARY_STRETCH_MODE", mode=mode)

    def set_ternary_stretch(self, stretch: bool) -> None:
        self._dispatch("SET_TERNARY_STRETCH", stretch=bool(stretch))

    def set_ternary_factors(self, factors: Any) -> None:
        self._dispatch("SET_TERNARY_FACTORS", factors=factors)

    def set_ternary_ranges(self, ranges: Any) -> None:
        self._dispatch("SET_TERNARY_RANGES", ranges=dict(ranges or {}))

    def set_isochron_error_columns(self, sx_col: str, sy_col: str, rxy_col: str) -> None:
        self._dispatch(
            "SET_ISOCHRON_ERROR_COLUMNS",
            sx_col=str(sx_col),
            sy_col=str(sy_col),
            rxy_col=str(rxy_col),
        )

    def set_isochron_error_fixed(self, sx_value: float, sy_value: float, rxy_value: float) -> None:
        self._dispatch(
            "SET_ISOCHRON_ERROR_FIXED",
            sx_value=float(sx_value),
            sy_value=float(sy_value),
            rxy_value=float(rxy_value),
        )

    def set_kde_style(self, style: Any) -> None:
        self._dispatch("SET_KDE_STYLE", style=dict(style or {}))

    def set_marginal_kde_style(self, style: Any) -> None:
        self._dispatch("SET_MARGINAL_KDE_STYLE", style=dict(style or {}))

    def set_ml_last_result(self, result: Any) -> None:
        self._dispatch("SET_ML_LAST_RESULT", result=result)

    def set_ml_last_model_meta(self, meta: Any) -> None:
        self._dispatch("SET_ML_LAST_MODEL_META", meta=meta)

    def set_equation_overlays(self, overlays: Any) -> None:
        self._dispatch("SET_EQUATION_OVERLAYS", overlays=list(overlays or []))

    def set_overlay_toggle(self, attr: str, checked: bool) -> None:
        handler = self._overlay_toggle_handlers.get(attr)
        if handler is not None:
            handler(bool(checked))
            return
        logger.warning("Ignored unknown overlay toggle attr: %s", attr)

    def set_marginal_axes(self, marginal_axes: Any) -> None:
        self._dispatch("SET_MARGINAL_AXES", marginal_axes=marginal_axes)

    def set_draw_selection_ellipse(self, enabled: bool) -> None:
        self._dispatch("SET_DRAW_SELECTION_ELLIPSE", enabled=bool(enabled))

    def set_preserve_import_render_mode(self, preserve: bool) -> None:
        self._dispatch("SET_PRESERVE_IMPORT_RENDER_MODE", enabled=bool(preserve))

    def set_group_data_columns(self, group_cols: list[str], data_cols: list[str]) -> None:
        self._dispatch("SET_GROUP_DATA_COLUMNS", group_cols=list(group_cols), data_cols=list(data_cols))

    def set_last_group_col(self, group_col: str | None) -> None:
        self._dispatch("SET_LAST_GROUP_COL", group_col=group_col)

    def reset_column_selection(self) -> None:
        self._dispatch("RESET_COLUMN_SELECTION")

    def set_selected_2d_columns(self, columns: list[str], *, confirmed: bool = False) -> None:
        self._dispatch("SET_SELECTED_2D_COLUMNS", columns=list(columns), confirmed=bool(confirmed))

    def set_selected_3d_columns(self, columns: list[str], *, confirmed: bool = False) -> None:
        self._dispatch("SET_SELECTED_3D_COLUMNS", columns=list(columns), confirmed=bool(confirmed))

    def set_selected_ternary_columns(self, columns: list[str], *, confirmed: bool = False) -> None:
        self._dispatch("SET_SELECTED_TERNARY_COLUMNS", columns=list(columns), confirmed=bool(confirmed))

    def sync_available_and_visible_groups(self, all_groups: list[str]) -> None:
        self._dispatch("SYNC_AVAILABLE_VISIBLE_GROUPS", all_groups=list(all_groups))

    def set_dataframe_and_source(
        self,
        df: Any,
        *,
        file_path: str,
        sheet_name: str | None,
    ) -> None:
        self._dispatch(
            "SET_DATAFRAME_SOURCE",
            df=df,
            file_path=file_path,
            sheet_name=sheet_name,
        )

    def bump_data_version(self) -> None:
        self._dispatch("BUMP_DATA_VERSION")
        logger.info("Data version updated: %s", self._state.data_version)

    def set_data_version(self, version: int) -> None:
        self._dispatch("SET_DATA_VERSION", version=int(version))

    def clear_selection(self) -> None:
        self._dispatch("CLEAR_SELECTION")

    def disable_selection_mode(self) -> None:
        self.set_selection_mode(False)

    def set_selection_mode(self, enabled: bool) -> None:
        self._dispatch("SET_SELECTION_MODE", enabled=bool(enabled))

    def set_initial_render_done(self, done: bool) -> None:
        self._dispatch("SET_INITIAL_RENDER_DONE", done=bool(done))

    def set_embedding_worker(
        self,
        worker: Any,
        *,
        running: bool,
        task_token: int | None = None,
    ) -> None:
        if task_token is not None:
            self.set_embedding_task_token(int(task_token))
        self._state.embedding_worker = worker
        self.set_embedding_task_running(bool(running))

    def set_embedding_task_token(self, task_token: int) -> None:
        self._dispatch("SET_EMBEDDING_TASK_TOKEN", task_token=int(task_token))

    def set_embedding_task_running(self, running: bool) -> None:
        self._dispatch("SET_EMBEDDING_TASK_RUNNING", running=bool(running))

    def set_rectangle_selector(self, selector: Any) -> None:
        self._state.rectangle_selector = selector

    def set_lasso_selector(self, selector: Any) -> None:
        self._state.lasso_selector = selector

    def set_selection_overlay(self, overlay: Any) -> None:
        self._state.selection_overlay = overlay

    def set_selection_ellipse(self, ellipse: Any) -> None:
        self._state.selection_ellipse = ellipse

    def set_selected_isochron_data(self, data: Any) -> None:
        self._dispatch("SET_SELECTED_ISOCHRON_DATA", data=data)

    def set_show_isochrons(self, show: bool) -> None:
        self._dispatch("SET_SHOW_ISOCHRONS", show=bool(show))

    def set_selection_tool(self, tool: str | None) -> None:
        self._dispatch("SET_SELECTION_TOOL", tool=tool)

    def set_visible_groups(self, groups: list[str] | None) -> None:
        self._dispatch("SET_VISIBLE_GROUPS", groups=groups)

    def set_active_subset_indices(self, indices: Any) -> None:
        self._dispatch("SET_ACTIVE_SUBSET_INDICES", indices=indices)

    def clear_selected_indices(self) -> None:
        self._dispatch("CLEAR_SELECTED_INDICES")

    def add_selected_indices(self, indices: list[int]) -> None:
        self._dispatch("ADD_SELECTED_INDICES", indices=indices)

    def remove_selected_indices(self, indices: list[int]) -> None:
        self._dispatch("REMOVE_SELECTED_INDICES", indices=indices)


state_gateway = AppStateGateway(app_state)
