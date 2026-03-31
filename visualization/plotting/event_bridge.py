"""Bridges between plotting helpers and event-layer callbacks."""

from __future__ import annotations

from typing import Callable


def get_refresh_selection_overlay() -> Callable[[], None] | None:
    """Return refresh_selection_overlay callback if available.

    This avoids direct hard imports from plotting modules to events,
    keeping the dependency boundary explicit and failure-tolerant.
    """
    try:
        from ..events import refresh_selection_overlay

        return refresh_selection_overlay
    except Exception:
        return None


def refresh_selection_overlay_safe() -> None:
    """Call refresh_selection_overlay when available."""
    callback = get_refresh_selection_overlay()
    if callback is None:
        return
    callback()
