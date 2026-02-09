"""
Qt5 三元图列选择对话框
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QFrame,
                              QListWidget, QListWidgetItem,
                              QWidget, QSizePolicy, QMessageBox,
                              QGroupBox, QDoubleSpinBox, QCheckBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.localization import translate
from core.state import app_state


class Qt5TernaryDialog(QDialog):
    """Qt5 三元图列选择对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = None
        self.selected_cols = []

        # 获取可用的数值列
        self.available_cols = app_state.data_cols

        if len(self.available_cols) < 3:
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Need at least 3 numeric columns for ternary plot.")
            )
            self.reject()
            return

        self._setup_ui()

        # 如果已有选择，恢复
        if app_state.selected_ternary_cols and len(app_state.selected_ternary_cols) == 3:
            self.selected_cols = app_state.selected_ternary_cols.copy()
            self._update_selection_display()

    def _setup_ui(self):
        """设置 UI"""
        self.setWindowTitle(translate("Select Ternary Columns"))
        self.resize(650, 700)
        self.setMinimumSize(550, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题
        header = QFrame()
        header.setStyleSheet("background-color: #edf2f7;")
        header.setFixedHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel(translate("Select Ternary Columns"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a202c;")
        header_layout.addWidget(title)

        layout.addWidget(header)

        # 内容
        content = QFrame()
        content.setStyleSheet("background-color: #edf2f7;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)

        subtitle = QLabel(translate(
            "Select exactly 3 numeric columns for Top, Left, and Right vertices."
        ))
        subtitle.setStyleSheet("color: #4a5568; font-size: 12px;")
        subtitle.setWordWrap(True)
        content_layout.addWidget(subtitle)

        # 当前选择显示
        selection_card = QFrame()
        selection_card.setStyleSheet("background-color: white; border-radius: 8px;")
        selection_layout = QVBoxLayout(selection_card)
        selection_layout.setContentsMargins(15, 15, 15, 15)

        selection_header = QLabel(translate("Current Selection"))
        selection_header.setStyleSheet("font-size: 14px; font-weight: bold;")
        selection_layout.addWidget(selection_header)

        self.top_label = QLabel(translate("Top: Not selected"))
        self.top_label.setStyleSheet("color: #4a5568; font-size: 12px;")
        selection_layout.addWidget(self.top_label)

        self.left_label = QLabel(translate("Left: Not selected"))
        self.left_label.setStyleSheet("color: #4a5568; font-size: 12px;")
        selection_layout.addWidget(self.left_label)

        self.right_label = QLabel(translate("Right: Not selected"))
        self.right_label.setStyleSheet("color: #4a5568; font-size: 12px;")
        selection_layout.addWidget(self.right_label)

        content_layout.addWidget(selection_card)

        # 可用列列表
        list_label = QLabel(translate("Available Columns (click to select)"))
        list_label.setStyleSheet("font-size: 12px; font-weight: bold; margin-top: 10px;")
        content_layout.addWidget(list_label)

        self.column_list = QListWidget()
        self.column_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
            }
            QListWidget::item:hover {
                background-color: #f7fafc;
            }
            QListWidget::item:selected {
                background-color: #2563eb;
                color: white;
            }
        """)

        for col in self.available_cols:
            item = QListWidgetItem(col)
            item.setData(Qt.UserRole, col)
            self.column_list.addItem(item)

        self.column_list.itemClicked.connect(self._on_column_clicked)

        content_layout.addWidget(self.column_list, 1)

        # 三元图参数
        params_group = QGroupBox(translate("Ternary Parameters"))
        params_layout = QVBoxLayout()

        # 拉伸选项
        self.stretch_check = QCheckBox(translate("Enable stretching"))
        self.stretch_check.setChecked(app_state.ternary_stretch)
        params_layout.addWidget(self.stretch_check)

        # 缩放因子
        factors_label = QLabel(translate("Scaling factors (Top, Left, Right):"))
        params_layout.addWidget(factors_label)

        factors_row = QHBoxLayout()

        self.top_factor = QDoubleSpinBox()
        self.top_factor.setRange(0.1, 10.0)
        self.top_factor.setSingleStep(0.1)
        self.top_factor.setValue(app_state.ternary_factors[0])
        factors_row.addWidget(QLabel("Top:"))
        factors_row.addWidget(self.top_factor)

        self.left_factor = QDoubleSpinBox()
        self.left_factor.setRange(0.1, 10.0)
        self.left_factor.setSingleStep(0.1)
        self.left_factor.setValue(app_state.ternary_factors[1])
        factors_row.addWidget(QLabel("Left:"))
        factors_row.addWidget(self.left_factor)

        self.right_factor = QDoubleSpinBox()
        self.right_factor.setRange(0.1, 10.0)
        self.right_factor.setSingleStep(0.1)
        self.right_factor.setValue(app_state.ternary_factors[2])
        factors_row.addWidget(QLabel("Right:"))
        factors_row.addWidget(self.right_factor)

        params_layout.addLayout(factors_row)

        params_group.setLayout(params_layout)
        content_layout.addWidget(params_group)

        # 提示
        hint_label = QLabel(translate("Tip: Click columns in order (Top, Left, Right)"))
        hint_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        content_layout.addWidget(hint_label)

        layout.addWidget(content, 1)

        # 底部按钮
        footer = QFrame()
        footer.setStyleSheet("background-color: #edf2f7;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(20, 10, 20, 10)

        clear_btn = QPushButton(translate("Clear"))
        clear_btn.clicked.connect(self._clear_selection)
        footer_layout.addWidget(clear_btn)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        footer_layout.addWidget(spacer)

        cancel_btn = QPushButton(translate("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)

        ok_btn = QPushButton(translate("OK"))
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                padding: 8px 24px;
                border-radius: 4px;
            }
        """)
        ok_btn.clicked.connect(self._ok_clicked)
        footer_layout.addWidget(ok_btn)

        layout.addWidget(footer)

    def _on_column_clicked(self, item):
        """列点击处理"""
        col = item.data(Qt.UserRole)

        if col in self.selected_cols:
            # 如果已选择，则取消选择
            self.selected_cols.remove(col)
        else:
            # 如果未选择，则添加（最多3个）
            if len(self.selected_cols) < 3:
                self.selected_cols.append(col)
            else:
                # 替换第一个
                self.selected_cols[0] = self.selected_cols[1]
                self.selected_cols[1] = self.selected_cols[2]
                self.selected_cols[2] = col

        self._update_selection_display()

    def _update_selection_display(self):
        """更新选择显示"""
        if len(self.selected_cols) >= 1:
            self.top_label.setText(translate("Top: {col}").format(col=self.selected_cols[0]))
            self.top_label.setStyleSheet("color: #1a202c; font-size: 12px; font-weight: bold;")
        else:
            self.top_label.setText(translate("Top: Not selected"))
            self.top_label.setStyleSheet("color: #4a5568; font-size: 12px;")

        if len(self.selected_cols) >= 2:
            self.left_label.setText(translate("Left: {col}").format(col=self.selected_cols[1]))
            self.left_label.setStyleSheet("color: #1a202c; font-size: 12px; font-weight: bold;")
        else:
            self.left_label.setText(translate("Left: Not selected"))
            self.left_label.setStyleSheet("color: #4a5568; font-size: 12px;")

        if len(self.selected_cols) >= 3:
            self.right_label.setText(translate("Right: {col}").format(col=self.selected_cols[2]))
            self.right_label.setStyleSheet("color: #1a202c; font-size: 12px; font-weight: bold;")
        else:
            self.right_label.setText(translate("Right: Not selected"))
            self.right_label.setStyleSheet("color: #4a5568; font-size: 12px;")

        # 更新列表项的选中状态
        for i in range(self.column_list.count()):
            item = self.column_list.item(i)
            col = item.data(Qt.UserRole)
            item.setSelected(col in self.selected_cols)

    def _clear_selection(self):
        """清除选择"""
        self.selected_cols.clear()
        self._update_selection_display()

    def _ok_clicked(self):
        """确定按钮点击"""
        if len(self.selected_cols) != 3:
            QMessageBox.warning(
                self,
                translate("Validation Error"),
                translate("Please select exactly 3 columns.")
            )
            return

        self.result = {
            'columns': self.selected_cols,
            'stretch': self.stretch_check.isChecked(),
            'factors': [
                self.top_factor.value(),
                self.left_factor.value(),
                self.right_factor.value()
            ]
        }
        self.accept()


def get_ternary_column_selection():
    """获取三元图列选择"""
    dialog = Qt5TernaryDialog()
    if dialog.exec_() == Qt5TernaryDialog.Accepted:
        return dialog.result
    return None
