"""Canvas and toolbar integration mixin for main window."""
from __future__ import annotations

import logging
from pathlib import Path

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtCore import QEvent, QObject, Qt
from PyQt5.QtGui import QIcon, QWindow
from PyQt5.QtWidgets import QAction, QApplication, QStyle, QWidget

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)

#: Keys of app_state.ternary_manual_limits in component order.
_LIMIT_KEYS = ("tmin", "tmax", "lmin", "lmax", "rmin", "rmax")


#: matplotlib toolbar labels -> translation keys used for their tooltips.
_MPL_TOOLTIP_TRANSLATIONS = {
    "Home": "Reset original view",
    "Back": "Back to previous view",
    "Forward": "Forward to next view",
    "Pan": "Pan axes with left mouse, zoom with right",
    "Zoom": "Zoom to rectangle",
    "Subplots": "Configure subplots",
    "Customize": "Edit axis, curve and image parameters",
    "Save": "Save the figure",
}


def is_blank_action(action) -> bool:
    """True for an action that would show up as an empty toolbar button.

    matplotlib's toolbar carries a placeholder action with no icon, no text and no
    tooltip; copying it verbatim produced a nameless button next to Save.
    """
    if action is None or action.isSeparator():
        return False
    if not action.icon().isNull():
        return False
    return not (action.text() or "").strip() and not (action.toolTip() or "").strip()


def copy_toolbar_actions(source, target, translations=None) -> None:
    """Copy *source*'s actions onto *target*, translating matplotlib tooltips.

    Separators are recreated on the target (a copied separator action renders as a
    plain button) and blank placeholder actions are skipped.
    """
    translations = translations or _MPL_TOOLTIP_TRANSLATIONS
    for action in source.actions():
        if action is None:
            continue
        if action.isSeparator():
            target.addSeparator()
            continue
        if is_blank_action(action):
            continue
        target.addAction(action)
        text = (action.text() or "").strip()
        for en_key, tr_key in translations.items():
            if en_key.lower() in text.lower():
                action.setToolTip(translate(tr_key))
                break


class MainWindowCanvasMixin:
    """Canvas and toolbar behavior for main window."""
    _selection_tool_actions = None

    # Declared by the class that uses them, so no probe is needed for widgets
    # that build() creates later (UI review item B).

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
        copy_toolbar_actions(toolbar, self.toolbar, _MPL_TOOLTIP_TRANSLATIONS)

        self.canvas_layout.addWidget(canvas)

        state_gateway.set_figure(fig)
        state_gateway.set_canvas(canvas)

        # Ternary zoom: a Qt-level drag over the canvas becomes a zoom into a
        # similar sub-triangle (the matplotlib event path never reaches us here).
        install_ternary_zoom_filter(canvas, toolbar)

        # NOTE: matplotlib event handlers (hover/click/legend-click) are
        # connected once in ui/app_parts/plotting.py::_connect_event_handlers
        # on app_state.fig.canvas (this same canvas). Connecting them again
        # here would double-fire every event (e.g. in-plot legend clicks and
        # double-click selection would toggle twice = net no-op).

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
        self._show_selection_tool_hint()

    def _show_selection_tool_hint(self):
        """Tell the user which tool is armed and how to leave it."""
        from core import app_state

        status_bar = self.statusBar()
        if status_bar is None:
            return
        active = app_state.selection_tool
        if active:
            status_bar.showMessage(
                translate("Selection tool armed ({tool}) - press Escape to cancel.").format(
                    tool=active
                ),
                4000,
            )
        else:
            status_bar.clearMessage()

    def _sync_selection_tool_actions(self):
        actions = self._selection_tool_actions
        if not actions:
            return
        current_tool = app_state.selection_tool
        # "rect" is the toolbar value; "export" is the analysis-panel alias.
        rect_checked = current_tool in ("rect", "export")
        lasso_checked = current_tool == "lasso"
        actions["rect"].blockSignals(True)
        actions["lasso"].blockSignals(True)
        actions["rect"].setChecked(rect_checked)
        actions["lasso"].setChecked(lasso_checked)
        actions["rect"].blockSignals(False)
        actions["lasso"].blockSignals(False)


