"""
Qt5 三元图列选择对话框
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton,
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
        self.setWindowTitle(translate("Select Ternary Axes"))
        self.resize(650, 700)
        self.setMinimumSize(550, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(translate("Select Ternary Axes"))
        title_font = QFont(title.font())
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel(translate(
            "Select three columns to map to the vertices of the ternary plot (Top, Left, Right)."
        ))
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        selection_group = QGroupBox(translate("Current selection"))
        selection_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        selection_layout = QVBoxLayout(selection_group)
        selection_layout.setContentsMargins(12, 10, 12, 12)
        selection_layout.setSpacing(6)

        self.top_label = QLabel(translate("Top: Not selected"))
        selection_layout.addWidget(self.top_label)

        self.left_label = QLabel(translate("Left: Not selected"))
        selection_layout.addWidget(self.left_label)

        self.right_label = QLabel(translate("Right: Not selected"))
        selection_layout.addWidget(self.right_label)

        layout.addWidget(selection_group)

        list_group = QGroupBox(translate("Available Columns"))
        list_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        list_layout = QVBoxLayout(list_group)
        list_layout.setContentsMargins(12, 10, 12, 12)
        list_layout.setSpacing(6)

        self.column_list = QListWidget()
        self.column_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        for col in self.available_cols:
            item = QListWidgetItem(col)
            item.setData(Qt.UserRole, col)
            self.column_list.addItem(item)

        self.column_list.itemClicked.connect(self._on_column_clicked)

        list_layout.addWidget(self.column_list, 1)

        hint_label = QLabel(translate("Tip: Click columns in order (Top, Left, Right)"))
        hint_label.setWordWrap(True)
        list_layout.addWidget(hint_label)

        layout.addWidget(list_group, 1)

        params_group = QGroupBox(translate("Ternary Parameters"))
        params_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        params_layout = QVBoxLayout()
        params_layout.setSpacing(6)

        # 拉伸选项
        self.stretch_check = QCheckBox(translate("Enable stretching"))
        self.stretch_check.setChecked(app_state.ternary_stretch)
        params_layout.addWidget(self.stretch_check)

        # 缩放因子
        factors_label = QLabel(translate("Scaling factors (Top, Left, Right):"))
        params_layout.addWidget(factors_label)

        factors_row = QHBoxLayout()
        factors_row.setSpacing(6)

        self.top_factor = QDoubleSpinBox()
        self.top_factor.setRange(0.1, 10.0)
        self.top_factor.setSingleStep(0.1)
        self.top_factor.setValue(app_state.ternary_factors[0])
        factors_row.addWidget(QLabel(f"{translate('Top')}:"))
        factors_row.addWidget(self.top_factor)

        self.left_factor = QDoubleSpinBox()
        self.left_factor.setRange(0.1, 10.0)
        self.left_factor.setSingleStep(0.1)
        self.left_factor.setValue(app_state.ternary_factors[1])
        factors_row.addWidget(QLabel(f"{translate('Left')}:"))
        factors_row.addWidget(self.left_factor)

        self.right_factor = QDoubleSpinBox()
        self.right_factor.setRange(0.1, 10.0)
        self.right_factor.setSingleStep(0.1)
        self.right_factor.setValue(app_state.ternary_factors[2])
        factors_row.addWidget(QLabel(f"{translate('Right')}:"))
        factors_row.addWidget(self.right_factor)

        params_layout.addLayout(factors_row)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(8)

        clear_btn = QPushButton(translate("Clear"))
        clear_btn.clicked.connect(self._clear_selection)
        footer_layout.addWidget(clear_btn)

        footer_layout.addStretch()

        cancel_btn = QPushButton(translate("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)

        ok_btn = QPushButton(translate("OK"))
        ok_btn.clicked.connect(self._ok_clicked)
        footer_layout.addWidget(ok_btn)

        layout.addLayout(footer_layout)

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
        else:
            self.top_label.setText(translate("Top: Not selected"))

        if len(self.selected_cols) >= 2:
            self.left_label.setText(translate("Left: {col}").format(col=self.selected_cols[1]))
        else:
            self.left_label.setText(translate("Left: Not selected"))

        if len(self.selected_cols) >= 3:
            self.right_label.setText(translate("Right: {col}").format(col=self.selected_cols[2]))
        else:
            self.right_label.setText(translate("Right: Not selected"))

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
                translate("Please select columns for all three axes.")
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
