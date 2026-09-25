"""Display panel: styles, themes and control helpers."""

from __future__ import annotations

from ..base_panel import BasePanel
from .build import DisplayBuildMixin
from .helpers import DisplayControlHelperMixin
from .themes import DisplayThemeMixin


class DisplayPanel(DisplayBuildMixin, DisplayThemeMixin, DisplayControlHelperMixin, BasePanel):
    """显示面板 - UI 与绘图样式设置"""
