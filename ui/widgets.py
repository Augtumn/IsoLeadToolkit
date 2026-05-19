"""Reusable UI widget factories for panels and dialogs."""
from __future__ import annotations

from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QSpinBox, QWidget,
)
from core import translate


def labeled_spin(label_key: str, range_min: int, range_max: int, default: int,
                 callback, parent=None, step: int = 1) -> tuple[QWidget, QSpinBox]:
    """Create a labeled QSpinBox row. Returns (row_widget, spin)."""
    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel(translate(label_key))
    label.setProperty('translate_key', label_key)
    layout.addWidget(label)
    spin = QSpinBox()
    spin.setRange(range_min, range_max)
    spin.setSingleStep(step)
    spin.setValue(default)
    if callback:
        spin.valueChanged.connect(callback)
    layout.addWidget(spin)
    return row, spin


def labeled_double_spin(label_key: str, range_min: float, range_max: float,
                        default: float, callback, parent=None,
                        step: float = 0.1, decimals: int = 2) -> tuple[QWidget, QDoubleSpinBox]:
    """Create a labeled QDoubleSpinBox row. Returns (row_widget, spin)."""
    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel(translate(label_key))
    label.setProperty('translate_key', label_key)
    layout.addWidget(label)
    spin = QDoubleSpinBox()
    spin.setRange(range_min, range_max)
    spin.setSingleStep(step)
    spin.setDecimals(decimals)
    spin.setValue(default)
    if callback:
        spin.valueChanged.connect(callback)
    layout.addWidget(spin)
    return row, spin


def labeled_combo(label_key: str, items: list[str], default_index: int,
                  callback, parent=None) -> tuple[QWidget, QComboBox]:
    """Create a labeled QComboBox row. Returns (row_widget, combo)."""
    row = QWidget(parent)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel(translate(label_key))
    label.setProperty('translate_key', label_key)
    layout.addWidget(label)
    combo = QComboBox()
    combo.addItems(items)
    combo.setCurrentIndex(default_index)
    if callback:
        combo.currentTextChanged.connect(callback)
    layout.addWidget(combo)
    return row, combo


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
