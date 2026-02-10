"""
Qt5 数据配置对话框
"""
import pandas as pd
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton,
                              QListWidget, QListWidgetItem,
                              QWidget, QSizePolicy, QMessageBox,
                              QGroupBox, QLineEdit, QBoxLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.localization import translate


class Qt5DataConfigDialog(QDialog):
    """Qt5 数据配置对话框"""

    def __init__(self, df, default_group_cols=None, default_data_cols=None, parent=None):
        super().__init__(parent)
        self.df = df
        self.result = None

        self.all_columns = list(df.columns)
        self.selected_group_cols = set(default_group_cols or [])
        self.selected_data_cols = set(default_data_cols or [])

        self._setup_ui()

    def _setup_ui(self):
        """设置 UI"""
        self.setWindowTitle(translate("Configure Data Columns"))
        self.resize(980, 700)
        self.setMinimumSize(900, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(translate("Select Columns"))
        title_font = QFont(title.font())
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        self.columns_container = QWidget()
        self.columns_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.columns_layout = QBoxLayout(QBoxLayout.LeftToRight, self.columns_container)
        self.columns_layout.setContentsMargins(0, 0, 0, 0)
        self.columns_layout.setSpacing(12)

        self.group_card = self._build_column_section(
            translate("Grouping Columns"),
            translate("Pick one or more categorical columns to color and organize the scatter plot."),
            'group'
        )
        self.data_card = self._build_column_section(
            translate("Data Columns"),
            translate("Choose numeric measurements that feed into UMAP or t-SNE embeddings."),
            'data'
        )

        self.columns_layout.addWidget(self.group_card)
        self.columns_layout.addWidget(self.data_card)
        layout.addWidget(self.columns_container, 1)

        # 底部
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(8)
        footer_layout.addStretch()

        cancel_btn = QPushButton(translate("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        footer_layout.addWidget(cancel_btn)

        apply_btn = QPushButton(translate("Apply"))
        apply_btn.clicked.connect(self._ok_clicked)
        footer_layout.addWidget(apply_btn)

        layout.addLayout(footer_layout)
        self._update_columns_layout()

    def _build_column_section(self, title, description, selection_type):
        """构建列选择区域"""
        card = QGroupBox(title)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 12)
        card_layout.setSpacing(8)

        desc = QLabel(description)
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        # 工具栏
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        select_all_btn = QPushButton(translate("Select all"))
        select_all_btn.clicked.connect(lambda: self._select_all(selection_type))
        toolbar.addWidget(select_all_btn)

        clear_btn = QPushButton(translate("Clear"))
        clear_btn.clicked.connect(lambda: self._clear_selection(selection_type))
        toolbar.addWidget(clear_btn)

        toolbar.addStretch()
        card_layout.addLayout(toolbar)

        # 列列表
        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.MultiSelection)
        list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 填充列
        for col in self.all_columns:
            is_numeric = pd.api.types.is_numeric_dtype(self.df[col])

            if selection_type == 'data' and not is_numeric:
                continue

            dtype_label = translate("numeric") if is_numeric else translate("text")
            display_text = translate("{column} ({dtype})").format(
                column=col,
                dtype=dtype_label
            )

            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, col)

            list_widget.addItem(item)

            if selection_type == 'group':
                item.setSelected(col in self.selected_group_cols)
            else:
                item.setSelected(col in self.selected_data_cols)

        # 连接选择变化事件
        list_widget.itemSelectionChanged.connect(
            lambda: self._on_selection_changed(list_widget, selection_type)
        )

        card_layout.addWidget(list_widget, 1)

        # 保存引用
        if selection_type == 'group':
            self.group_list = list_widget
        else:
            self.data_list = list_widget

        return card

    def _update_columns_layout(self):
        if not hasattr(self, 'columns_layout'):
            return
        direction = QBoxLayout.LeftToRight if self.width() >= 900 else QBoxLayout.TopToBottom
        if self.columns_layout.direction() == direction:
            return
        self.columns_layout.setDirection(direction)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_columns_layout()

    def _on_selection_changed(self, list_widget, selection_type):
        """选择变化处理"""
        selected_cols = set()
        for item in list_widget.selectedItems():
            col = item.data(Qt.UserRole)
            selected_cols.add(col)

        if selection_type == 'group':
            self.selected_group_cols = selected_cols
        else:
            self.selected_data_cols = selected_cols

    def _select_all(self, selection_type):
        """全选"""
        list_widget = self.group_list if selection_type == 'group' else self.data_list
        list_widget.selectAll()

    def _clear_selection(self, selection_type):
        """清除选择"""
        list_widget = self.group_list if selection_type == 'group' else self.data_list
        list_widget.clearSelection()

    def _ok_clicked(self):
        """确定"""
        # 验证选择
        if not self.selected_group_cols:
            QMessageBox.warning(
                self,
                translate("Validation Error"),
                translate("Please select at least one grouping column.")
            )
            return

        if not self.selected_data_cols:
            QMessageBox.warning(
                self,
                translate("Validation Error"),
                translate("Please select at least one data column.")
            )
            return

        # 检查数据列是否为数值型
        for col in self.selected_data_cols:
            if not pd.api.types.is_numeric_dtype(self.df[col]):
                QMessageBox.warning(
                    self,
                    translate("Validation Error"),
                    translate("Data column '{column}' is not numeric. Please select only numeric columns for data.").format(column=col)
                )
                return

        self.result = {
            'group_cols': list(self.selected_group_cols),
            'data_cols': list(self.selected_data_cols)
        }
        self.accept()


def get_data_configuration(df, default_group_cols=None, default_data_cols=None):
    """获取数据配置"""
    dialog = Qt5DataConfigDialog(df, default_group_cols, default_data_cols)
    if dialog.exec_() == Qt5DataConfigDialog.Accepted:
        return dialog.result
    return None
