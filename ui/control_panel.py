"""Section dialog factory for menu-driven UI mode.

The legacy Qt5ControlPanel tabbed widget is removed; the application now
uses per-section dialogs created by :func:`create_section_dialog`.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QComboBox, QFrame, QLabel

from core import app_state, available_languages, state_gateway, translate
from ui.panels import (
    AnalysisPanel,
    DataPanel,
    DisplayPanel,
    ExportPanel,
    GeoPanel,
    LegendPanel,
)

logger = logging.getLogger(__name__)


def create_section_dialog(
    section_key: str | None,
    callback: Callable[[], None] | None,
    parent: Any = None,
) -> Any | None:
    """Create a dialog that hosts a single control section."""
    from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QScrollArea, QVBoxLayout
    from core import set_language

    section_key = (section_key or '').lower()

    section_map = {
        'data': ("Data", DataPanel),
        'display': ("Display", DisplayPanel),
        'analysis': ("Analysis", AnalysisPanel),
        'export': ("Export", ExportPanel),
        'legend': ("Legend", LegendPanel),
        'geochemistry': ("Geochemistry", GeoPanel),
    }

    if section_key not in section_map:
        return None

    title_key, panel_cls = section_map[section_key]
    title = translate(title_key)

    dialog = QDialog(parent)
    dialog.setWindowTitle(title)

    root = QVBoxLayout(dialog)
    header = QHBoxLayout()
    title_label = QLabel(title)
    header.addWidget(title_label)
    header.addStretch()

    lang_label = QLabel(translate("Language"))
    header.addWidget(lang_label)

    lang_combo = QComboBox()
    lang_combo.setFixedWidth(140)
    lang_map = dict(available_languages())
    for code, label in lang_map.items():
        lang_combo.addItem(label, code)
    current_lang = getattr(app_state, 'language', None)
    if current_lang:
        idx = lang_combo.findData(current_lang)
        if idx >= 0:
            lang_combo.setCurrentIndex(idx)
    header.addWidget(lang_combo)
    root.addLayout(header)

    panel = panel_cls(callback, parent=dialog)
    panel.reset_state()

    content_widget = panel.build()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidget(content_widget)
    root.addWidget(scroll, 1)

    def _apply_adaptive_size():
        dialog.adjustSize()
        hint = dialog.sizeHint()
        screen = dialog.screen() or QApplication.primaryScreen()
        if screen is None:
            dialog.resize(hint)
            return
        bounds = screen.availableGeometry()
        max_w = int(bounds.width() * 0.9)
        max_h = int(bounds.height() * 0.85)
        min_w = 420
        min_h = 280
        target_w = min(max(hint.width(), min_w), max_w)
        target_h = min(max(hint.height(), min_h), max_h)
        dialog.resize(target_w, target_h)

    def _rebuild_section():
        panel.reset_state()
        new_content = panel.build()
        scroll.takeWidget()
        scroll.setWidget(new_content)
        QTimer.singleShot(0, _apply_adaptive_size)

    def _try_lightweight_update():
        """Try lightweight translation update; fall back to full rebuild."""
        content_widget = scroll.widget()
        if content_widget is not None and hasattr(panel, '_update_translations'):
            try:
                panel._update_translations(content_widget)
                return
            except Exception:
                logger.debug("Lightweight translation update failed, falling back to rebuild")
        _rebuild_section()

    def _refresh_titles():
        new_title = translate(title_key)
        dialog.setWindowTitle(new_title)
        title_label.setText(new_title)
        lang_label.setText(translate("Language"))

    def _on_language_change(_index):
        code = lang_combo.currentData()
        if not code:
            return
        set_language(code)
        QTimer.singleShot(0, _refresh_titles)
        QTimer.singleShot(0, _try_lightweight_update)

    lang_combo.currentIndexChanged.connect(_on_language_change)

    _dialog_last_lang = [getattr(app_state, 'language', None)]

    def _on_show(_event):
        state_gateway.set_control_panel_ref(panel)
        try:
            panel.update_selection_controls()
        except Exception:
            pass
        listeners = getattr(app_state, 'language_listeners', [])
        if _on_language_refresh not in listeners:
            try:
                app_state.register_language_listener(_on_language_refresh)
            except Exception:
                pass
        current_lang = getattr(app_state, 'language', None)
        if current_lang != _dialog_last_lang[0]:
            _dialog_last_lang[0] = current_lang
            idx = lang_combo.findData(current_lang)
            if idx >= 0 and lang_combo.currentIndex() != idx:
                lang_combo.blockSignals(True)
                lang_combo.setCurrentIndex(idx)
                lang_combo.blockSignals(False)
            QTimer.singleShot(0, _refresh_titles)
            QTimer.singleShot(0, _try_lightweight_update)
        QTimer.singleShot(0, _apply_adaptive_size)

    def _on_language_refresh():
        current_lang = getattr(app_state, 'language', None)
        _dialog_last_lang[0] = current_lang
        if current_lang:
            idx = lang_combo.findData(current_lang)
            if idx >= 0 and lang_combo.currentIndex() != idx:
                lang_combo.blockSignals(True)
                lang_combo.setCurrentIndex(idx)
                lang_combo.blockSignals(False)
        QTimer.singleShot(0, _refresh_titles)
        QTimer.singleShot(0, _try_lightweight_update)

    def _on_close(_event):
        if getattr(app_state, 'control_panel_ref', None) is panel:
            state_gateway.set_control_panel_ref(None)
        _dialog_last_lang[0] = getattr(app_state, 'language', None)
        listeners = getattr(app_state, 'language_listeners', [])
        if _on_language_refresh in listeners:
            listeners.remove(_on_language_refresh)

    dialog.showEvent = _on_show
    dialog.closeEvent = _on_close
    try:
        app_state.register_language_listener(_on_language_refresh)
    except Exception:
        pass

    return dialog
