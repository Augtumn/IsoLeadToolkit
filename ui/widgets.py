"""Reusable UI widget factories for panels and dialogs."""
from __future__ import annotations

from PyQt5.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QWidget,
)
from core import translate


def labeled_checkbox(label_key: str, default: bool, callback,
                     parent=None) -> tuple[QWidget, QCheckBox]:
    """Create a labeled QCheckBox row. Returns (row_widget, checkbox)."""
    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    check = QCheckBox(translate(label_key))
    check.setProperty('translate_key', label_key)
    check.setChecked(default)
    if callback:
        check.stateChanged.connect(callback)
    layout.addWidget(check)
    return row, check
