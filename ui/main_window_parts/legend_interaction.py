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
    QAbstractItemView,
)

from core import app_state, state_gateway, translate
from ui.icons import apply_color_swatch
from visualization.line_styles import resolve_line_style
from visualization.plotting.legend_model import OVERLAY_TOGGLE_MAP

logger = logging.getLogger(__name__)
from .legend_entries import reorder_legend_keys

#: Methods this class expects from the classes it is composed with
#: (explicit interface, UI review item I).
REQUIRES_MainWindowLegendInteractionMixin = (
    "_add_group_to_parent",
    "_apply_legend_z_order",
    "_bring_overlay_to_front",
    "_create_child_parent_group",
    "_create_parent_group",
    "_delete_parent_group",
    "_legend_order_key",
    "_move_legend_item_to_top",
    "_refresh_plot",
    "_reload_legend_panel",
    "_remove_group_from_parent",
    "_update_legend_panel",
)


class MainWindowLegendInteractionMixin:
    """Legend list interaction: drag/drop, reorder, context menu, checkboxes."""
    _legend_list = None

    # Declared by the class that uses them, so no probe is needed for widgets
    # that build() creates later (UI review item B).

    def _on_legend_item_double_clicked(self, item):
        meta = item.data(Qt.UserRole) if item is not None else None
        if not meta:
            return
        entry_type = meta.get("type")
        entry_key = meta.get("key")
        if entry_type == "group":
            self._bring_to_front(entry_key)
        elif entry_type == "overlay":
            self._bring_overlay_to_front(entry_key)
        elif entry_type == "parent":
            # Bring the whole parent block (all its children) to the top.
            self._move_legend_item_to_top("parent", entry_key)

    def _handle_legend_drop(self, list_widget, event):
        """Handle drops that merge groups (or nested parents) into parents.

        - A group row dropped on a parent row merges into that parent.
        - A parent row dropped EXACTLY ON a parent row (OnItem) nests the
          dragged parent under the target (cycle-checked).
        - A parent row dropped above/below rows is a plain reorder and is
          left to the default handling.
        """
        if event.source() is not list_widget:
            return False
        target_item = list_widget.itemAt(event.pos())
        if target_item is None:
            return False
        meta = target_item.data(Qt.UserRole)
        if not meta or meta.get("type") != "parent":
            return False
        target_parent = str(meta.get("key"))
        dragged = getattr(list_widget, "_dragging_items", None)
        if not dragged:
            dragged = list(list_widget.selectedItems())

        dragged_meta = [
            (item.data(Qt.UserRole) or {}) for item in dragged
        ]
        dragged_parents = [
            str(m.get("key")) for m in dragged_meta if m.get("type") == "parent"
        ]

        moved = False
        if dragged_parents:
            # Nested parents: only a drop exactly ON the target row nests;
            # above/below drops are reorders handled by the default path.
            from PyQt5.QtWidgets import QAbstractItemView

            if list_widget.dropIndicatorPosition() != QAbstractItemView.OnItem:
                return False
            from visualization.plotting.grouping import is_descendant

            for parent in dragged_parents:
                if parent == target_parent or is_descendant(app_state, parent, target_parent):
                    logger.warning(
                        "Refused to nest parent '%s' under '%s' (cycle)", parent, target_parent
                    )
                    continue
                self._add_group_to_parent(parent, target_parent)
                moved = True
        else:
            for item in dragged:
                item_meta = item.data(Qt.UserRole) or {}
                if item_meta.get("type") == "group":
                    self._add_group_to_parent(str(item_meta.get("key")), target_parent)
                    moved = True

        if moved:
            self._reload_legend_panel()
        return moved

    def _handle_legend_reorder(self, list_widget, event):
        """Plain reorder of any row type via ``legend_item_order``.

        Qt's default InternalMove drop is bypassed: rows are reordered by
        updating the order state and rebuilding the panel, so a drop can
        never stack two rows at the same position.
        """
        source = event.source()
        if source is not None and source is not list_widget:
            # Drops from other widgets are not internal reorders. Synthetic
            # events (no source) still pass; _dragging_items is only set by
            # our own startDrag, so the guard below remains authoritative.
            return False
        dragged = getattr(list_widget, "_dragging_items", None)
        if not dragged:
            return False
        src_meta = dragged[0].data(Qt.UserRole) or {}
        src_type = src_meta.get("type")
        src_key = src_meta.get("key")
        if not src_type or src_key is None:
            return False
        target_item = list_widget.itemAt(event.pos())
        if target_item is None:
            return False
        target_meta = target_item.data(Qt.UserRole) or {}
        target_type = target_meta.get("type")
        target_key = target_meta.get("key")
        if not target_type or target_key is None:
            return False

        src_full = self._legend_order_key(src_type, src_key)
        target_full = self._legend_order_key(target_type, target_key)

        order_keys = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            meta = item.data(Qt.UserRole) or {}
            if meta.get("type") and meta.get("key") is not None:
                order_keys.append(self._legend_order_key(meta["type"], meta["key"]))

        from PyQt5.QtWidgets import QAbstractItemView

        below = list_widget.dropIndicatorPosition() == QAbstractItemView.BelowItem
        new_order = reorder_legend_keys(order_keys, src_full, target_full, below)
        if new_order == order_keys:
            return False
        state_gateway.set_legend_item_order(new_order)
        # Rebuild directly from the NEW order state. Do NOT go through
        # _rebuild_legend_after_reorder here: its leading
        # _apply_legend_z_order() would read the OLD row order from the list
        # and write it back over the order we just set, reverting the drag.
        title = app_state.legend_last_title
        handles = app_state.legend_last_handles
        labels = app_state.legend_last_labels
        if title and handles is not None and labels is not None:
            self._update_legend_panel(title, handles, labels)
        else:
            self._apply_legend_z_order()
        return True

    def _show_legend_context_menu(self, pos):
        from PyQt5.QtWidgets import QMenu as _QMenu

        item = self._legend_list.itemAt(pos)
        meta = item.data(Qt.UserRole) if item is not None else None
        entry_type = meta.get("type") if meta else None
        entry_key = meta.get("key") if meta else None

        menu = _QMenu(self)
        if entry_type == "group" and entry_key is not None:
            from visualization.plotting.grouping import parent_of_group

            if parent_of_group(app_state, entry_key) is not None:
                remove_action = menu.addAction(translate("Remove from Parent Group"))
                remove_action.triggered.connect(
                    lambda checked=False, g=entry_key: self._remove_group_from_parent(g)
                )
                menu.addSeparator()
        elif entry_type == "parent" and entry_key is not None:
            from visualization.plotting.grouping import parent_of_group

            if parent_of_group(app_state, entry_key) is not None:
                remove_action = menu.addAction(translate("Remove from Parent Group"))
                remove_action.triggered.connect(
                    lambda checked=False, p=entry_key: self._remove_group_from_parent(p)
                )
                menu.addSeparator()
            child_action = menu.addAction(translate("New Child Parent Group..."))
            child_action.triggered.connect(
                lambda checked=False, p=entry_key: self._create_child_parent_group(p)
            )
            delete_action = menu.addAction(translate("Delete Parent Group"))
            delete_action.triggered.connect(
                lambda checked=False, p=entry_key: self._delete_parent_group(p)
            )
            menu.addSeparator()

        new_action = menu.addAction(translate("New Parent Group..."))
        new_action.triggered.connect(lambda checked=False: self._create_parent_group())
        menu.exec_(self._legend_list.mapToGlobal(pos))

    def _on_group_checkbox_change(self, group, state):
        if (not app_state.last_group_col
                or app_state.df_global is None
                or app_state.last_group_col not in app_state.df_global.columns):
            return

        groups = list(app_state.available_groups or app_state.df_global[app_state.last_group_col].unique())
        if app_state.visible_groups is None:
            current_visible = set(groups)
        else:
            current_visible = set(app_state.visible_groups)

        if state == Qt.Checked:
            current_visible.add(group)
        else:
            current_visible.discard(group)

        if len(current_visible) == len(groups):
            state_gateway.set_visible_groups(None)
        else:
            state_gateway.set_visible_groups(sorted(current_visible))

        self._refresh_plot()

    def _reveal_group_in_legend(self, group):
        """Scroll the legend panel to *group* and select its row.

        Long lists (hundreds of groups) make a row impossible to find by hand, so a
        double click on a data point brings its legend entry into view.
        """
        legend_list = self._legend_list
        if legend_list is None:
            return
        for index in range(legend_list.count()):
            item = legend_list.item(index)
            meta = item.data(Qt.UserRole) or {}
            if meta.get("type") == "group" and meta.get("key") == group:
                legend_list.scrollToItem(item, QAbstractItemView.PositionAtCenter)
                legend_list.setCurrentItem(item)
                return
        logger.info("Group %s is not shown in the legend panel.", group)

    def _bring_to_front(self, group):
        if group in app_state.group_to_scatter:
            sc = app_state.group_to_scatter[group]
            try:
                max_z = 2
                for c in app_state.scatter_collections:
                    max_z = max(max_z, c.get_zorder())

                sc.set_zorder(max_z + 1)
                if app_state.fig:
                    app_state.fig.canvas.draw_idle()
            except Exception as exc:
                logger.warning("Failed to bring %s to front: %s", group, exc)
        self._move_legend_item_to_top("group", group)
        # Keep the plot and the legend in step: the list order is the source of
        # truth for stacking, so re-apply it after the row moved to the top.
        self._apply_legend_z_order()
