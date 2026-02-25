"""导出面板 - 数据导出功能"""
import logging
import os

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QGroupBox, QMessageBox,
)
from PyQt5.QtCore import Qt

from core import translate, app_state
from .base_panel import BasePanel

logger = logging.getLogger(__name__)


class ExportPanel(BasePanel):
    """导出标签页"""

    def reset_state(self):
        super().reset_state()
        self.export_csv_button = None
        self.export_excel_button = None
        self.export_append_button = None
        self.export_selected_button = None

    def build(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        export_group = QGroupBox(translate("Export"))
        export_group.setProperty('translate_key', 'Export')
        export_layout = QVBoxLayout()

        self.export_csv_button = QPushButton(translate("Export CSV"))
        self.export_csv_button.setProperty('translate_key', 'Export CSV')
        self.export_csv_button.setFixedWidth(200)
        self.export_csv_button.clicked.connect(self._on_export_csv)
        export_layout.addWidget(self.export_csv_button, 0, Qt.AlignHCenter)

        self.export_excel_button = QPushButton(translate("Export Excel"))
        self.export_excel_button.setProperty('translate_key', 'Export Excel')
        self.export_excel_button.setFixedWidth(200)
        self.export_excel_button.clicked.connect(self._on_export_excel)
        export_layout.addWidget(self.export_excel_button, 0, Qt.AlignHCenter)

        self.export_append_button = QPushButton(translate("Append to Excel"))
        self.export_append_button.setProperty('translate_key', 'Append to Excel')
        self.export_append_button.setFixedWidth(200)
        self.export_append_button.clicked.connect(self._on_export_append_excel)
        export_layout.addWidget(self.export_append_button, 0, Qt.AlignHCenter)

        self.export_selected_button = QPushButton(translate("Export Selected"))
        self.export_selected_button.setProperty('translate_key', 'Export Selected')
        self.export_selected_button.setFixedWidth(200)
        self.export_selected_button.clicked.connect(self._on_export_clicked)
        export_layout.addWidget(self.export_selected_button, 0, Qt.AlignHCenter)

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        layout.addStretch()
        return widget

    # ------ 选择控制 ------

    def _sync_selection_buttons(self):
        """Sync selection button states with active tool."""
        tool = getattr(app_state, 'selection_tool', None)

        selection_button = getattr(self, 'selection_button', None)
        if selection_button is not None:
            selection_button.blockSignals(True)
            selection_button.setChecked(tool == 'export')
            selection_button.setText(
                translate("Disable Selection") if tool == 'export' else translate("Enable Selection")
            )
            selection_button.blockSignals(False)

        ellipse_button = getattr(self, 'ellipse_selection_button', None)
        if ellipse_button is not None:
            ellipse_active = getattr(app_state, 'draw_selection_ellipse', False)
            ellipse_button.blockSignals(True)
            ellipse_button.setChecked(ellipse_active)
            ellipse_button.setText(
                translate("Disable Ellipse") if ellipse_active else translate("Draw Ellipse")
            )
            ellipse_button.blockSignals(False)

        lasso_button = getattr(self, 'lasso_selection_button', None)
        if lasso_button is not None:
            lasso_button.blockSignals(True)
            lasso_button.setChecked(tool == 'lasso')
            lasso_button.setText(
                translate("Disable Custom Shape") if tool == 'lasso' else translate("Custom Shape")
            )
            lasso_button.blockSignals(False)

    def update_selection_controls(self):
        """Refresh selection UI state from app_state."""
        count = len(getattr(app_state, 'selected_indices', []))
        if getattr(self, 'selection_status_label', None) is not None:
            self.selection_status_label.setText(
                translate("Selected Samples: {count}").format(count=count)
            )

        enable_exports = count > 0
        for btn in (
            getattr(self, 'export_csv_button', None),
            getattr(self, 'export_excel_button', None),
            getattr(self, 'export_append_button', None),
            getattr(self, 'export_selected_button', None),
        ):
            if btn is not None:
                btn.setEnabled(enable_exports)
        status_export = getattr(self, 'status_export_button', None)
        if status_export is not None:
            status_export.setEnabled(enable_exports)

        if hasattr(self, '_sync_selection_buttons'):
            self._sync_selection_buttons()

    def _update_status_panel(self):
        """Refresh right-side status panel."""
        status_data_label = getattr(self, 'status_data_label', None)
        status_render_label = getattr(self, 'status_render_label', None)
        status_algo_label = getattr(self, 'status_algo_label', None)
        status_group_label = getattr(self, 'status_group_label', None)
        status_selected_label = getattr(self, 'status_selected_label', None)
        if any(label is None for label in (
            status_data_label,
            status_render_label,
            status_algo_label,
            status_group_label,
            status_selected_label,
        )):
            return

        data_count = len(app_state.df_global) if app_state.df_global is not None else 0
        render_mode = getattr(app_state, 'render_mode', '')
        algorithm = getattr(app_state, 'algorithm', '')
        group_col = getattr(app_state, 'last_group_col', '')
        selected_count = len(getattr(app_state, 'selected_indices', []))

        status_data_label.setText(
            translate("Loaded Data: {count} rows", count=data_count)
        )
        status_render_label.setText(
            translate("Render Mode: {mode}").format(mode=render_mode)
        )
        status_algo_label.setText(
            translate("Algorithm: {mode}").format(mode=algorithm)
        )
        status_group_label.setText(
            translate("Group Column: {col}").format(col=group_col)
        )
        status_selected_label.setText(
            translate("Selected Samples: {count}").format(count=selected_count)
        )

    def _clear_selection_only(self):
        """Clear selection and refresh overlays."""
        if app_state.selected_indices:
            app_state.selected_indices.clear()
        try:
            from visualization.events import refresh_selection_overlay
            refresh_selection_overlay()
        except Exception:
            pass
        self.update_selection_controls()

    def _on_toggle_selection(self):
        """切换选择模式"""
        try:
            from visualization.events import toggle_selection_mode
            toggle_selection_mode('export')
        except Exception as err:
            logger.warning("Failed to toggle selection mode: %s", err)
        self._sync_selection_buttons()

    def _on_toggle_ellipse_selection(self):
        """切换置信椭圆显示"""
        try:
            app_state.draw_selection_ellipse = not getattr(app_state, 'draw_selection_ellipse', False)
            from visualization.events import refresh_selection_overlay
            refresh_selection_overlay()
        except Exception as err:
            logger.warning("Failed to toggle ellipse display: %s", err)
        self._sync_selection_buttons()

    def _on_toggle_lasso_selection(self):
        """切换自定义图形选择模式"""
        try:
            from visualization.events import toggle_selection_mode
            toggle_selection_mode('lasso')
        except Exception as err:
            logger.warning("Failed to toggle custom shape selection: %s", err)
        self._sync_selection_buttons()

    # ------ 导出 ------

    def _build_export_df(self, selected_indices):
        """构建导出 DataFrame，降维算法附加嵌入坐标和参数信息"""
        import pandas as pd
        selected_df = app_state.df_global.iloc[list(selected_indices)].copy()

        algo = getattr(app_state, 'algorithm', None)
        embedding = getattr(app_state, 'last_embedding', None)
        embedding_type = getattr(app_state, 'last_embedding_type', None)

        dr_algorithms = {'UMAP', 'tSNE', 'PCA', 'RobustPCA'}
        if algo not in dr_algorithms or embedding is None or embedding_type is None:
            return selected_df

        if app_state.active_subset_indices is not None:
            data_indices = sorted(list(app_state.active_subset_indices))
        else:
            data_indices = list(range(len(app_state.df_global)))

        index_map = {orig: i for i, orig in enumerate(data_indices)}

        dim1, dim2 = [], []
        for idx in selected_indices:
            if idx in index_map and index_map[idx] < len(embedding):
                row = embedding[index_map[idx]]
                dim1.append(row[0])
                dim2.append(row[1] if len(row) > 1 else None)
            else:
                dim1.append(None)
                dim2.append(None)

        if embedding_type in ('PCA', 'RobustPCA'):
            pca_idx = getattr(app_state, 'pca_component_indices', [0, 1])
            col1 = f'PC{pca_idx[0] + 1}'
            col2 = f'PC{pca_idx[1] + 1}' if len(pca_idx) > 1 else 'PC2'
        else:
            col1 = f'{embedding_type} Dimension 1'
            col2 = f'{embedding_type} Dimension 2'

        selected_df[col1] = dim1
        selected_df[col2] = dim2

        params_map = {
            'UMAP': 'umap_params',
            'tSNE': 'tsne_params',
            'PCA': 'pca_params',
            'RobustPCA': 'robust_pca_params',
        }
        params_attr = params_map.get(algo)
        if params_attr:
            params = getattr(app_state, params_attr, {})
            for k, v in params.items():
                selected_df[f'param_{k}'] = v

        return selected_df

    def _on_export_csv(self):
        """导出CSV"""
        from PyQt5.QtWidgets import QFileDialog

        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected. Please select data points first.")
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Selected Data as CSV"),
            "",
            "CSV Files (*.csv);;All Files (*.*)"
        )

        if file_path:
            try:
                selected_df = self._build_export_df(app_state.selected_indices)
                selected_df.to_csv(file_path, index=False)
                QMessageBox.information(
                    self,
                    translate("Success"),
                    translate("Data exported successfully to {file}").format(file=file_path)
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    translate("Error"),
                    translate("Failed to export data: {error}").format(error=str(e))
                )

    def _on_export_excel(self):
        """导出Excel"""
        from PyQt5.QtWidgets import QFileDialog

        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected. Please select data points first.")
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Selected Data as Excel"),
            "",
            "Excel Files (*.xlsx);;All Files (*.*)"
        )

        if file_path:
            try:
                selected_df = self._build_export_df(app_state.selected_indices)
                selected_df.to_excel(file_path, index=False)
                QMessageBox.information(
                    self,
                    translate("Success"),
                    translate("Data exported successfully to {file}").format(file=file_path)
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    translate("Error"),
                    translate("Failed to export data: {error}").format(error=str(e))
                )

    def _on_export_append_excel(self):
        """追加数据到已有 Excel 文件的新 Sheet"""
        from PyQt5.QtWidgets import QFileDialog, QInputDialog
        import pandas as pd

        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected. Please select data points first.")
            )
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            translate("Select Excel File to Append"),
            "",
            "Excel Files (*.xlsx);;All Files (*.*)"
        )

        if not file_path:
            return

        algo = getattr(app_state, 'algorithm', '')
        default_name = algo if algo else 'Sheet'

        sheet_name, ok = QInputDialog.getText(
            self,
            translate("Sheet Name"),
            translate("Enter sheet name:"),
            text=default_name
        )

        if not ok or not sheet_name.strip():
            return
        sheet_name = sheet_name.strip()

        try:
            import openpyxl
            selected_df = self._build_export_df(app_state.selected_indices)

            if os.path.exists(file_path):
                with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='new') as writer:
                    selected_df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                selected_df.to_excel(file_path, sheet_name=sheet_name, index=False)

            QMessageBox.information(
                self,
                translate("Success"),
                translate("Data appended as sheet '{sheet}' to {file}").format(sheet=sheet_name, file=file_path)
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Failed to export data: {error}").format(error=str(e))
            )

    def _on_export_clicked(self):
        """导出按钮点击"""
        from PyQt5.QtWidgets import QFileDialog

        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected. Please select data points first.")
            )
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            translate("Export Selected Data"),
            "",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*.*)"
        )

        if file_path:
            try:
                selected_df = self._build_export_df(app_state.selected_indices)

                if file_path.endswith('.xlsx'):
                    selected_df.to_excel(file_path, index=False)
                else:
                    selected_df.to_csv(file_path, index=False)

                QMessageBox.information(
                    self,
                    translate("Success"),
                    translate("Data exported successfully to {file}").format(file=file_path)
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    translate("Error"),
                    translate("Failed to export data: {error}").format(error=str(e))
                )

    def _on_analyze_subset(self):
        """子集分析"""
        if not app_state.selected_indices:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No data selected for analysis.")
            )
            return

        QMessageBox.information(
            self,
            translate("Info"),
            translate("Subset analysis will be implemented.")
        )

    def _on_reset_data(self):
        """重置数据"""
        QMessageBox.information(
            self,
            translate("Info"),
            translate("Data reset will be implemented.")
        )
