"""Legend panel UI construction and editors."""

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QToolBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QColorDialog,
)

from core import app_state, state_gateway, translate
from ui.icons import build_marker_icon


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

        state_gateway.set_attrs(
            {
                'legend_position': inside_location,
                'legend_location': outside_location,
            }
        )

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
        self.legend_columns_spin.setRange(1, 5)
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
        style_layout.addWidget(auto_btn)

        style_group.setLayout(style_layout)
        _add_group_page(style_group, 'Inline Legend Style')

        self.legend_nudge_step = float(getattr(app_state, 'legend_nudge_step', self.legend_nudge_step))

        layout.addWidget(section_toolbox)
        layout.addStretch()
        return widget

    def _populate_base_shape_combo(self):
        self.auto_base_shape_combo.blockSignals(True)
        self.auto_base_shape_combo.clear()
        for label, marker in self._marker_shape_map.items():
            icon = build_marker_icon('#94a3b8', marker, size=14)
            self.auto_base_shape_combo.addItem(icon, "", marker)
            idx = self.auto_base_shape_combo.count() - 1
            self.auto_base_shape_combo.setItemData(idx, label, Qt.ToolTipRole)
        self.auto_base_shape_combo.setIconSize(QSize(16, 16))
        self.auto_base_shape_combo.blockSignals(False)

    def _populate_palette_combo(self, palette_names):
        self.auto_palette_combo.blockSignals(True)
        self.auto_palette_combo.clear()
        try:
            from visualization.style_manager import style_manager_instance
            palettes = style_manager_instance.palettes
        except Exception:
            palettes = {}

        for name in palette_names:
            colors = palettes.get(name, [])
            icon = self._build_palette_icon(colors)
            self.auto_palette_combo.addItem(icon, "", name)
            index = self.auto_palette_combo.count() - 1
            self.auto_palette_combo.setItemData(index, name, Qt.ToolTipRole)
        custom_icon = self._build_palette_icon([], label="+")
        self.auto_palette_combo.addItem(custom_icon, "", "__custom__")
        index = self.auto_palette_combo.count() - 1
        self.auto_palette_combo.setItemData(index, translate("Custom..."), Qt.ToolTipRole)
        self.auto_palette_combo.blockSignals(False)

    def _build_palette_icon(self, colors, width=120, height=12, label=None):
        if not colors:
            colors = ['#333333']
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.white)
        painter = QPainter(pixmap)
        try:
            seg_w = max(1, width // len(colors))
            for i, color in enumerate(colors):
                painter.fillRect(i * seg_w, 0, seg_w, height, QColor(color))
            if label:
                painter.setPen(QColor("#0f172a"))
                painter.drawText(4, height - 2, label)
        finally:
            painter.end()
        return QIcon(pixmap)

    def _prompt_custom_palette(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(translate("Custom Palette"))
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        name_row = QHBoxLayout()
        name_label = QLabel(translate("Palette Name"))
        name_label.setProperty('translate_key', 'Palette Name')
        name_row.addWidget(name_label)
        name_edit = QLineEdit()
        name_row.addWidget(name_edit)
        layout.addLayout(name_row)

        list_label = QLabel(translate("Selected Colors"))
        list_label.setProperty('translate_key', 'Selected Colors')
        layout.addWidget(list_label)

        color_list = QListWidget()
        color_list.setIconSize(QSize(24, 12))
        color_list.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(color_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton(translate("Add Color"))
        add_btn.setProperty('translate_key', 'Add Color')
        remove_btn = QPushButton(translate("Remove"))
        remove_btn.setProperty('translate_key', 'Remove')
        up_btn = QPushButton(translate("Move Up"))
        up_btn.setProperty('translate_key', 'Move Up')
        down_btn = QPushButton(translate("Move Down"))
        down_btn.setProperty('translate_key', 'Move Down')
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addWidget(up_btn)
        btn_row.addWidget(down_btn)
        layout.addLayout(btn_row)

        def _add_color():
            color = QColorDialog.getColor(QColor("#3b82f6"), dialog, translate("Add Color"))
            if not color.isValid():
                return
            hex_color = color.name()
            item = QListWidgetItem(self._color_icon(hex_color), hex_color)
            item.setData(Qt.UserRole, hex_color)
            color_list.addItem(item)

        def _remove_color():
            row = color_list.currentRow()
            if row >= 0:
                color_list.takeItem(row)

        def _move_item(delta):
            row = color_list.currentRow()
            if row < 0:
                return
            new_row = row + delta
            if new_row < 0 or new_row >= color_list.count():
                return
            item = color_list.takeItem(row)
            color_list.insertItem(new_row, item)
            color_list.setCurrentRow(new_row)

        add_btn.clicked.connect(_add_color)
        remove_btn.clicked.connect(_remove_color)
        up_btn.clicked.connect(lambda: _move_item(-1))
        down_btn.clicked.connect(lambda: _move_item(1))

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() != QDialog.Accepted:
            return None

        name = name_edit.text().strip()
        colors = []
        for i in range(color_list.count()):
            item = color_list.item(i)
            val = item.data(Qt.UserRole)
            if val:
                colors.append(val)
        if not name or not colors:
            QMessageBox.warning(self, translate("Warning"), translate("Please provide a name and at least one color."))
            return None

        try:
            from visualization.style_manager import style_manager_instance
            style_manager_instance.palettes[name] = colors
        except Exception:
            pass

        if not hasattr(app_state, 'custom_palettes'):
            state_gateway.set_attr('custom_palettes', {})
        app_state.custom_palettes[name] = colors

        try:
            from visualization.style_manager import style_manager_instance
            palette_names = style_manager_instance.get_palette_names()
        except Exception:
            palette_names = list(getattr(app_state, 'custom_palettes', {}).keys())
        self._populate_palette_combo(palette_names)
        return name

    def _color_icon(self, color_hex, width=24, height=12):
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(color_hex))
        return QIcon(pixmap)

    def _prompt_custom_shape_set(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(translate("Custom Shape Set"))
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        name_row = QHBoxLayout()
        name_label = QLabel(translate("Shape Set Name"))
        name_label.setProperty('translate_key', 'Shape Set Name')
        name_row.addWidget(name_label)
        name_edit = QLineEdit()
        name_row.addWidget(name_edit)
        layout.addLayout(name_row)

        lists_row = QHBoxLayout()
        available_col = QVBoxLayout()
        available_label = QLabel(translate("Available Shapes"))
        available_label.setProperty('translate_key', 'Available Shapes')
        available_col.addWidget(available_label)
        available_list = QListWidget()
        available_list.setIconSize(QSize(18, 18))
        available_list.setSelectionMode(QAbstractItemView.SingleSelection)
        available_col.addWidget(available_list)
        lists_row.addLayout(available_col)

        selected_col = QVBoxLayout()
        selected_label = QLabel(translate("Selected Shapes"))
        selected_label.setProperty('translate_key', 'Selected Shapes')
        selected_col.addWidget(selected_label)
        selected_list = QListWidget()
        selected_list.setIconSize(QSize(18, 18))
        selected_list.setSelectionMode(QAbstractItemView.SingleSelection)
        selected_col.addWidget(selected_list)
        lists_row.addLayout(selected_col)
        layout.addLayout(lists_row)

        btn_row = QHBoxLayout()
        add_btn = QPushButton(translate("Add"))
        add_btn.setProperty('translate_key', 'Add')
        remove_btn = QPushButton(translate("Remove"))
        remove_btn.setProperty('translate_key', 'Remove')
        up_btn = QPushButton(translate("Move Up"))
        up_btn.setProperty('translate_key', 'Move Up')
        down_btn = QPushButton(translate("Move Down"))
        down_btn.setProperty('translate_key', 'Move Down')
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addWidget(up_btn)
        btn_row.addWidget(down_btn)
        layout.addLayout(btn_row)

        self._ensure_marker_shape_map()
        for label, marker in self._marker_shape_map.items():
            icon = build_marker_icon('#94a3b8', marker, size=16)
            item = QListWidgetItem(icon, "")
            item.setData(Qt.UserRole, marker)
            item.setToolTip(label)
            available_list.addItem(item)

        def _add_shape():
            item = available_list.currentItem()
            if item is None:
                return
            marker = item.data(Qt.UserRole)
            icon = build_marker_icon('#94a3b8', marker, size=16)
            new_item = QListWidgetItem(icon, "")
            new_item.setData(Qt.UserRole, marker)
            new_item.setToolTip(item.toolTip())
            selected_list.addItem(new_item)

        def _remove_shape():
            row = selected_list.currentRow()
            if row >= 0:
                selected_list.takeItem(row)

        def _move_shape(delta):
            row = selected_list.currentRow()
            if row < 0:
                return
            new_row = row + delta
            if new_row < 0 or new_row >= selected_list.count():
                return
            item = selected_list.takeItem(row)
            selected_list.insertItem(new_row, item)
            selected_list.setCurrentRow(new_row)

        add_btn.clicked.connect(_add_shape)
        remove_btn.clicked.connect(_remove_shape)
        up_btn.clicked.connect(lambda: _move_shape(-1))
        down_btn.clicked.connect(lambda: _move_shape(1))
        available_list.itemDoubleClicked.connect(lambda _item: _add_shape())

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() != QDialog.Accepted:
            return None, None

        name = name_edit.text().strip()
        shapes = []
        for i in range(selected_list.count()):
            item = selected_list.item(i)
            marker = item.data(Qt.UserRole)
            if marker:
                shapes.append(marker)
        if not name or not shapes:
            QMessageBox.warning(self, translate("Warning"), translate("Please provide a name and at least one shape."))
            return None, None

        if not hasattr(app_state, 'custom_shape_sets'):
            state_gateway.set_attr('custom_shape_sets', {})
        app_state.custom_shape_sets[name] = shapes
        return name, shapes

    def _ensure_marker_shape_map(self):
        if not hasattr(self, '_marker_shape_map'):
            self._marker_shape_map = {
                translate("Point (.)"): '.',
                translate("Pixel (,)"): ',',
                translate("Circle (o)"): 'o',
                translate("Triangle Down (v)"): 'v',
                translate("Triangle Up (^)"): '^',
                translate("Triangle Left (<)"): '<',
                translate("Triangle Right (>)"): '>',
                translate("Tri Down (1)"): '1',
                translate("Tri Up (2)"): '2',
                translate("Tri Left (3)"): '3',
                translate("Tri Right (4)"): '4',
                translate("Octagon (8)"): '8',
                translate("Square (s)"): 's',
                translate("Pentagon (p)"): 'p',
                translate("Plus Filled (P)"): 'P',
                translate("Star (*)"): '*',
                translate("Hexagon 1 (h)"): 'h',
                translate("Hexagon 2 (H)"): 'H',
                translate("Diamond (D)"): 'D',
                translate("Plus (+)"): '+',
                translate("Cross (x)"): 'x',
                translate("X (X)"): 'X',
                translate("Thin Diamond (d)"): 'd',
                translate("Vline (|)"): '|',
                translate("Hline (_)"): '_',
            }

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
