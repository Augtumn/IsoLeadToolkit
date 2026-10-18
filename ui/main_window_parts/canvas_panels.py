"""The panel windows: building them, activating one, closing one, switching a panel's mode.

Split out of the canvas mixin, which held the figure lifecycle, the panel windows, the toolbar, the selection tools and
the zoom filter. The code is unchanged; MainWindowCanvasMixin inherits this mixin, so every self.* reference resolves as
before. What is left in canvas.py is the figure lifecycle and the zoom filter.
"""
from __future__ import annotations

import logging

from core import app_state, state_gateway

logger = logging.getLogger(__name__)


#: Methods this mixin calls that other mixins or the canvas class provide. Declared, not implied: the cross-mixin
#: guard checks the list against reality in both directions.
REQUIRES_CanvasPanelsMixin = (
    "_fit_panels_to_data",
    "_sync_navigation_buttons",
    "set_matplotlib_figure",
)


class CanvasPanelsMixin:
    #: The section dialogs the window has opened, by section name. Declared here because the panel activation
    #: follows the controls that live in them: the main window sets this when it builds a dialog, and until then -
    #: or on a window that never opens one - there is nothing to follow, which is a normal state and not a probe.
    _section_dialogs: dict = {}

    def _focused_panel_record(self):
        """The record of the panel in use: the active one, else the one the state mirrors, else none."""
        records = list(app_state.plot_panel_windows or [])
        for record in records:
            if record.active:
                return record
        for record in records:
            axis = record.axes
            if axis is not None and axis is app_state.ax:
                return record
        return records[0] if records else None
    def apply_render_mode_to_panel_in_use(self, mode) -> None:
        """Give the panel in use *mode*, keeping the panel windows and the state in step.

        A panel's render mode is its own - that is what comparing projections side by side means -
        so choosing a mode in the data panel changes the panel the user is working in. The figure
        is rebuilt through the same machinery that builds any panel, and the state's single render
        mode, which mirrors the panel in use, follows.
        """
        records = list(app_state.plot_panel_windows or [])
        if not records or mode is None:
            # A single-figure window: the chosen mode is the window's own.
            return
        active = next(
            (record for record in records if record.active), records[0]
        )
        if active.mode == str(mode):
            return
        modes = [record.mode for record in records]
        index = records.index(active)
        modes[index] = str(mode)
        panel = self._panel_windows
        if panel is None:
            return
        try:
            rebuilt = panel.sync(modes)
        except Exception as err:
            logger.warning("Could not switch the panel's mode: %s", err)
            return
        app_state.plot_panel_windows[:] = rebuilt
        # The renderer is handed the panel list and looks the windows up by it; leaving the state's
        # list behind made the two disagree, and a render then drew nothing at all - the new panel
        # stayed empty and the others kept the previous drawing.
        state_gateway.set_plot_panels(modes)
        state_gateway.set_render_mode(str(mode))
        logger.info("Panel %d switched to %s", index + 1, mode)
    def _on_panel_closed(self, window) -> None:
        """The user closed a child window: drop its panel and rebuild around what is left.

        Reported: closing a window left the panel list unsynchronised - the application still
        believed in a panel whose figure had gone. The list is corrected here and the rest is
        rebuilt the same way a change of the panel count is.
        """
        records = [
            record for record in list(app_state.plot_panel_windows or [])
            if record.window is not window
        ]
        # Drop this window from the panel bookkeeping by identity, before anything rebuilds: `sync`
        # shrinks by popping the tail, which removes a live window when the one closed is not the last.
        if self._panel_windows is not None:
            self._panel_windows.close_window(window)
        closed_was_active = any(
            record.window is window and record.active
            for record in list(app_state.plot_panel_windows or [])
        )
        modes = [record.mode for record in records]
        state_gateway.set_plot_panels(modes if len(modes) > 1 else [])
        figure = records[0].get("figure") if records else app_state.fig
        app_state.plot_panel_windows[:] = records
        logger.info("Panel window closed; %d panel(s) left", len(records))
        self.set_matplotlib_figure(figure)
        if closed_was_active and records:
            # The panel in use was the one closed, so the panel that takes over has to be followed:
            # otherwise the state's render mode and the data panel's control still describe a window
            # that no longer exists.
            self._on_panel_activated(records[0].get("window"))
    def _on_panel_activated(self, window) -> None:
        """Follow the child window in use: its figure, axes and canvas become the active ones.

        Reported: zoom, pan and the rest only ever worked in the first panel. The navigation
        toolbar is built around one canvas, so its buttons drove that one whatever the user had
        clicked; re-pointing it at the activated child makes the buttons act on the panel being
        used, and the application state follows so hover and selection do too.
        """
        if window is None:
            return
        for index, record in enumerate(list(app_state.plot_panel_windows or [])):
            if record.window is not window:
                continue
            # Exactly one panel is the active one, and the tools act on it. The flag lives in the
            # records rather than in a new state field, and the single-figure references are
            # mirrored from it, so nothing silently keeps acting on the first panel.
            for other in list(app_state.plot_panel_windows or []):
                other["active"] = other is record
            # The mode of the panel in use is mirrored too, so the code that reads the single
            # render mode (titles, exports, parts of the render) agrees with the active panel
            # instead of being left on whichever mode the single-figure window last had.
            mode = record.mode
            if mode and mode != str(getattr(app_state, "render_mode", "")):
                state_gateway.set_render_mode(mode)
            # The render-mode control follows the panel, as the navigation buttons do. Only while its dialog is
            # open: the mode is per panel, the control is one. getattr rather than except AttributeError - a window
            # that never opened a section dialog has no such attribute, which is a normal state, not a failure to
            # swallow.
            dialogs = self._section_dialogs
            panel = getattr(dialogs.get("data"), "section_panel", None)
            if panel is not None and hasattr(panel, "sync_render_mode"):
                panel.sync_render_mode(mode)
            # The legend panel shows the placement of the panel in use, the same way.
            legend_panel = getattr(dialogs.get("legend"), "section_panel", None)
            if legend_panel is not None and hasattr(legend_panel, "sync_legend_from_panel"):
                legend_panel.sync_legend_from_panel(record)
            state_gateway.set_figure(record["figure"])
            state_gateway.set_axis(record["axes"])
            state_gateway.set_canvas(record["canvas"])
            # The selection selectors belong to one axes, so they follow the panel in use.
            try:
                from visualization.event_handlers.selection_tools import refresh_selection_selectors

                refresh_selection_selectors()
            except Exception as err:
                logger.warning("Could not move the selection selectors to the active panel: %s", err)
            # The toolbar is NOT rebuilt here. Rebuilding it for every activation cleared it and
            # re-added the same action objects, which destroyed the checked state and the
            # connections - reported as the tools losing their state and refusing to turn on or
            # off. The panels are equal, and the interactions that matter per panel (wheel, middle
            # drag, box and lasso selection) are handled by the canvas under the pointer.
            # The highlight of the three navigation buttons follows the panel in use, so a tool
            # held in one panel does not stay lit after the focus moves to another.
            self._sync_navigation_buttons()
            logger.info("Active panel is now %s (index %d)", record.mode, index)
            return
    def _arrange_panels(self, kind: str = "grid") -> None:
        """Lay the panel windows out, on request."""
        panels = self._panel_windows
        if panels is None or not panels.count():
            return
        try:
            panels.arrange(kind)
            logger.info("Arranged %d panel window(s): %s", panels.count(), kind)
        except Exception as err:
            logger.warning("Could not arrange the panel windows: %s", err)
    def _panel_record_for(self, axis):
        """The panel record that draws *axis*, or None for the single-figure window."""
        for record in list(app_state.plot_panel_windows or []):
            if record.axes is axis:
                return record
        return None
    def _build_panel_windows(self, modes) -> list:
        """Show one independent child window per panel; the records, or [] if impossible."""
        from .mdi_panels import DEFAULT_PANEL_SIZE, PanelWindows, create_mdi_area

        try:
            area = self._panel_mdi_area
            if area is None:
                area = create_mdi_area(self.plot_container)
                # Once: the buttons must follow whichever child window is in use.
                area.subWindowActivated.connect(self._on_panel_activated)
                self.canvas_layout.addWidget(area)
                self._panel_mdi_area = area
            else:
                # It is reused, so it has to be in the layout before it can be seen.
                if self.canvas_layout.indexOf(area) < 0:
                    self.canvas_layout.addWidget(area)
                area.setVisible(True)
            # One owner, reused for the life of the window: a new PanelWindows per call starts with
            # no records, so every call created another batch of child windows and none was closed.
            panel = self._panel_windows
            if panel is None or getattr(panel, "area", None) is not area:
                panel = PanelWindows(area, on_close=self._on_panel_closed)
                self._panel_windows = panel
            records = panel.sync(modes)
        except Exception as err:
            logger.warning("Could not build the panel windows: %s", err)
            return []
        if not records:
            return []
        # The first panel is active when the windows are built; the user's click moves it.
        for index, record in enumerate(records):
            record["active"] = index == 0
        # A sub-window that was never shown, or shown at no size, would draw nothing.
        for record in records:
            window = record.window
            if window is None:
                continue
            if window.width() < 50 or window.height() < 50:
                window.resize(*DEFAULT_PANEL_SIZE)
            window.show()
        # A newly built set of panels fills the area: one panel maximises, several share it on a
        # grid. Opening at a fixed 520x420 left most of the window empty.
        panel.show_filling_area()
        # And the data is framed in every panel as soon as they exist, so a freshly loaded window
        # shows the points rather than whatever limits the figure started with.
        self._fit_panels_to_data()
        # Each child has its own canvas, and a matplotlib handler connected to one canvas never
        # sees another's events - so every child is connected here, at the moment it is built.
        from visualization.events import on_click, on_hover, on_legend_click

        for record in records:
            canvas = record.canvas
            if canvas is None:
                continue
            canvas.mpl_connect("motion_notify_event", on_hover)
            canvas.mpl_connect("button_press_event", on_click)
            canvas.mpl_connect("button_press_event", on_legend_click)
        # Everything that reads app_state.fig must see the panel being worked in; the first is
        # the natural start and the active one takes over as soon as it is clicked. Written
        # through the gateway, which is the only way this project's guard allows state to move.
        app_state.plot_panel_windows[:] = records
        # The first panel is the one in use, so the state's figure, axes, canvas AND render mode
        # follow it - along the same path a click on a panel takes, so a new set of panels and a
        # switch between panels cannot disagree about which mode and which figure are in force.
        self._on_panel_activated(records[0].get("window"))
        logger.info("Built %d panel window(s): %s", len(records), modes)
        return records
    def _open_multi_panel_dialog(self):
        """Ask how many figures to show and what each draws, then redraw."""
        from .multi_panel_dialog import MultiPanelDialog

        dialog = MultiPanelDialog(
            self,
            panels=list(getattr(app_state, "plot_panels", []) or []),
            default_mode=str(getattr(app_state, "render_mode", "2D") or "2D"),
        )
        if dialog.exec_() != dialog.Accepted:
            return
        state_gateway.set_plot_panels(dialog.selected_panels())
        # The child windows follow the panel list, so they are rebuilt before the redraw - and
        # rebuilt again when the list goes back to one, which restores the single canvas.
        self.set_matplotlib_figure(app_state.fig)
        try:
            from visualization.events import on_slider_change

            on_slider_change()
        except Exception as err:  # pragma: no cover - needs a live canvas
            logger.warning("Could not redraw after choosing panels: %s", err)
