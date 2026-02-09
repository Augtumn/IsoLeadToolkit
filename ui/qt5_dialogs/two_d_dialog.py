"""
Qt5 2D 列选择对话框
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QFrame,
                              QListWidget, QListWidgetItem,
                              QWidget, QSizePolicy, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.localization import translate
from core.state import app_state


class Qt5TwoDDialog(QDialog):
    """Qt5 2D 列选择对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = None
        self.selected_cols = []

        # 获取可用的数值列
        self.available_cols = app_state.data_cols

        if len(self.available_cols) < 2:
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Need at least 2 numeric columns for 2D plot.")
            )
            self.reject()
            return

        self._setup_ui()

        # 如果已有选择，恢复
        if app_state.selected_2d_cols and len(app_state.selected_2d_cols) == 2:
            self.selected_cols = app_state.selected_2d_cols.copy()
            self._update_selection_display()

    def _setup_ui(self):
        """设置 UI"""
        self.setWindowTitle(translate("Select 2D Columns"))
        self.resize(600, 500)
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题
        header = QFrame()
        header.setStyleSheet("background-color: #edf2f7;")
        header.setFixedHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel(translate("Select 2D Columns"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #1a202c;")
        header_layout.addWidget(title)

        layout.addWidget(header)

        # 内容
        content = QFrame()
        content.setStyleSheet("background-color: #edf2f7;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)

        subtitle = QLabel(translate(
            "Select exactly 2 numeric columns for X and Y axes."
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

        self.x_label = QLabel(translate("X-axis: Not selected"))
        self.x_label.setStyleSheet("color: #4a5568; font-size: 12px;")
        selection_layout.addWidget(self.x_label)

        self.y_label = QLabel(translate("Y-axis: Not selected"))
        self.y_label.setStyleSheet("color: #4a5568; font-size: 12px;")
        selection_layout.addWidget(self.y_label)

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

        # 提示
        hint_label = QLabel(translate("Tip: Click columns in order (X-axis first, then Y-axis)"))
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
            # 如果未选择，则添加（最多2个）
            if len(self.selected_cols) < 2:
                self.selected_cols.append(col)
            else:
                # 替换第一个
                self.selected_cols[0] = self.selected_cols[1]
                self.selected_cols[1] = col

        self._update_selection_display()

    def _update_selection_display(self):
        """更新选择显示"""
        if len(self.selected_cols) >= 1:
            self.x_label.setText(translate("X-axis: {col}").format(col=self.selected_cols[0]))
            self.x_label.setStyleSheet("color: #1a202c; font-size: 12px; font-weight: bold;")
        else:
            self.x_label.setText(translate("X-axis: Not selected"))
            self.x_label.setStyleSheet("color: #4a5568; font-size: 12px;")

        if len(self.selected_cols) >= 2:
            self.y_label.setText(translate("Y-axis: {col}").format(col=self.selected_cols[1]))
            self.y_label.setStyleSheet("color: #1a202c; font-size: 12px; font-weight: bold;")
        else:
            self.y_label.setText(translate("Y-axis: Not selected"))
            self.y_label.setStyleSheet("color: #4a5568; font-size: 12px;")

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
        if len(self.selected_cols) != 2:
            QMessageBox.warning(
                self,
                translate("Validation Error"),
                translate("Please select exactly 2 columns.")
            )
            return

        self.result = self.selected_cols
        self.accept()


def get_2d_column_selection():
    """获取 2D 列选择"""
    dialog = Qt5TwoDDialog()
    if dialog.exec_() == Qt5TwoDDialog.Accepted:
        return dialog.result
    return None
