"""Legend panel: colours, shapes and legend layout controls."""

from __future__ import annotations

from ..base_panel import BasePanel
from .actions import LegendActionsMixin
from .build import LegendBuildMixin
from .editors import LegendEditorsMixin


#: Section metadata used by ui.sections to build the menu dialogs.
PANEL_META = {
    "key": "legend",
    "title": "Legend",
    "shortcut": "Ctrl+L",
    "order": 5,
}


class LegendPanel(LegendBuildMixin, LegendEditorsMixin, LegendActionsMixin, BasePanel):
    """图例面板 - 颜色和形状设置"""
