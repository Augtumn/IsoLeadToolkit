"""The figure lifecycle: adopting a figure, its canvas and its toolbar, and releasing the old ones.

set_matplotlib_figure is what a window calls when it shows a different figure - startup, a panel switch, going back to
one figure. It lived in the canvas mixin, which had grown to hold the figure lifecycle, the panel windows, the toolbar,
the selection tools and the zoom filter; this is the last subject to leave. The code is unchanged and
MainWindowCanvasMixin inherits it.
"""
from __future__ import annotations

import logging

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import QAction, QMenu

from core import app_state, state_gateway, translate
from ui.main_window_parts.canvas_toolbar import _MPL_TOOLTIP_TRANSLATIONS, copy_toolbar_actions
from ui.main_window_parts.ternary_zoom import install_ternary_zoom_filter

logger = logging.getLogger(__name__)


#: Methods this mixin calls that other mixins provide. Declared, not implied: the cross-mixin guard checks the list
#: against reality in both directions.
REQUIRES_CanvasFigureMixin = (
    "_arrange_panels",
    "_build_panel_windows",
    "_fit_panels_to_data",
    "_get_selection_icon",
    "_navigation_action",
    "_release_plot_widgets",
    "_retarget_toolbar",
    "_sync_axis_scale_lock_action",
    "_sync_selection_tool_actions",
    "_toggle_selection_tool",
)


