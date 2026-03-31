"""分析面板 - KDE、选择与分析工具"""

import logging

from .analysis import AnalysisPanelMixin
from .base_panel import BasePanel

logger = logging.getLogger(__name__)


class AnalysisPanel(AnalysisPanelMixin, BasePanel):
    """分析标签页"""
