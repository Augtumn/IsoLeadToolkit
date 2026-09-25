"""Data panel: grouping, projection and axis controls."""

from __future__ import annotations

from ..base_panel import BasePanel
from .build import DataPanelBuildMixin
from .geochem import DataPanelGeochemMixin
from .grouping import DataPanelGroupingMixin
from .projection import DataPanelProjectionMixin


#: Section metadata used by ui.sections to build the menu dialogs.
PANEL_META = {
    "key": "data",
    "title": "Data",
    "shortcut": "Ctrl+D",
    "order": 1,
}


class DataPanel(
    DataPanelBuildMixin,
    DataPanelProjectionMixin,
    DataPanelGeochemMixin,
    DataPanelGroupingMixin,
    BasePanel,
):
    """数据面板 - 分组与投影设置"""
