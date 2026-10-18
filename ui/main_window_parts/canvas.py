"""Canvas and toolbar integration mixin for main window."""
from __future__ import annotations

import logging

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtCore import QEvent, QObject, Qt
from PyQt5.QtGui import QWindow
from PyQt5.QtWidgets import QAction, QApplication, QMenu, QWidget

from core import app_state, state_gateway, translate
from visualization.plotting.view_fit import fit_axes, panel_targets

logger = logging.getLogger(__name__)





from visualization.plotting.panel_labels import refresh_panel_labels  # noqa: F401  (re-export)


from ui.main_window_parts.canvas_selection import CanvasSelectionMixin
from ui.main_window_parts.canvas_toolbar import (  # noqa: F401  (re-exported for the toolbar tests)
    _MPL_TOOLTIP_TRANSLATIONS,
    CanvasToolbarMixin,
    copy_toolbar_actions,
    is_blank_action,
)


#: Methods this class calls that its mixins provide. Declared so the cross-mixin guard can check both directions.
#: Only the fit keeps a panel-record lookup here now; everything else it used moved with the methods that used them.
REQUIRES_MainWindowCanvasMixin = ("_panel_record_for",)


from ui.main_window_parts.canvas_panels import CanvasPanelsMixin
from ui.main_window_parts.ternary_zoom import (  # noqa: F401  (re-exported for the zoom tests)
    TernaryZoomEventFilter,
    install_ternary_zoom_filter,
)


from ui.main_window_parts.canvas_figure import CanvasFigureMixin


class MainWindowCanvasMixin(CanvasToolbarMixin, CanvasSelectionMixin, CanvasPanelsMixin, CanvasFigureMixin):
    """Canvas and toolbar behavior for main window."""
    _selection_tool_actions = None
    #: The axis-scale lock switch; None until set_matplotlib_figure() builds it.
    _axis_lock_action = None
    #: The area that holds the panel child windows; None until one is needed.
    _panel_mdi_area = None
    #: A newly built single-figure canvas is framed once; after that the view belongs to the user.
    #: The panels carry the same marker per record, set where their window is created.
    _single_figure_needs_fit = True
    #: The three navigation buttons of the main toolbar, empty until the toolbar is built; the
    #: button sync reads them, and panel activation can happen first.
    _navigation_actions: list = []
    #: The single owner of the child windows. It has to outlive every call: a new PanelWindows per
    #: call starts with no records, so each call created another batch of child windows and closed
    #: none of them - the flood of panels, with only the last batch drawing anything.
    _panel_windows = None
    #: The section dialogs the window has opened, so a panel inside one can be reached again.
    _section_dialogs: dict = {}
    #: The actions this application adds to the main toolbar, kept so the toolbar can be rebuilt
    #: around another canvas when the user moves to a different panel.
    _plot_actions = None
    #: The plotting toolbar currently on the main one. Kept so the tool in use - the magnifier or
    #: the hand - survives the rebuild that follows a change of panel, which is why the wheel
    #: appeared to stop working: the magnifier was no longer selected.
    _plot_toolbar = None
    #: The canvas the plot toolbar and the application-level wheel filter were built around. Both are
    #: replaced on every rebuild, and neither the toolbar nor the filter removes itself: four rebuilds
    #: left four toolbars and four filters alive.
    _plot_canvas = None

    # Declared by the class that uses them, so no probe is needed for widgets
    # that build() creates later (UI review item B).

    def _toggle_hover_readout(self, checked: bool) -> None:
        """One switch for the hover readout: the tooltip and the point it marks.

        Switching it off clears both at once, rather than waiting for the next mouse move, and
        every panel is repainted so the enlarged point goes back to its base size.
        """
        state_gateway.set_show_tooltip(bool(checked))
        if not checked:
            from visualization.event_handlers.pointer_events import clear_hover_highlight

            clear_hover_highlight()
        logger.info("Hover readout %s", "on" if checked else "off")

    def _panels_for_fit(self):
        """The axes to frame: which panels is the window's business, the framing is view_fit's."""
        return panel_targets(app_state.plot_panel_windows, app_state.ax, app_state.render_mode)

    @staticmethod
    def _fit_one_axes(mode, axis) -> bool:
        """Frame one axes around the points it draws; the rule lives in visualization.plotting.view_fit."""
        return fit_axes(mode, axis)

    def _fit_panels_to_data(self, force: bool = False):
        """Zoom every panel so its points fill the window.

        The command frames every panel. The automatic callers - when panels are built and after a
        reload - frame only panels that have never been framed: a view the user zoomed or panned is
        not something a render, a panel switch or a rebuild may throw away.
        """
        axes = self._panels_for_fit()
        fitted = 0
        framed: list = []
        for mode, axis in axes:
            record = self._panel_record_for(axis)
            if not force:
                if record is not None:
                    if not record.needs_fit:
                        # This window has already been framed once: the view is the user's now.
                        continue
                elif not self._single_figure_needs_fit:
                    continue
            try:
                if self._fit_one_axes(mode, axis):
                    fitted += 1
                    framed.append(axis)
                    if record is not None:
                        record["needs_fit"] = False
                    else:
                        self._single_figure_needs_fit = False
            except Exception as err:
                logger.warning("Could not fit a panel to the data: %s", err)
        for axis in framed:
            canvas = getattr(getattr(axis, "figure", None), "canvas", None)
            if canvas is not None:
                try:
                    canvas.draw_idle()
                except Exception as err:
                    logger.warning("Could not redraw after fitting: %s", err)
        if framed:
            # Fitting changes the limits, so the labels are laid out again for the new view.
            refresh_panel_labels()
        logger.info(
            "Fitted %d of %d panel(s) to the data%s",
            fitted,
            len(axes),
            " (requested)" if force else "",
        )

