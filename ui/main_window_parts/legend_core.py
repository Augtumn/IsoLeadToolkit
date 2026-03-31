"""Core legend ordering and state helpers for main window."""

import logging
import os

from PyQt5.QtCore import QSize, Qt, QTimer

from core import app_state, state_gateway, translate
from ui.icons import build_marker_icon
from visualization.plotting.legend_model import OVERLAY_TOGGLE_MAP, normalize_render_mode, overlay_legend_items

logger = logging.getLogger(__name__)
QT_DEBUG_MODE = os.environ.get("ISOTOPES_QT_DEBUG", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


class MainWindowLegendCoreMixin:
    """Legend model helpers shared by legend UI actions."""

    def _build_marker_icon(self, color, marker, size=14):
        return build_marker_icon(color, marker, size)

    def _ensure_marker_shape_map(self):
        if not hasattr(self, "_marker_shape_map"):
            self._marker_shape_map = {
                translate("Point (.)"): ".",
                translate("Pixel (,)"): ",",
                translate("Circle (o)"): "o",
                translate("Triangle Down (v)"): "v",
                translate("Triangle Up (^)"): "^",
                translate("Triangle Left (<)"): "<",
                translate("Triangle Right (>)"): ">",
                translate("Tri Down (1)"): "1",
                translate("Tri Up (2)"): "2",
                translate("Tri Left (3)"): "3",
                translate("Tri Right (4)"): "4",
                translate("Octagon (8)"): "8",
                translate("Square (s)"): "s",
                translate("Pentagon (p)"): "p",
                translate("Plus Filled (P)"): "P",
                translate("Star (*)"): "*",
                translate("Hexagon 1 (h)"): "h",
                translate("Hexagon 2 (H)"): "H",
                translate("Diamond (D)"): "D",
                translate("Plus (+)"): "+",
                translate("Cross (x)"): "x",
                translate("X (X)"): "X",
                translate("Thin Diamond (d)"): "d",
                translate("Vline (|)"): "|",
                translate("Hline (_)"): "_",
            }

    def _overlay_entries_for_legend(self):
        mode = normalize_render_mode(getattr(app_state, "render_mode", ""))
        return list(overlay_legend_items(render_mode=mode, include_disabled=True))

    def _is_plumbotectonics_group_style(self, style_key):
        return isinstance(style_key, str) and style_key.startswith("plumbotectonics_curve:")

    def _legend_order_key(self, entry_type, key):
        return f"{entry_type}:{key}"

    def _set_legend_item_meta(self, item, entry_type, key):
        if item is None:
            return
        item.setData(Qt.UserRole, {"type": entry_type, "key": key})

    def _overlay_artists_for_style(self, style_key, overlay_map=None):
        if overlay_map is None:
            overlay_map = getattr(app_state, "overlay_artists", {}) or {}
        artists = []

        def _extend_artists(value):
            if value is None:
                return
            if isinstance(value, dict):
                for nested in value.values():
                    _extend_artists(nested)
                return
            if isinstance(value, (list, tuple, set)):
                for artist in value:
                    if artist is not None:
                        artists.append(artist)
                return
            artists.append(value)

        _extend_artists(overlay_map.get(style_key))

        style_to_category = {
            "model_curve": "model_curves",
            "plumbotectonics_curve": "plumbotectonics_curves",
            "paleoisochron": "paleoisochrons",
            "model_age_line": "model_age_lines",
            "isochron": "isochrons",
            "growth_curve": "growth_curves",
        }
        category_key = style_to_category.get(style_key)
        if category_key:
            _extend_artists(overlay_map.get(category_key))

        if style_key == "isochron":
            _extend_artists(overlay_map.get("selected_isochron"))

        def _extend_text_artists(entries):
            for entry in entries or []:
                if not isinstance(entry, dict):
                    continue
                if entry.get("style_key") != style_key:
                    continue
                text_artist = entry.get("text")
                if text_artist is not None:
                    artists.append(text_artist)

        _extend_text_artists(getattr(app_state, "overlay_curve_label_data", []))
        if style_key == "paleoisochron":
            _extend_text_artists(getattr(app_state, "paleoisochron_label_data", []))
            _extend_text_artists(getattr(app_state, "plumbotectonics_isoage_label_data", []))
            _extend_text_artists(getattr(app_state, "plumbotectonics_label_data", []))

        if not artists:
            return []

        unique = []
        seen = set()
        for artist in artists:
            aid = id(artist)
            if aid in seen:
                continue
            seen.add(aid)
            unique.append(artist)
        return unique

    def _apply_legend_z_order(self):
        if not hasattr(self, "_legend_list") or self._legend_list is None:
            return
        ax = getattr(app_state, "ax", None)
        if ax is None:
            return

        order = []
        for i in range(self._legend_list.count()):
            item = self._legend_list.item(i)
            meta = item.data(Qt.UserRole)
            if not meta:
                continue
            entry_type = meta.get("type")
            entry_key = meta.get("key")
            if entry_type and entry_key is not None:
                order.append((entry_type, entry_key))

        if not order:
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

        target_z = max_z + len(order)
        overlay_map = getattr(app_state, "overlay_artists", {}) or {}
        group_map = getattr(app_state, "group_to_scatter", {}) or {}

        for entry_type, entry_key in order:
            if entry_type == "group":
                artist = group_map.get(entry_key)
                if artist is not None:
                    try:
                        artist.set_zorder(target_z)
                    except Exception:
                        pass
            elif entry_type == "overlay":
                for artist in self._overlay_artists_for_style(entry_key, overlay_map=overlay_map):
                    try:
                        z_value = target_z + 0.25 if hasattr(artist, "get_text") else target_z
                        artist.set_zorder(z_value)
                    except Exception:
                        pass
            target_z -= 1

        state_gateway.set_attr(
            "legend_item_order",
            [self._legend_order_key(entry_type, entry_key) for entry_type, entry_key in order],
        )

        if app_state.fig is not None and app_state.fig.canvas is not None:
            app_state.fig.canvas.draw_idle()

    def _on_legend_rows_moved(self, *args):
        QTimer.singleShot(0, self._rebuild_legend_after_reorder)

    def _rebuild_legend_after_reorder(self):
        self._apply_legend_z_order()
        title = getattr(app_state, "legend_last_title", None)
        handles = getattr(app_state, "legend_last_handles", None)
        labels = getattr(app_state, "legend_last_labels", None)
        if not title or handles is None or labels is None:
            return
        self._update_legend_panel(title, handles, labels)

    def _move_legend_item_to_top(self, entry_type, entry_key):
        if not hasattr(self, "_legend_list") or self._legend_list is None:
            return
        if QT_DEBUG_MODE:
            logger.debug("Move legend item to top: type=%s key=%s", entry_type, entry_key)
        order = []
        target = (entry_type, entry_key)
        for i in range(self._legend_list.count()):
            item = self._legend_list.item(i)
            meta = item.data(Qt.UserRole)
            if not meta:
                continue
            current_type = meta.get("type")
            current_key = meta.get("key")
            if current_type and current_key is not None:
                order.append((current_type, current_key))

        if not order:
            return
        if order[0] == target or target not in order:
            return

        new_order = [target] + [entry for entry in order if entry != target]
        state_gateway.set_attr(
            "legend_item_order",
            [self._legend_order_key(current_type, current_key) for current_type, current_key in new_order],
        )

        title = getattr(app_state, "legend_last_title", None)
        handles = getattr(app_state, "legend_last_handles", None)
        labels = getattr(app_state, "legend_last_labels", None)
        if title and handles is not None and labels is not None:
            self._update_legend_panel(title, handles, labels)
        else:
            self._apply_legend_z_order()

    def _overlay_checked_state(self, style_key):
        if self._is_plumbotectonics_group_style(style_key):
            visibility = getattr(app_state, "plumbotectonics_group_visibility", {}) or {}
            return bool(getattr(app_state, "show_plumbotectonics_curves", True) and visibility.get(style_key, True))
        attr = OVERLAY_TOGGLE_MAP.get(style_key)
        if attr:
            return bool(getattr(app_state, attr, True))
        if style_key == "isochron":
            return bool(getattr(app_state, "show_isochrons", False) or getattr(app_state, "selected_isochron_data", None))
        return True

    def _sync_geochem_toggle_panels(self, style_key):
        panel = getattr(app_state, "control_panel_ref", None)
        data_panel = getattr(panel, "data_panel", None) if panel is not None else None
        if data_panel is None:
            return
        try:
            if style_key == "model_curve":
                data_panel._sync_geochem_toggle_widgets(
                    app_state.show_model_curves,
                    getattr(data_panel, "modeling_show_model_check", None),
                    getattr(data_panel, "show_model_check", None),
                )
            elif style_key == "plumbotectonics_curve":
                data_panel._sync_geochem_toggle_widgets(
                    app_state.show_plumbotectonics_curves,
                    getattr(data_panel, "modeling_show_plumbotectonics_check", None),
                )
            elif style_key == "paleoisochron":
                data_panel._sync_geochem_toggle_widgets(
                    app_state.show_paleoisochrons,
                    getattr(data_panel, "modeling_show_paleoisochron_check", None),
                    getattr(data_panel, "show_paleoisochron_check", None),
                )
            elif style_key == "model_age_line":
                data_panel._sync_geochem_toggle_widgets(
                    app_state.show_model_age_lines,
                    getattr(data_panel, "modeling_show_model_age_check", None),
                    getattr(data_panel, "show_model_age_check", None),
                )
            elif style_key == "isochron":
                data_panel._sync_geochem_toggle_widgets(
                    app_state.show_isochrons,
                    getattr(data_panel, "modeling_show_isochron_check", None),
                    getattr(data_panel, "show_isochron_check", None),
                )
                if hasattr(data_panel, "_update_isochron_btn_text"):
                    data_panel._update_isochron_btn_text()
            elif style_key == "growth_curve":
                data_panel._sync_geochem_toggle_widgets(
                    app_state.show_growth_curves,
                    getattr(data_panel, "modeling_show_growth_curve_check", None),
                )
        except Exception:
            pass

    def _update_marker_swatch(self, group, swatch):
        color = app_state.current_palette.get(group, "#cccccc")
        marker = app_state.group_marker_map.get(group, getattr(app_state, "plot_marker_shape", "o"))
        icon = self._build_marker_icon(color, marker, size=16)
        swatch.setIcon(icon)
        swatch.setIconSize(QSize(16, 16))
        swatch.setStyleSheet("border: 1px solid #111827; border-radius: 3px; background: transparent;")

    def _sync_legend_panel_ui(self, refresh=False):
        panel = getattr(app_state, "control_panel_ref", None)
        if panel is None or not hasattr(panel, "legend_checkboxes"):
            return
        try:
            if refresh and hasattr(panel, "_update_group_list"):
                panel._update_group_list()
            elif hasattr(panel, "sync_legend_ui"):
                panel.sync_legend_ui()
        except Exception:
            pass
