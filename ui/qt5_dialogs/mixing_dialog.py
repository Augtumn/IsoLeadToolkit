"""
混合计算对话框
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                              QLabel, QTableWidget, QTableWidgetItem, QMessageBox,
                              QHeaderView, QSizePolicy, QGroupBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
import numpy as np

from core import app_state, translate


def show_mixing_calculator(parent=None):
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

        export_btn = QPushButton(translate("Export Results"))
        export_btn.clicked.connect(self._export_results)
        button_layout.addWidget(export_btn)

        close_btn = QPushButton(translate("Close"))
        close_btn.clicked.connect(self.accept)
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

        # 对每个混合物计算
        for mixture_name, mixture_indices in mixtures.items():
            if not mixture_indices:
                continue

            # 获取混合物的平均组成
            mixture_data = app_state.df_global.iloc[mixture_indices][numeric_cols].mean()

            # 构建端元矩阵
            endmember_names = list(endmembers.keys())
            endmember_matrix = []

            for em_name in endmember_names:
                em_indices = endmembers[em_name]
                if em_indices:
                    em_data = app_state.df_global.iloc[em_indices][numeric_cols].mean()
                    endmember_matrix.append(em_data.values)

            if not endmember_matrix:
                continue

            endmember_matrix = np.array(endmember_matrix).T  # 转置为列向量

            # 使用最小二乘法求解
            try:
                # 添加约束：比例和为1
                A = np.vstack([endmember_matrix, np.ones(len(endmember_names))])
                b = np.append(mixture_data.values, 1.0)

                # 求解
                proportions, residuals, rank, s = np.linalg.lstsq(A, b, rcond=None)

                # 计算残差
                predicted = endmember_matrix @ proportions
                residual = np.sqrt(np.mean((mixture_data.values - predicted) ** 2))

                # 添加结果
                for em_name, prop in zip(endmember_names, proportions):
                    results.append({
                        'mixture': mixture_name,
                        'endmember': em_name,
                        'proportion': prop,
                        'residual': residual
                    })

            except Exception as e:
                print(f"[ERROR] Failed to calculate mixing for {mixture_name}: {e}")
                continue

        # 显示结果
        self.result_table.setRowCount(len(results))
        for i, result in enumerate(results):
            self.result_table.setItem(i, 0, QTableWidgetItem(result['mixture']))
            self.result_table.setItem(i, 1, QTableWidgetItem(result['endmember']))
            self.result_table.setItem(i, 2, QTableWidgetItem(f"{result['proportion']:.4f}"))
            self.result_table.setItem(i, 3, QTableWidgetItem(f"{result['residual']:.4f}"))

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
