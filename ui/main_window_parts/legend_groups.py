"""Legend UI actions for main window."""
from __future__ import annotations

import logging
from typing import Any

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor, QCursor
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from core import app_state, state_gateway, translate
from ui.icons import apply_color_swatch
from visualization.line_styles import resolve_line_style
from visualization.plotting.legend_model import OVERLAY_TOGGLE_MAP

#: Methods this class expects from the classes it is composed with
#: (explicit interface, UI review item I).
REQUIRES_MainWindowLegendGroupMixin = (
    "_reload_legend_panel",
    "_set_legend_item_meta",
    "_show_parent_shape_menu",
    "_update_parent_swatch",
)

logger = logging.getLogger(__name__)


class MainWindowLegendGroupMixin:
    """Parent/child group structure of the legend."""

    def _current_parent_groups(self):
        return {
            str(k): list(v or []) for k, v in (app_state.parent_groups or {}).items()
        }

    def _create_parent_group(self):
        from PyQt5.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self,
            translate("New Parent Group"),
            translate("Parent Group Name"),
        )
        if not ok:
            return
        name = str(name or "").strip()
        if not name:
            return
        parents = self._current_parent_groups()
        if name in parents:
            logger.info("Parent group already exists: %s", name)
            return
        parents[name] = []
        state_gateway.set_parent_groups(parents)
        self._reload_legend_panel()

    def _create_child_parent_group(self, container):
        """Create a parent group nested directly under *container*."""
        from PyQt5.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self,
            translate("New Child Parent Group..."),
            translate("Parent Group Name"),
        )
        if not ok:
            return
        name = str(name or "").strip()
        if not name:
            return
        parents = self._current_parent_groups()
        if name in parents:
            logger.info("Parent group already exists: %s", name)
            QMessageBox.information(
                self,
                translate("New Parent Group"),
                translate("Parent group '{name}' already exists.").format(name=name),
            )
            return
        parents[name] = []
        parents.setdefault(container, []).append(name)
        state_gateway.set_parent_groups(parents)
        self._reload_legend_panel()

    def _delete_parent_group(self, parent):
        parents = self._current_parent_groups()
        if parent not in parents:
            return
        children = list(parents.pop(parent))
        # Children (groups or nested parents) move up one level: into the
        # deleted parent's own container, or to the top level.
        container = None
        for name, children_list in parents.items():
            if parent in children_list:
                container = name
                children_list.remove(parent)
                break
        if container is not None:
            target = parents.setdefault(container, [])
            for child in children:
                if child not in target:
                    target.append(child)
        state_gateway.set_parent_groups(parents)
        self._reload_legend_panel()

    def _add_group_to_parent(self, group, parent):
        parents = self._current_parent_groups()
        # A group can belong to only one parent.
        for children in parents.values():
            if group in children:
                children.remove(group)
        children = parents.setdefault(parent, [])
        if group not in children:
            children.append(group)
        state_gateway.set_parent_groups(parents)

    def _remove_group_from_parent(self, group):
        parents = self._current_parent_groups()
        changed = False
        for children in parents.values():
            if group in children:
                children.remove(group)
                changed = True
        if changed:
            state_gateway.set_parent_groups(parents)
            self._reload_legend_panel()

    def _add_parent_legend_item(self, parent, depth: int = 0):
        """Render a parent-group row: shape swatch, bold header, delete."""
        from visualization.plotting.grouping import parent_children, parent_shape

        children = parent_children(app_state, parent)
        item_widget = QWidget()
        item_layout = QHBoxLayout()
        # Nested parents are indented by their nesting level.
        item_layout.setContentsMargins(4 + 24 * max(0, depth), 2, 4, 2)
        item_layout.setSpacing(6)

        # Shape swatch: shows the shape shared by all children of this
        # parent; clicking opens the shape picker (manual override).
        shape_btn = QPushButton()
        shape_btn.setFixedSize(22, 22)
        self._update_parent_swatch(parent, shape_btn)
        shape_btn.setCursor(QCursor(Qt.PointingHandCursor))
        shape_btn.setToolTip(translate("Parent shape (shared by subgroups)"))
        shape_btn.clicked.connect(
            lambda checked=False, p=parent, btn=shape_btn: self._show_parent_shape_menu(p, btn)
        )
        item_layout.addWidget(shape_btn)

        label = QLabel(f"{translate('Parent')}: {parent}")
        label.setProperty("keepStyle", True)  # survive _NativeStyleFilter
        label.setStyleSheet("font-weight: bold;")
        item_layout.addWidget(label, 1)

        count_label = QLabel(f"({len(children)})")
        count_label.setProperty("keepStyle", True)  # survive _NativeStyleFilter
        count_label.setStyleSheet("color: #64748b;")
        item_layout.addWidget(count_label)

        # Eject button: only for parents nested inside another parent.
        from visualization.plotting.grouping import parent_of_group

        if parent_of_group(app_state, parent) is not None:
            eject_btn = QPushButton("⇱")
            eject_btn.setFixedSize(20, 20)
            eject_btn.setToolTip(translate("Remove from Parent Group"))
            eject_btn.clicked.connect(
                lambda checked=False, p=parent: self._remove_group_from_parent(p)
            )
            item_layout.addWidget(eject_btn)

        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(20, 20)
        delete_btn.setToolTip(translate("Delete Parent Group"))
        delete_btn.clicked.connect(lambda checked=False, p=parent: self._delete_parent_group(p))
        item_layout.addWidget(delete_btn)

        item_widget.setLayout(item_layout)

        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())
        self._set_legend_item_meta(item, "parent", parent)
        # Draggable (reorder the whole parent block's stacking) and a drop
        # target for group rows.
        item.setFlags(
            Qt.ItemIsEnabled
            | Qt.ItemIsSelectable
            | Qt.ItemIsDragEnabled
            | Qt.ItemIsDropEnabled
        )
        self._legend_list.addItem(item)
        self._legend_list.setItemWidget(item, item_widget)
