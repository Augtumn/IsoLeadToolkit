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
    QPushButton,
    QSizePolicy,
    QWidget,
)

from core import app_state, state_gateway, translate
from ui.icons import apply_color_swatch
from visualization.line_styles import resolve_line_style
from visualization.plotting.legend_model import OVERLAY_TOGGLE_MAP

logger = logging.getLogger(__name__)


def reorder_legend_keys(
    order_keys: list[str],
    src_full: str,
    target_full: str,
    below: bool,
) -> list[str]:
    """Return the reordered ``legend_item_order`` list after a drag.

    *src_full* is moved to the position of *target_full* (before it, or
    after it when *below*). Rows are identified by their full
    ``type:key`` order keys. No-op when either key is unknown.
    """
    order = list(order_keys)
    if src_full not in order or target_full not in order or src_full == target_full:
        return order
    order.remove(src_full)
    idx = order.index(target_full)
    if below:
        idx += 1
    order.insert(idx, src_full)
    return order


def build_legend_display_entries(
    entries: list[dict[str, Any]],
    top_parents: list[str],
    child_parent: dict[str, str],
    parent_names: set[str],
    order_index: dict[str, int],
) -> list[dict[str, Any]]:
    """Build the ordered legend display list with (possibly nested) parent blocks.

    Every visual unit participates in one unified ordering: a TOP-LEVEL parent
    block (its rows expanded recursively, children may themselves be parent
    groups at deeper indentation), an independent group, or an overlay. Units
    sort by their own ``legend_item_order`` position, so independent groups
    may be dragged above parent blocks. Children inside a block keep their
    own relative order.

    Args:
        entries: sorted group/overlay entries (groups carry "group" key).
        top_parents: top-level parent names (not nested inside another parent).
        child_parent: direct child name -> direct parent name (all levels).
        parent_names: set of ALL parent names (nested included).
        order_index: legend_item_order lookup.
    """
    if not top_parents:
        return list(entries)

    by_parent: dict[str, list[str]] = {}
    for child, parent in child_parent.items():
        by_parent.setdefault(parent, []).append(child)

    def _block(parent: str, depth: int) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = [
            {"type": "parent", "key": parent, "parent": parent, "depth": depth}
        ]
        children = sorted(
            by_parent.get(parent, []),
            key=lambda c: order_index.get(f"group:{c}", 10_000),
        )
        for child in children:
            if child in parent_names:
                out.extend(_block(child, depth + 1))
            else:
                out.append(
                    {
                        "type": "group",
                        "key": child,
                        "group": child,
                        "in_parent": parent,
                        "depth": depth + 1,
                    }
                )
        return out

    # Unified sort units: (order_index, unit_kind, payload).
    units: list[tuple[int, str, Any]] = []
    for parent in top_parents:
        units.append((order_index.get(f"parent:{parent}", 10_000), "parent", parent))
    for entry in entries:
        if entry["type"] == "group" and entry["group"] not in child_parent:
            units.append((order_index.get(f"group:{entry['group']}", 10_000), "group", entry))
        elif entry["type"] == "overlay":
            units.append((order_index.get(f"overlay:{entry['key']}", 10_000), "overlay", entry))

    # Stable sort: units with equal order keep their construction order.
    units.sort(key=lambda unit: unit[0])

    display_entries: list[dict[str, Any]] = []
    for _, unit_kind, payload in units:
        if unit_kind == "parent":
            display_entries.extend(_block(payload, 0))
        else:
            display_entries.append(payload)
    return display_entries


