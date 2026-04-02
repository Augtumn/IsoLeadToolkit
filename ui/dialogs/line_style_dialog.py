"""Line style dialog shared across panels and legend."""
from __future__ import annotations

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QGroupBox, QComboBox, QDoubleSpinBox,
    QLineEdit, QSpinBox,
)
from PyQt5.QtGui import QColor

from core import app_state, state_gateway, translate
from ui.icons import apply_color_swatch, normalize_color_hex


def _update_external_swatch(swatch, color_value: str) -> None:
    """Update external swatch widget color for both label and button widgets."""
    if swatch is None:
        return
    apply_color_swatch(swatch, color_value, marker='s', icon_size=16)


def open_line_style_dialog(parent, style_key, swatch=None, on_applied=None) -> bool:
    dialog = QDialog(parent)
    dialog.setWindowTitle(translate("Edit Line Style"))
    dialog.setModal(True)

    layout = QVBoxLayout(dialog)

    style = getattr(app_state, 'line_styles', {}).get(style_key, {}) or {}
    color_val = style.get('color') or ''

    color_row = QHBoxLayout()
    color_row.addWidget(QLabel(translate("Line Color")))
    color_swatch = QLabel()
    color_swatch.setFixedSize(20, 16)
    swatch_color = color_val if color_val else '#e2e8f0'
    apply_color_swatch(color_swatch, swatch_color)
    color_row.addWidget(color_swatch)

    auto_color_check = QCheckBox(translate("Auto Color"))
    auto_color_check.setChecked(color_val in ('', None))
    color_row.addWidget(auto_color_check)

    def _pick_color():
        from PyQt5.QtWidgets import QColorDialog
        chosen = QColorDialog.getColor(QColor(swatch_color), parent, translate("Line Color"))
        if chosen.isValid():
            new_color = chosen.name()
            apply_color_swatch(color_swatch, new_color)
            auto_color_check.setChecked(False)

    color_btn = QPushButton(translate("Choose Color"))
    color_btn.clicked.connect(_pick_color)
    color_row.addWidget(color_btn)
    color_row.addStretch()
    layout.addLayout(color_row)

    width_row = QHBoxLayout()
    width_row.addWidget(QLabel(translate("Line Width")))
    width_spin = QDoubleSpinBox()
    width_spin.setRange(0.2, 6.0)
    width_spin.setSingleStep(0.1)
    width_spin.setValue(float(style.get('linewidth', 1.0)))
    width_row.addWidget(width_spin)
    width_row.addStretch()
    layout.addLayout(width_row)

    style_row = QHBoxLayout()
    style_row.addWidget(QLabel(translate("Line Style")))
    style_combo = QComboBox()
    style_combo.addItems(['-', '--', '-.', ':'])
    style_combo.setCurrentText(style.get('linestyle', '-'))
    style_row.addWidget(style_combo)
    style_row.addStretch()
    layout.addLayout(style_row)

    alpha_row = QHBoxLayout()
    alpha_row.addWidget(QLabel(translate("Opacity")))
    alpha_spin = QDoubleSpinBox()
    alpha_spin.setRange(0.1, 1.0)
    alpha_spin.setSingleStep(0.05)
    alpha_spin.setValue(float(style.get('alpha', 0.85)))
    alpha_row.addWidget(alpha_spin)
    alpha_row.addStretch()
    layout.addLayout(alpha_row)

    label_checks = {}
    label_text_edit = None
    label_size_spin = None
    label_bg_check = None
    label_bg_color_swatch = None
    label_bg_alpha_spin = None
    label_pos_combo = None
    if style_key == 'isochron':
        label_group = QGroupBox(translate("Label Display"))
        label_group.setProperty('translate_key', 'Label Display')
        label_layout = QVBoxLayout(label_group)
        label_layout.setContentsMargins(8, 6, 8, 6)
        label_layout.setSpacing(4)

        opts = getattr(app_state, 'isochron_label_options', {})
        label_items = [
            ('show_age', translate("Age")),
            ('show_n_points', translate("Sample Count (n)")),
            ('show_mswd', 'MSWD'),
            ('show_r_squared', 'R²'),
            ('show_slope', translate("Slope")),
            ('show_intercept', translate("Intercept")),
        ]
        for key, text in label_items:
            chk = QCheckBox(text)
            chk.setChecked(opts.get(key, False))
            label_layout.addWidget(chk)
            label_checks[key] = chk

        layout.addWidget(label_group)

    if style_key in getattr(app_state, 'line_styles', {}):
        label_settings = QGroupBox(translate("Curve Label Settings"))
        label_settings.setProperty('translate_key', 'Curve Label Settings')
        label_layout = QVBoxLayout(label_settings)
        label_layout.setContentsMargins(8, 6, 8, 6)
        label_layout.setSpacing(6)

        label_text_row = QHBoxLayout()
        label_text_row.addWidget(QLabel(translate("Curve Label Text")))
        label_text_edit = QLineEdit()
        label_text_edit.setText(style.get('label_text', ''))
        label_text_row.addWidget(label_text_edit, 1)
        label_layout.addLayout(label_text_row)

        label_size_row = QHBoxLayout()
        label_size_row.addWidget(QLabel(translate("Curve Label Size")))
        label_size_spin = QSpinBox()
        label_size_spin.setRange(6, 24)
        default_label_size = 9 if style_key == 'isochron' else 8
        label_size_spin.setValue(int(style.get('label_fontsize', default_label_size)))
        label_size_row.addWidget(label_size_spin)
        label_size_row.addStretch()
        label_layout.addLayout(label_size_row)

        label_bg_row = QHBoxLayout()
        label_bg_check = QCheckBox(translate("Curve Label Background"))
        label_bg_check.setChecked(bool(style.get('label_background', False)))
        label_bg_row.addWidget(label_bg_check)
        label_bg_row.addStretch()
        label_layout.addLayout(label_bg_row)

        label_bg_color_row = QHBoxLayout()
        label_bg_color_row.addWidget(QLabel(translate("Curve Label Background Color")))
        label_bg_color_swatch = QLabel()
        label_bg_color_swatch.setFixedSize(20, 16)
        bg_color = style.get('label_bg_color', '#ffffff') or '#ffffff'
        apply_color_swatch(label_bg_color_swatch, bg_color, fallback='#ffffff')
        label_bg_color_row.addWidget(label_bg_color_swatch)

        def _pick_label_bg_color():
            from PyQt5.QtWidgets import QColorDialog
            chosen = QColorDialog.getColor(QColor(bg_color), parent, translate("Curve Label Background Color"))
            if chosen.isValid():
                new_color = chosen.name()
                apply_color_swatch(label_bg_color_swatch, new_color, fallback='#ffffff')

        label_bg_color_btn = QPushButton(translate("Choose Color"))
        label_bg_color_btn.clicked.connect(_pick_label_bg_color)
        label_bg_color_row.addWidget(label_bg_color_btn)
        label_bg_color_row.addStretch()
        label_layout.addLayout(label_bg_color_row)

        label_bg_alpha_row = QHBoxLayout()
        label_bg_alpha_row.addWidget(QLabel(translate("Curve Label Background Opacity")))
        label_bg_alpha_spin = QDoubleSpinBox()
        label_bg_alpha_spin.setRange(0.1, 1.0)
        label_bg_alpha_spin.setSingleStep(0.05)
        label_bg_alpha_spin.setValue(float(style.get('label_bg_alpha', 0.85)))
        label_bg_alpha_row.addWidget(label_bg_alpha_spin)
        label_bg_alpha_row.addStretch()
        label_layout.addLayout(label_bg_alpha_row)

        label_pos_row = QHBoxLayout()
        label_pos_row.addWidget(QLabel(translate("Curve Label Position")))
        label_pos_combo = QComboBox()
        label_pos_combo.addItem(translate("Auto"), 'auto')
        label_pos_combo.addItem(translate("Start"), 'start')
        label_pos_combo.addItem(translate("Center"), 'center')
        label_pos_combo.addItem(translate("End"), 'end')
        current_pos = style.get('label_position', 'auto')
        idx = label_pos_combo.findData(current_pos)
        if idx >= 0:
            label_pos_combo.setCurrentIndex(idx)
        label_pos_row.addWidget(label_pos_combo)
        label_pos_row.addStretch()
        label_layout.addLayout(label_pos_row)

        layout.addWidget(label_settings)

    btn_row = QHBoxLayout()
    btn_row.addStretch()
    cancel_btn = QPushButton(translate("Cancel"))
    cancel_btn.clicked.connect(dialog.reject)
    btn_row.addWidget(cancel_btn)
    save_btn = QPushButton(translate("Save"))

    def _apply():
        if not hasattr(app_state, 'line_styles'):
            state_gateway.set_line_styles({})
        style_ref = app_state.line_styles.setdefault(style_key, {})
        if auto_color_check.isChecked():
            style_ref['color'] = None
            new_swatch = '#e2e8f0'
        else:
            new_color = color_swatch.property('color_value') or ''
            style_ref['color'] = new_color or '#ef4444'
            new_swatch = style_ref['color']
        style_ref['linewidth'] = float(width_spin.value())
        style_ref['linestyle'] = style_combo.currentText()
        style_ref['alpha'] = float(alpha_spin.value())

        if style_key == 'model_curve':
            state_gateway.set_attr('model_curve_width', style_ref['linewidth'])
        elif style_key == 'plumbotectonics_curve':
            state_gateway.set_attr('plumbotectonics_curve_width', style_ref['linewidth'])
        elif style_key == 'paleoisochron':
            state_gateway.set_attr('paleoisochron_width', style_ref['linewidth'])
        elif style_key == 'model_age_line':
            state_gateway.set_attr('model_age_line_width', style_ref['linewidth'])
        elif style_key == 'isochron':
            state_gateway.set_attr('isochron_line_width', style_ref['linewidth'])
            if label_checks:
                if not hasattr(app_state, 'isochron_label_options'):
                    state_gateway.set_attr('isochron_label_options', {})
                for key, chk in label_checks.items():
                    app_state.isochron_label_options[key] = chk.isChecked()
        elif style_key == 'selected_isochron':
            state_gateway.set_attr('selected_isochron_line_width', style_ref['linewidth'])

        if label_text_edit is not None:
            style_ref['label_text'] = label_text_edit.text().strip()
        if label_size_spin is not None:
            style_ref['label_fontsize'] = float(label_size_spin.value())
        if label_bg_check is not None:
            style_ref['label_background'] = bool(label_bg_check.isChecked())
        if label_pos_combo is not None:
            style_ref['label_position'] = label_pos_combo.currentData() or 'auto'
        if label_bg_check is not None and label_bg_color_swatch is not None:
            label_color = normalize_color_hex(label_bg_color_swatch.property('color_value') or '', '#ffffff')
            style_ref['label_bg_color'] = label_color or '#ffffff'
        if label_bg_alpha_spin is not None:
            style_ref['label_bg_alpha'] = float(label_bg_alpha_spin.value())

        _update_external_swatch(swatch, new_swatch)
        dialog.accept()
        if on_applied:
            on_applied()

    save_btn.clicked.connect(_apply)
    btn_row.addWidget(save_btn)
    layout.addLayout(btn_row)

    dialog.exec_()
    return True


__all__ = ["open_line_style_dialog"]
