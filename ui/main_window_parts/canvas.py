"""Canvas and toolbar integration mixin for main window."""

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
        toolbar.setVisible(False)
        zoom_out_action = QAction(self._get_zoom_out_icon(), translate("Zoom Out"), self)
        zoom_out_action.setToolTip(translate("Zoom Out"))
        zoom_out_action.triggered.connect(self._zoom_out_view)

        zoom_action = None
        actions = toolbar.actions()
        for action in actions:
            if "zoom" in (action.text() or "").lower():
                zoom_action = action
                break

        if zoom_action is not None:
            zoom_index = actions.index(zoom_action)
            if zoom_index + 1 < len(actions):
                toolbar.insertAction(actions[zoom_index + 1], zoom_out_action)
            else:
                toolbar.addAction(zoom_out_action)
        else:
            toolbar.addAction(zoom_out_action)

        rect_select_action = QAction(self._get_selection_icon("selection_rect.svg"), translate("Box Select"), self)
        rect_select_action.setToolTip(translate("Box Select"))
        rect_select_action.setCheckable(True)
        rect_select_action.triggered.connect(lambda: self._toggle_selection_tool("export"))

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

        self._attach_matplotlib_toolbar_actions(toolbar)
        self.canvas_layout.addWidget(canvas)
        self.canvas_layout.addWidget(canvas)

        state_gateway.set_figure(fig)
        state_gateway.set_canvas(canvas)

        self._connect_event_handlers(canvas)

    def set_control_panel(self, panel_widget):
        """Attach the control panel widget above the canvas."""
        for i in reversed(range(self.panel_layout.count())):
            widget = self.panel_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        if panel_widget is None:
            self.panel_container.setVisible(False)
            return

        self.panel_layout.addWidget(panel_widget)
        self.panel_container.setVisible(True)
        try:
            self.main_splitter.setSizes([320, 560])
        except Exception:
            pass

    def _attach_matplotlib_toolbar_actions(self, toolbar):
        self._clear_matplotlib_toolbar_actions()
        self._mpl_toolbar = toolbar
        actions = list(toolbar.actions())
        if not actions:
            return
        filtered = []
        for action in actions:
            if action is None:
                continue
            if action.isSeparator():
                filtered.append(action)
                continue
            text = (action.text() or "").strip()
            tooltip = (action.toolTip() or "").strip()
            has_icon = action.icon() is not None and not action.icon().isNull()
            if not text and not tooltip and not has_icon:
                continue
            filtered.append(action)

        for action in filtered:
            self.toolbar.addAction(action)
        self._mpl_toolbar_actions = filtered

    def _clear_matplotlib_toolbar_actions(self):
        actions = getattr(self, "_mpl_toolbar_actions", [])
        if not actions:
            return
        for action in actions:
            try:
                self.toolbar.removeAction(action)
            except Exception:
                pass
        self._mpl_toolbar_actions = []

    def _get_zoom_out_icon(self):
        """Resolve a zoom-out icon, falling back to a standard icon."""
        base_dir = Path(__file__).resolve().parent.parent.parent
        svg_path = base_dir / "assets" / "icons" / "zoom_out.svg"
        if svg_path.exists():
            icon = QIcon(str(svg_path))
            if not icon.isNull():
                return icon
        for name in ("zoom-out", "view-zoom-out", "magnifier-zoom-out"):
            icon = QIcon.fromTheme(name)
            if not icon.isNull():
                return icon
        return self.style().standardIcon(QStyle.SP_TitleBarMinButton)

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

    def _zoom_out_view(self):
        """Zoom out the current axes view."""
        ax = getattr(app_state, "ax", None)
        if ax is None:
            return
        try:
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]
            if x_range == 0 or y_range == 0:
                return
            ax.set_xlim([xlim[0] - x_range * 0.25, xlim[1] + x_range * 0.25])
            ax.set_ylim([ylim[0] - y_range * 0.25, ylim[1] + y_range * 0.25])
            if app_state.fig is not None and app_state.fig.canvas is not None:
                app_state.fig.canvas.draw_idle()
        except Exception:
            pass
