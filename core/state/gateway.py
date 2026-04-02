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
        if name == "render_mode":
            self.set_render_mode(str(value))
            return
        if name == "selected_indices":
            self.set_selected_indices(value)
            return
        if name == "visible_groups":
            self.set_visible_groups(value)
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

    def set_overlay_label_flags(self, *, refreshing: bool, adjust_in_progress: bool) -> None:
        self._state.overlay_label_refreshing = bool(refreshing)
        self._state.adjust_text_in_progress = bool(adjust_in_progress)

    def set_overlay_label_state(self, label_state: dict[str, Any]) -> None:
        for key, value in label_state.items():
            if isinstance(value, list):
                setattr(self._state, key, list(value))
            else:
                setattr(self._state, key, value)

    def set_palette_and_marker_map(self, palette: dict[str, Any], marker_map: dict[str, Any]) -> None:
        self._state.current_palette = dict(palette)
        self._state.group_marker_map = dict(marker_map)

    def set_show_marginal_kde(self, show: bool) -> None:
        self._state.show_marginal_kde = bool(show)

    def set_marginal_axes(self, marginal_axes: Any) -> None:
        self._state.marginal_axes = marginal_axes

    def set_draw_selection_ellipse(self, enabled: bool) -> None:
        self._state.draw_selection_ellipse = bool(enabled)

    def set_preserve_import_render_mode(self, preserve: bool) -> None:
        self._state.preserve_import_render_mode = preserve

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

    def clear_selection(self) -> None:
        self._dispatch("CLEAR_SELECTED_INDICES")
        self._state.selection_mode = False

    def disable_selection_mode(self) -> None:
        self._state.selection_mode = False

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
        self._state.selection_tool = tool
        self._state.selection_mode = tool is not None

    def set_visible_groups(self, groups: list[str] | None) -> None:
        self._dispatch("SET_VISIBLE_GROUPS", groups=groups)

    def clear_selected_indices(self) -> None:
        self._dispatch("CLEAR_SELECTED_INDICES")

    def add_selected_indices(self, indices: list[int]) -> None:
        self._dispatch("ADD_SELECTED_INDICES", indices=indices)

    def remove_selected_indices(self, indices: list[int]) -> None:
        self._dispatch("REMOVE_SELECTED_INDICES", indices=indices)


state_gateway = AppStateGateway(app_state)
