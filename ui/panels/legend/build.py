"""Legend panel UI construction and editors."""
from __future__ import annotations

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QToolBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core import app_state, state_gateway, translate


class LegendBuildMixin:
    """Build and helper methods for legend panel."""

    def reset_state(self):
        super().reset_state()
        self.legend_inside_buttons = {}
        self.legend_outside_buttons = {}
        self.legend_columns_spin = None
        self.legend_step_spin = None
        self.auto_palette_combo = None
        self.auto_shape_set_combo = None
        self.auto_base_shape_combo = None
        self.auto_style_btn = None
        self.legend_nudge_step = 0.02
        self._last_palette_name = None

    def build(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        section_toolbox = QToolBox()
        section_toolbox.setObjectName('legend_section_toolbox')

        def _add_group_page(group_widget: QGroupBox, title_key: str) -> None:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(6, 6, 6, 6)
            page_layout.setSpacing(8)
            page_layout.addWidget(group_widget)
            page_layout.addStretch()
            section_toolbox.addItem(page, translate(title_key))

        position_group = QGroupBox(translate("Legend Position"))
        position_group.setProperty('translate_key', 'Legend Position')
        position_layout = QVBoxLayout()

        position_grid = QGridLayout()
        position_grid.setHorizontalSpacing(6)
        position_grid.setVerticalSpacing(6)

        outer_grid = QGridLayout()
        outer_grid.setHorizontalSpacing(6)
        outer_grid.setVerticalSpacing(6)

        self.legend_inside_buttons = {}
        self.legend_outside_buttons = {}

        grid_positions = [
            (0, 0, 'upper left', 'NW'),
            (0, 1, 'upper center', 'N'),
            (0, 2, 'upper right', 'NE'),
            (1, 0, 'center left', 'W'),
            (1, 1, 'center', 'C'),
            (1, 2, 'center right', 'E'),
            (2, 0, 'lower left', 'SW'),
            (2, 1, 'lower center', 'S'),
            (2, 2, 'lower right', 'SE'),
        ]

        for row, col, value, label in grid_positions:
            btn = QToolButton()
            btn.setText(label)
            btn.setCheckable(True)
            btn.setFixedSize(40, 32)
            btn.clicked.connect(lambda checked=False, loc=value: self._on_legend_inside_position_change(loc))
            self.legend_inside_buttons[value] = btn
            position_grid.addWidget(btn, row, col)

        for key, text, row, col, align in [
            ('outside_left', 'OUT L', 1, 0, Qt.AlignHCenter),
            ('outside_right', 'OUT R', 1, 2, Qt.AlignHCenter),
        ]:
            btn = QToolButton()
            btn.setText(text)
            btn.setCheckable(True)
            btn.setFixedSize(56, 32)
            btn.clicked.connect(lambda checked=False, loc=key: self._on_legend_outside_position_change(loc))
            self.legend_outside_buttons[key] = btn

        outer_grid.addWidget(self.legend_outside_buttons['outside_left'], 1, 0, Qt.AlignHCenter)
        outer_grid.addLayout(position_grid, 1, 1)
        outer_grid.addWidget(self.legend_outside_buttons['outside_right'], 1, 2, Qt.AlignHCenter)

        position_layout.addLayout(outer_grid)

        inside_location = getattr(app_state, 'legend_position', None)
        outside_location = getattr(app_state, 'legend_location', None)

        if outside_location and outside_location not in {'outside_left', 'outside_right'}:
            outside_location = None

        if inside_location not in self.legend_inside_buttons:
            inside_location = None
        if outside_location not in self.legend_outside_buttons:
            outside_location = None

        state_gateway.set_legend_position(inside_location)
        state_gateway.set_legend_location(outside_location)

        self._set_legend_inside_position_button(inside_location)
        self._set_legend_outside_position_button(outside_location)

        position_group.setLayout(position_layout)
        _add_group_page(position_group, 'Legend Position')

        style_group = QGroupBox(translate("Inline Legend Style"))
        style_group.setProperty('translate_key', 'Inline Legend Style')
        style_layout = QVBoxLayout()

        columns_row = QHBoxLayout()
        columns_label = QLabel(translate("Legend Columns"))
        columns_label.setProperty('translate_key', 'Legend Columns')
        columns_row.addWidget(columns_label)
        self.legend_columns_spin = QSpinBox()
        self.legend_columns_spin.setRange(0, 5)
        self.legend_columns_spin.setSpecialValueText(translate("Auto"))
        self.legend_columns_spin.setValue(app_state.legend_columns)
        self.legend_columns_spin.valueChanged.connect(self._on_legend_columns_change)
        columns_row.addWidget(self.legend_columns_spin)
        style_layout.addLayout(columns_row)

        step_row = QHBoxLayout()
        step_label = QLabel(translate("Nudge Step"))
        step_label.setProperty('translate_key', 'Nudge Step')
        step_row.addWidget(step_label)
        self.legend_step_spin = QDoubleSpinBox()
        self.legend_step_spin.setRange(0.001, 0.5)
        self.legend_step_spin.setDecimals(3)
        self.legend_step_spin.setSingleStep(0.005)
        self.legend_step_spin.setValue(float(getattr(app_state, 'legend_nudge_step', self.legend_nudge_step)))
        self.legend_step_spin.valueChanged.connect(self._on_nudge_step_change)
        step_row.addWidget(self.legend_step_spin)
        style_layout.addLayout(step_row)

        nudge_label = QLabel(translate("Nudge Legend"))
        nudge_label.setProperty('translate_key', 'Nudge Legend')
        style_layout.addWidget(nudge_label)

        nudge_grid = QGridLayout()
        nudge_grid.setHorizontalSpacing(6)
        nudge_grid.setVerticalSpacing(6)

        up_btn = QToolButton()
        up_btn.setText(translate("Up"))
        up_btn.setProperty('translate_key', 'Up')
        up_btn.clicked.connect(lambda checked=False: self._nudge_legend(0.0, self.legend_nudge_step))

        down_btn = QToolButton()
        down_btn.setText(translate("Down"))
        down_btn.setProperty('translate_key', 'Down')
        down_btn.clicked.connect(lambda checked=False: self._nudge_legend(0.0, -self.legend_nudge_step))

        left_btn = QToolButton()
        left_btn.setText(translate("Left"))
        left_btn.setProperty('translate_key', 'Left')
        left_btn.clicked.connect(lambda checked=False: self._nudge_legend(-self.legend_nudge_step, 0.0))

        right_btn = QToolButton()
        right_btn.setText(translate("Right"))
        right_btn.setProperty('translate_key', 'Right')
        right_btn.clicked.connect(lambda checked=False: self._nudge_legend(self.legend_nudge_step, 0.0))

        nudge_grid.addWidget(up_btn, 0, 1)
        nudge_grid.addWidget(left_btn, 1, 0)
        nudge_grid.addWidget(right_btn, 1, 2)
        nudge_grid.addWidget(down_btn, 2, 1)
        style_layout.addLayout(nudge_grid)

        auto_palette_row = QHBoxLayout()
        auto_palette_label = QLabel(translate("Color Scale"))
        auto_palette_label.setProperty('translate_key', 'Color Scale')
        auto_palette_row.addWidget(auto_palette_label)
        self.auto_palette_combo = QComboBox()
        self.auto_palette_combo.setIconSize(QSize(120, 12))
        try:
            from visualization.style_manager import style_manager_instance
            palette_names = style_manager_instance.get_palette_names()
        except Exception:
            palette_names = ['vibrant', 'bright', 'muted']
        self._populate_palette_combo(palette_names)
        current_scheme = getattr(app_state, 'color_scheme', 'vibrant')
        index = self.auto_palette_combo.findData(current_scheme)
        if index >= 0:
            self.auto_palette_combo.setCurrentIndex(index)
        self._last_palette_name = current_scheme
        self.auto_palette_combo.currentIndexChanged.connect(self._on_auto_palette_change)
        auto_palette_row.addWidget(self.auto_palette_combo)
        style_layout.addLayout(auto_palette_row)

        auto_shape_row = QHBoxLayout()
        auto_shape_label = QLabel(translate("Shape Set"))
        auto_shape_label.setProperty('translate_key', 'Shape Set')
        auto_shape_row.addWidget(auto_shape_label)
        self.auto_shape_set_combo = QComboBox()
        self.auto_shape_set_combo.addItem(translate("All Shapes"), "all")
        self.auto_shape_set_combo.addItem(translate("Basic Shapes"), "basic")
        self.auto_shape_set_combo.addItem(translate("Custom..."), "__custom__")
        for name, shapes in getattr(app_state, 'custom_shape_sets', {}).items():
            self.auto_shape_set_combo.addItem(name, list(shapes))
        self.auto_shape_set_combo.currentIndexChanged.connect(self._on_shape_set_change)
        auto_shape_row.addWidget(self.auto_shape_set_combo)
        style_layout.addLayout(auto_shape_row)

        base_shape_row = QHBoxLayout()
        base_shape_label = QLabel(translate("Base Shape"))
        base_shape_label.setProperty('translate_key', 'Base Shape')
        base_shape_row.addWidget(base_shape_label)
        self._ensure_marker_shape_map()
        self.auto_base_shape_combo = QComboBox()
        self._populate_base_shape_combo()
        base_marker = getattr(app_state, 'plot_marker_shape', 'o')
        for idx in range(self.auto_base_shape_combo.count()):
            if self.auto_base_shape_combo.itemData(idx) == base_marker:
                self.auto_base_shape_combo.setCurrentIndex(idx)
                break
        base_shape_row.addWidget(self.auto_base_shape_combo)
        style_layout.addLayout(base_shape_row)

        auto_btn = QPushButton(translate("Auto Style"))
        auto_btn.setProperty('translate_key', 'Auto Style')
        auto_btn.clicked.connect(self._auto_assign_styles)
        self.auto_style_btn = auto_btn
        style_layout.addWidget(auto_btn)

        style_group.setLayout(style_layout)
        _add_group_page(style_group, 'Inline Legend Style')

        self._restore_toolbox_state(section_toolbox, 'legend')
        self.legend_nudge_step = float(getattr(app_state, 'legend_nudge_step', self.legend_nudge_step))

        layout.addWidget(section_toolbox)
        layout.addStretch()
        return widget

    # ------ 位置 ------

    def _set_legend_inside_position_button(self, location):
        buttons = getattr(self, 'legend_inside_buttons', {})
        if not buttons:
            return
        target = buttons.get(location)
        for value, btn in buttons.items():
            btn.blockSignals(True)
            btn.setChecked(btn is target)
            btn.blockSignals(False)

    def _set_legend_outside_position_button(self, location):
        buttons = getattr(self, 'legend_outside_buttons', {})
        if not buttons:
            return
        target = buttons.get(location)
        for value, btn in buttons.items():
            btn.blockSignals(True)
            btn.setChecked(btn is target)
            btn.blockSignals(False)

    def _set_legend_position_button(self, location):
        if location and str(location).startswith('outside_'):
            self._set_legend_outside_position_button(location)
        else:
            self._set_legend_inside_position_button(location)
