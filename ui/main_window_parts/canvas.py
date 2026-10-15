"""Canvas and toolbar integration mixin for main window."""
from __future__ import annotations

import logging
import math
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


def _scatter_bounds(axis):
    """``(xs, ys, zs)`` of every finite point the axes currently draws."""
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for collection in getattr(axis, "collections", []) or []:
        try:
            offsets = collection.get_offsets()
        except Exception:
            continue
        for point in offsets if offsets is not None else []:
            try:
                x, y = float(point[0]), float(point[1])
            except (TypeError, ValueError, IndexError):
                continue
            if not (math.isfinite(x) and math.isfinite(y)):
                continue
            xs.append(x)
            ys.append(y)
            if len(point) > 2:
                try:
                    z = float(point[2])
                except (TypeError, ValueError):
                    continue
                if math.isfinite(z):
                    zs.append(z)
    return xs, ys, zs


class MainWindowCanvasMixin:
    """Canvas and toolbar behavior for main window."""
    _selection_tool_actions = None
    #: The axis-scale lock switch; None until set_matplotlib_figure() builds it.
    _axis_lock_action = None
    #: The area that holds the panel child windows; None until one is needed.
    _panel_mdi_area = None
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

    # Declared by the class that uses them, so no probe is needed for widgets
    # that build() creates later (UI review item B).

    def set_matplotlib_figure(self, fig):
        """设置 matplotlib 图形"""
        # The panel area belongs to this layout and is reused between rebuilds, so it is left
        # alone here - removing it would leave the child windows parented to nothing and thus
        # invisible. It is dropped explicitly when the window goes back to a single figure.
        for i in reversed(range(self.canvas_layout.count())):
            widget = self.canvas_layout.itemAt(i).widget()
            if widget and widget is not self._panel_mdi_area:
                widget.setParent(None)
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
        toolbar = NavigationToolbar(canvas, self)
        toolbar.setVisible(False)  # Keep hidden; actions are extracted below
        self._plot_toolbar = toolbar

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
            self._get_selection_icon("panels.svg"), translate("Multi-Panel..."), self
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
            self._get_selection_icon("fit_view.svg"), translate("Fit to Data..."), self
        )
        fit_action.setToolTip(
            translate("Zoom every panel so the data fills the window.")
        )
        fit_action.triggered.connect(self._fit_panels_to_data)
        self.toolbar.addAction(fit_action)

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

    def _focused_panel_record(self):
        """The record of the panel in use: the active one, else the one the state mirrors, else none."""
        records = list(app_state.plot_panel_windows or [])
        for record in records:
            if record.get("active"):
                return record
        for record in records:
            axis = record.get("axes")
            if axis is not None and axis is app_state.ax:
                return record
        return records[0] if records else None

    def _focused_toolbar(self):
        """The hidden navigation toolbar of the panel in use, so the buttons act on that panel."""
        record = self._focused_panel_record()
        if record is not None and record.get("toolbar") is not None:
            return record["toolbar"]
        return self._plot_toolbar

    def _borrowed_navigation_icon(self, kind: str):
        """matplotlib's own icon for a navigation button, borrowed so the look matches."""
        for record in list(app_state.plot_panel_windows or []):
            toolbar = record.get("toolbar")
            if toolbar is None:
                continue
            for candidate in list(getattr(toolbar, "actions", lambda: [])()):
                text = str(getattr(candidate, "text", lambda: "")() or "").lower()
                if kind in text:
                    icon = candidate.icon()
                    if icon is not None and not icon.isNull():
                        return icon
        return self._get_selection_icon("panels.svg")

    def _sync_navigation_buttons(self) -> None:
        """Show the tool the panel in use is actually holding.

        The buttons are checkable, so their highlight has to follow the focused panel: without
        this, switching from a panel whose magnifier was on left the magnifier highlighted while
        the panel in use held nothing - the reported state that did not synchronise. Setting the
        state is done with signals blocked, so syncing can never switch a tool by itself.
        """
        mode = ""
        try:
            toolbar = self._focused_toolbar()
            mode = str(getattr(getattr(toolbar, "mode", None), "name", "") or "").upper()
        except Exception as err:
            logger.warning("Could not read the panel's tool for the buttons: %s", err)
        for action, kind in zip(self._navigation_actions or [], ("zoom", "pan", "home")):
            if not action.isCheckable():
                continue
            wanted = kind.upper() in mode
            if action.isChecked() == wanted:
                continue
            was_blocked = action.blockSignals(True)
            action.setChecked(wanted)
            action.blockSignals(was_blocked)
        logger.info("Navigation buttons synced to the panel tool %r", mode or "NONE")

    def _refresh_labels_for(self, axes=None) -> None:
        """Lay the overlay labels out again for every panel whose view moved.

        Only the labels: a full re-render recomputes the axes from the data and threw the user's
        zoom away. The label data is one list of text artists belonging to different figures, so
        the panels to refresh are found from the artists themselves, each laid out on its own axes.

        This belongs to the window, which is what calls it during a fit; having it only on the
        event filter raised AttributeError there, cut the fit short and left a panel blank.
        """
        try:
            from visualization.plotting import refresh_paleoisochron_labels

            targets = []
            if axes is not None:
                targets.append(axes)
            # Every panel, each laid out from its own labels: the state's list only ever holds the
            # last panel's, which is why the other panels kept stale label positions.
            for state in list(getattr(app_state, "plot_panel_states", []) or []):
                panel_axes = state.get("ax") if isinstance(state, dict) else None
                if panel_axes is not None and panel_axes not in targets:
                    targets.append(panel_axes)
            for entry in list(getattr(app_state, "paleoisochron_label_data", None) or []):
                text = entry.get("text") if isinstance(entry, dict) else None
                owner = getattr(text, "axes", None)
                if owner is not None and owner not in targets:
                    targets.append(owner)
            for target in targets:
                refresh_paleoisochron_labels(ax=target)
            # Repaint every panel whose labels were just moved: a label that moves without its
            # canvas being redrawn leaves the panel showing its old buffer, which looks blank until
            # something else triggers a repaint - the reported "blank until I refresh manually".
            for target in targets:
                figure = getattr(target, "figure", None)
                canvas = getattr(figure, "canvas", None)
                if canvas is not None:
                    try:
                        canvas.draw_idle()
                    except Exception as err:
                        logger.warning("Could not repaint a panel after moving its labels: %s", err)
            logger.info("Labels refreshed for %d panel(s)", len(targets))
        except Exception as err:
            logger.warning("Could not refresh the labels for the panel: %s", err)

    def _navigation_action(self, kind: str, label: str) -> QAction:
        """A main-toolbar button that drives the toolbar of the panel in use."""
        action = QAction(self._borrowed_navigation_icon(kind), label, self)
        action.setToolTip(label)
        if kind in ("zoom", "pan"):
            action.setCheckable(True)

        def _trigger(checked: bool = False, kind: str = kind, action=action) -> None:
            target = self._focused_toolbar()
            if target is None:
                logger.warning("No panel toolbar to drive yet")
                return
            if kind == "home":
                try:
                    target.home()
                    target.canvas.draw_idle()
                except Exception as err:
                    logger.warning("Could not go home in the panel: %s", err)
                return
            method = getattr(target, kind, None)
            if method is None:
                logger.warning("The panel toolbar has no %s", kind)
                return
            try:
                method()
            except Exception as err:
                logger.warning("Could not switch the panel tool: %s", err)
                return
            # One set of buttons for every panel, so exactly one of them can be held at a time.
            for other in self._navigation_actions or []:
                if other is not action:
                    other.setChecked(False)

        action.triggered.connect(_trigger)
        return action

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
        """The axes to frame: one per panel window, or the single active axes."""
        axes = []
        for record in list(app_state.plot_panel_windows or []):
            axis = record.get("axes")
            if axis is not None:
                axes.append((str(record.get("mode", "")), axis))
        if not axes and app_state.ax is not None:
            axes.append((str(getattr(app_state, "render_mode", "") or ""), app_state.ax))
        return axes

    @staticmethod
    def _fit_one_axes(mode, axis) -> bool:
        """Frame one axes around the points it draws; True when something was framed."""
        name = getattr(axis, "name", "")
        if name == "ternary" or str(mode).strip().upper() == "TERNARY":
            # The whole triangle is the widest view a ternary diagram has.
            axis.set_ternary_lim(0.0, 1.0, 0.0, 1.0, 0.0, 1.0)
            return True
        xs, ys, zs = _scatter_bounds(axis)
        if not xs:
            return False
        if name == "3d":
            axis.set_xlim(min(xs), max(xs))
            axis.set_ylim(min(ys), max(ys))
            if zs:
                axis.set_zlim(min(zs), max(zs))
            return True
        span_x = max(xs) - min(xs)
        span_y = max(ys) - min(ys)
        pad_x = span_x * 0.05 if span_x > 0 else 1.0
        pad_y = span_y * 0.05 if span_y > 0 else 1.0
        axis.set_xlim(min(xs) - pad_x, max(xs) + pad_x)
        axis.set_ylim(min(ys) - pad_y, max(ys) + pad_y)
        return True

    def _retarget_toolbar(self, canvas) -> None:
        """Point the main toolbar's navigation buttons at *canvas*, by rebuilding them.

        A NavigationToolbar2QT cannot be moved to another canvas - its zoom and pan modes register
        their events on the canvas they were built with - so the toolbar is rebuilt around the new
        one instead. That is what makes a single set of buttons follow the panel in use.
        """
        if canvas is None or self.toolbar is None:
            return
        try:
            previous = self._plot_toolbar
            # matplotlib names the held tool differently across versions: mode.name on the
            # current one, _active on older builds. Both are read, and neither is assumed.
            active = ""
            if previous is not None:
                held = getattr(previous, "mode", None)
                active = str(getattr(held, "name", "") or "") or str(
                    getattr(previous, "_active", "") or ""
                )
            self.toolbar.clear()
            for action in self._plot_actions or []:
                self.toolbar.addAction(action)
            navigation = NavigationToolbar(canvas, self)
            navigation.setVisible(False)
            self._plot_toolbar = navigation
            # The tool the user is holding stays held: switching panel used to drop the magnifier,
            # and with it the wheel zoom that depends on it.
            held_tool = active.strip().lower()
            if "zoom" in held_tool:
                navigation.zoom()
                logger.info("Restored the magnifier after rebuilding the toolbar")
            elif "pan" in held_tool:
                navigation.pan()
                logger.info("Restored the pan tool after rebuilding the toolbar")
            # One set of buttons that act on the panel in use. matplotlib's own set is never copied
            # here: it is bound to one canvas, so its buttons only ever drove the first panel -
            # exactly what was reported when the panels stopped following the focus. Each panel
            # keeps its own hidden toolbar instead, and these buttons call into the one belonging
            # to the panel the user is working in.
            self._navigation_actions = [
                self._navigation_action("zoom", translate("Zoom to Rectangle")),
                self._navigation_action("pan", translate("Pan")),
                self._navigation_action("home", translate("Home")),
            ]
            self.toolbar.addSeparator()
            for action in self._navigation_actions:
                self.toolbar.addAction(action)
            logger.info(
                "Added %d navigation button(s): %s",
                len(self._navigation_actions),
                [action.text() for action in self._navigation_actions],
            )
            install_ternary_zoom_filter(canvas, self.toolbar)
            # A selection tool belongs to one canvas: the previous one has to let go of it, or a
            # tool the user cancelled keeps working on the old window, and the new window never
            # receives it, so the tool appears to lose its selection when the focus moves.
            from visualization.events import _disable_rectangle_selector, toggle_selection_mode

            try:
                _disable_rectangle_selector()
            except Exception as err:
                logger.warning("Could not clear the selection tool: %s", err)
            self._sync_selection_tool_actions()
            mode = str(getattr(app_state, "selection_mode", "") or "")
            if mode:
                state_gateway.disable_selection_mode()
                toggle_selection_mode(mode)
        except Exception as err:
            logger.warning("Could not retarget the toolbar: %s", err)

    def _on_panel_closed(self, window) -> None:
        """The user closed a child window: drop its panel and rebuild around what is left.

        Reported: closing a window left the panel list unsynchronised - the application still
        believed in a panel whose figure had gone. The list is corrected here and the rest is
        rebuilt the same way a change of the panel count is.
        """
        records = [
            record for record in list(app_state.plot_panel_windows or [])
            if record.get("window") is not window
        ]
        modes = [str(record.get("mode")) for record in records]
        state_gateway.set_plot_panels(modes if len(modes) > 1 else [])
        figure = records[0].get("figure") if records else app_state.fig
        app_state.plot_panel_windows[:] = records
        logger.info("Panel window closed; %d panel(s) left", len(records))
        self.set_matplotlib_figure(figure)

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
            if record.get("window") is not window:
                continue
            # Exactly one panel is the active one, and the tools act on it. The flag lives in the
            # records rather than in a new state field, and the single-figure references are
            # mirrored from it, so nothing silently keeps acting on the first panel.
            for other in list(app_state.plot_panel_windows or []):
                other["active"] = other is record
            # The mode of the panel in use is mirrored too, so the code that reads the single
            # render mode (titles, exports, parts of the render) agrees with the active panel
            # instead of being left on whichever mode the single-figure window last had.
            mode = str(record.get("mode") or "")
            if mode and mode != str(getattr(app_state, "render_mode", "")):
                state_gateway.set_render_mode(mode)
            # The render-mode control follows the panel, as the navigation buttons do. Only while
            # its dialog is open: the mode is per panel, the control is one.
            try:
                dialog = self._section_dialogs.get("data")
            except AttributeError:
                dialog = None
            panel = getattr(dialog, "section_panel", None)
            if panel is not None and hasattr(panel, "sync_render_mode"):
                panel.sync_render_mode(mode)
            # The legend panel shows the placement of the panel in use, the same way.
            try:
                legend_dialog = self._section_dialogs.get("legend")
            except AttributeError:
                legend_dialog = None
            legend_panel = getattr(legend_dialog, "section_panel", None)
            if legend_panel is not None and hasattr(legend_panel, "sync_legend_from_panel"):
                legend_panel.sync_legend_from_panel(record)
            state_gateway.set_figure(record["figure"])
            state_gateway.set_axis(record["axes"])
            state_gateway.set_canvas(record["canvas"])
            # The toolbar is NOT rebuilt here. Rebuilding it for every activation cleared it and
            # re-added the same action objects, which destroyed the checked state and the
            # connections - reported as the tools losing their state and refusing to turn on or
            # off. The panels are equal, and the interactions that matter per panel (wheel, middle
            # drag, box and lasso selection) are handled by the canvas under the pointer.
            # The highlight of the three navigation buttons follows the panel in use, so a tool
            # held in one panel does not stay lit after the focus moves to another.
            self._sync_navigation_buttons()
            logger.info("Active panel is now %s (index %d)", record.get("mode"), index)
            return

    def _fit_panels_to_data(self):
        """Zoom every panel so its points fill the window."""
        axes = self._panels_for_fit()
        fitted = 0
        for mode, axis in axes:
            try:
                if self._fit_one_axes(mode, axis):
                    fitted += 1
            except Exception as err:
                logger.warning("Could not fit a panel to the data: %s", err)
        for _mode, axis in axes:
            canvas = getattr(getattr(axis, "figure", None), "canvas", None)
            if canvas is not None:
                try:
                    canvas.draw_idle()
                except Exception as err:
                    logger.warning("Could not redraw after fitting: %s", err)
        logger.info("Fitted %d of %d panel(s) to the data", fitted, len(axes))
        # Fitting changes every panel's limits, so their labels are laid out again for the new view;
        # leaving this to a later render is what left them where the previous view had put them.
        self._refresh_labels_for()

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
            window = record.get("window")
            if window is None:
                continue
            if window.width() < 50 or window.height() < 50:
                window.resize(*DEFAULT_PANEL_SIZE)
            window.show()
        panel.tile()
        # Each child has its own canvas, and a matplotlib handler connected to one canvas never
        # sees another's events - so every child is connected here, at the moment it is built.
        from visualization.events import on_click, on_hover, on_legend_click

        for record in records:
            canvas = record.get("canvas")
            if canvas is None:
                continue
            canvas.mpl_connect("motion_notify_event", on_hover)
            canvas.mpl_connect("button_press_event", on_click)
            canvas.mpl_connect("button_press_event", on_legend_click)
        # Everything that reads app_state.fig must see the panel being worked in; the first is
        # the natural start and the active one takes over as soon as it is clicked. Written
        # through the gateway, which is the only way this project's guard allows state to move.
        state_gateway.set_figure(records[0]["figure"])
        state_gateway.set_axis(records[0]["axes"])
        state_gateway.set_canvas(records[0]["canvas"])
        app_state.plot_panel_windows[:] = records
        logger.info("Built %d panel window(s): %s", len(records), modes)
        return records

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

    def _toggle_axis_scale_lock(self, checked):
        """The toolbar's lock switch: record the ranges drawn now, or let go of them again.

        The work itself lives in visualization/plotting/axis_lock.py; this only carries the
        switch, keeps the button in step with the state and says what happened.
        """
        from visualization.plotting.axis_lock import (
            disable_axis_scale_lock,
            enable_axis_scale_lock,
        )

        locked = bool(checked)
        try:
            if locked:
                enable_axis_scale_lock(getattr(app_state, "canvas", None))
            else:
                disable_axis_scale_lock(getattr(app_state, "canvas", None))
        except Exception as exc:
            logger.warning("Failed to toggle the axis scale lock: %s", exc)
        self._sync_axis_scale_lock_action()
        self._show_axis_lock_hint(locked)

    def _sync_axis_scale_lock_action(self):
        """Show the lock state the state holds - it is persisted, so it can be on at startup."""
        action = self._axis_lock_action
        if action is None:
            return
        action.blockSignals(True)
        action.setChecked(bool(app_state.axis_scale_locked))
        action.blockSignals(False)

    def _show_axis_lock_hint(self, locked):
        """Say what the lock now does, since its effect is only visible on the next render."""
        status_bar = self.statusBar()
        if status_bar is None:
            return
        if locked:
            status_bar.showMessage(
                translate("Axis scale locked - new data is drawn on these axes."), 4000
            )
        else:
            status_bar.showMessage(
                translate("Axis scale unlocked - the axes fit the data again."), 4000
            )


