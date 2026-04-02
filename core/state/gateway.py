"""State gateway for coordinated app_state mutations."""

from __future__ import annotations

import logging
from typing import Any, Callable

from .app_state import app_state
from .store import StateStore

logger = logging.getLogger(__name__)


class AppStateGateway:
    """Provide explicit mutation entry points for shared app state."""

    def __init__(self, state: Any) -> None:
        self._state = state
        store = getattr(state, "state_store", None)
        if store is None:
            store = StateStore(state)
            setattr(state, "state_store", store)
        self._store = store
        self._compat_attr_handlers = self._build_compat_attr_handlers()
        self._overlay_toggle_handlers = self._build_overlay_toggle_handlers()

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
        self._state.export_image_options = value

    def _compat_handler(
        self,
        setter_name: str,
        converter: Callable[[Any], Any] | None = None,
    ) -> Callable[[Any], None]:
        """Build a set_attr compatibility handler from setter metadata."""
        setter = getattr(self, setter_name)
        if converter is None:
            return setter
        return lambda value, _setter=setter, _converter=converter: _setter(_converter(value))

    def _build_compat_attr_handlers(self) -> dict[str, Callable[[Any], None]]:
        """Build compatibility dispatch table for legacy set_attr callers."""
        direct_map = {
            "control_panel_ref": "set_control_panel_ref",
            "legend_update_callback": "set_legend_update_callback",
            "fig": "set_figure",
            "canvas": "set_canvas",
            "ax": "set_axis",
            "legend_ax": "set_legend_ax",
            "current_palette": "set_current_palette",
            "annotation": "set_annotation",
            "last_2d_cols": "set_last_2d_cols",
            "recent_files": "set_recent_files",
            "line_styles": "set_line_styles",
            "saved_themes": "set_saved_themes",
            "legend_position": "set_legend_position",
            "legend_location": "set_legend_location",
            "legend_offset": "set_legend_offset",
            "isochron_results": "set_isochron_results",
            "plumbotectonics_group_visibility": "set_plumbotectonics_group_visibility",
            "mu_kappa_age_col": "set_mu_kappa_age_col",
            "paleoisochron_ages": "set_paleoisochron_ages",
            "overlay_artists": "set_overlay_artists",
            "overlay_curve_label_data": "set_overlay_curve_label_data",
            "paleoisochron_label_data": "set_paleoisochron_label_data",
            "plumbotectonics_isoage_label_data": "set_plumbotectonics_isoage_label_data",
            "pca_component_indices": "set_pca_component_indices",
            "ternary_manual_limits": "set_ternary_manual_limits",
            "ternary_factors": "set_ternary_factors",
            "isochron_label_options": "set_isochron_label_options",
            "mixing_endmembers": "set_mixing_endmembers",
            "mixing_mixtures": "set_mixing_mixtures",
            "custom_palettes": "set_custom_palettes",
            "custom_shape_sets": "set_custom_shape_sets",
            "legend_item_order": "set_legend_item_order",
            "ternary_ranges": "set_ternary_ranges",
            "kde_style": "set_kde_style",
            "marginal_kde_style": "set_marginal_kde_style",
            "ml_last_result": "set_ml_last_result",
            "ml_last_model_meta": "set_ml_last_model_meta",
            "equation_overlays": "set_equation_overlays",
            "tooltip_columns": "set_tooltip_columns",
            "selected_indices": "set_selected_indices",
            "selection_tool": "set_selection_tool",
            "visible_groups": "set_visible_groups",
            "group_cols": "_set_group_cols_compat",
            "data_cols": "_set_data_cols_compat",
            "export_image_options": "_set_export_image_options_compat",
        }
        bool_map = {
            "show_kde": "set_show_kde",
            "show_marginal_kde": "set_show_marginal_kde",
            "show_equation_overlays": "set_show_equation_overlays",
            "paleo_label_refreshing": "set_paleo_label_refreshing",
            "adjust_text_in_progress": "set_adjust_text_in_progress",
            "overlay_label_refreshing": "set_overlay_label_refreshing",
            "show_model_curves": "set_show_model_curves",
            "show_plumbotectonics_curves": "set_show_plumbotectonics_curves",
            "show_paleoisochrons": "set_show_paleoisochrons",
            "show_model_age_lines": "set_show_model_age_lines",
            "show_growth_curves": "set_show_growth_curves",
            "use_real_age_for_mu_kappa": "set_use_real_age_for_mu_kappa",
            "standardize_data": "set_standardize_data",
            "ternary_auto_zoom": "set_ternary_auto_zoom",
            "ternary_manual_limits_enabled": "set_ternary_manual_limits_enabled",
            "ternary_stretch": "set_ternary_stretch",
            "marginal_kde_log_transform": "set_marginal_kde_compute_options",
            "show_tooltip": "set_show_tooltip",
            "preserve_import_render_mode": "set_preserve_import_render_mode",
            "selection_mode": "set_selection_mode",
        }
        int_map = {
            "legend_columns": "set_legend_columns",
            "paleoisochron_step": "set_paleoisochron_step",
            "marginal_kde_max_points": "set_marginal_kde_compute_options",
            "marginal_kde_gridsize": "set_marginal_kde_compute_options",
            "point_size": "set_point_size",
            "data_version": "set_data_version",
        }
        float_map = {
            "confidence_level": "set_confidence_level",
            "legend_nudge_step": "set_legend_nudge_step",
            "ternary_boundary_percent": "set_ternary_boundary_percent",
            "model_curve_width": "set_model_curve_width",
            "plumbotectonics_curve_width": "set_plumbotectonics_curve_width",
            "paleoisochron_width": "set_paleoisochron_width",
            "model_age_line_width": "set_model_age_line_width",
            "isochron_line_width": "set_isochron_line_width",
            "selected_isochron_line_width": "set_selected_isochron_line_width",
            "marginal_kde_top_size": "set_marginal_kde_layout",
            "marginal_kde_right_size": "set_marginal_kde_layout",
            "marginal_kde_bw_adjust": "set_marginal_kde_compute_options",
            "marginal_kde_cut": "set_marginal_kde_compute_options",
        }
        str_map = {
            "algorithm": "set_algorithm",
            "geo_model_name": "set_geo_model_name",
            "current_plot_title": "set_current_plot_title",
            "language": "set_language_code",
            "color_scheme": "set_color_scheme",
            "plumbotectonics_variant": "set_plumbotectonics_variant",
            "ternary_limit_mode": "set_ternary_limit_mode",
            "ternary_limit_anchor": "set_ternary_limit_anchor",
            "ternary_stretch_mode": "set_ternary_stretch_mode",
            "render_mode": "set_render_mode",
            "ui_theme": "set_ui_theme",
        }

        handlers: dict[str, Callable[[Any], None]] = {
            "last_embedding": lambda v: self.set_last_embedding(
                v,
                str(getattr(self._state, "last_embedding_type", "")),
            ),
            "last_embedding_type": lambda v: self.set_last_embedding(
                getattr(self._state, "last_embedding", None),
                str(v),
            ),
            "last_pca_variance": lambda v: self.set_pca_diagnostics(last_pca_variance=v),
            "last_pca_components": lambda v: self.set_pca_diagnostics(last_pca_components=v),
            "current_feature_names": lambda v: self.set_pca_diagnostics(current_feature_names=v),
            "marginal_kde_top_size": lambda v: self.set_marginal_kde_layout(top_size=float(v)),
            "marginal_kde_right_size": lambda v: self.set_marginal_kde_layout(right_size=float(v)),
            "marginal_kde_max_points": lambda v: self.set_marginal_kde_compute_options(max_points=int(v)),
            "marginal_kde_bw_adjust": lambda v: self.set_marginal_kde_compute_options(bw_adjust=float(v)),
            "marginal_kde_gridsize": lambda v: self.set_marginal_kde_compute_options(gridsize=int(v)),
            "marginal_kde_cut": lambda v: self.set_marginal_kde_compute_options(cut=float(v)),
            "marginal_kde_log_transform": lambda v: self.set_marginal_kde_compute_options(log_transform=bool(v)),
        }

        for name, setter_name in direct_map.items():
            handlers[name] = self._compat_handler(setter_name)
        for name, setter_name in bool_map.items():
            if name in handlers:
                continue
            handlers[name] = self._compat_handler(setter_name, bool)
        for name, setter_name in int_map.items():
            if name in handlers:
                continue
            handlers[name] = self._compat_handler(setter_name, int)
        for name, setter_name in float_map.items():
            if name in handlers:
                continue
            handlers[name] = self._compat_handler(setter_name, float)
        for name, setter_name in str_map.items():
            if name in handlers:
                continue
            handlers[name] = self._compat_handler(setter_name, str)

        return handlers

    def _build_overlay_toggle_handlers(self) -> dict[str, Callable[[bool], None]]:
        """Build dispatch table for overlay visibility toggle handlers."""
        return {
            "show_model_curves": self.set_show_model_curves,
            "show_plumbotectonics_curves": self.set_show_plumbotectonics_curves,
            "show_paleoisochrons": self.set_show_paleoisochrons,
            "show_model_age_lines": self.set_show_model_age_lines,
            "show_growth_curves": self.set_show_growth_curves,
            "show_isochrons": self.set_show_isochrons,
        }

    def set_attr(self, name: str, value: Any) -> None:
        """Set a single app_state attribute via gateway."""
        handler = self._compat_attr_handlers.get(name)
        if handler is not None:
            handler(value)
            return
        setattr(self._state, name, value)

    def set_attrs(self, values: dict[str, Any]) -> None:
        """Set multiple app_state attributes via gateway."""
        for name, value in values.items():
            self.set_attr(name, value)

    def set_panel_style_updates(self, updates: dict[str, Any]) -> None:
        """Apply style-control updates collected from panel widgets."""
        for name, value in updates.items():
            self.set_attr(name, value)

    def set_render_mode(self, render_mode: str) -> None:
        self._dispatch("SET_RENDER_MODE", render_mode=render_mode)

    def set_algorithm(self, algorithm: str) -> None:
        self._dispatch("SET_ALGORITHM", algorithm=algorithm)

    def set_show_kde(self, show: bool) -> None:
        self._dispatch("SET_SHOW_KDE", show=bool(show))

    def set_show_marginal_kde(self, show: bool) -> None:
        self._dispatch("SET_SHOW_MARGINAL_KDE", show=bool(show))

    def set_show_equation_overlays(self, show: bool) -> None:
        self._dispatch("SET_SHOW_EQUATION_OVERLAYS", show=bool(show))

    def set_geo_model_name(self, model_name: str) -> None:
        self._state.geo_model_name = str(model_name)

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
        gridsize: int | None = None,
        cut: float | None = None,
        log_transform: bool | None = None,
    ) -> None:
        self._dispatch(
            "SET_MARGINAL_KDE_COMPUTE_OPTIONS",
            max_points=max_points,
            bw_adjust=bw_adjust,
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

    def set_last_embedding(self, embedding: Any, embedding_type: str) -> None:
        self._state.last_embedding = embedding
        self._state.last_embedding_type = str(embedding_type)

    def set_pca_diagnostics(
        self,
        *,
        last_pca_variance: Any | None = None,
        last_pca_components: Any | None = None,
        current_feature_names: Any | None = None,
    ) -> None:
        if last_pca_variance is not None:
            self._state.last_pca_variance = last_pca_variance
        if last_pca_components is not None:
            self._state.last_pca_components = last_pca_components
        if current_feature_names is not None:
            self._state.current_feature_names = current_feature_names

    def set_overlay_label_flags(self, *, refreshing: bool, adjust_in_progress: bool) -> None:
        self._state.overlay_label_refreshing = bool(refreshing)
        self._state.adjust_text_in_progress = bool(adjust_in_progress)

    def set_paleo_label_refreshing(self, refreshing: bool) -> None:
        self._state.paleo_label_refreshing = bool(refreshing)

    def set_control_panel_ref(self, panel: Any) -> None:
        self._state.control_panel_ref = panel

    def set_confidence_level(self, level: float) -> None:
        self._state.confidence_level = float(level)

    def set_legend_update_callback(self, callback: Any) -> None:
        self._state.legend_update_callback = callback

    def set_overlay_label_state(self, label_state: dict[str, Any]) -> None:
        for key, value in label_state.items():
            if isinstance(value, list):
                setattr(self._state, key, list(value))
            else:
                setattr(self._state, key, value)

    def set_palette_and_marker_map(self, palette: dict[str, Any], marker_map: dict[str, Any]) -> None:
        self._state.current_palette = dict(palette)
        self._state.group_marker_map = dict(marker_map)

    def set_current_palette(self, palette: Any) -> None:
        self._state.current_palette = dict(palette or {})

    def set_adjust_text_in_progress(self, in_progress: bool) -> None:
        self._state.adjust_text_in_progress = bool(in_progress)

    def set_overlay_label_refreshing(self, refreshing: bool) -> None:
        self._state.overlay_label_refreshing = bool(refreshing)

    def set_current_plot_title(self, title: str) -> None:
        self._state.current_plot_title = str(title)

    def set_annotation(self, annotation: Any) -> None:
        self._state.annotation = annotation

    def set_last_2d_cols(self, columns: Any) -> None:
        self._state.last_2d_cols = list(columns or []) if columns is not None else None

    def set_recent_files(self, files: Any) -> None:
        self._dispatch("SET_RECENT_FILES", files=list(files or []))

    def set_file_path(self, file_path: str) -> None:
        self._state.file_path = str(file_path)

    def set_sheet_name(self, sheet_name: Any) -> None:
        self._state.sheet_name = sheet_name

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

    def set_legend_columns(self, columns: int) -> None:
        self._dispatch("SET_LEGEND_COLUMNS", columns=columns)

    def set_legend_nudge_step(self, step: float) -> None:
        self._dispatch("SET_LEGEND_NUDGE_STEP", step=step)

    def set_legend_offset(self, offset: Any) -> None:
        self._dispatch("SET_LEGEND_OFFSET", offset=offset)

    def set_legend_snapshot(self, title: Any, handles: Any, labels: Any) -> None:
        self._state.legend_last_title = title
        self._state.legend_last_handles = handles
        self._state.legend_last_labels = labels

    def set_isochron_results(self, results: Any) -> None:
        self._state.isochron_results = dict(results or {})

    def set_plumbotectonics_group_visibility(self, visibility: Any) -> None:
        self._state.plumbotectonics_group_visibility = dict(visibility or {})

    def set_show_model_curves(self, show: bool) -> None:
        self._state.show_model_curves = bool(show)

    def set_show_plumbotectonics_curves(self, show: bool) -> None:
        self._state.show_plumbotectonics_curves = bool(show)

    def set_show_paleoisochrons(self, show: bool) -> None:
        self._state.show_paleoisochrons = bool(show)

    def set_show_model_age_lines(self, show: bool) -> None:
        self._state.show_model_age_lines = bool(show)

    def set_show_growth_curves(self, show: bool) -> None:
        self._state.show_growth_curves = bool(show)

    def set_use_real_age_for_mu_kappa(self, enabled: bool) -> None:
        self._state.use_real_age_for_mu_kappa = bool(enabled)

    def set_mu_kappa_age_col(self, column: Any) -> None:
        self._state.mu_kappa_age_col = column

    def set_plumbotectonics_variant(self, variant: str) -> None:
        self._state.plumbotectonics_variant = str(variant)

    def set_paleoisochron_step(self, step: int) -> None:
        self._state.paleoisochron_step = int(step)

    def set_paleoisochron_ages(self, ages: Any) -> None:
        self._state.paleoisochron_ages = list(ages or [])

    def set_overlay_artists(self, artists: Any) -> None:
        self._state.overlay_artists = dict(artists or {})

    def set_overlay_curve_label_data(self, data: Any) -> None:
        self._state.overlay_curve_label_data = list(data or [])

    def set_paleoisochron_label_data(self, data: Any) -> None:
        self._state.paleoisochron_label_data = list(data or [])

    def set_plumbotectonics_isoage_label_data(self, data: Any) -> None:
        self._state.plumbotectonics_isoage_label_data = list(data or [])

    def set_standardize_data(self, enabled: bool) -> None:
        self._state.standardize_data = bool(enabled)

    def set_pca_component_indices(self, indices: Any) -> None:
        if indices is None:
            self._state.pca_component_indices = []
            return
        self._state.pca_component_indices = list(indices)

    def set_ternary_auto_zoom(self, enabled: bool) -> None:
        self._state.ternary_auto_zoom = bool(enabled)

    def set_ternary_limit_mode(self, mode: str) -> None:
        self._state.ternary_limit_mode = str(mode)

    def set_ternary_limit_anchor(self, anchor: str) -> None:
        self._state.ternary_limit_anchor = str(anchor)

    def set_ternary_boundary_percent(self, percent: float) -> None:
        self._state.ternary_boundary_percent = float(percent)

    def set_ternary_manual_limits_enabled(self, enabled: bool) -> None:
        self._state.ternary_manual_limits_enabled = bool(enabled)

    def set_ternary_manual_limits(self, limits: Any) -> None:
        self._state.ternary_manual_limits = dict(limits or {})

    def set_ternary_stretch_mode(self, mode: str) -> None:
        self._state.ternary_stretch_mode = str(mode)

    def set_ternary_stretch(self, enabled: bool) -> None:
        self._state.ternary_stretch = bool(enabled)

    def set_ternary_factors(self, factors: Any) -> None:
        self._state.ternary_factors = dict(factors or {})

    def set_model_curve_width(self, width: float) -> None:
        self._state.model_curve_width = float(width)

    def set_plumbotectonics_curve_width(self, width: float) -> None:
        self._state.plumbotectonics_curve_width = float(width)

    def set_paleoisochron_width(self, width: float) -> None:
        self._state.paleoisochron_width = float(width)

    def set_model_age_line_width(self, width: float) -> None:
        self._state.model_age_line_width = float(width)

    def set_isochron_line_width(self, width: float) -> None:
        self._state.isochron_line_width = float(width)

    def set_selected_isochron_line_width(self, width: float) -> None:
        self._state.selected_isochron_line_width = float(width)

    def set_isochron_label_options(self, options: Any) -> None:
        self._state.isochron_label_options = dict(options or {})

    def set_mixing_endmembers(self, mapping: Any) -> None:
        self._state.mixing_endmembers = dict(mapping or {})

    def set_mixing_mixtures(self, mapping: Any) -> None:
        self._state.mixing_mixtures = dict(mapping or {})

    def set_custom_palettes(self, palettes: Any) -> None:
        self._dispatch("SET_CUSTOM_PALETTES", palettes=dict(palettes or {}))

    def set_custom_shape_sets(self, shape_sets: Any) -> None:
        self._dispatch("SET_CUSTOM_SHAPE_SETS", shape_sets=dict(shape_sets or {}))

    def set_legend_item_order(self, order: Any) -> None:
        self._dispatch("SET_LEGEND_ITEM_ORDER", order=list(order or []))

    def set_ternary_ranges(self, ranges: Any) -> None:
        self._state.ternary_ranges = dict(ranges or {})

    def set_isochron_error_columns(self, sx_col: str, sy_col: str, rxy_col: str) -> None:
        self._state.isochron_error_mode = "columns"
        self._state.isochron_sx_col = str(sx_col)
        self._state.isochron_sy_col = str(sy_col)
        self._state.isochron_rxy_col = str(rxy_col)

    def set_isochron_error_fixed(self, sx_value: float, sy_value: float, rxy_value: float) -> None:
        self._state.isochron_error_mode = "fixed"
        self._state.isochron_sx_value = float(sx_value)
        self._state.isochron_sy_value = float(sy_value)
        self._state.isochron_rxy_value = float(rxy_value)

    def set_kde_style(self, style: Any) -> None:
        self._state.kde_style = dict(style or {})

    def set_marginal_kde_style(self, style: Any) -> None:
        self._state.marginal_kde_style = dict(style or {})

    def set_ml_last_result(self, result: Any) -> None:
        self._state.ml_last_result = result

    def set_ml_last_model_meta(self, meta: Any) -> None:
        self._state.ml_last_model_meta = meta

    def set_equation_overlays(self, overlays: Any) -> None:
        self._state.equation_overlays = list(overlays or [])

    def set_overlay_toggle(self, attr: str, checked: bool) -> None:
        handler = self._overlay_toggle_handlers.get(attr)
        if handler is not None:
            handler(bool(checked))
            return
        setattr(self._state, attr, bool(checked))

    def set_marginal_axes(self, marginal_axes: Any) -> None:
        self._state.marginal_axes = marginal_axes

    def set_draw_selection_ellipse(self, enabled: bool) -> None:
        self._state.draw_selection_ellipse = bool(enabled)

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
        self._state.data_version = int(version)

    def clear_selection(self) -> None:
        self._dispatch("CLEAR_SELECTION")

    def disable_selection_mode(self) -> None:
        self.set_selection_mode(False)

    def set_selection_mode(self, enabled: bool) -> None:
        self._dispatch("SET_SELECTION_MODE", enabled=bool(enabled))

    def set_initial_render_done(self, done: bool) -> None:
        self._state.initial_render_done = done

    def set_embedding_worker(
        self,
        worker: Any,
        *,
        running: bool,
        task_token: int | None = None,
    ) -> None:
        if task_token is not None:
            self._state.embedding_task_token = task_token
        self._state.embedding_worker = worker
        self._state.embedding_task_running = running

    def set_rectangle_selector(self, selector: Any) -> None:
        self._state.rectangle_selector = selector

    def set_lasso_selector(self, selector: Any) -> None:
        self._state.lasso_selector = selector

    def set_selection_overlay(self, overlay: Any) -> None:
        self._state.selection_overlay = overlay

    def set_selection_ellipse(self, ellipse: Any) -> None:
        self._state.selection_ellipse = ellipse

    def set_selected_isochron_data(self, data: Any) -> None:
        self._state.selected_isochron_data = data

    def set_show_isochrons(self, show: bool) -> None:
        self._state.show_isochrons = bool(show)

    def set_selection_tool(self, tool: str | None) -> None:
        self._dispatch("SET_SELECTION_TOOL", tool=tool)

    def set_visible_groups(self, groups: list[str] | None) -> None:
        self._dispatch("SET_VISIBLE_GROUPS", groups=groups)

    def clear_selected_indices(self) -> None:
        self._dispatch("CLEAR_SELECTED_INDICES")

    def add_selected_indices(self, indices: list[int]) -> None:
        self._dispatch("ADD_SELECTED_INDICES", indices=indices)

    def remove_selected_indices(self, indices: list[int]) -> None:
        self._dispatch("REMOVE_SELECTED_INDICES", indices=indices)


state_gateway = AppStateGateway(app_state)
