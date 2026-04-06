"""Legend display state."""
from __future__ import annotations

from typing import Any, Callable


class LegendState:
    """Groups all legend position, style, and panel state fields."""

    def __init__(self) -> None:
        # In-plot legend position
        self.legend_position: str | None = None  # 'upper left', etc. or None to hide
        self.legend_columns = 0  # 0 means auto
        self.legend_offset: tuple[float, float] = (0.0, 0.0)  # Nudge in axes fraction
        self.legend_nudge_step = 0.02

        # Outside legend panel
        self.legend_location = 'outside_left'  # 'outside_left' | 'outside_right'
        self.legend_display_mode = 'inline'  # 'inline' | 'window'

        # Legend frame styling
        self.legend_frame_on = True
        self.legend_frame_alpha = 0.95
        self.legend_frame_facecolor = '#ffffff'
        self.legend_frame_edgecolor = '#cbd5f5'

        # Group visibility in legend
        self.hidden_groups: set[str] = set()
        self.legend_to_scatter: dict[Any, Any] = {}

        # Runtime callback (not persisted)
        self.legend_update_callback: Callable[[], None] | None = None
        self.legend_last_title: Any | None = None
        self.legend_last_handles: Any | None = None
        self.legend_last_labels: Any | None = None
