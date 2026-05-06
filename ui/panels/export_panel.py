"""导出面板 - 数据导出功能"""
from __future__ import annotations

import logging

from PyQt5.QtWidgets import QMessageBox

from core import app_state, translate
from .base_panel import BasePanel
from .export import (
    ExportPanelBuildMixin,
    ExportPanelCommonMixin,
    ExportPanelDataExportMixin,
    ExportPanelImageExportMixin,
    ExportPanelOriginExportMixin,
    ExportPanelSelectionMixin,
)

logger = logging.getLogger(__name__)


class ExportPanel(
    ExportPanelBuildMixin,
    ExportPanelSelectionMixin,
    ExportPanelDataExportMixin,
    ExportPanelImageExportMixin,
    ExportPanelOriginExportMixin,
    ExportPanelCommonMixin,
    BasePanel,
):
    """导出标签页"""

    def _on_analyze_subset(self):
        """子集分析"""
        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected for analysis."),
            )
            return

        QMessageBox.information(
            self,
            translate("Info"),
            translate("Subset analysis will be implemented."),
        )

    def _on_reset_data(self):
        """重置数据"""
        QMessageBox.information(
            self,
            translate("Info"),
            translate("Data reset will be implemented."),
        )
