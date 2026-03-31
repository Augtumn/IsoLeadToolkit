"""显示面板 - UI 与绘图样式设置"""

import logging

from .base_panel import BasePanel
from .display import DisplayPanelMixin

logger = logging.getLogger(__name__)


class DisplayPanel(DisplayPanelMixin, BasePanel):
    """显示标签页"""
