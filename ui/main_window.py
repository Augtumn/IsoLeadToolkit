"""Qt5 main window composed from dedicated mixins."""
from __future__ import annotations

import logging

from PyQt5.QtWidgets import QMainWindow

from core import state_gateway
from ui.main_window_parts import (
    MainWindowCanvasMixin,
    MainWindowLegendMixin,
    MainWindowLifecycleMixin,
    MainWindowSetupMixin,
)

logger = logging.getLogger(__name__)


class Qt5MainWindow(
    MainWindowSetupMixin,
    MainWindowLegendMixin,
    MainWindowCanvasMixin,
    MainWindowLifecycleMixin,
    QMainWindow,
):
    """Qt5 主窗口基类。"""

    def __init__(self, parent: QMainWindow | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._setup_menubar()
        self._setup_toolbar()
        self._setup_statusbar()
        self._restore_state()
        state_gateway.set_legend_update_callback(self._update_legend_panel)
        state_gateway.set_group_front_callback(self._bring_to_front)
