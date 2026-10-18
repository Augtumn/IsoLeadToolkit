"""The canvas toolbar: navigation buttons, their actions, and pointing them at a panel.

Split out of the canvas mixin, which had grown to hold the figure lifecycle, the panel windows, the toolbar, the
selection tools and the zoom filter. The code is unchanged; what moved is who owns it, so each file has one subject.
MainWindowCanvasMixin inherits both mixins, so every self.* reference resolves as before.
"""
from __future__ import annotations

import logging

from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import QAction, QApplication

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)

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


#: Methods this mixin calls that another mixin (or the canvas class) provides. Declared, not implied: the
#: cross-mixin guard checks the list against reality in both directions.
REQUIRES_CanvasToolbarMixin = (
    "_focused_panel_record",
    "_get_selection_icon",
    "_sync_selection_tool_actions",
)


class CanvasToolbarMixin:
    def _release_plot_widgets(self) -> None:
        """Let go of the toolbar and the filters the previous canvas owned.

        The toolbar's parent is this widget, so dropping the reference left it alive; the wheel filter is
        installed on the QApplication, so it outlived every canvas it was made for. Both are deleted here.
        """
        application = QApplication.instance()
        previous_canvas = self._plot_canvas
        filt = getattr(previous_canvas, "_ternary_zoom_filter", None) if previous_canvas is not None else None
        if filt is not None:
            if application is not None:
                application.removeEventFilter(filt)
            if previous_canvas is not None:
                previous_canvas.removeEventFilter(filt)
            filt.deleteLater()
            if previous_canvas is not None:
                previous_canvas._ternary_zoom_filter = None
        toolbar = self._plot_toolbar
        if toolbar is not None:
            toolbar.setParent(None)
            toolbar.deleteLater()
        self._plot_toolbar = None
        self._plot_canvas = None

    def _focused_toolbar(self):
        """The hidden navigation toolbar of the panel in use, so the buttons act on that panel."""
        record = self._focused_panel_record()
        if record is not None and record.toolbar is not None:
            return record["toolbar"]
        return self._plot_toolbar

    def _borrowed_navigation_icon(self, kind: str):
        """matplotlib's own icon for a navigation button, borrowed so the look matches."""
        for record in list(app_state.plot_panel_windows or []):
            toolbar = record.toolbar
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
            if previous is not None and previous is not navigation:
                previous.setParent(None)
                previous.deleteLater()
            self._plot_toolbar = navigation
            self._plot_canvas = canvas
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
