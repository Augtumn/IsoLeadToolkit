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

logger = logging.getLogger(__name__)


from .legend_entries import build_legend_display_entries, reorder_legend_keys
from .legend_groups import MainWindowLegendGroupMixin
from .legend_interaction import MainWindowLegendInteractionMixin
from .legend_overlay import MainWindowLegendOverlayMixin
from .legend_styles import MainWindowLegendStyleMixin
from visualization.plotting.grouping import all_parents, parent_children
from core.legend_state import wants_docked_legend


def filter_legend_groups(
    groups: list,
    query: str,
    parent_children: dict[str, set] | None = None,
) -> list:
    """Groups matching the legend search box.

    No query shows every group - the panel used to display only the first 100 and
    silently hide the rest; with a query the labels and the parent-group names are
    searched.
    """
    text_query = str(query or "").strip().lower()
    if text_query:
        selected = []
        for group in groups:
            if text_query in str(group).lower():
                selected.append(group)
                continue
            for parent, children in (parent_children or {}).items():
                if text_query in str(parent).lower() and group in children:
                    selected.append(group)
                    break
        return selected

    return list(groups)


class MainWindowLegendActionsMixin(
    MainWindowLegendOverlayMixin,
    MainWindowLegendStyleMixin,
    MainWindowLegendGroupMixin,
    MainWindowLegendInteractionMixin,
):
    """Legend user interaction handlers and UI updates."""

    # ------------------------------------------------------------------
    # Parent group management (merge subgroups under one shape)
    # ------------------------------------------------------------------

    def _reload_legend_panel(self):
        title = app_state.legend_last_title
        handles = app_state.legend_last_handles
        labels = app_state.legend_last_labels
        if title and handles is not None and labels is not None:
            self._update_legend_panel(title, handles, labels)
        else:
            self._apply_legend_z_order()
        self._refresh_plot()

    def _on_legend_search_changed(self, _query=""):
        """Re-filter the legend list for the current search text."""
        payload = getattr(self, "_legend_panel_payload", None)
        if payload is None:
            return
        self._update_legend_panel(*payload)

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
            # Keep the last payload so the search box can re-filter without a
            # full re-render.
            self._legend_panel_payload = (title, handles, labels)
            self._apply_legend_panel_layout()
            location_key = app_state.legend_location
            if not wants_docked_legend(location_key):
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

            search_edit = getattr(self, "legend_search_edit", None)
            query = str(search_edit.text() or "") if search_edit is not None else ""
            parent_map = {
                parent: set(parent_children(app_state, parent))
                for parent in (app_state.parent_groups or {})
            }
            groups_to_show = filter_legend_groups(list(groups), query, parent_map)

            entries = []
            if has_groups:
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
            parents = all_parents(app_state)
            if parents:
                parent_names = set((app_state.parent_groups or {}).keys())
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
