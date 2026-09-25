"""Export panel: data, image and Origin export."""

from __future__ import annotations

from ..base_panel import BasePanel
from .build import ExportPanelBuildMixin
from .common import ExportPanelCommonMixin
from .data_export import ExportPanelDataExportMixin
from .image_export import ExportPanelImageExportMixin
from .origin_export import ExportPanelOriginExportMixin


#: Section metadata used by ui.sections to build the menu dialogs.
PANEL_META = {
    "key": "export",
    "title": "Export",
    "shortcut": "Ctrl+E",
    "order": 4,
}


class ExportPanel(
    ExportPanelBuildMixin,
    ExportPanelDataExportMixin,
    ExportPanelImageExportMixin,
    ExportPanelOriginExportMixin,
    ExportPanelCommonMixin,
    BasePanel,
):
    """导出面板 - 数据导出功能"""
