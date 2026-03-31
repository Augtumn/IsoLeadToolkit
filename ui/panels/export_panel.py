"""导出面板 - 数据导出功能"""
import logging
import os
import sys
from pathlib import Path

from matplotlib.colors import to_hex

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QGroupBox, QMessageBox, QToolBox,
    QHBoxLayout, QLabel, QComboBox, QSpinBox, QDialog, QDialogButtonBox, QSlider, QFileDialog,
    QCheckBox, QDoubleSpinBox,
    QScrollArea,
)
from PyQt5.QtCore import Qt

from core import CONFIG, translate, app_state
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
        self.image_preset_combo = None
        self.image_format_combo = None
        self.image_point_size_spin = None
        self.image_legend_size_spin = None
        self.image_dpi_spin = None
        self.image_tight_bbox_check = None
        self.image_transparent_check = None
        self.image_pad_inches_spin = None
        self.image_style_source_label = None
        self.export_image_button = None
        self.preview_image_button = None
        self._scienceplots_available = None

    def build(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        section_toolbox = QToolBox()
        section_toolbox.setObjectName('export_section_toolbox')

        data_export_group = QGroupBox(translate("Data Export"))
        data_export_group.setProperty('translate_key', 'Data Export')
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

        data_export_group.setLayout(export_layout)

        export_page = QWidget()
        export_page_layout = QVBoxLayout(export_page)
        export_page_layout.setContentsMargins(6, 6, 6, 6)
        export_page_layout.setSpacing(8)
        export_page_layout.addWidget(data_export_group)
        export_page_layout.addStretch()
        section_toolbox.addItem(export_page, translate("Data Export"))

        image_group = QGroupBox(translate("Image Export"))
        image_group.setProperty('translate_key', 'Image Export')
        image_layout = QVBoxLayout()

        preset_row = QHBoxLayout()
        preset_label = QLabel(translate("Journal Preset"))
        preset_label.setProperty('translate_key', 'Journal Preset')
        preset_row.addWidget(preset_label)
        self.image_preset_combo = QComboBox()
        self.image_preset_combo.addItem(translate("Science Single Column"), 'science_single')
        self.image_preset_combo.addItem(translate("IEEE Single Column"), 'ieee_single')
        self.image_preset_combo.addItem(translate("Nature Double Column"), 'nature_double')
        self.image_preset_combo.addItem(translate("Presentation"), 'presentation')
        self.image_preset_combo.currentIndexChanged.connect(self._on_image_preset_changed)
        preset_row.addWidget(self.image_preset_combo)
        image_layout.addLayout(preset_row)

        format_row = QHBoxLayout()
        format_label = QLabel(translate("Image Format"))
        format_label.setProperty('translate_key', 'Image Format')
        format_row.addWidget(format_label)
        self.image_format_combo = QComboBox()
        self.image_format_combo.addItem("PNG", "png")
        self.image_format_combo.addItem("TIFF", "tiff")
        self.image_format_combo.addItem("PDF", "pdf")
        self.image_format_combo.addItem("SVG", "svg")
        self.image_format_combo.addItem("EPS", "eps")
        format_row.addWidget(self.image_format_combo)
        image_layout.addLayout(format_row)

        style_source_row = QHBoxLayout()
        style_source_label = QLabel(translate("Template Source"))
        style_source_label.setProperty('translate_key', 'Template Source')
        style_source_row.addWidget(style_source_label)
        self.image_style_source_label = QLabel()
        style_source_row.addWidget(self.image_style_source_label)
        image_layout.addLayout(style_source_row)

        dpi_row = QHBoxLayout()
        dpi_label = QLabel(translate("Export DPI"))
        dpi_label.setProperty('translate_key', 'Export DPI')
        dpi_row.addWidget(dpi_label)
        self.image_dpi_spin = QSpinBox()
        self.image_dpi_spin.setRange(72, 1200)
        self.image_dpi_spin.setSingleStep(25)
        self.image_dpi_spin.setValue(int(CONFIG.get('savefig_dpi', 400)))
        dpi_row.addWidget(self.image_dpi_spin)
        image_layout.addLayout(dpi_row)

        point_size_row = QHBoxLayout()
        point_size_label = QLabel(translate("Point Size"))
        point_size_label.setProperty('translate_key', 'Point Size')
        point_size_row.addWidget(point_size_label)
        self.image_point_size_spin = QSpinBox()
        self.image_point_size_spin.setRange(1, 50)
        self.image_point_size_spin.setSingleStep(1)
        self.image_point_size_spin.setValue(int(getattr(app_state, 'point_size', 60)))
        point_size_row.addWidget(self.image_point_size_spin)
        image_layout.addLayout(point_size_row)

        legend_size_row = QHBoxLayout()
        legend_size_label = QLabel(translate("Legend Size"))
        legend_size_label.setProperty('translate_key', 'Legend Size')
        legend_size_row.addWidget(legend_size_label)
        self.image_legend_size_spin = QSpinBox()
        self.image_legend_size_spin.setRange(1, 15)
        self.image_legend_size_spin.setSingleStep(1)
        self.image_legend_size_spin.setValue(8)
        legend_size_row.addWidget(self.image_legend_size_spin)
        image_layout.addLayout(legend_size_row)

        bbox_row = QHBoxLayout()
        self.image_tight_bbox_check = QCheckBox(translate("Tight Bounding Box"))
        self.image_tight_bbox_check.setProperty('translate_key', 'Tight Bounding Box')
        self.image_tight_bbox_check.setChecked(True)
        self.image_transparent_check = QCheckBox(translate("Transparent Background"))
        self.image_transparent_check.setProperty('translate_key', 'Transparent Background')
        self.image_transparent_check.setChecked(False)
        bbox_row.addWidget(self.image_tight_bbox_check)
        bbox_row.addWidget(self.image_transparent_check)
        image_layout.addLayout(bbox_row)

        pad_row = QHBoxLayout()
        pad_label = QLabel(translate("Padding (inch)"))
        pad_label.setProperty('translate_key', 'Padding (inch)')
        pad_row.addWidget(pad_label)
        self.image_pad_inches_spin = QDoubleSpinBox()
        self.image_pad_inches_spin.setRange(0.0, 1.0)
        self.image_pad_inches_spin.setSingleStep(0.01)
        self.image_pad_inches_spin.setDecimals(2)
        self.image_pad_inches_spin.setValue(0.02)
        pad_row.addWidget(self.image_pad_inches_spin)
        image_layout.addLayout(pad_row)

        if self.image_tight_bbox_check is not None and self.image_pad_inches_spin is not None:
            self.image_tight_bbox_check.toggled.connect(self.image_pad_inches_spin.setEnabled)
            self.image_pad_inches_spin.setEnabled(self.image_tight_bbox_check.isChecked())

        button_row = QHBoxLayout()
        self.export_image_button = QPushButton(translate("Export Image"))
        self.export_image_button.setProperty('translate_key', 'Export Image')
        self.export_image_button.setFixedWidth(160)
        self.export_image_button.clicked.connect(self._on_export_image_clicked)
        button_row.addWidget(self.export_image_button, 0, Qt.AlignHCenter)

        self.preview_image_button = QPushButton(translate("Preview Export"))
        self.preview_image_button.setProperty('translate_key', 'Preview Export')
        self.preview_image_button.setFixedWidth(160)
        self.preview_image_button.clicked.connect(self._on_preview_image_clicked)
        button_row.addWidget(self.preview_image_button, 0, Qt.AlignHCenter)
        image_layout.addLayout(button_row)

        image_group.setLayout(image_layout)

        image_page = QWidget()
        image_page_layout = QVBoxLayout(image_page)
        image_page_layout.setContentsMargins(6, 6, 6, 6)
        image_page_layout.setSpacing(8)
        image_page_layout.addWidget(image_group)
        image_page_layout.addStretch()
        section_toolbox.addItem(image_page, translate("Image Export"))

        layout.addWidget(section_toolbox)

        self._on_image_preset_changed()

        layout.addStretch()
        return widget

    def _on_image_preset_changed(self):
        """Sync export point size input with the selected preset defaults."""
        if self.image_preset_combo is None or self.image_point_size_spin is None:
            return
        preset_key = self.image_preset_combo.currentData() or 'science_single'
        profile = self._image_export_profile(str(preset_key))
        self.image_point_size_spin.blockSignals(True)
        self.image_point_size_spin.setValue(int(profile.get('point_size', 60)))
        self.image_point_size_spin.blockSignals(False)
        if self.image_legend_size_spin is not None:
            default_legend_size = int(round(float((profile.get('legend', {}) or {}).get('fontsize', 8.0))))
            self.image_legend_size_spin.blockSignals(True)
            self.image_legend_size_spin.setValue(default_legend_size)
            self.image_legend_size_spin.blockSignals(False)
        if self.image_dpi_spin is not None:
            self.image_dpi_spin.blockSignals(True)
            self.image_dpi_spin.setValue(int(profile.get('dpi', CONFIG.get('savefig_dpi', 400))))
            self.image_dpi_spin.blockSignals(False)
        self._update_style_source_label()

    def _is_scienceplots_available(self) -> bool:
        """Cache SciencePlots availability for responsive UI interactions."""
        cached = getattr(self, '_scienceplots_available', None)
        if cached is None:
            cached = self._load_scienceplots()
            self._scienceplots_available = bool(cached)
        return bool(cached)

    def _update_style_source_label(self) -> None:
        """Refresh style source hint for current export preset."""
        if self.image_style_source_label is None:
            return
        if self._is_scienceplots_available():
            text = translate("Template Source: SciencePlots")
        else:
            text = translate("Template Source: Built-in fallback")
        self.image_style_source_label.setText(text)

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

    def _resolve_group_col(self) -> str | None:
        """Resolve group column using current state fallback rules."""
        group_col = getattr(app_state, 'last_group_col', None)
        group_cols = list(getattr(app_state, 'group_cols', []) or [])
        if not group_col or group_col not in group_cols:
            if group_cols:
                return group_cols[0]
            return None
        return group_col

    def _default_numeric_cols(self) -> list[str]:
        """Return numeric data columns available in current dataframe."""
        df_global = getattr(app_state, 'df_global', None)
        if df_global is None:
            return []
        data_cols = list(getattr(app_state, 'data_cols', []) or [])
        return [c for c in data_cols if c in df_global.columns]

    def _resolve_2d_cols(self) -> list[str]:
        """Return valid 2D column selection with fallback defaults."""
        available = self._default_numeric_cols()
        selected = [c for c in list(getattr(app_state, 'selected_2d_cols', []) or []) if c in available]
        if len(selected) >= 2:
            return selected[:2]
        return available[:2]

    def _resolve_3d_cols(self) -> list[str]:
        """Return valid 3D column selection with fallback defaults."""
        available = self._default_numeric_cols()
        selected = [c for c in list(getattr(app_state, 'selected_3d_cols', []) or []) if c in available]
        if len(selected) >= 3:
            return selected[:3]
        return available[:3]

    def _render_current_mode_sync(self, point_size: int | None = None) -> bool:
        """Render current mode synchronously onto app_state.fig/app_state.ax."""
        from visualization.plotting import plot_embedding, plot_2d_data, plot_3d_data

        render_mode = str(getattr(app_state, 'render_mode', '') or '')
        group_col = self._resolve_group_col()
        if not group_col:
            logger.warning("No group column available for image export")
            return False

        size = int(point_size if point_size is not None else getattr(app_state, 'point_size', 60))

        if render_mode == '2D':
            cols_2d = self._resolve_2d_cols()
            if len(cols_2d) != 2:
                return False
            is_kde = bool(getattr(app_state, 'show_kde', False) or getattr(app_state, 'show_2d_kde', False))
            return bool(plot_2d_data(group_col, cols_2d, size=size, show_kde=is_kde))

        if render_mode == '3D':
            cols_3d = self._resolve_3d_cols()
            if len(cols_3d) != 3:
                return False
            return bool(plot_3d_data(group_col, cols_3d, size=size))

        mode_normalized = str(render_mode).strip().upper()
        if mode_normalized == 'TSNE':
            expected_embedding_type = 'tSNE'
        elif mode_normalized == 'ROBUSTPCA':
            expected_embedding_type = 'RobustPCA'
        else:
            expected_embedding_type = render_mode

        cached_embedding = getattr(app_state, 'last_embedding', None)
        cached_type = getattr(app_state, 'last_embedding_type', None)
        use_cached_embedding = (
            cached_embedding is not None
            and str(cached_type or '') == str(expected_embedding_type)
        )

        precomputed_meta = {
            'last_pca_variance': getattr(app_state, 'last_pca_variance', None),
            'last_pca_components': getattr(app_state, 'last_pca_components', None),
            'current_feature_names': getattr(app_state, 'current_feature_names', None),
        }

        return bool(
            plot_embedding(
                group_col,
                render_mode,
                umap_params=getattr(app_state, 'umap_params', None),
                tsne_params=getattr(app_state, 'tsne_params', None),
                pca_params=getattr(app_state, 'pca_params', None),
                robust_pca_params=getattr(app_state, 'robust_pca_params', None),
                size=size,
                precomputed_embedding=cached_embedding if use_cached_embedding else None,
                precomputed_meta=precomputed_meta if use_cached_embedding else None,
            )
        )

    @staticmethod
    def _capture_axis_view(ax) -> dict | None:
        """Capture axis limits and camera so export matches current view."""
        if ax is None:
            return None
        try:
            view = {
                'is3d': getattr(ax, 'name', '') == '3d',
                'xlim': ax.get_xlim(),
                'ylim': ax.get_ylim(),
            }
            if view['is3d']:
                view['zlim'] = ax.get_zlim()
                view['elev'] = getattr(ax, 'elev', None)
                view['azim'] = getattr(ax, 'azim', None)
            return view
        except Exception:
            return None

    @staticmethod
    def _apply_axis_view(ax, view: dict | None) -> None:
        """Apply previously captured axis view when axes are compatible."""
        if ax is None or not view:
            return
        try:
            is3d_now = getattr(ax, 'name', '') == '3d'
            if bool(view.get('is3d', False)) != is3d_now:
                return
            ax.set_xlim(view['xlim'])
            ax.set_ylim(view['ylim'])
            if is3d_now and 'zlim' in view:
                ax.set_zlim(view['zlim'])
                elev = view.get('elev')
                azim = view.get('azim')
                if elev is not None or azim is not None:
                    ax.view_init(
                        elev=elev if elev is not None else getattr(ax, 'elev', None),
                        azim=azim if azim is not None else getattr(ax, 'azim', None),
                    )
        except Exception:
            pass

    def _load_scienceplots(self):
        """Load scienceplots from installed environment or local reference clone."""
        try:
            import scienceplots  # noqa: F401
            return True
        except Exception:
            pass

        workspace_root = Path(__file__).resolve().parents[2]
        local_src = workspace_root / 'reference' / 'SciencePlots-master' / 'src'
        if local_src.exists():
            src_str = str(local_src)
            if src_str not in sys.path:
                sys.path.insert(0, src_str)
        try:
            import scienceplots  # noqa: F401
            return True
        except Exception as err:
            logger.warning("Failed to import scienceplots: %s", err)
            return False

    @staticmethod
    def _mm_to_inch(mm_value: float) -> float:
        return float(mm_value) / 25.4

    def _image_export_profile(self, preset_key: str) -> dict:
        """Return export profile for a journal preset."""
        profiles = {
            'science_single': {
                'styles': ['science', 'no-latex'],
                'width_mm': 85.0,
                'height_ratio': 0.72,
                'dpi': 300,
                'point_size': 48,
                'legend': {
                    'fontsize': 7.0,
                    'title_fontsize': 7.5,
                    'markerscale': 0.82,
                    'handlelength': 1.05,
                    'handletextpad': 0.30,
                    'labelspacing': 0.10,
                    'borderpad': 0.15,
                    'columnspacing': 0.45,
                },
            },
            'ieee_single': {
                'styles': ['science', 'ieee', 'no-latex'],
                'width_mm': 88.0,
                'height_ratio': 0.72,
                'dpi': 300,
                'point_size': 46,
                'legend': {
                    'fontsize': 7.0,
                    'title_fontsize': 7.5,
                    'markerscale': 0.80,
                    'handlelength': 1.00,
                    'handletextpad': 0.28,
                    'labelspacing': 0.10,
                    'borderpad': 0.14,
                    'columnspacing': 0.40,
                },
            },
            'nature_double': {
                'styles': ['science', 'nature', 'no-latex'],
                'width_mm': 180.0,
                'height_ratio': 0.55,
                'dpi': 300,
                'point_size': 50,
                'legend': {
                    'fontsize': 8.0,
                    'title_fontsize': 8.5,
                    'markerscale': 0.90,
                    'handlelength': 1.10,
                    'handletextpad': 0.34,
                    'labelspacing': 0.12,
                    'borderpad': 0.18,
                    'columnspacing': 0.50,
                },
            },
            'presentation': {
                'styles': ['science', 'no-latex'],
                'width_mm': 240.0,
                'height_ratio': 0.55,
                'dpi': 220,
                'point_size': 60,
                'legend': {
                    'fontsize': 10.0,
                    'title_fontsize': 11.0,
                    'markerscale': 1.00,
                    'handlelength': 1.15,
                    'handletextpad': 0.38,
                    'labelspacing': 0.14,
                    'borderpad': 0.20,
                    'columnspacing': 0.55,
                },
            },
        }
        profile = dict(profiles.get(preset_key, profiles['science_single']))
        width_in = self._mm_to_inch(profile['width_mm'])
        height_in = max(2.0, width_in * float(profile.get('height_ratio', 0.72)))
        profile['figsize'] = (width_in, height_in)
        return profile

    def _resolve_export_point_size(self, profile: dict) -> int:
        """Resolve point size from UI override or profile default."""
        point_size = int(profile.get('point_size', 60))
        if self.image_point_size_spin is not None:
            point_size = int(self.image_point_size_spin.value())
        return point_size

    def _resolve_export_legend_size(self, profile: dict) -> int:
        """Resolve legend font size from UI override or profile default."""
        point_size = int(round(float((profile.get('legend', {}) or {}).get('fontsize', 8.0))))
        if self.image_legend_size_spin is not None:
            point_size = int(self.image_legend_size_spin.value())
        return point_size

    def _resolve_export_dpi(self, profile: dict) -> int:
        """Resolve export DPI from UI override or profile default."""
        dpi_value = int(profile.get('dpi', CONFIG.get('savefig_dpi', 400)))
        if self.image_dpi_spin is not None:
            dpi_value = int(self.image_dpi_spin.value())
        return max(72, dpi_value)

    def _resolve_export_save_options(self, profile: dict) -> dict:
        """Collect figure save options from export controls."""
        export_dpi = self._resolve_export_dpi(profile)
        use_tight_bbox = bool(self.image_tight_bbox_check.isChecked()) if self.image_tight_bbox_check is not None else True
        transparent = bool(self.image_transparent_check.isChecked()) if self.image_transparent_check is not None else False
        pad_inches = 0.02
        if self.image_pad_inches_spin is not None:
            pad_inches = float(self.image_pad_inches_spin.value())
        return {
            'dpi': export_dpi,
            'bbox_tight': use_tight_bbox,
            'pad_inches': max(0.0, pad_inches),
            'transparent': transparent,
        }

    @staticmethod
    def _fallback_export_rc(profile: dict) -> dict:
        """Fallback rcParams when SciencePlots is unavailable."""
        legend_style = dict(profile.get('legend', {}) or {})
        base_font_size = float(legend_style.get('fontsize', 8.0))
        return {
            'font.size': base_font_size + 0.5,
            'axes.titlesize': base_font_size + 1.8,
            'axes.labelsize': base_font_size + 1.0,
            'xtick.labelsize': base_font_size,
            'ytick.labelsize': base_font_size,
            'legend.fontsize': base_font_size,
            'axes.grid': True,
            'grid.alpha': 0.22,
            'grid.linestyle': '--',
            'axes.linewidth': 0.8,
            'lines.linewidth': 1.15,
        }

    @staticmethod
    def _normalize_export_target(file_path: str, preferred_ext: str) -> tuple[str, str]:
        """Normalize output path and extension using supported export formats."""
        supported = {'png', 'tiff', 'pdf', 'svg', 'eps'}
        normalized_ext = str(preferred_ext or 'png').lower().strip('.')
        if normalized_ext not in supported:
            normalized_ext = 'png'

        target_path = Path(file_path)
        suffix = target_path.suffix.lower().strip('.')
        if suffix in supported:
            return str(target_path), suffix

        if target_path.suffix:
            target_path = target_path.with_suffix(f'.{normalized_ext}')
        else:
            target_path = Path(f"{file_path}.{normalized_ext}")
        return str(target_path), normalized_ext

    def _save_export_figure(
        self,
        export_fig,
        file_path: str,
        image_ext: str,
        export_dpi: int,
        bbox_tight: bool,
        pad_inches: float,
        transparent: bool,
    ) -> None:
        """Save figure using unified export options."""
        save_kwargs = {
            'format': image_ext,
            'dpi': int(export_dpi),
            'bbox_inches': 'tight' if bbox_tight else None,
            'transparent': bool(transparent),
        }
        if bbox_tight:
            save_kwargs['pad_inches'] = float(max(0.0, pad_inches))

        # EPS backend does not preserve alpha channels reliably.
        if image_ext == 'eps' and save_kwargs['transparent']:
            save_kwargs['transparent'] = False

        export_fig.savefig(file_path, **save_kwargs)

    def _on_export_image_clicked(self):
        """Export figure directly without opening preview dialog."""
        import matplotlib.pyplot as plt

        if getattr(app_state, 'df_global', None) is None or len(app_state.df_global) == 0:
            QMessageBox.warning(self, translate("Warning"), translate("No data loaded."))
            return
        if getattr(app_state, 'fig', None) is None:
            QMessageBox.warning(self, translate("Warning"), translate("Plot figure is not initialized."))
            return

        preset_key = self.image_preset_combo.currentData() if self.image_preset_combo is not None else 'science_single'
        profile = self._image_export_profile(str(preset_key))
        preferred_ext = self.image_format_combo.currentData() if self.image_format_combo is not None else 'png'
        filters = (
            "PNG Files (*.png);;TIFF Files (*.tiff);;PDF Files (*.pdf);;"
            "SVG Files (*.svg);;EPS Files (*.eps);;All Files (*.*)"
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Figure"),
            "",
            filters,
        )
        if not file_path:
            return

        file_path, image_ext = self._normalize_export_target(file_path, str(preferred_ext))
        point_size_for_export = self._resolve_export_point_size(profile)
        legend_size_for_export = self._resolve_export_legend_size(profile)
        save_options = self._resolve_export_save_options(profile)

        export_fig = None
        try:
            export_fig = self._create_export_figure(
                profile,
                point_size_for_export,
                legend_size_for_export,
            )
            self._save_export_figure(
                export_fig,
                file_path,
                image_ext,
                export_dpi=int(save_options['dpi']),
                bbox_tight=bool(save_options['bbox_tight']),
                pad_inches=float(save_options['pad_inches']),
                transparent=bool(save_options['transparent']),
            )
            QMessageBox.information(
                self,
                translate("Success"),
                translate("Figure exported successfully to {file}").format(file=file_path),
            )
        except Exception as export_err:
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Failed to export image: {error}").format(error=str(export_err)),
            )
        finally:
            if export_fig is not None:
                try:
                    plt.close(export_fig)
                except Exception:
                    pass

    def _create_export_figure(
        self,
        profile: dict,
        point_size_for_export: int,
        legend_size_for_export: int | None = None,
    ):
        """Create an offscreen figure rendered with current mode and export profile."""
        import matplotlib.pyplot as plt
        from matplotlib.figure import Figure
        from visualization.plotting import refresh_paleoisochron_labels

        original_fig = app_state.fig
        original_ax = app_state.ax
        original_view = self._capture_axis_view(original_ax)
        original_palette = dict(getattr(app_state, 'current_palette', {}) or {})
        original_marker_map = dict(getattr(app_state, 'group_marker_map', {}) or {})
        locked_palette = self._palette_from_axis_collections(original_ax, original_palette)
        locked_marker_map = dict(original_marker_map)
        original_marginal_axes = getattr(app_state, 'marginal_axes', None)
        original_show_marginal_kde = bool(getattr(app_state, 'show_marginal_kde', False))
        original_has_marginal_axes = bool(original_fig is not None and len(getattr(original_fig, 'axes', [])) > 1)

        try:
            use_scienceplots = self._is_scienceplots_available()
            style_chain = profile['styles'] if use_scienceplots else ['default']
            with plt.style.context(style_chain):
                if not use_scienceplots:
                    plt.rcParams.update(self._fallback_export_rc(profile))
                export_fig = Figure(
                    figsize=profile['figsize'],
                    dpi=int(profile['dpi']),
                    constrained_layout=True,
                )
                export_ax = export_fig.add_subplot(111)

                app_state.fig = export_fig
                app_state.ax = export_ax
                app_state.current_palette = dict(locked_palette)
                app_state.group_marker_map = dict(locked_marker_map)

                # Preserve visible marginal KDE when current interactive figure uses marginal axes.
                if original_has_marginal_axes:
                    app_state.show_marginal_kde = True

                render_ok = self._render_current_mode_sync(point_size=point_size_for_export)
                if not render_ok:
                    raise RuntimeError("Failed to render export figure.")

                # Re-run overlay label placement for the export/preview canvas.
                try:
                    refresh_paleoisochron_labels()
                except Exception as label_err:
                    logger.debug("Overlay label refresh skipped: %s", label_err)

                # Keep exported geometry consistent with what user sees currently.
                self._apply_axis_view(export_ax, original_view)
                try:
                    refresh_paleoisochron_labels()
                except Exception:
                    pass
                self._normalize_export_legends(
                    export_fig,
                    profile,
                    legend_size_override=legend_size_for_export,
                    point_size_override=point_size_for_export,
                )
                self._attach_preview_label_state(export_fig)
                return export_fig
        finally:
            app_state.fig = original_fig
            app_state.ax = original_ax
            app_state.current_palette = dict(original_palette)
            app_state.group_marker_map = dict(original_marker_map)
            app_state.show_marginal_kde = original_show_marginal_kde
            app_state.marginal_axes = original_marginal_axes
            try:
                self._render_current_mode_sync(point_size=int(getattr(app_state, 'point_size', 60)))
                if app_state.fig is not None and app_state.fig.canvas is not None:
                    app_state.fig.canvas.draw_idle()
            except Exception as restore_err:
                logger.warning("Failed to restore interactive canvas after export: %s", restore_err)

    @staticmethod
    def _snapshot_overlay_label_state() -> dict:
        """Capture overlay label entries currently tracked in app_state."""
        keys = (
            'paleoisochron_label_data',
            'plumbotectonics_label_data',
            'plumbotectonics_isoage_label_data',
            'overlay_curve_label_data',
        )
        snapshot = {}
        for key in keys:
            value = getattr(app_state, key, [])
            if isinstance(value, list):
                snapshot[key] = list(value)
            else:
                snapshot[key] = []
        return snapshot

    def _attach_preview_label_state(self, preview_fig) -> None:
        """Attach overlay label metadata to preview figure for interaction refresh."""
        if preview_fig is None:
            return
        try:
            preview_fig._overlay_label_state = self._snapshot_overlay_label_state()
        except Exception:
            preview_fig._overlay_label_state = {}

    def _refresh_preview_overlay_labels(self, preview_fig, preview_ax) -> None:
        """Refresh overlay labels on preview axes after pan/zoom interactions."""
        from visualization.plotting import refresh_paleoisochron_labels

        if preview_fig is None or preview_ax is None:
            return
        label_state = getattr(preview_fig, '_overlay_label_state', None)
        if not isinstance(label_state, dict) or not label_state:
            return

        keys = (
            'paleoisochron_label_data',
            'plumbotectonics_label_data',
            'plumbotectonics_isoage_label_data',
            'overlay_curve_label_data',
        )
        backup = {
            'fig': getattr(app_state, 'fig', None),
            'ax': getattr(app_state, 'ax', None),
            'overlay_label_refreshing': bool(getattr(app_state, 'overlay_label_refreshing', False)),
            'adjust_text_in_progress': bool(getattr(app_state, 'adjust_text_in_progress', False)),
        }
        for key in keys:
            backup[key] = getattr(app_state, key, [])

        try:
            app_state.fig = preview_fig
            app_state.ax = preview_ax
            app_state.overlay_label_refreshing = False
            app_state.adjust_text_in_progress = False
            for key in keys:
                setattr(app_state, key, list(label_state.get(key, [])))

            refresh_paleoisochron_labels()

            # Keep updated references on the preview figure for subsequent interactions.
            for key in keys:
                label_state[key] = list(getattr(app_state, key, []) or [])
        except Exception as err:
            logger.debug("Preview overlay label refresh skipped: %s", err)
        finally:
            app_state.fig = backup['fig']
            app_state.ax = backup['ax']
            app_state.overlay_label_refreshing = backup['overlay_label_refreshing']
            app_state.adjust_text_in_progress = backup['adjust_text_in_progress']
            for key in keys:
                setattr(app_state, key, backup[key])

    @staticmethod
    def _palette_from_axis_collections(ax, fallback_palette: dict) -> dict:
        """Extract visible scatter colors from current axis to preserve user-edited colors."""
        palette = dict(fallback_palette or {})
        if ax is None:
            return palette
        for collection in list(getattr(ax, 'collections', []) or []):
            try:
                label = str(collection.get_label() or '')
                if not label or label.startswith('_'):
                    continue
                facecolors = collection.get_facecolors()
                if facecolors is None or len(facecolors) == 0:
                    continue
                rgba = facecolors[0]
                palette[label] = to_hex(rgba, keep_alpha=False)
            except Exception:
                continue
        return palette

    def _normalize_export_legends(
        self,
        export_fig,
        profile: dict,
        legend_size_override: int | None = None,
        point_size_override: int | None = None,
    ) -> None:
        """Rebuild legends with preset-specific style so size is deterministic."""
        if export_fig is None:
            return
        legend_style = dict(profile.get('legend', {}) or {})
        legend_size = float(legend_size_override if legend_size_override is not None else legend_style.get('fontsize', 8.0))
        title_size = float(legend_style.get('title_fontsize', legend_size + 0.5))
        marker_scale = float(legend_style.get('markerscale', 0.9))
        point_size_for_legend = float(point_size_override if point_size_override is not None else profile.get('point_size', 50))
        handlelength = float(legend_style.get('handlelength', 1.2))
        handletextpad = float(legend_style.get('handletextpad', 0.5))
        labelspacing = float(legend_style.get('labelspacing', 0.3))
        borderpad = float(legend_style.get('borderpad', 0.3))
        columnspacing = float(legend_style.get('columnspacing', 0.7))

        for ax in list(getattr(export_fig, 'axes', []) or []):
            legend = None
            try:
                legend = ax.get_legend()
            except Exception:
                legend = None
            if legend is None:
                continue

            handles = getattr(legend, 'legend_handles', None)
            if handles is None:
                handles = getattr(legend, 'legendHandles', None)
            labels = [text.get_text() for text in legend.get_texts()]
            if not handles or not labels or len(handles) != len(labels):
                handles, labels = ax.get_legend_handles_labels()
            if not handles or not labels:
                continue

            frame_on = True
            try:
                frame_on = bool(legend.get_frame_on())
            except Exception:
                pass

            loc = getattr(legend, '_loc', 'best')
            ncol = int(getattr(legend, '_ncols', 1) or 1)
            bbox_anchor = None
            try:
                bbox = legend.get_bbox_to_anchor()
                if bbox is not None:
                    points = bbox.get_points()
                    if points is not None:
                        points_axes = ax.transAxes.inverted().transform(points)
                        x0, y0 = points_axes[0]
                        x1, y1 = points_axes[1]
                        if abs(x1 - x0) < 1e-9 and abs(y1 - y0) < 1e-9:
                            bbox_anchor = (float(x0), float(y0))
                        else:
                            bbox_anchor = (float(x0), float(y0), float(x1 - x0), float(y1 - y0))
            except Exception:
                bbox_anchor = None

            try:
                legend.remove()
            except Exception:
                pass

            new_legend_kwargs = {
                'handles': handles,
                'labels': labels,
                'title': "",
                'loc': loc,
                'ncol': max(1, ncol),
                'frameon': frame_on,
                'fontsize': legend_size,
                'title_fontsize': title_size,
                'markerscale': marker_scale,
                'handlelength': handlelength,
                'handletextpad': handletextpad,
                'labelspacing': labelspacing,
                'borderpad': borderpad,
                'columnspacing': columnspacing,
                'borderaxespad': 0.2,
            }
            if bbox_anchor is not None:
                new_legend_kwargs['bbox_to_anchor'] = bbox_anchor

            try:
                rebuilt_legend = ax.legend(**new_legend_kwargs)
                if rebuilt_legend is not None:
                    rebuilt_legend.set_title("")
                    rebuilt_legend.get_title().set_visible(False)
                    self._apply_legend_marker_size_from_point(rebuilt_legend, point_size_for_legend)
            except Exception:
                try:
                    # Fallback for older Matplotlib versions lacking title_fontsize.
                    new_legend_kwargs.pop('title_fontsize', None)
                    rebuilt_legend = ax.legend(**new_legend_kwargs)
                    if rebuilt_legend is not None:
                        rebuilt_legend.get_title().set_fontsize(title_size)
                        rebuilt_legend.set_title("")
                        rebuilt_legend.get_title().set_visible(False)
                        self._apply_legend_marker_size_from_point(rebuilt_legend, point_size_for_legend)
                except Exception:
                    pass

    @staticmethod
    def _apply_legend_marker_size_from_point(legend, point_size: float) -> None:
        """Scale legend marker glyphs to follow plotted scatter point size."""
        import math

        if legend is None:
            return
        point_area = max(1.0, float(point_size))
        marker_size_pt = max(2.0, math.sqrt(point_area))
        scatter_area = point_area
        try:
            legend.set_markerscale(1.0)
        except Exception:
            pass

        handles = getattr(legend, 'legend_handles', None)
        if handles is None:
            handles = getattr(legend, 'legendHandles', None)
        if not handles:
            return

        for handle in handles:
            try:
                if hasattr(handle, 'set_markersize'):
                    handle.set_markersize(marker_size_pt)
                elif hasattr(handle, 'set_sizes'):
                    handle.set_sizes([scatter_area])
            except Exception:
                continue

    def _on_preview_image_clicked(self):
        """Preview export result in a separate dialog before saving."""
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT

        if getattr(app_state, 'df_global', None) is None or len(app_state.df_global) == 0:
            QMessageBox.warning(self, translate("Warning"), translate("No data loaded."))
            return
        if getattr(app_state, 'fig', None) is None:
            QMessageBox.warning(self, translate("Warning"), translate("Plot figure is not initialized."))
            return

        preset_key = self.image_preset_combo.currentData() if self.image_preset_combo is not None else 'science_single'
        profile = self._image_export_profile(str(preset_key))
        point_size_for_export = self._resolve_export_point_size(profile)
        legend_size_for_export = self._resolve_export_legend_size(profile)
        image_ext = self.image_format_combo.currentData() if self.image_format_combo is not None else 'png'

        try:
            preview_fig = self._create_export_figure(profile, point_size_for_export, legend_size_for_export)
            preview_width_px = int(round(float(profile['figsize'][0]) * float(profile['dpi'])))
            preview_height_px = int(round(float(profile['figsize'][1]) * float(profile['dpi'])))

            dialog = QDialog(self)
            dialog.setWindowTitle(translate("Export Preview"))
            dialog.resize(min(1400, preview_width_px + 120), min(1000, preview_height_px + 180))

            layout = QVBoxLayout(dialog)

            # Keep preview controls in dialog so users can fine-tune before exporting.
            control_row = QHBoxLayout()
            point_size_label = QLabel(translate("Point Size"))
            point_size_slider = QSlider(Qt.Horizontal)
            point_size_slider.setRange(1, 50)
            point_size_slider.setValue(int(point_size_for_export))
            point_size_spin = QSpinBox()
            point_size_spin.setRange(1, 50)
            point_size_spin.setValue(int(point_size_for_export))

            control_row.addWidget(point_size_label)
            control_row.addWidget(point_size_slider, 1)
            control_row.addWidget(point_size_spin)
            layout.addLayout(control_row)

            legend_control_row = QHBoxLayout()
            legend_size_label = QLabel(translate("Legend Size"))
            legend_size_slider = QSlider(Qt.Horizontal)
            legend_size_slider.setRange(1, 15)
            legend_size_slider.setValue(int(legend_size_for_export))
            legend_size_spin = QSpinBox()
            legend_size_spin.setRange(1, 15)
            legend_size_spin.setValue(int(legend_size_for_export))
            legend_control_row.addWidget(legend_size_label)
            legend_control_row.addWidget(legend_size_slider, 1)
            legend_control_row.addWidget(legend_size_spin)
            layout.addLayout(legend_control_row)

            canvas = FigureCanvasQTAgg(preview_fig)
            canvas.setFixedSize(preview_width_px, preview_height_px)
            toolbar = NavigationToolbar2QT(canvas, dialog)
            layout.addWidget(toolbar)

            scroll_area = QScrollArea(dialog)
            scroll_area.setWidget(canvas)
            scroll_area.setWidgetResizable(False)
            layout.addWidget(scroll_area)

            main_preview_ax = preview_fig.axes[0] if preview_fig.axes else None

            # Reposition overlay labels whenever preview viewport changes.
            refresh_guard = {'busy': False}

            def _refresh_preview_labels_now():
                if refresh_guard['busy'] or main_preview_ax is None:
                    return
                refresh_guard['busy'] = True
                try:
                    self._refresh_preview_overlay_labels(preview_fig, main_preview_ax)
                    canvas.draw_idle()
                finally:
                    refresh_guard['busy'] = False

            axis_callback_ids = []
            canvas_callback_ids = []
            if main_preview_ax is not None:
                try:
                    axis_callback_ids.append(main_preview_ax.callbacks.connect('xlim_changed', lambda _ax: _refresh_preview_labels_now()))
                    axis_callback_ids.append(main_preview_ax.callbacks.connect('ylim_changed', lambda _ax: _refresh_preview_labels_now()))
                except Exception:
                    axis_callback_ids = []
            try:
                canvas_callback_ids.append(canvas.mpl_connect('button_release_event', lambda _evt: _refresh_preview_labels_now()))
            except Exception:
                canvas_callback_ids = []

            _refresh_preview_labels_now()

            def _apply_preview_point_size(new_size: int):
                size_value = float(new_size)
                if main_preview_ax is None:
                    return
                for collection in main_preview_ax.collections:
                    if not hasattr(collection, 'get_sizes') or not hasattr(collection, 'set_sizes'):
                        continue
                    if not hasattr(collection, 'get_offsets'):
                        continue
                    try:
                        offsets = collection.get_offsets()
                        n_offsets = len(offsets) if offsets is not None else 0
                        if n_offsets <= 0:
                            continue
                        # Update scatter-like collections only; avoid touching KDE artists.
                        collection.set_sizes([size_value] * n_offsets)
                    except Exception:
                        continue
                for ax in preview_fig.axes:
                    legend = None
                    try:
                        legend = ax.get_legend()
                    except Exception:
                        legend = None
                    if legend is None:
                        continue
                    self._apply_legend_marker_size_from_point(legend, size_value)
                canvas.draw_idle()

            def _on_slider_changed(value: int):
                point_size_spin.blockSignals(True)
                point_size_spin.setValue(value)
                point_size_spin.blockSignals(False)
                if self.image_point_size_spin is not None:
                    self.image_point_size_spin.blockSignals(True)
                    self.image_point_size_spin.setValue(value)
                    self.image_point_size_spin.blockSignals(False)
                _apply_preview_point_size(value)

            def _on_spin_changed(value: int):
                point_size_slider.blockSignals(True)
                point_size_slider.setValue(value)
                point_size_slider.blockSignals(False)
                if self.image_point_size_spin is not None:
                    self.image_point_size_spin.blockSignals(True)
                    self.image_point_size_spin.setValue(value)
                    self.image_point_size_spin.blockSignals(False)
                _apply_preview_point_size(value)

            point_size_slider.valueChanged.connect(_on_slider_changed)
            point_size_spin.valueChanged.connect(_on_spin_changed)

            def _apply_preview_legend_size(new_size: int):
                legend_size = float(new_size)
                for ax in preview_fig.axes:
                    legend = None
                    try:
                        legend = ax.get_legend()
                    except Exception:
                        legend = None
                    if legend is None:
                        continue
                    for text in legend.get_texts():
                        try:
                            text.set_fontsize(legend_size)
                        except Exception:
                            pass
                    try:
                        legend.set_title("")
                        legend.get_title().set_visible(False)
                    except Exception:
                        pass
                canvas.draw_idle()

            def _on_legend_slider_changed(value: int):
                legend_size_spin.blockSignals(True)
                legend_size_spin.setValue(value)
                legend_size_spin.blockSignals(False)
                if self.image_legend_size_spin is not None:
                    self.image_legend_size_spin.blockSignals(True)
                    self.image_legend_size_spin.setValue(value)
                    self.image_legend_size_spin.blockSignals(False)
                _apply_preview_legend_size(value)

            def _on_legend_spin_changed(value: int):
                legend_size_slider.blockSignals(True)
                legend_size_slider.setValue(value)
                legend_size_slider.blockSignals(False)
                if self.image_legend_size_spin is not None:
                    self.image_legend_size_spin.blockSignals(True)
                    self.image_legend_size_spin.setValue(value)
                    self.image_legend_size_spin.blockSignals(False)
                _apply_preview_legend_size(value)

            legend_size_slider.valueChanged.connect(_on_legend_slider_changed)
            legend_size_spin.valueChanged.connect(_on_legend_spin_changed)

            def _save_preview_image():
                filters = (
                    "PNG Files (*.png);;TIFF Files (*.tiff);;PDF Files (*.pdf);;"
                    "SVG Files (*.svg);;EPS Files (*.eps);;All Files (*.*)"
                )
                file_path, _ = QFileDialog.getSaveFileName(
                    dialog,
                    translate("Save"),
                    "",
                    filters,
                )
                if not file_path:
                    return
                file_path, export_ext = self._normalize_export_target(file_path, str(image_ext))
                save_options = self._resolve_export_save_options(profile)
                try:
                    self._save_export_figure(
                        preview_fig,
                        file_path,
                        export_ext,
                        export_dpi=int(save_options['dpi']),
                        bbox_tight=bool(save_options['bbox_tight']),
                        pad_inches=float(save_options['pad_inches']),
                        transparent=bool(save_options['transparent']),
                    )
                    QMessageBox.information(
                        dialog,
                        translate("Success"),
                        translate("Figure exported successfully to {file}").format(file=file_path),
                    )
                except Exception as save_err:
                    QMessageBox.critical(
                        dialog,
                        translate("Error"),
                        translate("Failed to save preview image: {error}").format(error=str(save_err)),
                    )

            button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
            save_button = button_box.button(QDialogButtonBox.Save)
            if save_button is not None:
                save_button.setText(translate("Save"))
            if save_button is not None:
                save_button.clicked.connect(_save_preview_image)
            close_button = button_box.button(QDialogButtonBox.Close)
            if close_button is not None:
                close_button.setText(translate("Close"))
                close_button.clicked.connect(dialog.reject)
            layout.addWidget(button_box)

            def _cleanup_preview(_result):
                try:
                    if main_preview_ax is not None:
                        for cid in axis_callback_ids:
                            try:
                                main_preview_ax.callbacks.disconnect(cid)
                            except Exception:
                                pass
                    for cid in canvas_callback_ids:
                        try:
                            canvas.mpl_disconnect(cid)
                        except Exception:
                            pass
                finally:
                    plt.close(preview_fig)

            dialog.finished.connect(_cleanup_preview)
            dialog.exec_()
        except Exception as err:
            logger.error("Failed to generate export preview: %s", err)
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Failed to generate export preview: {error}").format(error=str(err)),
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
