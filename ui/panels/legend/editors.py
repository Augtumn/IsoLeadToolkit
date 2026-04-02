"""Legend panel palette and marker editor helpers."""

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core import app_state, state_gateway, translate
from ui.icons import build_marker_icon


class LegendEditorsMixin:
    """Palette and shape editor helpers used by legend panel."""

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
            state_gateway.set_custom_palettes({})
        custom_palettes = dict(getattr(app_state, 'custom_palettes', {}) or {})
        custom_palettes[name] = list(colors)
        state_gateway.set_custom_palettes(custom_palettes)

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
            state_gateway.set_custom_shape_sets({})
        custom_shape_sets = dict(getattr(app_state, 'custom_shape_sets', {}) or {})
        custom_shape_sets[name] = list(shapes)
        state_gateway.set_custom_shape_sets(custom_shape_sets)
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