class MainWindowLegendActionsMixin:
    """Legend user interaction handlers and UI updates."""

    def _open_line_style_dialog(self, style_key, swatch):
        from ui.dialogs.line_style_dialog import open_line_style_dialog

        open_line_style_dialog(self, style_key, swatch=swatch, on_applied=self._refresh_plot)

    def _add_overlay_legend_item(self, label_key, style_key, default_color=None, fallback=None):
        item_widget = QWidget()
        item_layout = QHBoxLayout()
        item_layout.setContentsMargins(4, 2, 4, 2)
        item_layout.setSpacing(6)

        style = getattr(app_state, "line_styles", {}).get(style_key, {}) or {}
        swatch_color = style.get("color")
        if not swatch_color and fallback:
            resolved = resolve_line_style(app_state, style_key, fallback)
            swatch_color = resolved.get("color")
        if not swatch_color:
            swatch_color = default_color or "#e2e8f0"

        swatch = QPushButton()
        swatch.setFixedSize(22, 22)
        apply_color_swatch(swatch, swatch_color, marker="s", icon_size=16)
        swatch.setCursor(QCursor(Qt.PointingHandCursor))
        swatch.clicked.connect(lambda checked=False, k=style_key, btn=swatch: self._open_line_style_dialog(k, btn))
        item_layout.addWidget(swatch)

        checkbox = QCheckBox()
        checkbox.setChecked(self._overlay_checked_state(style_key))
        checkbox.stateChanged.connect(lambda state, k=style_key: self._on_overlay_checkbox_change(k, state))
        checkbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        checkbox.setFixedWidth(18)
        item_layout.addWidget(checkbox)

        label = QLabel(translate(label_key))
        item_layout.addWidget(label, 1)
        item_layout.addStretch()

        item_widget.setLayout(item_layout)

        item = QListWidgetItem()
        item.setSizeHint(item_widget.sizeHint())
        self._set_legend_item_meta(item, "overlay", style_key)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
        self._legend_list.addItem(item)
        self._legend_list.setItemWidget(item, item_widget)

    def _on_overlay_checkbox_change(self, style_key, state):
        checked = state == Qt.Checked
        if self._is_plumbotectonics_group_style(style_key):
            if not hasattr(app_state, "plumbotectonics_group_visibility"):
                state_gateway.set_plumbotectonics_group_visibility({})
            visibility = getattr(app_state, "plumbotectonics_group_visibility", {}) or {}
            visibility[style_key] = checked
            state_gateway.set_plumbotectonics_group_visibility(visibility)
            self._refresh_plot()
            return
        if style_key == "isochron":
            if checked:
                state_gateway.set_show_isochrons(True)
                try:
                    selected = getattr(app_state, "selected_indices", set()) or set()
                    if app_state.render_mode == "PB_EVOL_76" and len(selected) >= 2:
                        from visualization.events import calculate_selected_isochron

                        calculate_selected_isochron()
                except Exception as err:
                    logger.warning("Failed to calculate selected isochron: %s", err)
            else:
                state_gateway.set_show_isochrons(False)
                state_gateway.set_selected_isochron_data(None)
                state_gateway.set_isochron_results({})

            self._sync_geochem_toggle_panels(style_key)
            self._refresh_plot()
            return
        attr = OVERLAY_TOGGLE_MAP.get(style_key)
        if attr:
            state_gateway.set_overlay_toggle(attr, checked)

        if style_key == "isochron" and not checked:
            state_gateway.set_selected_isochron_data(None)
            state_gateway.set_isochron_results({})

        self._sync_geochem_toggle_panels(style_key)
        self._refresh_plot()

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

    def _bring_overlay_to_front(self, style_key):
        ax = getattr(app_state, "ax", None)
        if ax is None:
            return
        overlay_map = getattr(app_state, "overlay_artists", {}) or {}
        artists = self._overlay_artists_for_style(style_key, overlay_map=overlay_map)
        if not artists:
            return

        max_z = 2
        try:
            for artist in ax.get_children():
                try:
                    max_z = max(max_z, artist.get_zorder())
                except Exception:
                    continue
        except Exception:
            pass

        target_z = max_z + 1
        for artist in artists:
            try:
                z_value = target_z + 0.25 if hasattr(artist, "get_text") else target_z
                artist.set_zorder(z_value)
            except Exception:
                pass

        if app_state.fig is not None and app_state.fig.canvas is not None:
            app_state.fig.canvas.draw_idle()
        self._move_legend_item_to_top("overlay", style_key)

    def _pick_color(self, group, swatch):
        current_color = app_state.current_palette.get(group, "#cccccc")
        color = QColorDialog.getColor(QColor(current_color), self, f"Color for {group}")
        if color.isValid():
            new_hex = color.name()
            updated_palette = dict(getattr(app_state, "current_palette", {}) or {})
            updated_palette[group] = new_hex
            marker_map = dict(getattr(app_state, "group_marker_map", {}) or {})
            state_gateway.set_palette_and_marker_map(updated_palette, marker_map)
            self._update_marker_swatch(group, swatch)

            if hasattr(app_state, "group_to_scatter") and group in app_state.group_to_scatter:
                sc = app_state.group_to_scatter[group]
                try:
                    sc.set_color(new_hex)
                    sc.set_edgecolor("#1e293b")
                    if app_state.fig:
                        app_state.fig.canvas.draw_idle()
                except Exception as exc:
                    logger.warning("Failed to update color for %s: %s", group, exc)
            self._sync_legend_panel_ui(refresh=True)

    def _set_group_shape_value(self, group, marker_value, swatch):
        self._ensure_marker_shape_map()
        marker = marker_value or getattr(app_state, "plot_marker_shape", "o")
        updated_marker_map = dict(getattr(app_state, "group_marker_map", {}) or {})
        updated_marker_map[group] = marker
        palette = dict(getattr(app_state, "current_palette", {}) or {})
        state_gateway.set_palette_and_marker_map(palette, updated_marker_map)
        self._update_marker_swatch(group, swatch)
        self._sync_legend_panel_ui(refresh=True)
        self._refresh_plot()

    def _show_color_shape_menu(self, group, swatch):
        from visualization.plotting.grouping import parent_of_group, parent_shape

        self._ensure_marker_shape_map()
        menu = QMenu(self)

        parent = parent_of_group(app_state, group)
        color_action = QAction(translate("Color..."), self)
        color_action.triggered.connect(lambda checked=False, g=group, btn=swatch: self._pick_color(g, btn))
        menu.addAction(color_action)

        shape_menu = menu.addMenu(translate("Shape"))
        if parent is not None:
            # Children of a parent group share the parent's shape; keep the
            # menu visible but disabled so the rule stays discoverable.
            parent_marker = parent_shape(app_state, parent)
            locked_action = QAction(
                translate("Shape follows parent group ({marker})").format(marker=parent_marker),
                self,
            )
            locked_action.setEnabled(False)
            shape_menu.addAction(locked_action)
        else:
            current_marker = app_state.group_marker_map.get(group, getattr(app_state, "plot_marker_shape", "o"))
            for label, value in self._marker_shape_map.items():
                icon = self._build_marker_icon("#94a3b8", value, size=14)
                action = QAction(icon, label, self)
                action.setToolTip(label)
                action.setCheckable(True)
                action.setChecked(value == current_marker)
                action.triggered.connect(
                    lambda checked=False, g=group, v=value, btn=swatch: self._set_group_shape_value(g, v, btn)
                )
                shape_menu.addAction(action)

        menu.exec_(QCursor.pos())

    # ------------------------------------------------------------------
    # Parent group management (merge subgroups under one shape)
    # ------------------------------------------------------------------

    def _current_parent_groups(self):
        return {
            str(k): list(v or []) for k, v in (getattr(app_state, "parent_groups", {}) or {}).items()
        }

    def _reload_legend_panel(self):
        title = getattr(app_state, "legend_last_title", None)
        handles = getattr(app_state, "legend_last_handles", None)
        labels = getattr(app_state, "legend_last_labels", None)
        if title and handles is not None and labels is not None:
            self._update_legend_panel(title, handles, labels)
        else:
            self._apply_legend_z_order()
        self._refresh_plot()

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
            translate("New Child Parent Group"),
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
        title = getattr(app_state, "legend_last_title", None)
        handles = getattr(app_state, "legend_last_handles", None)
        labels = getattr(app_state, "legend_last_labels", None)
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

        self._sync_legend_panel_ui()
        self._refresh_plot()

    def _bring_to_front(self, group):
        if hasattr(app_state, "group_to_scatter") and group in app_state.group_to_scatter:
            sc = app_state.group_to_scatter[group]
            try:
                max_z = 2
                if hasattr(app_state, "scatter_collections"):
                    for c in app_state.scatter_collections:
                        max_z = max(max_z, c.get_zorder())

                sc.set_zorder(max_z + 1)
                if app_state.fig:
                    app_state.fig.canvas.draw_idle()
            except Exception as exc:
                logger.warning("Failed to bring %s to front: %s", group, exc)
        self._move_legend_item_to_top("group", group)

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

    def _update_parent_swatch(self, parent, swatch):
        from visualization.plotting.grouping import parent_shape

        marker = parent_shape(app_state, parent)
        icon = self._build_marker_icon("#94a3b8", marker, size=16)
        swatch.setIcon(icon)
        swatch.setIconSize(QSize(16, 16))
        swatch.setProperty("keepStyle", True)  # survive _NativeStyleFilter
        swatch.setStyleSheet("border: 1px solid #111827; border-radius: 3px; background: transparent;")

    def _set_parent_shape(self, parent, marker):
        """Apply a manual shape override for a parent group ('' = auto)."""
        mapping = dict(getattr(app_state, "parent_shape_map", {}) or {})
        if marker:
            mapping[parent] = marker
        else:
            mapping.pop(parent, None)
        state_gateway.set_parent_shape_map(mapping)
        self._reload_legend_panel()

    def _show_parent_shape_menu(self, parent, swatch):
        from visualization.plotting.grouping import PARENT_SHAPE_CYCLE, parent_shape

        menu = QMenu(self)
        current = parent_shape(app_state, parent)
        manual = bool((getattr(app_state, "parent_shape_map", {}) or {}).get(parent))

        auto_action = QAction(translate("Auto (by order)"), self)
        auto_action.setCheckable(True)
        auto_action.setChecked(not manual)
        auto_action.triggered.connect(
            lambda checked=False, p=parent: self._set_parent_shape(p, "")
        )
        menu.addAction(auto_action)
        menu.addSeparator()

        for value in PARENT_SHAPE_CYCLE:
            icon = self._build_marker_icon("#94a3b8", value, size=14)
            label = next(
                (k for k, v in self._marker_shape_map.items() if v == value),
                value,
            )
            action = QAction(icon, label, self)
            action.setToolTip(label)
            action.setCheckable(True)
            action.setChecked(value == current)
            action.triggered.connect(
                lambda checked=False, p=parent, v=value, btn=swatch: self._set_parent_shape(p, v)
            )
            menu.addAction(action)

        menu.exec_(QCursor.pos())

    def _open_legend_settings(self):
        """Open the full legend settings dialog (same as Ctrl+L)."""
        try:
            self._show_section_dialog("legend")
        except Exception as exc:
            logger.warning("Failed to open legend settings: %s", exc)

    def _update_legend_panel(self, title, handles, labels):
        try:
            if not hasattr(self, "_legend_list") or self._legend_list is None:
                return
            self._apply_legend_panel_layout()
            location_key = getattr(app_state, "legend_location", None)
            if location_key not in {"outside_left", "outside_right"}:
                return

            if self._legend_title_label is not None:
                self._legend_title_label.setText(str(title))

            # Preserve the scroll position across rebuilds (checkbox toggles
            # rebuild the whole list and would otherwise reset the view).
            scrollbar = self._legend_list.verticalScrollBar()
            previous_scroll = scrollbar.value() if scrollbar is not None else 0

            self._legend_list.clear()

            has_groups = (
                app_state.last_group_col
                and app_state.df_global is not None
                and app_state.last_group_col in app_state.df_global.columns
            )
            groups = []
            if has_groups:
                groups = list(app_state.df_global[app_state.last_group_col].unique())
            overlay_entries = self._overlay_entries_for_legend()

            entries = []
            if has_groups:
                max_items = 100
                groups_to_show = list(groups)[:max_items]
                if len(groups) > max_items:
                    logger.warning("Showing first %d groups only.", max_items)
                for group in groups_to_show:
                    entries.append({"type": "group", "key": group, "group": group})
            for overlay_entry in overlay_entries:
                entries.append(
                    {
                        "type": "overlay",
                        "key": overlay_entry["style_key"],
                        "label_key": overlay_entry["label_key"],
                        "default_color": overlay_entry.get("default_color"),
                        "fallback": overlay_entry.get("fallback"),
                    }
                )

            order_keys = getattr(app_state, "legend_item_order", []) or []
            order_index = {key: idx for idx, key in enumerate(order_keys)}
            entries.sort(key=lambda e: order_index.get(self._legend_order_key(e["type"], e["key"]), 10_000))

            if has_groups:
                self._ensure_marker_shape_map()
                visible = set(app_state.visible_groups) if app_state.visible_groups is not None else set(groups)

            # Interleave parent rows before their children so the merge
            # structure is visible and draggable groups can be dropped on
            # them. Parent blocks follow the parent's legend_item_order
            # position; nested parents expand recursively inside their
            # ancestor's block.
            from visualization.plotting.grouping import all_parents, parent_children

            parents = all_parents(app_state)
            if parents:
                parent_names = set((getattr(app_state, "parent_groups", {}) or {}).keys())
                child_parent: dict[str, str] = {
                    child: parent
                    for parent in parent_names
                    for child in parent_children(app_state, parent)
                }
                entries = build_legend_display_entries(
                    entries, parents, child_parent, parent_names, order_index
                )

            for entry in entries:
                if entry["type"] == "parent":
                    self._add_parent_legend_item(entry["parent"], depth=entry.get("depth", 0))
                elif entry["type"] == "group":
                    group = entry["group"]
                    in_parent = entry.get("in_parent")
                    depth = int(entry.get("depth", 1) if in_parent else 0)
                    item_widget = QWidget()
                    item_layout = QHBoxLayout()
                    # Children of a parent group are indented by nesting level.
                    left_margin = 4 + 24 * depth
                    item_layout.setContentsMargins(left_margin, 2, 4, 2)
                    item_layout.setSpacing(6)

                    color_btn = QPushButton()
                    color_btn.setFixedSize(22, 22)
                    self._update_marker_swatch(group, color_btn)
                    color_btn.setCursor(QCursor(Qt.PointingHandCursor))
                    color_btn.clicked.connect(
                        lambda checked=False, g=group, btn=color_btn: self._show_color_shape_menu(g, btn)
                    )
                    item_layout.addWidget(color_btn)

                    checkbox = QCheckBox()
                    checkbox.setChecked(group in visible)
                    checkbox.stateChanged.connect(lambda state, g=group: self._on_group_checkbox_change(g, state))
                    checkbox.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                    checkbox.setFixedWidth(18)
                    item_layout.addWidget(checkbox)

                    label = QLabel(str(group))
                    if in_parent:
                        label.setToolTip(
                            translate("In parent group {parent}").format(parent=in_parent)
                        )
                    item_layout.addWidget(label, 1)
                    item_layout.addStretch()

                    item_widget.setLayout(item_layout)

                    item = QListWidgetItem()
                    item.setSizeHint(item_widget.sizeHint())
                    self._set_legend_item_meta(item, "group", group)
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
                    self._legend_list.addItem(item)
                    self._legend_list.setItemWidget(item, item_widget)
                elif entry["type"] == "overlay":
                    self._add_overlay_legend_item(
                        entry["label_key"],
                        entry["key"],
                        default_color=entry.get("default_color"),
                        fallback=entry.get("fallback"),
                    )
            self._apply_legend_z_order()
            if scrollbar is not None:
                scrollbar.setValue(previous_scroll)
        except Exception as exc:
            import traceback

            logger.error("Legend panel update failed: %s", exc)
            traceback.print_exc()
