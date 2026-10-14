"""Application use case for interactive point selection logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

_RAY_CAST_EPSILON: float = 1e-12


@dataclass(frozen=True)
class SelectionTogglePlan:
    """Describe how a candidate selection should mutate current state."""

    action: str
    indices: list[int]


class SelectionInteractionUseCase:
    """Provide pure selection computations decoupled from UI framework."""

    def __init__(self, *, hover_distance_threshold: float = 0.15) -> None:
        self._hover_distance_threshold = float(hover_distance_threshold)

    def resolve_next_tool(self, current_tool: str | None, requested_tool: str, render_mode: str) -> str | None:
        """Return next tool state, raising when selection is unsupported."""
        if current_tool == requested_tool:
            return None
        if requested_tool and render_mode == "3D":
            raise ValueError("Selection mode is only available for 2D projections.")
        return requested_tool

    def rectangle_indices(
        self,
        sample_coordinates: Mapping[int, tuple[float, float]],
        *,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> list[int]:
        """Return sample indices falling inside an axis-aligned rectangle."""
        return [
            idx
            for idx, (x_val, y_val) in sample_coordinates.items()
            if x_min <= x_val <= x_max and y_min <= y_val <= y_max
        ]

    def lasso_indices(
        self,
        sample_coordinates: Mapping[int, tuple[float, float]],
        vertices: Sequence[tuple[float, float]],
    ) -> list[int]:
        """Return sample indices inside a polygon defined by lasso vertices."""
        if len(vertices) < 3:
            return []

        return [
            idx
            for idx, point in sample_coordinates.items()
            if self._point_in_polygon(point, vertices)
        ]

    def nearest_sample_index(
        self,
        sample_coordinates: Mapping[int, tuple[float, float]],
        *,
        x: float,
        y: float,
    ) -> int | None:
        """Return nearest sample index if within hover threshold."""
        best_idx: int | None = None
        best_distance = float("inf")
        for idx, (sx, sy) in sample_coordinates.items():
            distance = ((x - sx) ** 2 + (y - sy) ** 2) ** 0.5
            if distance < self._hover_distance_threshold and distance < best_distance:
                best_distance = distance
                best_idx = idx
        return best_idx

    def plan_toggle(self, current_selected: set[int], candidate_indices: Sequence[int]) -> SelectionTogglePlan:
        """Decide whether to add or remove candidates based on current selection."""
        if not candidate_indices:
            return SelectionTogglePlan(action="noop", indices=[])
        if all(idx in current_selected for idx in candidate_indices):
            return SelectionTogglePlan(action="remove", indices=list(candidate_indices))
        return SelectionTogglePlan(action="add", indices=list(candidate_indices))

    def next_visible_groups(
        self,
        *,
        current_visible_groups: list[str] | None,
        all_groups: list[str],
        target_group: str,
        target_visible: bool,
    ) -> list[str] | None:
        """Return updated visible groups list.

        ``None`` means "all visible"; an empty list is a real answer too - it comes back
        when the last visible group is clicked off, and the plot then draws nothing.
        """
        visible_groups = list(all_groups) if current_visible_groups is None else list(current_visible_groups)

        if target_visible:
            if target_group not in visible_groups:
                visible_groups.append(target_group)
        else:
            if target_group in visible_groups:
                visible_groups.remove(target_group)

        if len(visible_groups) == len(all_groups):
            return None
        return visible_groups

    def _point_in_polygon(
        self,
        point: tuple[float, float],
        vertices: Sequence[tuple[float, float]],
    ) -> bool:
        """Ray-casting point-in-polygon test."""
        x, y = point
        inside = False
        n = len(vertices)
        x1, y1 = vertices[0]
        for i in range(1, n + 1):
            x2, y2 = vertices[i % n]
            if (y1 > y) != (y2 > y):
                dy = y2 - y1
                if abs(dy) < _RAY_CAST_EPSILON:
                    x_intersection = x1
                else:
                    x_intersection = (x2 - x1) * (y - y1) / dy + x1

                if x < x_intersection:
                    inside = not inside
            x1, y1 = x2, y2
        return inside
