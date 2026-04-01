"""Compatibility facade for selection and interaction handlers."""
from __future__ import annotations

from .isochron import calculate_selected_isochron
from .legend import on_legend_click
from .overlay import refresh_selection_overlay
from .pointer_events import on_click, on_hover
from .selection_tools import _disable_rectangle_selector, sync_selection_tools, toggle_selection_mode
from .shared import notify_selection_ui as _notify_selection_ui

__all__ = [
    'calculate_selected_isochron',
    'on_click',
    'on_hover',
    'on_legend_click',
    'refresh_selection_overlay',
    'sync_selection_tools',
    'toggle_selection_mode',
    '_disable_rectangle_selector',
    '_notify_selection_ui',
]
