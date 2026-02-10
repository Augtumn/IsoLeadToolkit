"""
Qt5 工作表选择对话框
"""
import pandas as pd
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton,
                              QListWidget, QListWidgetItem,
                              QWidget, QSizePolicy, QMessageBox,
                              QGroupBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.localization import translate


class Qt5SheetDialog(QDialog):
    """Qt5 工作表选择对话框"""

    def __init__(self, file_path, default_sheet=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.result = None
        self.default_sheet = default_sheet
        self.sheets = []

        # 加载工作表
        try:
            self.sheets = list(pd.ExcelFile(file_path).sheet_names)
        except Exception as e:
            print(f"[ERROR] Could not load sheets: {e}", flush=True)
            QMessageBox.critical(self, translate("Error"),
                               translate("Failed to load Excel file: {error}").format(error=str(e)))
            return

        self._setup_ui()

    def _setup_ui(self):
        """设置 UI"""
        self.setWindowTitle(translate("Select Sheet"))
        self.resize(620, 460)
        self.setMinimumSize(560, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(translate("Choose a Sheet"))
        title_font = QFont(title.font())
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel(translate(
            "Select the worksheet that contains the measurements you want to analyze."
        ))
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        list_group = QGroupBox(translate("Available Sheets"))
        list_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        list_layout = QVBoxLayout(list_group)
        list_layout.setContentsMargins(12, 10, 12, 12)
        list_layout.setSpacing(8)

        self.sheet_list = QListWidget()
        self.sheet_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        for sheet in self.sheets:
            item = QListWidgetItem(sheet)
            self.sheet_list.addItem(item)
            if sheet == self.default_sheet:
                item.setSelected(True)

        if self.sheet_list.count() > 0 and not self.default_sheet:
            self.sheet_list.item(0).setSelected(True)

        self.sheet_list.itemDoubleClicked.connect(self._ok_clicked)

        list_layout.addWidget(self.sheet_list, 1)
        layout.addWidget(list_group, 1)

        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(8)
        footer_layout.addStretch()

        cancel_btn = QPushButton(translate("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)

        continue_btn = QPushButton(translate("Continue"))
        continue_btn.clicked.connect(self._ok_clicked)
        footer_layout.addWidget(continue_btn)

        layout.addLayout(footer_layout)

    def _ok_clicked(self):
        """确定按钮点击"""
        selected_items = self.sheet_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, translate("Warning"),
                               translate("Please select a sheet."))
            return

        self.result = selected_items[0].text()
        self.accept()


def get_sheet_selection(file_path, default_sheet=None):
    """获取工作表选择"""
    dialog = Qt5SheetDialog(file_path, default_sheet)
    if dialog.exec_() == Qt5SheetDialog.Accepted:
        return dialog.result
    return None
