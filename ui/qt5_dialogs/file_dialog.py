"""
Qt5 文件选择对话框
"""
import os
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton,
                              QComboBox, QFileDialog, QWidget,
                              QSizePolicy, QGroupBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.localization import translate, available_languages, set_language
from core.state import app_state


class Qt5FileDialog(QDialog):
    """Qt5 文件选择对话框"""

    def __init__(self, default_file=None, parent=None):
        super().__init__(parent)
        self.result = None
        self.selected_file = None
        self.default_file = default_file

        self._language_labels = dict(available_languages())
        self._translations = {}

        self._setup_ui()
        self._refresh_language()
        self._apply_translations()

        try:
            app_state.register_language_listener(self._apply_translations)
        except Exception:
            pass

        if default_file and os.path.exists(default_file):
            self.selected_file = default_file
            self._update_file_display(default_file)

    def _setup_ui(self):
        """设置 UI"""
        self.setWindowTitle(translate("Select Data File"))
        self.resize(820, 520)
        self.setMinimumSize(760, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self.title_label = QLabel(translate("Select Data File"))
        title_font = QFont(self.title_label.font())
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        header_row.addWidget(self.title_label)

        header_row.addStretch()

        self.lang_label = QLabel(f"{translate('Language')}:")
        header_row.addWidget(self.lang_label)

        self.lang_combo = QComboBox()
        self.lang_combo.setMinimumWidth(140)
        self.lang_combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.lang_combo.currentIndexChanged.connect(self._on_language_change)
        header_row.addWidget(self.lang_combo)

        layout.addLayout(header_row)

        self.subtitle_label = QLabel(translate(
            "Choose a CSV or Excel file (.csv, .xlsx, .xls) that contains "
            "the isotope dataset you want to explore."
        ))
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.subtitle_label)

        selection_group = QGroupBox(translate("Current selection"))
        selection_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        selection_layout = QVBoxLayout(selection_group)
        selection_layout.setContentsMargins(12, 10, 12, 12)
        selection_layout.setSpacing(8)

        self.file_label = QLabel(translate("No file selected"))
        self.file_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.file_label.setWordWrap(True)
        selection_layout.addWidget(self.file_label)

        self.tip_label = QLabel(translate(
            "Tip: For Excel workbooks, you can pick the sheet in the next step."
        ))
        self.tip_label.setWordWrap(True)
        selection_layout.addWidget(self.tip_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.browse_btn = QPushButton(translate("Browse..."))
        self.browse_btn.clicked.connect(self._browse_file)
        btn_row.addWidget(self.browse_btn)

        self.clear_btn = QPushButton(translate("Clear Selection"))
        self.clear_btn.clicked.connect(self._clear_file)
        btn_row.addWidget(self.clear_btn)

        btn_row.addStretch()
        selection_layout.addLayout(btn_row)

        layout.addWidget(selection_group, 1)

        # 底部按钮
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(8)
        footer_layout.addStretch()

        self.cancel_btn = QPushButton(translate("Cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(self.cancel_btn)

        self.continue_btn = QPushButton(translate("Continue"))
        self.continue_btn.clicked.connect(self._ok_clicked)
        footer_layout.addWidget(self.continue_btn)

        layout.addLayout(footer_layout)

    def _refresh_language(self):
        """刷新语言"""
        current_lang = app_state.language or 'en'

        # 更新语言下拉框
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()
        for code, name in self._language_labels.items():
            self.lang_combo.addItem(f"{code} - {name}", code)

        # 设置当前语言
        index = self.lang_combo.findData(current_lang)
        if index >= 0:
            self.lang_combo.setCurrentIndex(index)
        self.lang_combo.blockSignals(False)
        self._apply_translations()

    def _apply_translations(self):
        """Apply translations to UI text."""
        self.setWindowTitle(translate("Select Data File"))
        self.title_label.setText(translate("Select Data File"))
        self.lang_label.setText(f"{translate('Language')}:")
        self.subtitle_label.setText(translate(
            "Choose a CSV or Excel file (.csv, .xlsx, .xls) that contains "
            "the isotope dataset you want to explore."
        ))
        self.tip_label.setText(translate(
            "Tip: For Excel workbooks, you can pick the sheet in the next step."
        ))
        self.browse_btn.setText(translate("Browse..."))
        self.clear_btn.setText(translate("Clear Selection"))
        self.cancel_btn.setText(translate("Cancel"))
        self.continue_btn.setText(translate("Continue"))

        if not self.selected_file:
            self.file_label.setText(translate("No file selected"))

    def _on_language_change(self, index):
        """语言变化处理"""
        code = self.lang_combo.currentData()
        if code and set_language(code):
            app_state.language = code
            self._apply_translations()

    def closeEvent(self, event):
        listeners = getattr(app_state, 'language_listeners', [])
        if self._apply_translations in listeners:
            listeners.remove(self._apply_translations)
        super().closeEvent(event)

    def _update_file_display(self, file_path):
        """更新文件显示"""
        display_path = os.path.basename(file_path)
        directory = os.path.dirname(file_path)
        self.file_label.setText(f"{display_path}\n{directory}")

    def _browse_file(self):
        """浏览文件"""
        file_types = ";;".join([
            f"{translate('Excel files')} (*.xlsx *.xls)",
            f"{translate('CSV files')} (*.csv)",
            f"{translate('All files')} (*.*)"
        ])

        file_path, selected_filter = QFileDialog.getOpenFileName(
            self,
            translate("Select Data File"),
            self.selected_file or "",
            file_types
        )

        if file_path:
            self.selected_file = file_path
            self._update_file_display(file_path)

    def _clear_file(self):
        """清除文件选择"""
        self.selected_file = None
        self.file_label.setText(translate("No file selected"))

    def _ok_clicked(self):
        """确定按钮点击"""
        if not self.selected_file:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, translate("Warning"),
                               translate("Please select a file."))
            return

        self.result = {'file': self.selected_file}
        self.accept()


def get_file_sheet_selection(default_file=None):
    """获取文件和工作表选择"""
    dialog = Qt5FileDialog(default_file)
    if dialog.exec_() == Qt5FileDialog.Accepted:
        return dialog.result
    return None
