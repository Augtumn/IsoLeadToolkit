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


class MainWindowLegendOverlayMixin:
    """Overlay legend entries: creation, visibility and stacking."""

    def _open_line_style_dialog(self, style_key, swatch):
        from ui.panels.display.dialogs.line_style_dialog import open_line_style_dialog

        open_line_style_dialog(self, style_key, swatch=swatch, on_applied=self._refresh_plot)

    def _add_overlay_legend_item(self, label_key, style_key, default_color=None, fallback=None):
        item_widget = QWidget()
        item_layout = QHBoxLayout()
        item_layout.setContentsMargins(4, 2, 4, 2)
        item_layout.setSpacing(6)

        style = app_state.line_styles.get(style_key, {}) or {}
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
            visibility = app_state.plumbotectonics_group_visibility or {}
            visibility[style_key] = checked
            state_gateway.set_plumbotectonics_group_visibility(visibility)
            self._refresh_plot()
            return
        if style_key == "isochron":
            if checked:
                state_gateway.set_show_isochrons(True)
                try:
                    selected = app_state.selected_indices or set()
                    if app_state.render_mode == "PB_EVOL_76" and len(selected) >= 2:
                        from visualization.events import calculate_selected_isochron

                        calculate_selected_isochron()
                except Exception as err:
                    logger.warning("Failed to calculate selected isochron: %s", err)
            else:
                state_gateway.set_show_isochrons(False)
                state_gateway.set_selected_isochron_data(None)
                state_gateway.set_isochron_results({})

            self._refresh_plot()
            return
        attr = OVERLAY_TOGGLE_MAP.get(style_key)
        if attr:
            state_gateway.set_overlay_toggle(attr, checked)

        if style_key == "isochron" and not checked:
            state_gateway.set_selected_isochron_data(None)
            state_gateway.set_isochron_results({})

        self._refresh_plot()

    def _bring_overlay_to_front(self, style_key):
        ax = app_state.ax
        if ax is None:
            return
        overlay_map = app_state.overlay_artists or {}
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
