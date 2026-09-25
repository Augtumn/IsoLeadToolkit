"""Analysis panel: selection tools, diagnostics, equations and mixing."""

from __future__ import annotations

from ..base_panel import BasePanel
from .build import AnalysisPanelBuildMixin
from .diagnostics import AnalysisPanelDiagnosticsMixin
from .equations import AnalysisPanelEquationMixin
from .mixing import AnalysisPanelMixingMixin
from .selection import AnalysisPanelSelectionMixin


class AnalysisPanel(
    AnalysisPanelBuildMixin,
    AnalysisPanelDiagnosticsMixin,
    AnalysisPanelSelectionMixin,
    AnalysisPanelEquationMixin,
    AnalysisPanelMixingMixin,
    BasePanel,
):
    """分析面板 - KDE、选择与分析工具"""
