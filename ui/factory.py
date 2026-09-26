"""Composition root for the main window.

Tests and application entry points construct the window through build_main_window()
so that the widget graph is created in exactly one place; UI behaviour tests no longer
need ad-hoc host objects that fake the mixin attributes.
"""
from __future__ import annotations

from typing import Any


def build_main_window() -> Any:
    """Create the application's main window (Qt widget graph included)."""
    from ui.main_window import Qt5MainWindow

    return Qt5MainWindow()
