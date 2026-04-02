"""Analysis equation and KDE overlays mixin."""

from __future__ import annotations

import ast
import uuid

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
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

    def _on_kde_change(self, state):
        """Handle KDE visibility change."""
        state_gateway.set_show_kde(state == Qt.Checked)
        self._sync_toggle_widgets(
            app_state.show_kde,
            getattr(self, 'kde_check', None),
            getattr(self, 'group_kde_check', None),
            getattr(self, 'tools_kde_check', None),
        )
        self._on_change()

    def _on_marginal_kde_change(self, state):
        """Handle marginal KDE visibility change."""
        state_gateway.set_show_marginal_kde(state == Qt.Checked)
        self._sync_toggle_widgets(
            app_state.show_marginal_kde,
            getattr(self, 'marginal_kde_check', None),
            getattr(self, 'tools_marginal_kde_check', None),
        )
        self._on_change()

    def _on_equation_overlays_change(self, state):
        """Handle equation overlays visibility change."""
        state_gateway.set_show_equation_overlays(state == Qt.Checked)
        self._on_change()

    def _on_equation_overlay_toggle(self, overlay, state):
        """Handle single equation overlay toggle."""
        overlay['enabled'] = state == Qt.Checked
        self._on_change()

    def _refresh_equation_overlays(self):
        """Refresh equation overlays list widgets."""
        if self.equation_overlays_layout is None:
            return

        while self.equation_overlays_layout.count():
            item = self.equation_overlays_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        overlays = getattr(app_state, 'equation_overlays', []) or []
        for overlay in overlays:
            self._add_equation_overlay_row(overlay)

    def _add_equation_overlay_row(self, overlay):
        """Add one equation overlay row widget."""
        if self.equation_overlays_layout is None:
            return

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)

        label_text = overlay.get('label', 'Equation')
        eq_checkbox = QCheckBox(translate(label_text))
        eq_checkbox.setChecked(overlay.get('enabled', True))
        eq_checkbox.stateChanged.connect(lambda state, ov=overlay: self._on_equation_overlay_toggle(ov, state))
        row_layout.addWidget(eq_checkbox)

        swatch = QLabel()
        swatch.setFixedSize(16, 16)
        _, style = self._ensure_equation_style(overlay)
        color_value = style.get('color') or '#e2e8f0'
        apply_color_swatch(swatch, color_value)
        swatch.mousePressEvent = lambda event, ov=overlay, sw=swatch: self._open_equation_style_dialog(ov, sw)
        row_layout.addWidget(swatch)
        row_layout.addStretch()

        self.equation_overlays_layout.addWidget(row)

    def _ensure_equation_style(self, overlay):
        """Ensure line style for overlay and return style key/style."""
        if overlay is None:
            return None, {}
        style_key = overlay.get('style_key')
        if not style_key:
            overlay_id = overlay.get('id') or overlay.get('expression') or overlay.get('label') or 'equation'
            style_key = f"equation:{overlay_id}"
            overlay['style_key'] = style_key
        existing_style = getattr(app_state, 'line_styles', {}).get(style_key, {}) or {}
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
        from ui.dialogs.line_style_dialog import open_line_style_dialog

        style_key, style = self._ensure_equation_style(overlay)
        if style_key is None:
            return
        if swatch is not None:
            swatch_color = style.get('color') or '#e2e8f0'
            apply_color_swatch(swatch, swatch_color)
        open_line_style_dialog(self, style_key, swatch=swatch, on_applied=self._on_change)

    def _open_kde_style_dialog(self, target, swatch):
        """Open style dialog for KDE overlays."""
        dialog = QDialog(self)
        title_key = "KDE Style" if target == 'kde' else "Marginal KDE Style"
        dialog.setWindowTitle(translate(title_key))
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)

        legacy_key = 'kde_style' if target == 'kde' else 'marginal_kde_style'
        style_key = 'kde_curve' if target == 'kde' else 'marginal_kde_curve'
        legacy_style = getattr(app_state, legacy_key, {}) or {}
        fallback_style = {
            'color': None,
            'linewidth': float(legacy_style.get('linewidth', 1.0)),
            'linestyle': '-',
            'alpha': float(legacy_style.get('alpha', 0.6 if target == 'kde' else 0.25)),
            'fill': bool(legacy_style.get('fill', True)),
        }
        if target == 'kde':
            fallback_style['levels'] = int(legacy_style.get('levels', 10))
        else:
            fallback_style['bw_adjust'] = float(legacy_style.get('bw_adjust', 1.0))
            fallback_style['gridsize'] = int(legacy_style.get('gridsize', 256))
            fallback_style['cut'] = float(legacy_style.get('cut', 1.0))
            fallback_style['log_transform'] = bool(legacy_style.get('log_transform', False))
        style = ensure_line_style(app_state, style_key, fallback_style)

        alpha_row = QHBoxLayout()
        alpha_row.addWidget(QLabel(translate("Opacity")))
        alpha_spin = QDoubleSpinBox()
        alpha_spin.setRange(0.05, 1.0)
        alpha_spin.setSingleStep(0.05)
        alpha_spin.setValue(float(style.get('alpha', 0.6 if target == 'kde' else 0.25)))
        alpha_row.addWidget(alpha_spin)
        alpha_row.addStretch()
        layout.addLayout(alpha_row)

        width_row = QHBoxLayout()
        width_row.addWidget(QLabel(translate("Line Width")))
        width_spin = QDoubleSpinBox()
        width_spin.setRange(0.0, 4.0)
        width_spin.setSingleStep(0.1)
        width_spin.setValue(float(style.get('linewidth', 1.0)))
        width_row.addWidget(width_spin)
        width_row.addStretch()
        layout.addLayout(width_row)

        fill_row = QHBoxLayout()
        fill_row.addWidget(QLabel(translate("Fill")))
        fill_checkbox = QCheckBox()
        fill_checkbox.setChecked(bool(style.get('fill', True)))
        fill_row.addWidget(fill_checkbox)
        fill_row.addStretch()
        layout.addLayout(fill_row)

        levels_spin = None
        if target == 'kde':
            levels_row = QHBoxLayout()
            levels_row.addWidget(QLabel(translate("KDE Levels")))
            levels_spin = QSpinBox()
            levels_spin.setRange(3, 30)
            levels_spin.setValue(int(style.get('levels', 10)))
            levels_row.addWidget(levels_spin)
            levels_row.addStretch()
            layout.addLayout(levels_row)

        top_size_spin = None
        right_size_spin = None
        max_points_spin = None
        bw_adjust_spin = None
        cut_spin = None
        log_transform_check = None
        if target == 'marginal_kde':
            top_row = QHBoxLayout()
            top_row.addWidget(QLabel(translate("Top KDE Height (%)")))
            top_size_spin = QDoubleSpinBox()
            top_size_spin.setRange(5.0, 40.0)
            top_size_spin.setSingleStep(1.0)
            top_size_spin.setValue(float(getattr(app_state, 'marginal_kde_top_size', 15.0)))
            top_row.addWidget(top_size_spin)
            top_row.addStretch()
            layout.addLayout(top_row)

            right_row = QHBoxLayout()
            right_row.addWidget(QLabel(translate("Right KDE Width (%)")))
            right_size_spin = QDoubleSpinBox()
            right_size_spin.setRange(5.0, 40.0)
            right_size_spin.setSingleStep(1.0)
            right_size_spin.setValue(float(getattr(app_state, 'marginal_kde_right_size', 15.0)))
            right_row.addWidget(right_size_spin)
            right_row.addStretch()
            layout.addLayout(right_row)

            max_points_row = QHBoxLayout()
            max_points_row.addWidget(QLabel(translate("Marginal KDE Max Points")))
            max_points_spin = QSpinBox()
            max_points_spin.setRange(200, 50000)
            max_points_spin.setSingleStep(100)
            max_points_spin.setValue(int(getattr(app_state, 'marginal_kde_max_points', 5000)))
            max_points_row.addWidget(max_points_spin)
            max_points_row.addStretch()
            layout.addLayout(max_points_row)

            bw_row = QHBoxLayout()
            bw_row.addWidget(QLabel(translate("Bandwidth Adjust")))
            bw_adjust_spin = QDoubleSpinBox()
            bw_adjust_spin.setRange(0.05, 5.0)
            bw_adjust_spin.setSingleStep(0.05)
            bw_adjust_spin.setValue(float(getattr(app_state, 'marginal_kde_bw_adjust', style.get('bw_adjust', 1.0))))
            bw_row.addWidget(bw_adjust_spin)
            bw_row.addStretch()
            layout.addLayout(bw_row)

            cut_row = QHBoxLayout()
            cut_row.addWidget(QLabel(translate("KDE Cut")))
            cut_spin = QDoubleSpinBox()
            cut_spin.setRange(0.0, 5.0)
            cut_spin.setSingleStep(0.1)
            cut_spin.setValue(float(getattr(app_state, 'marginal_kde_cut', style.get('cut', 1.0))))
            cut_row.addWidget(cut_spin)
            cut_row.addStretch()
            layout.addLayout(cut_row)

            log_row = QHBoxLayout()
            log_transform_check = QCheckBox(translate("Log Transform Density"))
            log_transform_check.setChecked(
                bool(getattr(app_state, 'marginal_kde_log_transform', style.get('log_transform', False)))
            )
            log_row.addWidget(log_transform_check)
            log_row.addStretch()
            layout.addLayout(log_row)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch()
        cancel_button = QPushButton(translate("Cancel"))
        cancel_button.clicked.connect(dialog.reject)
        buttons_row.addWidget(cancel_button)
        save_button = QPushButton(translate("Save"))

        def _apply():
            style_ref = getattr(app_state, 'line_styles', {}).setdefault(style_key, {})
            style_ref['alpha'] = float(alpha_spin.value())
            style_ref['linewidth'] = float(width_spin.value())
            style_ref['fill'] = bool(fill_checkbox.isChecked())
            if target == 'kde' and levels_spin is not None:
                style_ref['levels'] = int(levels_spin.value())
            if target == 'marginal_kde':
                if top_size_spin is not None:
                    state_gateway.set_marginal_kde_layout(top_size=float(top_size_spin.value()))
                if right_size_spin is not None:
                    state_gateway.set_marginal_kde_layout(right_size=float(right_size_spin.value()))
                if max_points_spin is not None:
                    state_gateway.set_marginal_kde_compute_options(max_points=int(max_points_spin.value()))
                if bw_adjust_spin is not None:
                    style_ref['bw_adjust'] = float(bw_adjust_spin.value())
                    state_gateway.set_marginal_kde_compute_options(bw_adjust=float(bw_adjust_spin.value()))
                if cut_spin is not None:
                    style_ref['cut'] = float(cut_spin.value())
                    state_gateway.set_marginal_kde_compute_options(cut=float(cut_spin.value()))
                if log_transform_check is not None:
                    style_ref['log_transform'] = bool(log_transform_check.isChecked())
                    state_gateway.set_marginal_kde_compute_options(
                        log_transform=bool(log_transform_check.isChecked())
                    )
            legacy_payload = {
                'alpha': style_ref.get('alpha', 0.6 if target == 'kde' else 0.25),
                'linewidth': style_ref.get('linewidth', 1.0),
                'fill': style_ref.get('fill', True),
            }
            if target == 'kde':
                legacy_payload['levels'] = style_ref.get('levels', 10)
            else:
                legacy_payload['bw_adjust'] = style_ref.get('bw_adjust', 1.0)
                legacy_payload['gridsize'] = style_ref.get('gridsize', 256)
                legacy_payload['cut'] = style_ref.get('cut', 1.0)
                legacy_payload['log_transform'] = style_ref.get('log_transform', False)
            if target == 'kde':
                state_gateway.set_kde_style(legacy_payload)
            else:
                state_gateway.set_marginal_kde_style(legacy_payload)

            if swatch is not None:
                apply_color_swatch(swatch, '#e2e8f0')
            dialog.accept()
            self._on_change()

        save_button.clicked.connect(_apply)
        buttons_row.addWidget(save_button)
        layout.addLayout(buttons_row)

        dialog.exec_()

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

        working_overlays = list(getattr(app_state, 'equation_overlays', []) or [])

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