class TernaryZoomEventFilter(QObject):
    """Turns a left-button drag over the canvas into ternary limits."""

    def __init__(self, canvas: QWidget, toolbar=None) -> None:
        super().__init__(canvas)
        self._canvas = canvas
        self._toolbar = toolbar
        self._press: tuple[float, float] | None = None
        self._axes = None
        #: Where a middle-button pan started, in data coordinates.
        self._pan_from: tuple[float, float] | None = None

    def _zoom_tool_active(self) -> bool:
        """True while the toolbar's magnifier is selected.

        Until then a drag stays a selection gesture, which is how the toolbar is
        meant to behave.
        """
        return str(getattr(self._toolbar, "mode", "") or "") == "zoom rect"

    # ── helpers ──────────────────────────────────────────────────────────
    def _ternary_axes(self):
        try:
            for axes in self._canvas.figure.axes:
                if hasattr(axes, "set_ternary_lim"):
                    return axes
        except Exception as err:
            logger.warning("_ternary_axes failed: %s", err)
        return None

    def _axes_now(self):
        """The ternary axes of the live canvas, falling back to the app state."""
        axes = self._ternary_axes()
        if axes is None:
            try:
                candidate = app_state.ax
                if candidate is not None and hasattr(candidate, "set_ternary_lim"):
                    axes = candidate
            except Exception:
                axes = None
        return axes


    def _handle_wheel(self, axes, coords, event) -> None:
        """Wheel over the plot: zoom about the cursor (any plot type).

        Only while the toolbar's magnifier is selected; otherwise the wheel belongs to
        whatever else is listening (scrolling the panel, matplotlib's own handlers).
        """
        from visualization.plotting.ternary import cartesian_to_ternary
        from visualization.plotting.view_zoom import (
            is_ternary_axes,
            wheel_factor,
            zoom_cartesian,
            zoom_ternary,
        )

        factor = wheel_factor(event.angleDelta().y())
        if factor == 1.0:
            return
        try:
            if is_ternary_axes(axes):
                t, l, r = cartesian_to_ternary(coords[0], coords[1])
                limits = zoom_ternary(axes, factor, t, l, r)
                self._remember_ternary_limits(limits)
            else:
                zoom_cartesian(axes, factor, coords[0], coords[1])
            if self._canvas is not None:
                self._canvas.draw_idle()
        except Exception as err:
            logger.warning("Wheel zoom failed: %s", err)

    def _pan_view(self, current) -> None:
        """Middle-button drag: translate the view by the drag delta."""
        from visualization.plotting.view_zoom import (
            is_ternary_axes,
            pan_cartesian,
            pan_ternary,
        )

        if self._pan_from is None or current is None:
            return
        dx = current[0] - self._pan_from[0]
        dy = current[1] - self._pan_from[1]
        axes = self._current_axes()
        if axes is None:
            return
        try:
            if is_ternary_axes(axes):
                from visualization.plotting.ternary import cartesian_to_ternary

                t0, l0, _r0 = cartesian_to_ternary(*self._pan_from)
                t1, l1, _r1 = cartesian_to_ternary(*current)
                limits = pan_ternary(axes, (t1 - t0 + l1 - l0) / 2.0)
                self._remember_ternary_limits(limits)
            else:
                pan_cartesian(axes, -dx, -dy)
            if self._canvas is not None:
                self._canvas.draw_idle()
        except Exception as err:
            logger.warning("Pan failed: %s", err)
        self._pan_from = current

    def _remember_ternary_limits(self, limits) -> None:
        """Persist a ternary view so a re-render keeps it."""
        keys = ("tmin", "tmax", "lmin", "lmax", "rmin", "rmax")
        try:
            manual = dict(app_state.ternary_manual_limits or {})
            manual.update(dict(zip(keys, limits)))
            state_gateway.set_ternary_manual_limits(manual)
            state_gateway.set_ternary_auto_zoom(True)
            state_gateway.set_ternary_manual_limits_enabled(True)
        except Exception as err:
            logger.warning("Could not persist the ternary view: %s", err)

    def _current_axes(self):
        """The axes under the pointer: the ternary one when present, else the live axes.

        ``_axes_now()`` deliberately only returns ternary axes (the drag zoom needs them);
        wheel zoom and pan work on any plot type, so they use this wider accessor.
        """
        axes = self._ternary_axes()
        if axes is not None:
            return axes
        try:
            return app_state.ax
        except Exception:
            return None

    def _targets_canvas(self, obj) -> bool:
        """True when *obj* is (a child of) the canvas or its native window.

        Unrelated widgets (panels, menus, toolbar buttons) are excluded: the
        old global-position fallback once accepted a press on a QCheckBox as
        a gesture start.
        """
        if obj is self._canvas:
            return True
        if isinstance(obj, QWidget):
            try:
                return self._canvas.isAncestorOf(obj)
            except RuntimeError:
                return False
        if isinstance(obj, QWindow):
            return True
        return False

    def _data_coords(self, obj, event):
        """Widget position -> data coordinates, or None when outside the canvas."""
        try:
            if obj is self._canvas:
                point = event.pos()
            elif isinstance(obj, QWidget) and self._canvas.isAncestorOf(obj):
                point = self._canvas.mapFrom(obj, event.pos())
            elif isinstance(obj, QWindow):
                # Native-window copy of the event: its pos() is window-local,
                # so map through the global position instead.
                point = self._canvas.mapFromGlobal(event.globalPos())
            else:
                return None
            if not (0 <= point.x() <= self._canvas.width() and 0 <= point.y() <= self._canvas.height()):
                return None
            ratio = self._canvas.devicePixelRatioF()
            display = (point.x() * ratio, (self._canvas.height() - point.y()) * ratio)
            axes = self._axes if self._axes is not None else self._current_axes()
            if axes is None:
                return None
            data = axes.transData.inverted().transform(display)
            return float(data[0]), float(data[1])
        except Exception as err:
            logger.debug("Ternary zoom Qt: coordinate mapping failed: %s", err)
            return None

    # ── event filter ─────────────────────────────────────────────────────
    def eventFilter(self, obj, event) -> bool:
        try:
            kind = event.type()
            if kind == QEvent.Wheel:
                if not self._zoom_tool_active():
                    return False
                axes = self._current_axes()
                coords = self._data_coords(obj, event) if axes is not None else None
                if axes is not None and coords is not None:
                    self._handle_wheel(axes, coords, event)
                    return False
            if kind == QEvent.MouseButtonPress and event.button() == Qt.MiddleButton:
                if not self._zoom_tool_active():
                    # A pan left over from a previous mode must not continue.
                    self._pan_from = None
                    return False
                if self._targets_canvas(obj):
                    self._pan_from = self._data_coords(obj, event)
                    return False
            if kind == QEvent.MouseMove and self._pan_from is not None:
                current = self._data_coords(obj, event)
                if current is not None:
                    self._pan_view(current)
                    return False
            if kind == QEvent.MouseButtonRelease and event.button() == Qt.MiddleButton:
                if self._pan_from is not None:
                    logger.debug("Pan finished.")
                self._pan_from = None
                return False
            if kind == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                if not self._zoom_tool_active():
                    return False
                if not self._targets_canvas(obj):
                    return False
                self._axes = self._axes_now()
                if self._axes is None:
                    self._press = None
                    return False
                coords = self._data_coords(obj, event)
                if coords is None:
                    # The native QWindow copy of a press outside the canvas
                    # (e.g. over the axes frame) arrives first; the widget
                    # copy below may still map inside. Keep state clean.
                    self._press = None
                    return False
                self._press = coords
                logger.info(
                    "Ternary zoom press accepted at (%.4f, %.4f)", *coords
                )
            elif kind == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                start = self._press
                if start is None:
                    return False
                coords = self._data_coords(obj, event)
                if coords is None:
                    # Never conclude on an unusable copy: the QWindow copy
                    # arrives first and cannot be mapped via pos(); the
                    # canvas copy (or the QWindow copy via globalPos) right
                    # after it carries usable coordinates. Only a release
                    # genuinely delivered to the canvas but outside it
                    # cancels the gesture.
                    if obj is self._canvas:
                        logger.info(
                            "Ternary zoom cancelled: release outside the canvas"
                        )
                        self._press = None
                        self._axes = None
                    return False
                axes = self._axes
                self._press = None
                self._axes = None
                self._apply(axes, start, coords)
        except Exception as err:
            logger.warning("eventFilter failed: %s", err)
        return False  # never swallow the event

    def _apply(self, axes, start, end) -> None:
        from visualization.plotting.ternary import (
            similar_subtriangle_limits,
            ternary_limits_cover_full_view,
        )

        limits = similar_subtriangle_limits(start[0], start[1], end[0], end[1])
        logger.info(
            "Ternary zoom drag -> limits %s",
            tuple(round(float(value), 4) for value in limits),
        )
        full_view = ternary_limits_cover_full_view(limits)
        try:
            if full_view:
                state_gateway.set_ternary_manual_limits_enabled(False)
                logger.info("Ternary zoom reset by an outward drag.")
            else:
                manual = dict(app_state.ternary_manual_limits or {})
                manual.update(dict(zip(_LIMIT_KEYS, limits)))
                state_gateway.set_ternary_manual_limits(manual)
                state_gateway.set_ternary_auto_zoom(True)
                state_gateway.set_ternary_manual_limits_enabled(True)
                if axes is not None:
                    axes.set_ternary_lim(*limits)
                logger.info(
                    "Ternary local zoom (Qt): t=[%.3f, %.3f] l=[%.3f, %.3f] r=[%.3f, %.3f]",
                    limits[0], limits[1], limits[2], limits[3], limits[4], limits[5],
                )
        except Exception as err:
            logger.warning("Failed to apply ternary zoom (Qt): %s", err)
            return
        if full_view:
            return
        try:
            from visualization.events import on_slider_change

            on_slider_change()
        except Exception as err:
            logger.warning("Failed to refresh the plot after ternary zoom: %s", err)

def install_ternary_zoom_filter(canvas: QWidget, toolbar=None):
    """Install the filter on the application (once per canvas).

    An application-level filter sees both the native QWindow copy and the
    widget copy of each mouse event; installing on the canvas alone would
    miss the QWindow copy (and historically missed events entirely when the
    canvas was replaced during a redraw).
    """
    existing = getattr(canvas, "_ternary_zoom_filter", None)
    if existing is not None:
        return existing
    filt = TernaryZoomEventFilter(canvas, toolbar)
    application = QApplication.instance()
    if application is not None:
        application.installEventFilter(filt)
    else:  # pragma: no cover - no QApplication in headless use
        canvas.installEventFilter(filt)
    canvas._ternary_zoom_filter = filt
    logger.info(
        "Ternary zoom filter installed: canvas id=%s app_filter=%s",
        id(canvas),
        application is not None,
    )
    return filt
