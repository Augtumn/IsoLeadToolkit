"""
Unified data import dialog: file, sheet, and column selection.
"""
from __future__ import annotations

from PyQt5.QtWidgets import QDialog

from .data_import import Qt5DataImportDialogMixin


class Qt5DataImportDialog(Qt5DataImportDialogMixin, QDialog):
    """Unified dialog for data import and configuration."""


def get_data_import_configuration(
    default_file=None,
    default_sheet=None,
    default_group_cols=None,
    default_data_cols=None,
    default_render_mode=None,
    parent=None,
):
    """Open unified data import dialog and return configuration."""
    dialog = Qt5DataImportDialog(
        default_file=default_file,
        default_sheet=default_sheet,
        default_group_cols=default_group_cols,
        default_data_cols=default_data_cols,
        default_render_mode=default_render_mode,
        parent=parent,
    )
    if dialog.exec_() == Qt5DataImportDialog.Accepted:
        return dialog.result
    return None