class CanvasFigureMixin:
    def set_matplotlib_figure(self, fig):
        """设置 matplotlib 图形"""
        # The panel area belongs to this layout and is reused between rebuilds, so it is left
        # alone here - removing it would leave the child windows parented to nothing and thus
        # invisible. It is dropped explicitly when the window goes back to a single figure.
        self._release_plot_widgets()
        for i in reversed(range(self.canvas_layout.count())):
            widget = self.canvas_layout.itemAt(i).widget()
            if widget and widget is not self._panel_mdi_area:
                widget.setParent(None)
                # A parentless widget is not garbage: something has to delete it, and nothing else will.
                widget.deleteLater()
        app_state.plot_panel_windows[:] = []

        # Several figures means independent child windows, one per panel, each with its own
        # figure and canvas. Everything below - the selection tools, the panel, fit and hover
        # buttons, and the copy that puts them on the main toolbar - runs for both cases, with
        # the first panel standing in for the single canvas. Returning early here is what once
        # left the main toolbar empty.
        modes = [str(mode) for mode in list(getattr(app_state, "plot_panels", []) or [])]
        records = self._build_panel_windows(modes) if len(modes) > 1 else []
        if records:
            canvas = records[0]["canvas"]
        else:
            if self._panel_mdi_area is not None:
                self._panel_mdi_area.setParent(None)
                self._panel_mdi_area = None
            canvas = FigureCanvas(fig)
            # A brand-new canvas is framed once, when the panels ask for it below.
            self._single_figure_needs_fit = True
        toolbar = NavigationToolbar(canvas, self)
        toolbar.setVisible(False)  # Keep hidden; actions are extracted below
        self._plot_toolbar = toolbar
        self._plot_canvas = canvas

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

        # The toolbar is rebuilt whenever the figure or the panel list changes, so it is emptied
        # first: without this the actions below were appended again on every switch and the
        # toolbar grew a row of duplicates each time.
        self.toolbar.clear()

        self.toolbar.addSeparator()
        self.toolbar.addAction(rect_select_action)
        self.toolbar.addAction(lasso_select_action)

        self._selection_tool_actions = {
            "rect": rect_select_action,
            "lasso": lasso_select_action,
        }
        self._sync_selection_tool_actions()

        # The axis-scale lock: while it is on, every render draws the ranges it recorded, so
        # two datasets can be compared on the same axes. Built before the copy below, because
        # that is what puts it on the main toolbar.
        axis_lock_action = QAction(
            self._get_selection_icon("axis_lock.svg"), translate("Lock Axis Scale"), self
        )
        axis_lock_action.setToolTip(
            translate(
                "Lock the axis scale so new data is drawn on the same ranges. "
                "While it is on, the lock wins over a ternary zoom."
            )
        )
        axis_lock_action.setCheckable(True)
        axis_lock_action.triggered.connect(self._toggle_axis_scale_lock)
        self.toolbar.addAction(axis_lock_action)
        self._axis_lock_action = axis_lock_action
        self._sync_axis_scale_lock_action()

        # Several figures in one window, so the same data can be judged by different means at
        # once; hovering a point highlights the same sample in every panel.
        panels_action = QAction(
            self._get_selection_icon("panels.svg"), translate("Multi-Panel…"), self
        )
        panels_action.setToolTip(
            translate(
                "Show more than one figure at once. Hovering a point highlights the same "
                "sample in every panel."
            )
        )
        panels_action.triggered.connect(self._open_multi_panel_dialog)
        self.toolbar.addAction(panels_action)

        # Frame the data so the points fill the window, per panel; the counterpart of a
        # navigation toolbar's home button, which only ever restores the last saved limits.
        fit_action = QAction(
            self._get_selection_icon("fit_view.svg"), translate("Fit to Data…"), self
        )
        fit_action.setToolTip(
            translate("Rescale every panel so all of its data lies inside the view.")
        )
        fit_action.triggered.connect(lambda _checked=False: self._fit_panels_to_data(force=True))
        self.toolbar.addAction(fit_action)

        # The panels can be moved and resized one by one, which leaves the window in whatever
        # arrangement the last drag produced. These put them back: beside each other, stacked, or
        # on a grid that uses the whole area.
        arrange_action = QAction(
            self._get_selection_icon("panels.svg"), translate("Arrange Panels"), self
        )
        arrange_action.setToolTip(
            translate("Arrange the panel windows so each one is visible at once: tiled, cascaded, or on a grid.")
        )
        arrange_menu = QMenu(self)
        for kind, label in (
            ("tile", translate("Tile")),
            ("cascade", translate("Cascade")),
            ("grid", translate("Grid")),
        ):
            entry = arrange_menu.addAction(label)
            entry.triggered.connect(
                lambda _checked=False, kind=kind: self._arrange_panels(kind)
            )
        arrange_action.setMenu(arrange_menu)
        self.toolbar.addAction(arrange_action)

        # One switch for the hover readout: the tooltip and the point it marks. It used to be
        # always on and buried in the data panel, and it enlarged a whole group rather than the
        # point under the cursor, which told the user nothing.
        hover_action = QAction(
            self._get_selection_icon("hover_readout.svg"), translate("Hover Tooltip"), self
        )
        hover_action.setToolTip(
            translate("Show the sample under the cursor and highlight that point in every panel.")
        )
        hover_action.setCheckable(True)
        hover_action.setChecked(bool(app_state.show_tooltip))
        hover_action.toggled.connect(self._toggle_hover_readout)
        self.toolbar.addAction(hover_action)
        self._hover_action = hover_action

        # One set of navigation buttons that act on the panel in use: the zoom, the hand and home.
        # Each panel keeps its own toolbar, hidden, because a NavigationToolbar's modes register
        # their events on the canvas they were built with and cannot be moved to another; these
        # buttons call into the one belonging to the panel the user is working in. They appear with
        # panels only - the ordinary window keeps matplotlib's own buttons, right for its canvas.
        self._navigation_actions = []
        if records:
            self._navigation_actions = [
                self._navigation_action("zoom", translate("Zoom to Rectangle")),
                self._navigation_action("pan", translate("Pan")),
                self._navigation_action("home", translate("Home")),
            ]
            self.toolbar.addSeparator()
            for action in self._navigation_actions:
                self.toolbar.addAction(action)

        # Copy NavigationToolbar actions to main toolbar, translating tooltips
        # Kept so the toolbar can be rebuilt around another canvas when the user switches panels.
        self._plot_actions = [
            rect_select_action,
            lasso_select_action,
            axis_lock_action,
            panels_action,
            fit_action,
            arrange_action,
            hover_action,
        ]
        # Freshly built actions start unchecked, so a tool that is still active in the state
        # would show as unselected - the reported "tool state does not follow".
        self._sync_selection_tool_actions()

        # With several windows the navigation buttons are rebuilt per panel instead, so this
        # copy is only for the single-figure window; the panel case aims them at the first one.
        if not records:
            copy_toolbar_actions(toolbar, self.toolbar, _MPL_TOOLTIP_TRANSLATIONS)
        else:
            self._retarget_toolbar(canvas)

        if not records:
            self.canvas_layout.addWidget(canvas)

        state_gateway.set_figure(records[0]["figure"] if records else fig)
        state_gateway.set_canvas(canvas)

        # Ternary zoom: a Qt-level drag over the canvas becomes a zoom into a
        # similar sub-triangle (the matplotlib event path never reaches us here).
        install_ternary_zoom_filter(canvas, toolbar)

        # A canvas replaced while the lock is on must keep it: the record lives in the state,
        # but the hook that re-applies it lives on the canvas. Imported here rather than at the
        # top of the module because visualization.plotting's facade pulls in the whole render
        # stack, and this module is imported while the window is being built.
        if bool(app_state.axis_scale_locked):
            from visualization.plotting.axis_lock import install_axis_scale_lock

            install_axis_scale_lock(canvas)

        # NOTE: matplotlib event handlers (hover/click/legend-click) are
        # connected once in ui/app_parts/plotting.py::_connect_event_handlers
        # on app_state.fig.canvas (this same canvas). Connecting them again
        # here would double-fire every event (e.g. in-plot legend clicks and
        # double-click selection would toggle twice = net no-op).

