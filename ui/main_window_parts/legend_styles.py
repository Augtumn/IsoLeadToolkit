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
REQUIRES_MainWindowLegendStyleMixin = (
    "_build_marker_icon",
    "_ensure_marker_shape_map",
    "_refresh_plot",
    "_reload_legend_panel",
    "_update_marker_swatch",
)

logger = logging.getLogger(__name__)


class MainWindowLegendStyleMixin:
    """Colour and shape editing for legend entries."""

    def _pick_color(self, group, swatch):
        current_color = app_state.current_palette.get(group, "#cccccc")
        color = QColorDialog.getColor(QColor(current_color), self, f"Color for {group}")
        if color.isValid():
            new_hex = color.name()
            updated_palette = dict(app_state.current_palette or {})
            updated_palette[group] = new_hex
            marker_map = dict(app_state.group_marker_map or {})
            state_gateway.set_palette_and_marker_map(updated_palette, marker_map)
            self._update_marker_swatch(group, swatch)

            if group in app_state.group_to_scatter:
                sc = app_state.group_to_scatter[group]
                try:
                    sc.set_color(new_hex)
                    sc.set_edgecolor("#1e293b")
                    if app_state.fig:
                        app_state.fig.canvas.draw_idle()
                except Exception as exc:
                    logger.warning("Failed to update color for %s: %s", group, exc)

    def _set_group_shape_value(self, group, marker_value, swatch):
        self._ensure_marker_shape_map()
        marker = marker_value or app_state.plot_marker_shape
        updated_marker_map = dict(app_state.group_marker_map or {})
        updated_marker_map[group] = marker
        palette = dict(app_state.current_palette or {})
        state_gateway.set_palette_and_marker_map(palette, updated_marker_map)
        self._update_marker_swatch(group, swatch)
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
            current_marker = app_state.group_marker_map.get(group, app_state.plot_marker_shape)
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
        mapping = dict(app_state.parent_shape_map or {})
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
        manual = bool((app_state.parent_shape_map or {}).get(parent))

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
