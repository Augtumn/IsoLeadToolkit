"""混合计算对话框。"""
from __future__ import annotations

import logging

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QTableWidget, QTableWidgetItem, QMessageBox,
                              QHeaderView, QSizePolicy, QGroupBox)
from PyQt5.QtGui import QFont
import numpy as np

from core import app_state, translate

logger = logging.getLogger(__name__)


def show_mixing_calculator(parent: object | None = None) -> None:
    """
    显示混合计算器对话框

    Args:
        parent: 父窗口
    """
    dialog = MixingCalculatorDialog(parent)
    dialog.exec_()


class MixingCalculatorDialog(QDialog):
    """混合计算器对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translate("Mixing Calculator"))
        self.setMinimumWidth(760)
        self.setMinimumHeight(520)

        self._setup_ui()
        self._calculate_mixing()

    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(translate("Mixing Calculator"))
        title_font = QFont(title.font())
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        info_label = QLabel(translate("Mixing proportions calculated using least squares:"))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        results_group = QGroupBox(translate("Results"))
        results_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        results_layout = QVBoxLayout(results_group)
        results_layout.setContentsMargins(12, 10, 12, 12)
        results_layout.setSpacing(6)

        self.result_table = QTableWidget()
        self.result_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.result_table.setColumnCount(4)
        self.result_table.setHorizontalHeaderLabels([
            translate("Mixture"),
            translate("Endmember"),
            translate("Proportion"),
            translate("Residual")
        ])
        self.result_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        results_layout.addWidget(self.result_table, 1)

        layout.addWidget(results_group, 1)

        # 按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        button_layout.addStretch()

        run_btn = QPushButton(translate("Recalculate"))
        run_btn.clicked.connect(self._calculate_mixing)
        button_layout.addWidget(run_btn)
        self.run_btn = run_btn

        export_btn = QPushButton(translate("Export Results"))
        export_btn.clicked.connect(self._export_results)
        button_layout.addWidget(export_btn)

        close_btn = QPushButton(translate("Close"))
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _calculate_mixing(self):
        """计算混合比例"""
        if app_state.df_global is None:
            return

        endmembers = getattr(app_state, 'mixing_endmembers', {})
        mixtures = getattr(app_state, 'mixing_mixtures', {})

        if not endmembers or not mixtures:
            return

        # 获取数值列
        numeric_cols = app_state.df_global.select_dtypes(include=[np.number]).columns.tolist()
        if not numeric_cols:
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("No numeric columns found for mixing calculation.")
            )
            return

        results = []
        from plugins.registry import plugin_manager
        mixing_plugin = plugin_manager.get("mixing_plugin")
        if mixing_plugin is None:
            logger.error("mixing_plugin is not available")
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Mixing plugin is not available. Check the log for details."),
            )
            return

        if getattr(self, "_mixing_worker", None) is not None and self._mixing_worker.isRunning():
            return

        def _calculate():
            return mixing_plugin.calculate(
                app_state.df_global, endmembers, mixtures, numeric_cols
            )

        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QApplication

        from ui.dialogs.analysis_worker import AnalysisWorker

        def _on_finished(plugin_results):
            try:
                QApplication.restoreOverrideCursor()
            except Exception:
                pass
            self.run_btn.setEnabled(True)
            self._mixing_worker = None
            for r in plugin_results:
                results.append({
                    'mixture': r['mixture'],
                    'endmember': r['endmember'],
                    'proportion': r['weight'],
                    'residual': r['rmse'],
                })
            # 显示结果
            self.result_table.setRowCount(len(results))
            for i, result in enumerate(results):
                self.result_table.setItem(i, 0, QTableWidgetItem(result['mixture']))
                self.result_table.setItem(i, 1, QTableWidgetItem(result['endmember']))
                self.result_table.setItem(i, 2, QTableWidgetItem(f"{result['proportion']:.4f}"))
                self.result_table.setItem(i, 3, QTableWidgetItem(f"{result['residual']:.4f}"))

        def _on_failed(message):
            try:
                QApplication.restoreOverrideCursor()
            except Exception:
                pass
            self.run_btn.setEnabled(True)
            self._mixing_worker = None
            logger.error("Mixing calculation failed: %s", message)
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Mixing calculation failed: {error}").format(error=message),
            )

        QApplication.setOverrideCursor(Qt.WaitCursor)
        self.run_btn.setEnabled(False)
        self._mixing_worker = AnalysisWorker(_calculate)
        self._mixing_worker.finished_signal.connect(_on_finished)
        self._mixing_worker.failed.connect(_on_failed)
        self._mixing_worker.start()

    def closeEvent(self, event):
        from ui.dialogs.analysis_worker import stop_analysis_worker

        stop_analysis_worker(getattr(self, "_mixing_worker", None))
        super().closeEvent(event)

    def _export_results(self):
        """导出结果"""
        from PyQt5.QtWidgets import QFileDialog
        import pandas as pd

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Mixing Results"),
            "",
            ";;".join([
                f"{translate('CSV files')} (*.csv)",
                f"{translate('Excel files')} (*.xlsx *.xls)",
                f"{translate('All files')} (*.*)"
            ])
        )

        if file_path:
            try:
                # 收集结果
                results = []
                for row in range(self.result_table.rowCount()):
                    results.append({
                        'Mixture': self.result_table.item(row, 0).text(),
                        'Endmember': self.result_table.item(row, 1).text(),
                        'Proportion': float(self.result_table.item(row, 2).text()),
                        'Residual': float(self.result_table.item(row, 3).text())
                    })

                df = pd.DataFrame(results)

                # 保存
                if file_path.endswith('.xlsx'):
                    df.to_excel(file_path, index=False)
                else:
                    df.to_csv(file_path, index=False)

                QMessageBox.information(
                    self,
                    translate("Success"),
                    translate("Results exported successfully to {file}").format(file=file_path)
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    translate("Error"),
                    translate("Failed to export results: {error}").format(error=str(e))
                )
