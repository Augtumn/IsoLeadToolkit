"""
Unified data import dialog: file, sheet, and column selection.
"""
import os
import pandas as pd
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QFileDialog,
    QWidget,
    QSizePolicy,
    QMessageBox,
    QGroupBox,
    QListWidget,
    QListWidgetItem,
    QBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QHeaderView,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from core.localization import translate
from data.loader import read_data_frame


class Qt5DataImportDialog(QDialog):
    """Unified dialog for data import and configuration."""

    PREVIEW_ROWS = 8
    PREVIEW_COLS = 6

    def __init__(self, default_file=None, default_sheet=None,
                 default_group_cols=None, default_data_cols=None, parent=None):
        super().__init__(parent)
        self.result = None
        self.selected_file = default_file
        self.selected_sheet = default_sheet
        self.default_group_cols = set(default_group_cols or [])
        self.default_data_cols = set(default_data_cols or [])
        self.df = None
        self.all_columns = []

        self._setup_ui()
        self._refresh_from_defaults()

    def _setup_ui(self):
        self.setWindowTitle(translate("Data Import Wizard"))
        self.resize(980, 720)
        self.setMinimumSize(900, 640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel(translate("Data Import Wizard"))
        title_font = QFont(title.font())
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel(translate("Select a file, worksheet, and columns in one step."))
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addWidget(self._build_file_section())
        layout.addWidget(self._build_sheet_section())
        layout.addWidget(self._build_columns_section(), 1)
        layout.addWidget(self._build_preview_section())

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

    def _build_file_section(self):
        group = QGroupBox(translate("File"))
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(12, 10, 12, 12)
        group_layout.setSpacing(8)

        self.file_label = QLabel(translate("No file selected"))
        self.file_label.setWordWrap(True)
        group_layout.addWidget(self.file_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        browse_btn = QPushButton(translate("Browse..."))
        browse_btn.clicked.connect(self._browse_file)
        btn_row.addWidget(browse_btn)

        clear_btn = QPushButton(translate("Clear Selection"))
        clear_btn.clicked.connect(self._clear_file)
        btn_row.addWidget(clear_btn)

        btn_row.addStretch()
        group_layout.addLayout(btn_row)

        return group

    def _build_sheet_section(self):
        group = QGroupBox(translate("Sheet"))
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(12, 10, 12, 12)
        group_layout.setSpacing(8)

        self.sheet_combo = QComboBox()
        self.sheet_combo.setEditable(False)
        self.sheet_combo.currentIndexChanged.connect(self._on_sheet_change)
        group_layout.addWidget(self.sheet_combo)

        return group

    def _build_columns_section(self):
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
        self._update_columns_layout()
        return self.columns_container

    def _build_preview_section(self):
        group = QGroupBox(translate("Data Preview"))
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        group_layout = QVBoxLayout(group)
        group_layout.setContentsMargins(12, 10, 12, 12)
        group_layout.setSpacing(6)

        self.preview_label = QLabel(
            translate("Showing first {rows} rows and {cols} columns.").format(
                rows=self.PREVIEW_ROWS,
                cols=self.PREVIEW_COLS
            )
        )
        self.preview_label.setWordWrap(True)
        group_layout.addWidget(self.preview_label)

        self.preview_table = QTableWidget()
        self.preview_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.preview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.preview_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.preview_table.verticalHeader().setVisible(False)
        group_layout.addWidget(self.preview_table)

        return group

    def _build_column_section(self, title, description, selection_type):
        card = QGroupBox(title)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 12)
        card_layout.setSpacing(8)

        desc = QLabel(description)
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

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

        list_widget = QListWidget()
        list_widget.setSelectionMode(QListWidget.MultiSelection)
        list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        list_widget.itemSelectionChanged.connect(
            lambda: self._on_selection_changed(list_widget, selection_type)
        )

        card_layout.addWidget(list_widget, 1)

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

    def _refresh_from_defaults(self):
        if self.selected_file and os.path.exists(self.selected_file):
            self._update_file_display(self.selected_file)
            self._load_sheets()
            self._load_dataframe()
        else:
            self._update_file_display(None)
            self._reset_sheet_combo()
            self._clear_columns()

    def _update_file_display(self, file_path):
        if not file_path:
            self.file_label.setText(translate("No file selected"))
            return
        display_path = os.path.basename(file_path)
        directory = os.path.dirname(file_path)
        self.file_label.setText(f"{display_path}\n{directory}")

    def _reset_sheet_combo(self):
        self.sheet_combo.blockSignals(True)
        self.sheet_combo.clear()
        self.sheet_combo.addItem(translate("No sheet"), '')
        self.sheet_combo.setCurrentIndex(0)
        self.sheet_combo.setEnabled(False)
        self.sheet_combo.blockSignals(False)

    def _browse_file(self):
        file_types = ";;".join([
            f"{translate('Excel files')} (*.xlsx *.xls)",
            f"{translate('CSV files')} (*.csv)",
            f"{translate('All files')} (*.*)"
        ])

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            translate("Select Data File"),
            self.selected_file or "",
            file_types
        )

        if file_path:
            self.selected_file = file_path
            self.selected_sheet = None
            self._update_file_display(file_path)
            self._load_sheets()
            self._load_dataframe()

    def _clear_file(self):
        self.selected_file = None
        self.selected_sheet = None
        self._update_file_display(None)
        self._reset_sheet_combo()
        self._clear_columns()

    def _load_sheets(self):
        if not self.selected_file:
            self._reset_sheet_combo()
            return

        is_excel = self.selected_file.lower().endswith(('.xlsx', '.xls'))
        if not is_excel:
            self._reset_sheet_combo()
            return

        try:
            sheets = list(pd.ExcelFile(self.selected_file).sheet_names)
        except Exception as exc:
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Failed to load Excel file: {error}").format(error=str(exc))
            )
            self._reset_sheet_combo()
            return

        self.sheet_combo.blockSignals(True)
        self.sheet_combo.clear()
        for sheet in sheets:
            self.sheet_combo.addItem(sheet, sheet)

        if self.selected_sheet and self.selected_sheet in sheets:
            self.sheet_combo.setCurrentText(self.selected_sheet)
        elif sheets:
            self.sheet_combo.setCurrentIndex(0)
            self.selected_sheet = self.sheet_combo.currentData()

        self.sheet_combo.setEnabled(True)
        self.sheet_combo.blockSignals(False)

    def _on_sheet_change(self, index):
        if not self.sheet_combo.isEnabled():
            return
        self.selected_sheet = self.sheet_combo.currentData()
        self._load_dataframe()

    def _load_dataframe(self):
        if not self.selected_file:
            self.df = None
            self._clear_columns()
            return

        sheet_name = self.selected_sheet if self.sheet_combo.isEnabled() else None
        try:
            self.df = read_data_frame(self.selected_file, sheet_name)
        except Exception as exc:
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to load data: {error}").format(error=str(exc))
            )
            self.df = None
            self._clear_columns()
            return

        self.all_columns = list(self.df.columns)
        self._apply_recommended_data_cols()
        self._refresh_column_lists()
        self._refresh_preview()

    def _clear_columns(self):
        self.all_columns = []
        self.df = None
        self.group_list.clear()
        self.data_list.clear()
        self._clear_preview()

    def _clear_preview(self):
        self.preview_table.clear()
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)

    def _refresh_preview(self):
        if self.df is None or self.df.empty:
            self._clear_preview()
            return

        cols = list(self.df.columns)[:self.PREVIEW_COLS]
        df_preview = self.df[cols].head(self.PREVIEW_ROWS)

        self.preview_table.setRowCount(len(df_preview))
        self.preview_table.setColumnCount(len(cols))
        self.preview_table.setHorizontalHeaderLabels([str(col) for col in cols])

        for r_idx, (_, row) in enumerate(df_preview.iterrows()):
            for c_idx, col in enumerate(cols):
                value = row[col]
                item = QTableWidgetItem(str(value))
                self.preview_table.setItem(r_idx, c_idx, item)

    def _apply_recommended_data_cols(self):
        if self.df is None:
            return

        recommended = [
            "206Pb/204Pb",
            "207Pb/204Pb",
            "208Pb/204Pb",
        ]
        available = [
            col for col in recommended
            if col in self.df.columns and pd.api.types.is_numeric_dtype(self.df[col])
        ]
        if not available:
            return

        if not self.default_data_cols:
            self.default_data_cols = set(available)

    def _refresh_column_lists(self):
        self.group_list.clear()
        self.data_list.clear()

        if self.df is None:
            return

        for col in self.all_columns:
            is_numeric = pd.api.types.is_numeric_dtype(self.df[col])
            if is_numeric:
                data_item = QListWidgetItem(col)
                data_item.setData(Qt.UserRole, col)
                data_item.setSelected(col in self.default_data_cols)
                self.data_list.addItem(data_item)

            group_item = QListWidgetItem(col)
            group_item.setData(Qt.UserRole, col)
            group_item.setSelected(col in self.default_group_cols)
            self.group_list.addItem(group_item)

    def _on_selection_changed(self, list_widget, selection_type):
        selected_cols = set()
        for item in list_widget.selectedItems():
            col = item.data(Qt.UserRole)
            selected_cols.add(col)

        if selection_type == 'group':
            self.default_group_cols = selected_cols
        else:
            self.default_data_cols = selected_cols

    def _select_all(self, selection_type):
        list_widget = self.group_list if selection_type == 'group' else self.data_list
        list_widget.selectAll()

    def _clear_selection(self, selection_type):
        list_widget = self.group_list if selection_type == 'group' else self.data_list
        list_widget.clearSelection()

    def _ok_clicked(self):
        if not self.selected_file:
            QMessageBox.warning(self, translate("Warning"), translate("Please select a file."))
            return

        if self.df is None:
            QMessageBox.warning(self, translate("Warning"), translate("Please load data before applying."))
            return

        if not self.default_group_cols:
            QMessageBox.warning(
                self,
                translate("Validation Error"),
                translate("Please select at least one grouping column.")
            )
            return

        if not self.default_data_cols:
            QMessageBox.warning(
                self,
                translate("Validation Error"),
                translate("Please select at least one data column.")
            )
            return

        for col in self.default_data_cols:
            if not pd.api.types.is_numeric_dtype(self.df[col]):
                QMessageBox.warning(
                    self,
                    translate("Validation Error"),
                    translate("Data column '{column}' is not numeric. Please select only numeric columns for data.").format(column=col)
                )
                return

        self.result = {
            'file': self.selected_file,
            'sheet': self.selected_sheet,
            'group_cols': list(self.default_group_cols),
            'data_cols': list(self.default_data_cols),
            'df': self.df,
        }
        self.accept()


def get_data_import_configuration(default_file=None, default_sheet=None,
                                  default_group_cols=None, default_data_cols=None, parent=None):
    """Open unified data import dialog and return configuration."""
    dialog = Qt5DataImportDialog(
        default_file=default_file,
        default_sheet=default_sheet,
        default_group_cols=default_group_cols,
        default_data_cols=default_data_cols,
        parent=parent
    )
    if dialog.exec_() == Qt5DataImportDialog.Accepted:
        return dialog.result
    return None
