"""Submit/validation mixin for data import dialog."""
from __future__ import annotations

import pandas as pd
from PyQt5.QtWidgets import QMessageBox

from core import translate


class DataImportSubmitMixin:
    """Validate and return dialog result payload."""

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
                translate("Please select at least one grouping column."),
            )
            return

        if not self.default_data_cols:
            QMessageBox.warning(
                self,
                translate("Validation Error"),
                translate("Please select at least one data column."),
            )
            return

        for col in self.default_data_cols:
            if not pd.api.types.is_numeric_dtype(self.df[col]):
                QMessageBox.warning(
                    self,
                    translate("Validation Error"),
                    translate("Data column '{column}' is not numeric. Please select only numeric columns for data.")
                    .format(column=col),
                )
                return

        self.result = {
            'file': self.selected_file,
            'sheet': self.selected_sheet,
            'group_cols': list(self.default_group_cols),
            'data_cols': list(self.default_data_cols),
            'render_mode': self.render_mode_combo.currentData(),
            'df': self.df,
        }
        self.accept()
