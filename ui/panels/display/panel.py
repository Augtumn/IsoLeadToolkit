"""Display panel: styles, themes and control helpers."""

from __future__ import annotations

from ..base_panel import BasePanel
from .build import DisplayBuildMixin
from .helpers import DisplayControlHelperMixin
from .themes import DisplayThemeMixin


#: Section metadata used by ui.sections to build the menu dialogs.
PANEL_META = {
    "key": "display",
    "title": "Display",
    "shortcut": "Ctrl+Shift+D",
    "order": 2,
}


class DisplayPanel(DisplayBuildMixin, DisplayThemeMixin, DisplayControlHelperMixin, BasePanel):
    """显示面板 - UI 与绘图样式设置"""
