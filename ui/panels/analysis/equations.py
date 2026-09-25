"""Analysis equation and KDE overlays mixin."""

from __future__ import annotations

import ast
import uuid

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core import app_state, state_gateway, translate
from ui.icons import apply_color_swatch
from visualization.line_styles import ensure_line_style


class AnalysisPanelEquationMixin:
    """Equation/KDE related actions for analysis panel."""

    def _ensure_equation_style(self, overlay):
        """Ensure line style for overlay and return style key/style."""
        if overlay is None:
            return None, {}
        style_key = overlay.get('style_key')
        if not style_key:
            overlay_id = overlay.get('id') or overlay.get('expression') or overlay.get('label') or 'equation'
            style_key = f"equation:{overlay_id}"
            overlay['style_key'] = style_key
        existing_style = app_state.line_styles.get(style_key, {}) or {}
        fallback_color = None if existing_style.get('color', '__missing__') in (None, '') else overlay.get('color', '#ef4444')
        fallback = {
            'color': fallback_color,
            'linewidth': overlay.get('linewidth', 1.0),
            'linestyle': overlay.get('linestyle', '--'),
            'alpha': overlay.get('alpha', 0.85),
        }
        style = ensure_line_style(app_state, style_key, fallback)
        return style_key, style

    def _open_equation_style_dialog(self, overlay, swatch):
        """Open line style dialog for equation overlay."""
        from ui.panels.display.dialogs.line_style_dialog import open_line_style_dialog

        style_key, style = self._ensure_equation_style(overlay)
        if style_key is None:
            return
        if swatch is not None:
            swatch_color = style.get('color') or '#e2e8f0'
            apply_color_swatch(swatch, swatch_color)
        open_line_style_dialog(self, style_key, swatch=swatch, on_applied=self._on_change)

    def _open_add_equation_dialog(self):
        """Open equation management dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle(translate("Manage Equations"))
        dialog.setModal(True)
        dialog.resize(520, 640)

        layout = QVBoxLayout(dialog)

        info_label = QLabel(translate("Select equations to display."))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        presets = [
            {
                'label': translate("y=x"),
                'latex': translate("y=x"),
                'expression': 'x',
            },
            {
                'label': translate("y=1.0049x+20.259"),
                'latex': translate("y=1.0049x+20.259"),
                'expression': '1.0049*x+20.259',
            },
        ]

        working_overlays = list(app_state.equation_overlays or [])

        list_group = QGroupBox(translate("Equation Library"))
        list_group.setProperty('translate_key', 'Equation Library')
        list_layout = QVBoxLayout()

        list_container = QWidget()
        list_container_layout = QVBoxLayout(list_container)
        list_container_layout.setContentsMargins(0, 0, 0, 0)
        list_container_layout.setSpacing(6)

        entries = []

        def _clear_layout(target_layout):
            while target_layout.count():
                item = target_layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        def _find_overlay(expression):
            for overlay in working_overlays:
                if overlay.get('expression') == expression:
                    return overlay
            return None

        def _add_entry_row(label_text, overlay, checked=False, is_preset=False):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)

            checkbox = QCheckBox(label_text)
            checkbox.setChecked(bool(checked))
            row_layout.addWidget(checkbox)

            swatch = QLabel()
            swatch.setFixedSize(16, 16)
            _, style = self._ensure_equation_style(overlay)
            swatch_color = style.get('color') or '#e2e8f0'
            apply_color_swatch(swatch, swatch_color)
            swatch.setProperty("keepStyle", True)
            swatch.mousePressEvent = lambda event, ov=overlay, sw=swatch: self._open_equation_style_dialog(ov, sw)
            row_layout.addWidget(swatch)
            row_layout.addStretch()

            list_container_layout.addWidget(row)
            entries.append({
                'checkbox': checkbox,
                'overlay': overlay,
                'is_preset': is_preset,
            })

        def _rebuild_list():
            entries.clear()
            _clear_layout(list_container_layout)

            existing_label = QLabel(translate("Existing Equations"))
            existing_label.setProperty("keepStyle", True)  # survive _NativeStyleFilter
            existing_label.setStyleSheet("font-weight: bold;")
            list_container_layout.addWidget(existing_label)

            if working_overlays:
                for overlay in working_overlays:
                    label_text = overlay.get('label', 'Equation')
                    _add_entry_row(translate(label_text), overlay, checked=overlay.get('enabled', False))
            else:
                empty_label = QLabel(translate("No equations yet."))
                list_container_layout.addWidget(empty_label)

            preset_label = QLabel(translate("Preset Equations"))
            preset_label.setProperty("keepStyle", True)  # survive _NativeStyleFilter
            preset_label.setStyleSheet("font-weight: bold; margin-top: 6px;")
            list_container_layout.addWidget(preset_label)

            for preset in presets:
                existing = _find_overlay(preset['expression'])
                if existing is not None:
                    continue
                preset_overlay = {
                    'label': preset['label'],
                    'latex': preset['latex'],
                    'expression': preset['expression'],
                    'enabled': False,
                    'color': '#ef4444',
                    'linewidth': 1.0,
                    'linestyle': '--',
                    'alpha': 0.85,
                }
                _add_entry_row(preset['label'], preset_overlay, checked=False, is_preset=True)

            list_container_layout.addStretch()

        _rebuild_list()

        list_layout.addWidget(list_container)
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        custom_group = QGroupBox(translate("Custom Equation"))
        custom_group.setProperty('translate_key', 'Custom Equation')
        custom_layout = QVBoxLayout()

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel(translate("Equation Name")))
        name_edit = QLineEdit()
        name_row.addWidget(name_edit)
        custom_layout.addLayout(name_row)

        latex_row = QHBoxLayout()
        latex_row.addWidget(QLabel(translate("Equation (LaTeX)")))
        latex_edit = QLineEdit()
        latex_row.addWidget(latex_edit)
        custom_layout.addLayout(latex_row)

        expression_row = QHBoxLayout()
        expression_row.addWidget(QLabel(translate("Expression (Python, x only)")))
        expression_edit = QLineEdit()
        expression_row.addWidget(expression_edit)
        custom_layout.addLayout(expression_row)

        add_custom_row = QHBoxLayout()
        add_custom_row.addStretch()
        add_custom_button = QPushButton(translate("Add to List"))
        add_custom_row.addWidget(add_custom_button)
        custom_layout.addLayout(add_custom_row)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_button = QPushButton(translate("Cancel"))
        cancel_button.clicked.connect(dialog.reject)
        button_row.addWidget(cancel_button)

        def _validate_expression(expression):
            expression = expression.strip()
            if not expression:
                QMessageBox.warning(dialog, translate("Warning"), translate("Expression cannot be empty."))
                return None
            try:
                ast.parse(expression, mode='eval')
            except Exception:
                QMessageBox.warning(dialog, translate("Warning"), translate("Invalid expression."))
                return None
            return expression

        def _add_custom_to_list():
            expression = _validate_expression(expression_edit.text())
            if expression is None:
                return
            label_text = name_edit.text().strip() or 'Equation'
            latex_text = latex_edit.text().strip() or label_text
            overlay = {
                'id': f"eq_custom_{uuid.uuid4().hex[:8]}",
                'label': label_text,
                'latex': latex_text,
                'expression': expression,
                'enabled': False,
                'color': '#ef4444',
                'linewidth': 1.0,
                'linestyle': '--',
                'alpha': 0.85,
            }
            working_overlays.append(overlay)
            name_edit.clear()
            latex_edit.clear()
            expression_edit.clear()
            _rebuild_list()

        def _apply_selection():
            new_overlays = []
            for entry in entries:
                overlay = entry['overlay']
                checked = bool(entry['checkbox'].isChecked())
                if entry['is_preset']:
                    if not checked:
                        continue
                    overlay = dict(overlay)
                    overlay['id'] = overlay.get('id') or f"eq_preset_{uuid.uuid4().hex[:8]}"
                    overlay['enabled'] = True
                    new_overlays.append(overlay)
                else:
                    overlay['enabled'] = checked
                    new_overlays.append(overlay)

            state_gateway.set_equation_overlays(new_overlays)
            state_gateway.set_show_equation_overlays(any(ov.get('enabled', False) for ov in new_overlays))
            self._on_change()
            dialog.accept()

        add_custom_button.clicked.connect(_add_custom_to_list)

        apply_button = QPushButton(translate("Apply"))
        apply_button.clicked.connect(_apply_selection)
        button_row.addWidget(apply_button)
        layout.addLayout(button_row)

        dialog.exec_()
