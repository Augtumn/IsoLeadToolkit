"""The selection tools and the axis-scale lock: their buttons, icons and hints.

Split out of the canvas mixin for the same reason as the toolbar: one file, one subject. The icon lookup resolves paths
from __file__, and this file sits beside canvas.py, so the base directory it computes is unchanged.
"""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QStyle

from core import app_state, translate

logger = logging.getLogger(__name__)


class CanvasSelectionMixin:
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
