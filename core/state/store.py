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
            "show_kde": bool(getattr(state, "show_kde", False)),
            "show_marginal_kde": bool(getattr(state, "show_marginal_kde", True)),
            "show_equation_overlays": bool(getattr(state, "show_equation_overlays", False)),
            "marginal_kde_top_size": float(getattr(state, "marginal_kde_top_size", 15.0)),
            "marginal_kde_right_size": float(getattr(state, "marginal_kde_right_size", 15.0)),
            "marginal_kde_max_points": int(getattr(state, "marginal_kde_max_points", 5000)),
            "marginal_kde_bw_adjust": float(getattr(state, "marginal_kde_bw_adjust", 1.0)),
            "marginal_kde_gridsize": int(getattr(state, "marginal_kde_gridsize", 256)),
            "marginal_kde_cut": float(getattr(state, "marginal_kde_cut", 1.0)),
            "marginal_kde_log_transform": bool(getattr(state, "marginal_kde_log_transform", False)),
            "selected_indices": set(getattr(state, "selected_indices", set()) or set()),
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

        elif action_type == "SET_SHOW_KDE":
            self._snapshot["show_kde"] = bool(action.get("show", False))

        elif action_type == "SET_SHOW_MARGINAL_KDE":
            self._snapshot["show_marginal_kde"] = bool(action.get("show", False))

        elif action_type == "SET_SHOW_EQUATION_OVERLAYS":
            self._snapshot["show_equation_overlays"] = bool(action.get("show", False))

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

        elif action_type == "BUMP_DATA_VERSION":
            self._snapshot["data_version"] = int(self._snapshot.get("data_version", 0)) + 1
            cache = getattr(self._state, "embedding_cache", None)
            if cache is not None and hasattr(cache, "clear"):
                try:
                    cache.clear()
                except Exception:
                    pass

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
            "show_kde": bool(self._snapshot["show_kde"]),
            "show_marginal_kde": bool(self._snapshot["show_marginal_kde"]),
            "show_equation_overlays": bool(self._snapshot["show_equation_overlays"]),
            "marginal_kde_top_size": float(self._snapshot["marginal_kde_top_size"]),
            "marginal_kde_right_size": float(self._snapshot["marginal_kde_right_size"]),
            "marginal_kde_max_points": int(self._snapshot["marginal_kde_max_points"]),
            "marginal_kde_bw_adjust": float(self._snapshot["marginal_kde_bw_adjust"]),
            "marginal_kde_gridsize": int(self._snapshot["marginal_kde_gridsize"]),
            "marginal_kde_cut": float(self._snapshot["marginal_kde_cut"]),
            "marginal_kde_log_transform": bool(self._snapshot["marginal_kde_log_transform"]),
            "selected_indices": set(self._snapshot["selected_indices"]),
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
        self._state.show_kde = bool(self._snapshot["show_kde"])
        self._state.show_marginal_kde = bool(self._snapshot["show_marginal_kde"])
        self._state.show_equation_overlays = bool(self._snapshot["show_equation_overlays"])
        self._state.marginal_kde_top_size = float(self._snapshot["marginal_kde_top_size"])
        self._state.marginal_kde_right_size = float(self._snapshot["marginal_kde_right_size"])
        self._state.marginal_kde_max_points = int(self._snapshot["marginal_kde_max_points"])
        self._state.marginal_kde_bw_adjust = float(self._snapshot["marginal_kde_bw_adjust"])
        self._state.marginal_kde_gridsize = int(self._snapshot["marginal_kde_gridsize"])
        self._state.marginal_kde_cut = float(self._snapshot["marginal_kde_cut"])
        self._state.marginal_kde_log_transform = bool(self._snapshot["marginal_kde_log_transform"])

        self._state.selected_indices = set(self._snapshot["selected_indices"])
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
