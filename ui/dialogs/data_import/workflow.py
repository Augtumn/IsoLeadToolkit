"""Workflow mixin for data import dialog."""
from __future__ import annotations

import os

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog, QListWidgetItem, QMessageBox, QTableWidgetItem

from core import app_state, state_gateway, translate
from data.loader import read_data_frame


class DataImportWorkflowMixin:
    """Load files/sheets, preview data, and maintain column selections."""

    def _refresh_from_defaults(self):
        self._refresh_recent_files()
        if self.selected_file and os.path.exists(self.selected_file):
            self._update_file_display(self.selected_file)
            self._load_sheets()
            self._load_dataframe()
        else:
            self._update_file_display(None)
            self._reset_sheet_list()
            self._clear_columns()

    def _reset_sheet_list(self):
        self.sheet_list.blockSignals(True)
        self.sheet_list.clear()
        self.sheet_list.addItem(translate("No sheet"))
        self.sheet_list.setEnabled(False)
        self.sheet_list.blockSignals(False)

    def _browse_file(self):
        file_types = ";;".join(
            [
                f"{translate('Excel files')} (*.xlsx *.xls)",
                f"{translate('CSV files')} (*.csv)",
                f"{translate('All files')} (*.*)",
            ]
        )

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            translate("Select Data File"),
            self.selected_file or "",
            file_types,
        )

        if file_path:
            self.selected_file = file_path
            self.selected_sheet = None
            self._update_file_display(file_path)
            self._add_recent_file(file_path)
            self._load_sheets()
            self._load_dataframe()

    def _clear_file(self):
        self.selected_file = None
        self.selected_sheet = None
        self._update_file_display(None)
        self._reset_sheet_list()
        self._clear_columns()

    def _load_sheets(self):
        if not self.selected_file:
            self._reset_sheet_list()
            return

        is_excel = self.selected_file.lower().endswith(('.xlsx', '.xls'))
        if not is_excel:
            self._reset_sheet_list()
            return

        try:
            sheets = list(pd.ExcelFile(self.selected_file).sheet_names)
        except Exception as exc:
            QMessageBox.critical(
                self,
                translate("Error"),
                translate("Failed to load Excel file: {error}").format(error=str(exc)),
            )
            self._reset_sheet_list()
            return

        self.sheet_list.blockSignals(True)
        self.sheet_list.clear()
        for sheet in sheets:
            item = QListWidgetItem(sheet)
            item.setData(Qt.UserRole, sheet)
            self.sheet_list.addItem(item)

        if self.selected_sheet and self.selected_sheet in sheets:
            self._select_sheet_item(self.selected_sheet)
        elif sheets:
            self.sheet_list.setCurrentRow(0)
            self.selected_sheet = sheets[0]

        self.sheet_list.setEnabled(True)
        self.sheet_list.blockSignals(False)

    def _select_sheet_item(self, sheet_name):
        for idx in range(self.sheet_list.count()):
            item = self.sheet_list.item(idx)
            if item.data(Qt.UserRole) == sheet_name:
                self.sheet_list.setCurrentRow(idx)
                break

    def _on_sheet_selected(self):
        if not self.sheet_list.isEnabled():
            return
        items = self.sheet_list.selectedItems()
        if not items:
            return
        self.selected_sheet = items[0].data(Qt.UserRole)
        self._load_dataframe()

    def _load_dataframe(self):
        if not self.selected_file:
            self.df = None
            self._clear_columns()
            return

        sheet_name = self.selected_sheet if self.sheet_list.isEnabled() else None
        try:
            self.df = read_data_frame(self.selected_file, sheet_name)
        except Exception as exc:
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to load data: {error}").format(error=str(exc)),
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

    def _refresh_recent_files(self):
        self.recent_list.clear()
        recent_files = getattr(app_state, 'recent_files', [])
        for path in recent_files:
            if not path:
                continue
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.UserRole, path)
            item.setToolTip(path)
            self.recent_list.addItem(item)

    def _add_recent_file(self, file_path):
        recent_files = list(getattr(app_state, 'recent_files', []))
        recent_files = [path for path in recent_files if path and path != file_path]
        recent_files.insert(0, file_path)
        recent_files = recent_files[:8]
        state_gateway.set_recent_files(recent_files)
        self._refresh_recent_files()

    def _on_recent_file_selected(self, item):
        if item is None:
            return
        file_path = item.data(Qt.UserRole)
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("File not found: {path}").format(path=file_path),
            )
            return
        self.selected_file = file_path
        self.selected_sheet = None
        self._update_file_display(file_path)
        self._add_recent_file(file_path)
        self._load_sheets()
        self._load_dataframe()

    def _clear_preview(self):
        self.preview_table.clear()
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)

    def _refresh_preview(self):
        if self.df is None or self.df.empty:
            self._clear_preview()
            return

        cols = list(self.df.columns)
        df_preview = self.df[cols].head(self.PREVIEW_ROWS)

        self.preview_table.setRowCount(len(df_preview))
        self.preview_table.setColumnCount(len(cols))
        self.preview_table.setHorizontalHeaderLabels([str(col) for col in cols])

        for row_index, (_, row) in enumerate(df_preview.iterrows()):
            for col_index, col in enumerate(cols):
                value = row[col]
                item = QTableWidgetItem(str(value))
                self.preview_table.setItem(row_index, col_index, item)

    def _apply_recommended_data_cols(self):
        if self.df is None:
            return

        recommended = [
            "206Pb/204Pb",
            "207Pb/204Pb",
            "208Pb/204Pb",
        ]
        available = [
            col
            for col in recommended
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
