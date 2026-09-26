"""Display panel control helper methods."""
from __future__ import annotations

from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QColorDialog, QHBoxLayout, QLineEdit, QPushButton, QWidget

from core import app_state, translate
from ui.icons import apply_color_swatch, normalize_color_hex


class DisplayControlHelperMixin:
    """Color and legend-position helper methods for display panel."""
    legend_panel = None

    # Declared by the class that uses them, so no probe is needed for widgets
    # that build() creates later (UI review item B).

    def _set_legend_position_button(self, inside_location, outside_location=None):
        panel = self.legend_panel
        if panel is None:
            return
        if hasattr(panel, '_set_legend_inside_position_button'):
            panel._set_legend_inside_position_button(inside_location)
        if hasattr(panel, '_set_legend_outside_position_button'):
            panel._set_legend_outside_position_button(outside_location)

    def _normalize_color_value(self, value: str, fallback: str) -> str:
        """Normalize a color string to a valid hex representation."""
        return normalize_color_hex(value, fallback)

    def _set_color_button(self, button: QPushButton, color_value: str) -> None:
        normalized = apply_color_swatch(button, color_value, fallback='#e2e8f0', marker='s', icon_size=16)
        button.setToolTip(f"{translate('Choose Color')}: {normalized}")

    def _set_color_control_value(
        self,
        control: QWidget | None,
        value: str,
        fallback: str,
        trigger_refresh: bool = False,
    ) -> None:
        """Sync a color control value and trigger refresh when requested."""
        if control is None:
            return
        normalized = self._normalize_color_value(value, fallback)
        if isinstance(control, QPushButton):
            self._set_color_button(control, normalized)
        elif isinstance(control, QLineEdit):
            control.setText(normalized)
        if trigger_refresh:
            self._on_style_change()

    def _get_color_control_value(self, control: QWidget | None, fallback: str) -> str:
        """Return the normalized color represented by a display control."""
        if control is None:
            return fallback
        if isinstance(control, QPushButton):
            return self._normalize_color_value(control.property('color_value') or '', fallback)
        if isinstance(control, QLineEdit):
            return self._normalize_color_value(control.text(), fallback)
        return fallback

    def _sync_color_controls_from_state(self) -> None:
        """Initialize all display color controls from current app_state values."""
        color_bindings = [
            ('figure_bg_edit', 'plot_facecolor', '#ffffff'),
            ('axes_bg_edit', 'axes_facecolor', '#ffffff'),
            ('grid_color_edit', 'grid_color', '#e2e8f0'),
            ('minor_grid_color_edit', 'minor_grid_color', '#e2e8f0'),
            ('tick_color_edit', 'tick_color', '#1f2937'),
            ('axis_line_color_edit', 'axis_line_color', '#1f2937'),
            ('label_color_edit', 'label_color', '#1f2937'),
            ('title_color_edit', 'title_color', '#111827'),
        ]
        for control_attr, state_attr, fallback in color_bindings:
            control = getattr(self, control_attr, None)
            if control is None:
                continue
            value = getattr(app_state, state_attr, fallback)
            self._set_color_control_value(control, value, fallback, trigger_refresh=False)

    def _create_color_picker(self, initial_color: str) -> tuple[QWidget, QPushButton]:
        """Create a curve-style color picker: button opens dialog and shows current color."""
        normalized = self._normalize_color_value(initial_color, '#e2e8f0')

        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        color_button = QPushButton()
        color_button.setFixedSize(20, 16)
        self._set_color_button(color_button, normalized)
        row.addWidget(color_button)
        row.addStretch()

        def _pick_color() -> None:
            current_color = self._get_color_control_value(color_button, normalized)
            chosen = QColorDialog.getColor(QColor(current_color), self, translate("Choose Color"))
            if chosen.isValid():
                self._set_color_control_value(color_button, chosen.name(), normalized, trigger_refresh=True)

        color_button.clicked.connect(_pick_color)

        return container, color_button
