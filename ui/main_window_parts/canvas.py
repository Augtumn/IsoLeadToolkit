"""Canvas and toolbar integration mixin for main window."""
from __future__ import annotations

import logging
from pathlib import Path

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QStyle

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


class MainWindowCanvasMixin:
    """Canvas and toolbar behavior for main window."""

    def set_matplotlib_figure(self, fig):
        """设置 matplotlib 图形"""
        for i in reversed(range(self.canvas_layout.count())):
            widget = self.canvas_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(canvas, self)
        toolbar.setVisible(False)  # Keep hidden; actions are extracted below

        rect_select_action = QAction(self._get_selection_icon("selection_rect.svg"), translate("Box Select"), self)
        rect_select_action.setToolTip(translate("Box Select"))
        rect_select_action.setCheckable(True)
        rect_select_action.triggered.connect(lambda: self._toggle_selection_tool("rect"))

        lasso_select_action = QAction(
            self._get_selection_icon("selection_polygon.svg"), translate("Lasso Select"), self
        )
        lasso_select_action.setToolTip(translate("Lasso Select"))
        lasso_select_action.setCheckable(True)
        lasso_select_action.triggered.connect(lambda: self._toggle_selection_tool("lasso"))

        toolbar.addSeparator()
        toolbar.addAction(rect_select_action)
        toolbar.addAction(lasso_select_action)

        self._selection_tool_actions = {
            "rect": rect_select_action,
            "lasso": lasso_select_action,
        }
        self._sync_selection_tool_actions()

        # Copy NavigationToolbar actions to main toolbar, translating tooltips
        _MPL_TOOLTIP_TRANSLATIONS = {
            "Home": "Reset original view",
            "Back": "Back to previous view",
            "Forward": "Forward to next view",
            "Pan": "Pan axes with left mouse, zoom with right",
            "Zoom": "Zoom to rectangle",
            "Subplots": "Configure subplots",
            "Save": "Save the figure",
        }
        for action in toolbar.actions():
            if action is None:
                continue
            self.toolbar.addAction(action)
            text = (action.text() or "").strip()
            for en_key, tr_key in _MPL_TOOLTIP_TRANSLATIONS.items():
                if en_key.lower() in text.lower():
                    action.setToolTip(translate(tr_key))
                    break

        self.canvas_layout.addWidget(canvas)

        state_gateway.set_figure(fig)
        state_gateway.set_canvas(canvas)

        self._connect_event_handlers(canvas)

    def _get_selection_icon(self, filename):
        """Resolve selection tool icon from assets."""
        base_dir = Path(__file__).resolve().parent.parent.parent
        svg_path = base_dir / "assets" / "icons" / filename
        if svg_path.exists():
            icon = QIcon(str(svg_path))
            if not icon.isNull():
                return icon
        return self.style().standardIcon(QStyle.SP_ArrowCursor)

    def _toggle_selection_tool(self, tool_type):
        try:
            from visualization.events import toggle_selection_mode

            toggle_selection_mode(tool_type)
        except Exception as exc:
            logger.warning("Failed to toggle selection tool: %s", exc)
        self._sync_selection_tool_actions()

    def _sync_selection_tool_actions(self):
        actions = getattr(self, "_selection_tool_actions", None)
        if not actions:
            return
        current_tool = getattr(app_state, "selection_tool", None)
        rect_checked = current_tool == "export"
        lasso_checked = current_tool == "lasso"
        actions["rect"].blockSignals(True)
        actions["lasso"].blockSignals(True)
        actions["rect"].setChecked(rect_checked)
        actions["lasso"].setChecked(lasso_checked)
        actions["rect"].blockSignals(False)
        actions["lasso"].blockSignals(False)
