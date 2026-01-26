"""
UI Panel - Control Panel for visualization settings

This package provides the interactive control panel for the application.
"""

from .control_panel import ControlPanel, create_control_panel

# Re-export mixins for convenience
from .mixins import (
    PanelUtilsMixin,
    PanelHandlersMixin,
    PanelDialogsMixin,
    PanelExportMixin,
)

from .tabs import (
    SettingsTabMixin,
    AlgorithmTabMixin,
    ToolsTabMixin,
    StyleTabMixin,
    LegendTabMixin,
    GeochemistryTabMixin,
)

__all__ = [
    'ControlPanel',
    'create_control_panel',
    # Mixins
    'PanelUtilsMixin',
    'PanelHandlersMixin',
    'PanelDialogsMixin',
    'PanelExportMixin',
    # Tabs
    'SettingsTabMixin',
    'AlgorithmTabMixin',
    'ToolsTabMixin',
    'StyleTabMixin',
    'LegendTabMixin',
    'GeochemistryTabMixin',
]
