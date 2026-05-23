"""Section dialog factory for menu-driven UI mode.

The legacy Qt5ControlPanel tabbed widget is removed; the application now
uses per-section dialogs created by :func:`create_section_dialog`.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QFrame, QLabel

from core import app_state, state_gateway, translate
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
    from PyQt5.QtWidgets import QApplication, QDialog, QHBoxLayout, QPushButton, QScrollArea, QVBoxLayout
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
    if parent is not None:
        dialog.setWindowModality(Qt.WindowModal)
    dialog.setWindowTitle(title)
    shortcuts = {"data": "Ctrl+D", "display": "Ctrl+Shift+D", "analysis": "Ctrl+Shift+A",
                 "export": "Ctrl+E", "legend": "Ctrl+L", "geochemistry": "Ctrl+G"}
    shortcut = shortcuts.get(section_key, "")
    dialog.setWindowTitle(f"{title}  ({shortcut})" if shortcut else title)
    dialog.resize(480, 400)

    root = QVBoxLayout(dialog)
    header = QHBoxLayout()
    title_label = QLabel(title)
    header.addWidget(title_label)
    header.addStretch()

    # Previous/Next panel navigation
    prev_btn = QPushButton("◀")
    prev_btn.setFixedWidth(28)
    prev_btn.setToolTip(translate("Previous Panel"))
    next_btn = QPushButton("▶")
    next_btn.setFixedWidth(28)
    next_btn.setToolTip(translate("Next Panel"))
    section_order = ['data', 'display', 'analysis', 'export', 'legend', 'geochemistry']
    current_idx = section_order.index(section_key) if section_key in section_order else -1
    if current_idx >= 0:
        prev_idx = (current_idx - 1) % len(section_order)
        next_idx = (current_idx + 1) % len(section_order)
        def _make_nav_handler(target_key, dlg):
            def _handler():
                dlg.close()
                if parent is not None and hasattr(parent, '_show_section_dialog'):
                    parent._show_section_dialog(target_key)
            return _handler
        prev_btn.clicked.connect(_make_nav_handler(section_order[prev_idx], dialog))
        next_btn.clicked.connect(_make_nav_handler(section_order[next_idx], dialog))
    header.addWidget(prev_btn)
    header.addWidget(next_btn)

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
            except AttributeError:
                logger.debug("Lightweight translation update failed, falling back to rebuild")
            except Exception as e:
                logger.warning("Lightweight translation update failed: %s", e)
                return
        _rebuild_section()

    def _refresh_titles():
        new_title = translate(title_key)
        dialog.setWindowTitle(new_title)

    def _on_show(_event):
        state_gateway.set_control_panel_ref(panel)
        try:
            panel.update_selection_controls()
        except Exception:
            pass
        QTimer.singleShot(0, _apply_adaptive_size)

    def _on_language_refresh():
        QTimer.singleShot(0, _refresh_titles)
        QTimer.singleShot(0, _try_lightweight_update)

    def _on_close(_event):
        if getattr(app_state, 'control_panel_ref', None) is panel:
            state_gateway.set_control_panel_ref(None)
        listeners = getattr(app_state, 'language_listeners', [])
        if _on_language_refresh in listeners:
            listeners.remove(_on_language_refresh)

    dialog.showEvent = _on_show
    dialog.closeEvent = _on_close
    try:
        app_state.register_language_listener(_on_language_refresh)
    except Exception:
        pass

    # Ctrl+Z 样式撤销快捷键
    from PyQt5.QtGui import QKeySequence
    from PyQt5.QtWidgets import QShortcut
    undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), dialog)
    undo_shortcut.activated.connect(
        lambda p=panel: p._undo_style() if hasattr(p, '_undo_style') else None
    )

    return dialog
