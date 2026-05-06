"""Origin export logic for export panel."""
from __future__ import annotations

import logging

from PyQt5.QtWidgets import QFileDialog, QMessageBox

from core import app_state, translate

logger = logging.getLogger(__name__)

_origin_checked = False
_origin_available = False


class ExportPanelOriginExportMixin:
    """Origin export methods for ExportPanel."""

    @staticmethod
    def _is_origin_available() -> bool:
        """Check if originpro can be imported (cached)."""
        global _origin_checked, _origin_available
        if _origin_checked:
            return _origin_available
        _origin_checked = True
        try:
            from application.use_cases.export_origin import is_origin_available

            _origin_available = is_origin_available()
        except Exception:
            _origin_available = False
        return _origin_available

    def _on_export_origin_clicked(self):
        """Handle Export to Origin button click."""
        if getattr(app_state, "df_global", None) is None or len(app_state.df_global) == 0:
            QMessageBox.warning(self, translate("Warning"), translate("No data loaded."))
            return
        if getattr(app_state, "fig", None) is None:
            QMessageBox.warning(
                self, translate("Warning"), translate("Plot figure is not initialized.")
            )
            return

        if not self._is_origin_available():
            QMessageBox.warning(
                self,
                translate("Origin Not Available"),
                translate(
                    "Origin export requires the originpro package."
                    " Please install it with: pip install originpro"
                ),
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export to Origin Project"),
            "",
            "Origin Project Files (*.opju);;All Files (*.*)",
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".opju"):
            file_path += ".opju"

        try:
            from application.use_cases.export_origin import export_to_origin

            ok = export_to_origin(file_path)
        except Exception as export_err:
            logger.exception("Origin export failed")
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Failed to export Origin project: {error}").format(
                    error=str(export_err)
                ),
            )
            return

        if ok:
            QMessageBox.information(
                self,
                translate("Success"),
                translate("Origin project exported successfully to {file}").format(
                    file=file_path
                ),
            )
        else:
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Failed to export Origin project."),
            )