class TernaryZoomEventFilter(QObject):
    #: The last wheel event already handled, so the second filter does not apply it again.
    _last_wheel_event = None
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


    def _zoom_tool_active_for(self, canvas) -> bool:
        """True while the panel shown in *canvas* holds the magnifier.

        Every panel has its own toolbar and the state mirrors one of them, so the tool must be read
        from the panel the event is over.
        """
        for record in list(getattr(app_state, "plot_panel_windows", []) or []):
            if record.get("canvas") is not canvas:
                continue
            toolbar = record.get("toolbar")
            mode = str(getattr(getattr(toolbar, "mode", None), "name", "") or "")
            return mode.upper() == "ZOOM"
        return self._zoom_tool_active()

    def _zoom_cartesian(self, axes, coords, event) -> None:
        """Zoom a 2D axes around the pointer, by one wheel step.

        Kept here rather than left to the toolbar's magnifier so that it works in every panel and
        cannot be lost when the toolbar is rebuilt for another one.
        """
        try:
            delta = int(event.angleDelta().y())
        except Exception as err:
            logger.warning("Could not read the wheel delta: %s", err)
            return
        if delta == 0:
            return
        factor = 0.85 if delta > 0 else 1.0 / 0.85
        try:
            x, y = float(coords[0]), float(coords[1])
        except Exception:
            return
        try:
            x0, x1 = axes.get_xlim()
            y0, y1 = axes.get_ylim()
            axes.set_xlim(x - (x - x0) * factor, x + (x1 - x) * factor)
            axes.set_ylim(y - (y - y0) * factor, y + (y1 - y) * factor)
            figure = getattr(axes, "figure", None)
            if figure is not None:
                figure.canvas.draw_idle()
        except Exception as err:
            logger.warning("Could not zoom the panel: %s", err)


    def _handle_wheel(self, axes, coords, event) -> None:
        """Wheel over the plot: zoom about the cursor (any plot type).

        A ternary wheel zoom magnifies the view the same way the 2D one does - the axes are handed
        the zoomed window, so the points grow on screen - and the tick labels move with the
        drawing. The window is recorded so a re-render keeps it (no checkbox needed).

        Only while the toolbar's magnifier is selected; otherwise the wheel belongs to
        whatever else is listening (scrolling the panel, matplotlib's own handlers).
        """
        if str(getattr(axes, "name", "")) != "ternary":
            # The wheel zooms here, per canvas, whatever the toolbar is doing: depending on the
            # magnifier being selected meant the zoom quietly stopped whenever the toolbar was
            # rebuilt for another panel.
            self._zoom_cartesian(axes, coords, event)
            return
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
        """Persist a ternary view window so every later render keeps it.

        The window is the region the gesture asked to see, so it is what the drawing shows and what
        the labels report. The zoom itself records it on the axes (``store_ternary_view_window`` in
        visualization/plotting/ternary.py), which is what makes the next render draw it again; this
        write is the copy the panel and the session keep. The manual-limits box keeps meaning "my
        window, not the inferred one", and this deliberately does not touch it.
        """
        keys = ("tmin", "tmax", "lmin", "lmax", "rmin", "rmax")
        try:
            manual = dict(app_state.ternary_manual_limits or {})
            manual.update(dict(zip(keys, limits)))
            state_gateway.set_ternary_manual_limits(manual)
            state_gateway.set_ternary_auto_zoom(True)
            # The manual-limits checkbox is left to the user: enabling it here made a zoom
            # flip it on, and it then came up ticked on the next launch.
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
        # Qt-level tracing, because on a real machine matplotlib's own mouse callbacks do not
        # receive canvas events at all: without this, a click that does nothing gives no clue
        # whether Qt saw it, whether it was a canvas, or whether it arrived as a double click.
        try:
            kind = event.type()
            if kind in (
                QEvent.MouseButtonPress,
                QEvent.MouseButtonRelease,
                QEvent.MouseButtonDblClick,
            ):
                widget = obj if isinstance(obj, QWidget) else None
                is_canvas = bool(widget is not None and hasattr(widget, "figure"))
                if kind != QEvent.MouseMove or is_canvas:
                    logger.info(
                        "qt mouse: %s on %s (canvas=%s) button=%s",
                        kind,
                        type(obj).__name__,
                        is_canvas,
                        getattr(event, "button", lambda: None)(),
                    )
                if (
                    is_canvas
                    and kind == QEvent.MouseButtonDblClick
                    and event.button() == Qt.LeftButton
                    and not app_state.selection_mode
                ):
                    # Only when no selection tool is active: with the tool on, the tool already
                    # handles the click, and forwarding it as well toggled the sample twice -
                    # the conflict where a double click appeared to do nothing.
                    # Qt saw a double click on a canvas but matplotlib's callback may never be
                    # called, so the click handler is invoked here with an equivalent event.
                    from matplotlib.backend_bases import MouseEvent
                    from visualization.event_handlers import on_click

                    position = event.pos()
                    height = widget.figure.bbox.height if widget.figure is not None else 0.0
                    synthetic = MouseEvent(
                        "button_press_event",
                        widget,
                        float(position.x()),
                        float(height - position.y()),
                        button=1,
                    )
                    synthetic.dblclick = True
                    on_click(synthetic)
                    return True
        except Exception as err:
            logger.warning("qt mouse tracing failed: %s", err)

        try:
            kind = event.type()
            if kind == QEvent.Wheel:
                # One notch is one step. Qt hands the same event to every filter that watches it,
                # and this filter is installed on the application as well as on each canvas, so a
                # notch was applied twice - and a different number of times per window.
                # The event itself, not its id: an id is reused once the event is collected, and a
                # later notch then looked like the same one and was skipped.
                if event is self._last_wheel_event:
                    return False
                self._last_wheel_event = event
                # Bound to the magnifier, as asked, and to the magnifier of the panel the wheel is
                # over: a wheel that ignores the tool is what this used to be.
                canvas = obj if isinstance(obj, QWidget) and hasattr(obj, "figure") else self._canvas
                if not self._zoom_tool_active_for(canvas):
                    return False
                axes = None
                coords = None
                try:
                    point = canvas.mapFromGlobal(event.globalPos())
                    ratio = canvas.devicePixelRatioF()
                    display = (point.x() * ratio, (canvas.height() - point.y()) * ratio)
                    for candidate in list(canvas.figure.axes):
                        try:
                            if candidate.bbox.contains(*display):
                                axes = candidate
                                break
                        except Exception:
                            continue
                    if axes is not None:
                        data = axes.transData.inverted().transform(display)
                        coords = (float(data[0]), float(data[1]))
                except Exception as err:
                    logger.warning("Wheel: could not resolve the panel under the pointer: %s", err)
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
            apply_ternary_zoom_window,
            drag_ternary_window,
            ternary_axes_limits,
            ternary_limits_cover_full_view,
        )

        # The drag is measured against what is drawn, not against the whole triangle, so a second
        # drag composes with the first and an outward drag stays a usable reset gesture.
        window = ternary_axes_limits(axes)
        if window is None:
            logger.info("Ternary zoom drag ignored: the drawn window could not be read.")
            return
        limits = drag_ternary_window(window, start, end)
        if limits is None:
            logger.info("Ternary zoom drag ignored: too short to be a gesture.")
            return
        logger.info(
            "Ternary zoom drag -> view window %s",
            tuple(round(float(value), 4) for value in limits),
        )
        full_view = ternary_limits_cover_full_view(limits)
        try:
            if full_view:
                # An outward drag is the reset gesture: it drops the stored window, so the drawing
                # goes back to the whole triangle and the labels to the range the data implies. The
                # manual-limits box is cleared with it, because its window is not what is being
                # asked for here.
                state_gateway.set_ternary_manual_limits_enabled(False)
                self._reset_ternary_view(axes)
                logger.info("Ternary zoom reset by an outward drag.")
            else:
                manual = dict(app_state.ternary_manual_limits or {})
                manual.update(dict(zip(_LIMIT_KEYS, limits)))
                state_gateway.set_ternary_manual_limits(manual)
                state_gateway.set_ternary_auto_zoom(True)
                # The manual-limits checkbox is left to the user: enabling it here made a zoom
                # flip it on, and it then came up ticked on the next launch.
                apply_ternary_zoom_window(axes, limits)
                logger.info(
                    "Ternary local zoom (Qt): t=[%.3f, %.3f] l=[%.3f, %.3f] r=[%.3f, %.3f]",
                    limits[0], limits[1], limits[2], limits[3], limits[4], limits[5],
                )
        except Exception as err:
            logger.warning("Failed to apply ternary zoom (Qt): %s", err)
            return
        # The canvas needs a repaint, not a fresh render: the zoom would survive a render now, but a
        # repaint is all this gesture asks for.
        if self._canvas is not None:
            self._canvas.draw_idle()

    def _reset_ternary_view(self, axes) -> None:
        """Undo the zoom: the whole triangle again, labelled with the range the data implies."""
        from visualization.plotting.ternary import reset_ternary_view

        window = reset_ternary_view(axes)
        logger.info(
            "Ternary view reset to t=[%.3f, %.3f] l=[%.3f, %.3f] r=[%.3f, %.3f]",
            window[0], window[1], window[2], window[3], window[4], window[5],
        )


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
