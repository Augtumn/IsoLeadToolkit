"""Analysis panel: selection tools, diagnostics, equations and mixing."""

from __future__ import annotations

from ..base_panel import BasePanel
from .build import AnalysisPanelBuildMixin
from .diagnostics import AnalysisPanelDiagnosticsMixin
from .equations import AnalysisPanelEquationMixin
from .mixing import AnalysisPanelMixingMixin
from .ml import AnalysisPanelMlMixin
from .selection import AnalysisPanelSelectionMixin


#: Section metadata used by ui.sections to build the menu dialogs.
PANEL_META = {
    "key": "analysis",
    "title": "Analysis",
    "shortcut": "Ctrl+Shift+A",
    "order": 3,
}


class AnalysisPanel(
    AnalysisPanelBuildMixin,
    AnalysisPanelDiagnosticsMixin,
    AnalysisPanelSelectionMixin,
    AnalysisPanelEquationMixin,
    AnalysisPanelMixingMixin,
    AnalysisPanelMlMixin,
    BasePanel,
):
    """分析面板 - KDE、选择与分析工具"""
