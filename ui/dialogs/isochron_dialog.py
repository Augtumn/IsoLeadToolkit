"""
Isochron regression error configuration dialog.
"""
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QRadioButton,
    QComboBox,
    QDoubleSpinBox,
    QMessageBox,
    QButtonGroup,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

import numpy as np

from core.localization import translate
from core.state import app_state


def get_isochron_error_settings(parent=None):
    """Open the isochron regression error settings dialog."""
    dialog = IsochronErrorConfigDialog(parent)
    if dialog.exec_() == QDialog.Accepted:
        return dialog.get_settings()
    return None


class IsochronErrorConfigDialog(QDialog):
    """Dialog to configure error inputs for York regression."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(translate("Isochron Regression Settings"))
        self.setMinimumWidth(520)
        self.setMinimumHeight(420)

        self._settings = None
        self._numeric_cols = self._get_numeric_columns()
        self._setup_ui()
        self._load_state()

    def _get_numeric_columns(self):
        if app_state.df_global is None:
            return []
        return app_state.df_global.select_dtypes(include=[np.number]).columns.tolist()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(translate("Isochron Regression Settings"))
        title_font = QFont(title.font())
        title_font.setPointSize(title_font.pointSize() + 2)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        subtitle = QLabel(translate("Select how to provide measurement errors for York regression."))
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        mode_group = QGroupBox(translate("Error Input Mode"))
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setContentsMargins(12, 10, 12, 12)
        mode_layout.setSpacing(8)

        self.mode_button_group = QButtonGroup(self)
        self.columns_radio = QRadioButton(translate("Use columns for 1-sigma errors and rXY"))
        self.fixed_radio = QRadioButton(translate("Use fixed values"))
        self.mode_button_group.addButton(self.columns_radio)
        self.mode_button_group.addButton(self.fixed_radio)
        mode_layout.addWidget(self.columns_radio)
        mode_layout.addWidget(self.fixed_radio)
        layout.addWidget(mode_group)

        self.columns_group = QGroupBox(translate("Column Mapping"))
        columns_layout = QVBoxLayout(self.columns_group)
        columns_layout.setContentsMargins(12, 10, 12, 12)
        columns_layout.setSpacing(8)

        self.sx_combo = QComboBox()
        self.sy_combo = QComboBox()
        self.rxy_combo = QComboBox()

        self._populate_combo(self.sx_combo)
        self._populate_combo(self.sy_combo)
        self._populate_combo(self.rxy_combo, allow_none=True)

        columns_layout.addLayout(self._row(translate("Standard error (sX)"), self.sx_combo))
        columns_layout.addLayout(self._row(translate("Standard error (sY)"), self.sy_combo))
        columns_layout.addLayout(self._row(translate("Error correlation (rXY)"), self.rxy_combo))
        layout.addWidget(self.columns_group)

        self.fixed_group = QGroupBox(translate("Fixed Values"))
        fixed_layout = QVBoxLayout(self.fixed_group)
        fixed_layout.setContentsMargins(12, 10, 12, 12)
        fixed_layout.setSpacing(8)

        self.sx_spin = QDoubleSpinBox()
        self.sx_spin.setRange(0.0, 1e9)
        self.sx_spin.setDecimals(8)
        self.sx_spin.setSingleStep(0.0001)

        self.sy_spin = QDoubleSpinBox()
        self.sy_spin.setRange(0.0, 1e9)
        self.sy_spin.setDecimals(8)
        self.sy_spin.setSingleStep(0.0001)

        self.rxy_spin = QDoubleSpinBox()
        self.rxy_spin.setRange(-1.0, 1.0)
        self.rxy_spin.setDecimals(4)
        self.rxy_spin.setSingleStep(0.01)

        fixed_layout.addLayout(self._row(translate("Fixed sX (1-sigma)"), self.sx_spin))
        fixed_layout.addLayout(self._row(translate("Fixed sY (1-sigma)"), self.sy_spin))
        fixed_layout.addLayout(self._row(translate("Fixed rXY"), self.rxy_spin))
        layout.addWidget(self.fixed_group)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_btn = QPushButton(translate("Cancel"))
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)

        ok_btn = QPushButton(translate("OK"))
        ok_btn.clicked.connect(self._on_ok)
        buttons.addWidget(ok_btn)

        layout.addLayout(buttons)

        self.columns_radio.toggled.connect(self._sync_mode)
        self.fixed_radio.toggled.connect(self._sync_mode)

    def _row(self, label_text, widget):
        row = QHBoxLayout()
        row.addWidget(QLabel(label_text))
        row.addWidget(widget, 1)
        return row

    def _populate_combo(self, combo, allow_none=False):
        combo.clear()
        if allow_none:
            combo.addItem(translate("None (assume 0)"), '')
        for col in self._numeric_cols:
            combo.addItem(col, col)

    def _load_state(self):
        mode = getattr(app_state, 'isochron_error_mode', 'fixed')
        self.columns_radio.setChecked(mode == 'columns')
        self.fixed_radio.setChecked(mode != 'columns')

        self._select_combo_value(self.sx_combo, getattr(app_state, 'isochron_sx_col', ''))
        self._select_combo_value(self.sy_combo, getattr(app_state, 'isochron_sy_col', ''))
        self._select_combo_value(self.rxy_combo, getattr(app_state, 'isochron_rxy_col', ''))

        self.sx_spin.setValue(float(getattr(app_state, 'isochron_sx_value', 0.001)))
        self.sy_spin.setValue(float(getattr(app_state, 'isochron_sy_value', 0.001)))
        self.rxy_spin.setValue(float(getattr(app_state, 'isochron_rxy_value', 0.0)))

        self._sync_mode()

    def _select_combo_value(self, combo, value):
        for idx in range(combo.count()):
            if combo.itemData(idx) == value:
                combo.setCurrentIndex(idx)
                return
        if combo.count() > 0:
            combo.setCurrentIndex(0)

    def _sync_mode(self):
        use_columns = self.columns_radio.isChecked()
        self.columns_group.setEnabled(use_columns)
        self.fixed_group.setEnabled(not use_columns)

    def _on_ok(self):
        if self.columns_radio.isChecked():
            if not self._numeric_cols:
                QMessageBox.warning(
                    self,
                    translate("Validation Error"),
                    translate("No numeric columns available for error mapping.")
                )
                return

            sx_col = self.sx_combo.currentData()
            sy_col = self.sy_combo.currentData()
            rxy_col = self.rxy_combo.currentData()

            if not sx_col or not sy_col:
                QMessageBox.warning(
                    self,
                    translate("Validation Error"),
                    translate("Please select columns for sX and sY.")
                )
                return

            self._settings = {
                'mode': 'columns',
                'sx_col': sx_col,
                'sy_col': sy_col,
                'rxy_col': rxy_col or '',
            }
        else:
            sx_val = float(self.sx_spin.value())
            sy_val = float(self.sy_spin.value())
            rxy_val = float(self.rxy_spin.value())

            if sx_val <= 0 or sy_val <= 0:
                QMessageBox.warning(
                    self,
                    translate("Validation Error"),
                    translate("Fixed sX and sY must be greater than 0.")
                )
                return

            self._settings = {
                'mode': 'fixed',
                'sx_value': sx_val,
                'sy_value': sy_val,
                'rxy_value': rxy_val,
            }

        self.accept()

    def get_settings(self):
        return self._settings
