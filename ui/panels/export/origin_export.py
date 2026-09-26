"""Origin export logic for export panel."""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox

from core import app_state, translate

logger = logging.getLogger(__name__)


class ExportPanelOriginExportMixin:
    """Origin export methods for ExportPanel."""

    @staticmethod
    def _is_origin_available() -> bool:
        """Check if originpro can be imported (single source of truth)."""
        try:
            from application.use_cases.export_origin import is_origin_available

            return bool(is_origin_available())
        except Exception:
            return False

    def _on_export_origin_clicked(self):
        """Handle Export to Origin button click."""
        if app_state.df_global is None or len(app_state.df_global) == 0:
            QMessageBox.warning(self, translate("Warning"), translate("No data loaded."))
            return
        if app_state.fig is None:
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
                )
                + "\n\n"
                + translate(
                    'Use "Export Origin Data" instead to write an Origin-importable '
                    "Excel workbook."
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

        target = Path(file_path)
        if target.suffix.lower() != ".opju":
            # Replace any stray extension instead of appending a second one.
            file_path = str(target.with_suffix(".opju"))

        reason = ""
        try:
            from application.use_cases.export_origin import export_to_origin_detailed

            # Origin COM automation can take seconds; show a wait cursor.
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                ok, reason = export_to_origin_detailed(file_path)
            finally:
                QApplication.restoreOverrideCursor()
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
            # Show why it failed instead of a bare "failed" dialog.
            detail = translate("Failed to export Origin project.") 
            if reason:
                detail += "\n\n" + translate("Reason: {reason}").format(reason=reason)
            QMessageBox.critical(self, translate("Error"), detail)

    def _on_export_origin_data_clicked(self):
        """Export Origin-importable Excel data (no originpro required)."""
        if app_state.df_global is None or len(app_state.df_global) == 0:
            QMessageBox.warning(self, translate("Warning"), translate("No data loaded."))
            return
        if app_state.fig is None:
            QMessageBox.warning(
                self, translate("Warning"), translate("Plot figure is not initialized.")
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Origin Data"),
            "",
            "Origin Data Files (*.xlsx);;All Files (*.*)",
        )
        if not file_path:
            return

        target = Path(file_path)
        if target.suffix.lower() != ".xlsx":
            file_path = str(target.with_suffix(".xlsx"))

        try:
            from application.use_cases.export_origin import export_origin_ready_data

            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                ok = export_origin_ready_data(file_path)
            finally:
                QApplication.restoreOverrideCursor()
        except Exception as export_err:
            logger.exception("Origin data export failed")
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Failed to export Origin data: {error}").format(
                    error=str(export_err)
                ),
            )
            return

        if ok:
            QMessageBox.information(
                self,
                translate("Success"),
                translate("Origin data exported successfully to {file}").format(
                    file=file_path
                ),
            )
        else:
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Failed to export Origin data."),
            )
