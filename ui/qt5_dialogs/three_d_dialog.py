"""
Qt5 3D 列选择对话框
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton,
                              QListWidget, QListWidgetItem,
                              QWidget, QSizePolicy, QMessageBox,
                              QGroupBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.localization import translate
from core.state import app_state


class Qt5ThreeDDialog(QDialog):
    """Qt5 3D 列选择对话框"""

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
                translate("Need at least 3 numeric columns for 3D plot.")
            )
            self.reject()
            return

        self._setup_ui()

        # 如果已有选择，恢复
        if app_state.selected_3d_cols and len(app_state.selected_3d_cols) == 3:
            self.selected_cols = app_state.selected_3d_cols.copy()
            self._update_selection_display()

    def _setup_ui(self):
        """设置 UI"""
        self.setWindowTitle(translate("Select 3D Axes"))
        self.resize(600, 550)
        self.setMinimumSize(500, 450)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(translate("Select 3D Axes"))
        title_font = QFont(title.font())
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel(translate(
            "Select one column for each axis. Columns must be unique."
        ))
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        selection_group = QGroupBox(translate("Current selection"))
        selection_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        selection_layout = QVBoxLayout(selection_group)
        selection_layout.setContentsMargins(12, 10, 12, 12)
        selection_layout.setSpacing(6)

        self.x_label = QLabel(translate("X-axis: Not selected"))
        selection_layout.addWidget(self.x_label)

        self.y_label = QLabel(translate("Y-axis: Not selected"))
        selection_layout.addWidget(self.y_label)

        self.z_label = QLabel(translate("Z-axis: Not selected"))
        selection_layout.addWidget(self.z_label)

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

        hint_label = QLabel(translate("Tip: Click columns in order (X, Y, Z)"))
        hint_label.setWordWrap(True)
        list_layout.addWidget(hint_label)

        layout.addWidget(list_group, 1)

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
            self.x_label.setText(translate("X-axis: {col}").format(col=self.selected_cols[0]))
        else:
            self.x_label.setText(translate("X-axis: Not selected"))

        if len(self.selected_cols) >= 2:
            self.y_label.setText(translate("Y-axis: {col}").format(col=self.selected_cols[1]))
        else:
            self.y_label.setText(translate("Y-axis: Not selected"))

        if len(self.selected_cols) >= 3:
            self.z_label.setText(translate("Z-axis: {col}").format(col=self.selected_cols[2]))
        else:
            self.z_label.setText(translate("Z-axis: Not selected"))

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
                translate("Please choose a column for each axis.")
            )
            return

        self.result = self.selected_cols
        self.accept()


def get_3d_column_selection():
    """获取 3D 列选择"""
    dialog = Qt5ThreeDDialog()
    if dialog.exec_() == Qt5ThreeDDialog.Accepted:
        return dialog.result
    return None
