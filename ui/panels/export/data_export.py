"""Data export logic for export panel."""
from __future__ import annotations

from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from application import (
    append_selected_data_to_excel,
    build_export_dataframe,
    export_selected_data_to_file,
)
from core import app_state, translate


class ExportPanelDataExportMixin:
    """Data export methods for ExportPanel."""

    @staticmethod
    def _current_export_context() -> dict:
        """Collect export context from app_state for application use cases."""
        algo = getattr(app_state, 'algorithm', None)
        embedding = getattr(app_state, 'last_embedding', None)
        embedding_type = getattr(app_state, 'last_embedding_type', None)
        ax = getattr(app_state, 'ax', None)
        axis_labels = {}
        if ax is not None:
            try:
                xl = ax.get_xlabel()
                yl = ax.get_ylabel()
                zl = ax.get_zlabel() if hasattr(ax, 'get_zlabel') else ''
                if xl:
                    axis_labels['x'] = str(xl)
                if yl:
                    axis_labels['y'] = str(yl)
                if zl:
                    axis_labels['z'] = str(zl)
            except Exception:
                pass
        params_map = {
            'UMAP': 'umap_params',
            'tSNE': 'tsne_params',
            'PCA': 'pca_params',
            'RobustPCA': 'robust_pca_params',
        }
        params_attr = params_map.get(algo)
        params = getattr(app_state, params_attr, {}) if params_attr else {}
        return {
            'df_global': app_state.df_global,
            'algorithm': algo,
            'embedding': embedding,
            'embedding_type': embedding_type,
            'active_subset_indices': app_state.active_subset_indices,
            'pca_component_indices': getattr(app_state, 'pca_component_indices', [0, 1]),
            'algorithm_params': params,
            'axis_labels': axis_labels,
        }

    def _build_export_df(self, selected_indices):
        """构建导出 DataFrame，降维算法附加嵌入坐标和参数信息"""
        context = self._current_export_context()
        return build_export_dataframe(
            selected_indices=selected_indices,
            **context,
        )

    def _on_export_csv(self):
        """导出CSV"""
        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected. Please select data points first."),
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Selected Data as CSV"),
            "",
            "CSV Files (*.csv);;All Files (*.*)",
        )

        if file_path:
            try:
                export_path = export_selected_data_to_file(
                    selected_indices=app_state.selected_indices,
                    file_path=file_path,
                    preferred_format='csv',
                    **self._current_export_context(),
                )
                QMessageBox.information(
                    self,
                    translate("Success"),
                    translate("Data exported successfully to {file}").format(file=export_path),
                )
            except Exception as err:
                QMessageBox.critical(
                    self,
                    translate("Error"),
                    translate("Failed to export data: {error}").format(error=str(err)),
                )

    def _on_export_excel(self):
        """导出Excel"""
        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected. Please select data points first."),
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Selected Data as Excel"),
            "",
            "Excel Files (*.xlsx);;All Files (*.*)",
        )

        if file_path:
            try:
                export_path = export_selected_data_to_file(
                    selected_indices=app_state.selected_indices,
                    file_path=file_path,
                    preferred_format='xlsx',
                    **self._current_export_context(),
                )
                QMessageBox.information(
                    self,
                    translate("Success"),
                    translate("Data exported successfully to {file}").format(file=export_path),
                )
            except Exception as err:
                QMessageBox.critical(
                    self,
                    translate("Error"),
                    translate("Failed to export data: {error}").format(error=str(err)),
                )

    def _on_export_append_excel(self):
        """追加数据到已有 Excel 文件的新 Sheet"""
        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected. Please select data points first."),
            )
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            translate("Select Excel File to Append"),
            "",
            "Excel Files (*.xlsx);;All Files (*.*)",
        )

        if not file_path:
            return

        algo = getattr(app_state, 'algorithm', '')
        default_name = algo if algo else 'Sheet'

        sheet_name, ok = QInputDialog.getText(
            self,
            translate("Sheet Name"),
            translate("Enter sheet name:"),
            text=default_name,
        )

        if not ok or not sheet_name.strip():
            return
        sheet_name = sheet_name.strip()

        try:
            export_path = append_selected_data_to_excel(
                selected_indices=app_state.selected_indices,
                file_path=file_path,
                sheet_name=sheet_name,
                **self._current_export_context(),
            )

            QMessageBox.information(
                self,
                translate("Success"),
                translate("Data appended as sheet '{sheet}' to {file}").format(sheet=sheet_name, file=export_path),
            )
        except Exception as err:
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Failed to export data: {error}").format(error=str(err)),
            )

    def _on_export_clicked(self):
        """导出按钮点击"""
        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected. Please select data points first."),
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Selected Data"),
            "",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*.*)",
        )

        if file_path:
            try:
                export_path = export_selected_data_to_file(
                    selected_indices=app_state.selected_indices,
                    file_path=file_path,
                    preferred_format=None,
                    **self._current_export_context(),
                )

                QMessageBox.information(
                    self,
                    translate("Success"),
                    translate("Data exported successfully to {file}").format(file=export_path),
                )
            except Exception as err:
                QMessageBox.critical(
                    self,
                    translate("Error"),
                    translate("Failed to export data: {error}").format(error=str(err)),
                )
