"""Selection overlay synchronization helpers."""
from __future__ import annotations

from visualization.selection_overlay import refresh_selection_overlay_state

from .shared import app_state, state_gateway


def refresh_selection_overlay() -> None:
    """Update selection overlay scatter to highlight chosen points."""
    refresh_selection_overlay_state(
        state=app_state,
        state_write=state_gateway,
    )
