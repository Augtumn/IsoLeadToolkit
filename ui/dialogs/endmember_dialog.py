"""端元识别对话框。"""
import logging
from typing import Any

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QTableWidget, QTableWidgetItem, QMessageBox,
                              QHeaderView, QSizePolicy, QGroupBox, QComboBox,
                              QDoubleSpinBox, QGridLayout, QTextEdit, QFileDialog,
                              QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import numpy as np

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


def show_endmember_analysis(parent: Any = None) -> None:
    dialog = EndmemberAnalysisDialog(parent)
    dialog.exec_()


class EndmemberAnalysisDialog(QDialog):
    """端元识别对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translate("Endmember Analysis"))
        self.setMinimumWidth(720)
        self.setMinimumHeight(600)
        self._result = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # 标题
        title = QLabel(translate("Endmember Analysis"))
        title_font = QFont(title.font())
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # ---- 数据范围 ----
        scope_group = QGroupBox(translate("Data Scope"))
        scope_layout = QVBoxLayout()

        self.radio_all = QRadioButton(translate("All data"))
        self.radio_selected = QRadioButton(translate("Selected data only"))

        selected_count = len(getattr(app_state, 'selected_indices', set()))
        total_count = len(app_state.df_global) if app_state.df_global is not None else 0

        if selected_count > 0:
            self.radio_selected.setText(
                translate("Selected data only") + f" ({selected_count}/{total_count})")
            self.radio_selected.setChecked(True)
        else:
            self.radio_all.setChecked(True)
            self.radio_selected.setEnabled(False)
            self.radio_selected.setText(
                translate("Selected data only") + f" ({translate('no selection')})")

        scope_layout.addWidget(self.radio_all)
        scope_layout.addWidget(self.radio_selected)
        scope_group.setLayout(scope_layout)
        layout.addWidget(scope_group)

        # ---- 列选择 ----
        col_group = QGroupBox(translate("Column Selection"))
        col_layout = QGridLayout()

        numeric_cols = []
        if app_state.df_global is not None:
            numeric_cols = app_state.df_global.select_dtypes(
                include=[np.number]).columns.tolist()

        col_layout.addWidget(QLabel("206Pb/204Pb:"), 0, 0)
        self.combo_206 = QComboBox()
        self.combo_206.addItems(numeric_cols)
        col_layout.addWidget(self.combo_206, 0, 1)

        col_layout.addWidget(QLabel("207Pb/204Pb:"), 1, 0)
        self.combo_207 = QComboBox()
        self.combo_207.addItems(numeric_cols)
        col_layout.addWidget(self.combo_207, 1, 1)

        col_layout.addWidget(QLabel("208Pb/204Pb:"), 2, 0)
        self.combo_208 = QComboBox()
        self.combo_208.addItems(numeric_cols)
        col_layout.addWidget(self.combo_208, 2, 1)

        col_group.setLayout(col_layout)
        layout.addWidget(col_group)

        # 自动检测 Pb 列
        self._auto_detect_pb_columns(numeric_cols)

        # ---- 参数设置 ----
        param_group = QGroupBox(translate("Parameters"))
        param_layout = QGridLayout()

        param_layout.addWidget(QLabel(translate("Tolerance A:")), 0, 0)
        self.spin_tol_a = QDoubleSpinBox()
        self.spin_tol_a.setRange(0.001, 10.0)
        self.spin_tol_a.setDecimals(3)
        self.spin_tol_a.setSingleStep(0.005)
        self.spin_tol_a.setValue(0.01)
        param_layout.addWidget(self.spin_tol_a, 0, 1)

        param_layout.addWidget(QLabel(translate("Clamp A:")), 0, 2)
        self.spin_clamp_a = QDoubleSpinBox()
        self.spin_clamp_a.setRange(0.01, 99999.0)
        self.spin_clamp_a.setDecimals(2)
        self.spin_clamp_a.setValue(99999.0)
        param_layout.addWidget(self.spin_clamp_a, 0, 3)

        param_layout.addWidget(QLabel(translate("Tolerance B:")), 1, 0)
        self.spin_tol_b = QDoubleSpinBox()
        self.spin_tol_b.setRange(0.001, 10.0)
        self.spin_tol_b.setDecimals(3)
        self.spin_tol_b.setSingleStep(0.005)
        self.spin_tol_b.setValue(0.01)
        param_layout.addWidget(self.spin_tol_b, 1, 1)

        param_layout.addWidget(QLabel(translate("Clamp B:")), 1, 2)
        self.spin_clamp_b = QDoubleSpinBox()
        self.spin_clamp_b.setRange(0.01, 99999.0)
        self.spin_clamp_b.setDecimals(2)
        self.spin_clamp_b.setValue(99999.0)
        param_layout.addWidget(self.spin_clamp_b, 1, 3)

        # Geochron 斜率显示
        from data.endmember import compute_geochron_slope
        geo_slope = compute_geochron_slope()
        param_layout.addWidget(QLabel(translate("Geochron Slope:")), 2, 0)
        self.slope_label = QLabel(f"{geo_slope:.6f}")
        param_layout.addWidget(self.slope_label, 2, 1)
        hint_label = QLabel(translate("(computed from decay constants)"))
        hint_label.setStyleSheet("color: gray; font-size: 11px;")
        param_layout.addWidget(hint_label, 2, 2, 1, 2)

        param_group.setLayout(param_layout)
        layout.addWidget(param_group)

        # ---- 运行按钮 ----
        run_btn = QPushButton(translate("Run Endmember Analysis"))
        run_btn.setFixedWidth(220)
        run_btn.clicked.connect(self._on_run_analysis)
        layout.addWidget(run_btn, 0, Qt.AlignHCenter)

        # ---- PCA 摘要 ----
        self.pca_group = QGroupBox(translate("PCA Summary"))
        pca_layout = QVBoxLayout()
        self.pca_label = QLabel("—")
        self.pca_label.setWordWrap(True)
        pca_layout.addWidget(self.pca_label)
        self.pca_group.setLayout(pca_layout)
        self.pca_group.setVisible(False)
        layout.addWidget(self.pca_group)

        # ---- 警告信息 ----
        self.warning_label = QLabel("")
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("color: #cc6600; font-weight: bold;")
        self.warning_label.setVisible(False)
        layout.addWidget(self.warning_label)

        # ---- 结果表格 ----
        self.result_group = QGroupBox(translate("Endmember Results"))
        result_layout = QVBoxLayout()

        self.result_table = QTableWidget()
        self.result_table.setColumnCount(6)
        self.result_table.setHorizontalHeaderLabels([
            translate("Group"),
            translate("N Samples"),
            translate("Shapiro W (PC2)"),
            translate("p-value (PC2)"),
            translate("Shapiro W (PC3)"),
            translate("p-value (PC3)"),
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        result_layout.addWidget(self.result_table)

        self.result_group.setLayout(result_layout)
        self.result_group.setVisible(False)
        layout.addWidget(self.result_group)

        # ---- 底部按钮 ----
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.addStretch()

        self.apply_btn = QPushButton(translate("Apply as Group Column"))
        self.apply_btn.clicked.connect(self._on_apply_group_column)
        self.apply_btn.setEnabled(False)
        button_layout.addWidget(self.apply_btn)

        self.export_btn = QPushButton(translate("Export Results"))
        self.export_btn.clicked.connect(self._on_export_results)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)

        close_btn = QPushButton(translate("Close"))
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _auto_detect_pb_columns(self, columns):
        """自动检测并选中 Pb 同位素列"""
        patterns = {
            '206': self.combo_206,
            '207': self.combo_207,
            '208': self.combo_208,
        }
        for key, combo in patterns.items():
            for i, col in enumerate(columns):
                col_lower = col.lower().replace(' ', '')
                if key in col and '204' in col:
                    combo.setCurrentIndex(i)
                    break

    def _on_run_analysis(self):
        """运行端元分析"""
        col_206 = self.combo_206.currentText()
        col_207 = self.combo_207.currentText()
        col_208 = self.combo_208.currentText()

        if not col_206 or not col_207 or not col_208:
            QMessageBox.warning(
                self, translate("Warning"),
                translate("No Pb isotope columns detected."))
            return

        if len({col_206, col_207, col_208}) < 3:
            QMessageBox.warning(
                self, translate("Warning"),
                translate("Please select three different columns."))
            return

        tol_a = self.spin_tol_a.value()
        tol_b = self.spin_tol_b.value()
        clamp_a = self.spin_clamp_a.value()
        clamp_b = self.spin_clamp_b.value()

        # 99999 视为无限制
        if clamp_a >= 99999.0:
            clamp_a = np.inf
        if clamp_b >= 99999.0:
            clamp_b = np.inf

        try:
            from data.endmember import run_endmember_analysis

            # 确定数据范围
            if self.radio_selected.isChecked():
                selected = sorted(list(app_state.selected_indices))
                df_input = app_state.df_global.iloc[selected].reset_index(drop=True)
                self._selected_original_indices = selected
            else:
                df_input = app_state.df_global
                self._selected_original_indices = None

            self._result = run_endmember_analysis(
                df_input,
                col_206, col_207, col_208,
                tolerance=(tol_a, tol_b),
                clamp=(clamp_a, clamp_b),
            )
            self._display_results()
        except Exception as e:
            logger.error("Endmember analysis failed: %s", e)
            QMessageBox.critical(
                self, translate("Error"),
                translate("Endmember analysis failed: {error}").format(error=str(e)))

    def _display_results(self):
        """显示分析结果"""
        r = self._result
        if r is None:
            return

        # PCA 摘要
        var = r['pca']['explained_variance_ratio']
        var_texts = []
        for i, v in enumerate(var):
            var_texts.append(f"PC{i+1}: {v * 100:.1f}%")
        cumulative = np.cumsum(var)
        self.pca_label.setText(
            "  |  ".join(var_texts) +
            f"\n{translate('Cumulative')}: {cumulative[-1] * 100:.1f}%"
            f"    {translate('Geochron Slope')}: {r['geochron_slope']:.6f}"
        )
        self.pca_group.setVisible(True)

        # 警告
        if r['warnings']:
            self.warning_label.setText("\n".join(r['warnings']))
            self.warning_label.setVisible(True)
        else:
            self.warning_label.setVisible(False)

        # 结果表格
        validation = r['validation']
        label_order = ['Endmember_A', 'Endmember_B', 'Mixing']
        display_names = {
            'Endmember_A': translate("Endmember A"),
            'Endmember_B': translate("Endmember B"),
            'Mixing': translate("Mixing"),
        }

        self.result_table.setRowCount(len(label_order))
        for row, label in enumerate(label_order):
            v = validation.get(label, {})
            self.result_table.setItem(row, 0, QTableWidgetItem(display_names.get(label, label)))
            self.result_table.setItem(row, 1, QTableWidgetItem(str(v.get('n_samples', 0))))

            for col_offset, key in [(2, 'pc2_W'), (3, 'pc2_p'), (4, 'pc3_W'), (5, 'pc3_p')]:
                val = v.get(key)
                text = f"{val:.4f}" if val is not None else "N/A"
                self.result_table.setItem(row, col_offset, QTableWidgetItem(text))

        self.result_group.setVisible(True)
        self.apply_btn.setEnabled(True)
        self.export_btn.setEnabled(True)

    def _on_apply_group_column(self):
        """将端元分组应用为分组列"""
        if self._result is None:
            QMessageBox.warning(
                self, translate("Warning"),
                translate("Please run the analysis first."))
            return

        col_name = '_Endmember_Group'
        display_names = {
            'Endmember_A': translate("Endmember A"),
            'Endmember_B': translate("Endmember B"),
            'Mixing': translate("Mixing"),
        }

        # 初始化全部为 Unknown
        full_labels = np.full(len(app_state.df_global), 'Unknown', dtype=object)

        result_labels = self._result['group_labels']
        orig_indices = getattr(self, '_selected_original_indices', None)

        if orig_indices is not None:
            # 子集模式：映射回原始索引
            for i, orig_idx in enumerate(orig_indices):
                label = result_labels[i]
                full_labels[orig_idx] = display_names.get(label, label) if label else 'Unknown'
        else:
            # 全量模式
            for i, label in enumerate(result_labels):
                full_labels[i] = display_names.get(label, label) if label else 'Unknown'

        app_state.df_global[col_name] = full_labels

        if col_name not in app_state.group_cols:
            app_state.group_cols.append(col_name)

        # 触发重绘
        state_gateway.set_last_group_col(col_name)
        state_gateway.set_visible_groups(None)

        if hasattr(app_state, '_notify_listeners'):
            app_state._notify_listeners()

        QMessageBox.information(
            self, translate("Success"),
            translate("Endmember group column applied successfully."))

    def _on_export_results(self):
        """导出结果"""
        if self._result is None:
            QMessageBox.warning(
                self, translate("Warning"),
                translate("Please run the analysis first."))
            return

        import pandas as pd

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Results"),
            "",
            ";;".join([
                f"{translate('CSV files')} (*.csv)",
                f"{translate('Excel files')} (*.xlsx)",
                f"{translate('All files')} (*.*)"
            ])
        )

        if not file_path:
            return

        try:
            r = self._result
            valid_idx = r['valid_indices']
            assignments = r['assignments']
            scores = r['pca']['scores']
            label_map = r['label_map']

            rows = []
            for i, orig_idx in enumerate(valid_idx):
                row = {'Index': int(orig_idx), 'Group': label_map[assignments[i]]}
                for pc in range(scores.shape[1]):
                    row[f'PC{pc+1}'] = float(scores[i, pc])
                rows.append(row)

            df = pd.DataFrame(rows)

            if file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)

            QMessageBox.information(
                self, translate("Success"),
                translate("Results exported successfully to {file}").format(file=file_path))
        except Exception as e:
            QMessageBox.critical(
                self, translate("Error"),
                translate("Failed to export results: {error}").format(error=str(e)))
