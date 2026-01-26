"""
Panel Tabs - Modular tab builders for the Control Panel

This package contains mixins for building each tab in the ControlPanel.
"""

from .settings_tab import SettingsTabMixin
from .algorithm_tab import AlgorithmTabMixin
from .tools_tab import ToolsTabMixin
from .style_tab import StyleTabMixin
from .legend_tab import LegendTabMixin
from .geochemistry_tab import GeochemistryTabMixin

__all__ = [
    'SettingsTabMixin',
    'AlgorithmTabMixin',
    'ToolsTabMixin',
    'StyleTabMixin',
    'LegendTabMixin',
    'GeochemistryTabMixin',
]
