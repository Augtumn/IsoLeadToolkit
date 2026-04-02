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
            "selected_indices": set(getattr(state, "selected_indices", set()) or set()),
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
            "selected_indices": set(self._snapshot["selected_indices"]),
            "export_image_options": dict(self._snapshot["export_image_options"]),
        }

    def _sync_state(self) -> None:
        render_mode = str(self._snapshot["render_mode"])
        self._state.render_mode = render_mode
        if render_mode in ("UMAP", "tSNE", "PCA", "RobustPCA"):
            self._state.algorithm = render_mode

        self._state.selected_indices = set(self._snapshot["selected_indices"])
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
