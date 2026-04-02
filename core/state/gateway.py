"""State gateway for coordinated app_state mutations."""

from __future__ import annotations

import logging
from typing import Any

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

    def _dispatch(self, action_type: str, **payload: Any) -> dict[str, Any]:
        return self._store.dispatch({"type": action_type, **payload})

    def set_attr(self, name: str, value: Any) -> None:
        """Set a single app_state attribute via gateway."""
        if name == "algorithm":
            self.set_algorithm(str(value))
            return
        if name == "show_kde":
            self.set_show_kde(bool(value))
            return
        if name == "show_marginal_kde":
            self.set_show_marginal_kde(bool(value))
            return
        if name == "show_equation_overlays":
            self.set_show_equation_overlays(bool(value))
            return
        if name == "geo_model_name":
            self.set_geo_model_name(str(value))
            return
        if name == "paleo_label_refreshing":
            self.set_paleo_label_refreshing(bool(value))
            return
        if name == "control_panel_ref":
            self.set_control_panel_ref(value)
            return
        if name == "confidence_level":
            self.set_confidence_level(float(value))
            return
        if name == "legend_update_callback":
            self.set_legend_update_callback(value)
            return
        if name == "fig":
            self.set_figure(value)
            return
        if name == "canvas":
            self.set_canvas(value)
            return
        if name == "ax":
            self.set_axis(value)
            return
        if name == "legend_ax":
            self.set_legend_ax(value)
            return
        if name == "last_pca_variance":
            self.set_pca_diagnostics(last_pca_variance=value)
            return
        if name == "last_pca_components":
            self.set_pca_diagnostics(last_pca_components=value)
            return
        if name == "current_feature_names":
            self.set_pca_diagnostics(current_feature_names=value)
            return
        if name == "current_palette":
            self.set_current_palette(value)
            return
        if name == "render_mode":
            self.set_render_mode(str(value))
            return
        if name == "marginal_kde_top_size":
            self.set_marginal_kde_layout(top_size=float(value))
            return
        if name == "marginal_kde_right_size":
            self.set_marginal_kde_layout(right_size=float(value))
            return
        if name == "marginal_kde_max_points":
            self.set_marginal_kde_compute_options(max_points=int(value))
            return
        if name == "marginal_kde_bw_adjust":
            self.set_marginal_kde_compute_options(bw_adjust=float(value))
            return
        if name == "marginal_kde_gridsize":
            self.set_marginal_kde_compute_options(gridsize=int(value))
            return
        if name == "marginal_kde_cut":
            self.set_marginal_kde_compute_options(cut=float(value))
            return
        if name == "marginal_kde_log_transform":
            self.set_marginal_kde_compute_options(log_transform=bool(value))
            return
        if name == "point_size":
            self.set_point_size(int(value))
            return
        if name == "show_tooltip":
            self.set_show_tooltip(bool(value))
            return
        if name == "tooltip_columns":
            self.set_tooltip_columns(value)
            return
        if name == "ui_theme":
            self.set_ui_theme(str(value))
            return
        if name == "preserve_import_render_mode":
            self.set_preserve_import_render_mode(bool(value))
            return
        if name == "selected_indices":
            self.set_selected_indices(value)
            return
        if name == "selection_mode":
            self.set_selection_mode(bool(value))
            return
        if name == "selection_tool":
            self.set_selection_tool(value)
            return
        if name == "data_version":
            self.set_data_version(int(value))
            return
        if name == "visible_groups":
            self.set_visible_groups(value)
            return
        if name == "group_cols":
            group_cols = [] if value is None else list(value)
            self.set_group_data_columns(group_cols, list(getattr(self._state, "data_cols", []) or []))
            return
        if name == "data_cols":
            data_cols = [] if value is None else list(value)
            self.set_group_data_columns(list(getattr(self._state, "group_cols", []) or []), data_cols)
            return
        if name == "export_image_options" and isinstance(value, dict):
            self.set_export_image_options(**value)
            return
        setattr(self._state, name, value)

    def set_attrs(self, values: dict[str, Any]) -> None:
        """Set multiple app_state attributes via gateway."""
        for name, value in values.items():
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
