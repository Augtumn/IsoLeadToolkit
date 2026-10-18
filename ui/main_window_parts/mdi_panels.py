"""Independent child windows for panels, in the style of Origin.

Each panel gets its own ``QMdiSubWindow`` holding its own ``Figure`` and ``FigureCanvas``, so the
figures are genuinely independent: they can be moved, resized, maximised and closed one by one,
and a render into one cannot disturb another. That is what the single-figure window has always
been, generalised to several.

The area publishes what it built through a runtime list the render loop reads, so the figures
reach the renderer without the application layer importing anything from this one.
"""
from __future__ import annotations

import logging
from typing import Any, Sequence

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QMdiArea, QMdiSubWindow

from core import app_state, translate

#: The size a new child window opens at, in pixels.
DEFAULT_PANEL_SIZE = (520, 420)


def create_mdi_area(parent: Any) -> QMdiArea:
    """A new area for independent figures, ready to be put in the window."""
    area = QMdiArea(parent)
    area.setViewMode(QMdiArea.SubWindowView)
    area.setOption(QMdiArea.DontMaximizeSubWindowOnActivation, True)
    # A child window must never make the area - and with it the whole window - demand a minimum
    # size: the area takes whatever room the layout gives it.
    area.setMinimumSize(1, 1)
    return area


class _PanelWindow(QMdiSubWindow):
    """A child window that tells its owner when the user closes it.

    Without this, closing a window left the panel list and the window list disagreeing: the
    application still believed in a panel whose figure no longer existed.
    """

    def __init__(self, on_close=None) -> None:
        super().__init__()
        self._on_close = on_close

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt's spelling
        if self._on_close is not None:
            try:
                self._on_close(self)
            except Exception as err:  # pragma: no cover - a callback must not break closing
                logging.getLogger(__name__).warning("Panel close callback failed: %s", err)
        super().closeEvent(event)


class PanelWindows:
    """The child windows of one area: one figure and one canvas each."""

    #: The render mode per panel, in creation order.
    _records: list[dict[str, Any]]

    def __init__(self, area: QMdiArea, on_close=None) -> None:
        self.area = area
        self._on_close = on_close
        self._records = []
        #: How many times the grid has been deferred waiting for the area to be laid out.
        self._grid_retries = 0

    def count(self) -> int:
        return len(self._records)

    @property
    def records(self) -> list[dict[str, Any]]:
        """What was built: ``mode``, ``figure``, ``canvas``, ``window`` and ``axes``."""
        return list(self._records)

    def close_window(self, window) -> None:
        """Drop exactly *window*, by identity, and take it out of the area.

        `sync` shrinks the list by popping its tail, so closing a window that was not the last one removed a
        live window from the records and left the closed one in them: the state described a window that had
        gone and the area lost a good one.
        """
        for index, record in enumerate(self._records):
            if record.get("window") is window:
                del self._records[index]
                break
        if window is not None:
            self.area.removeSubWindow(window)
            window.setParent(None)

    def sync(self, modes: Sequence[str]) -> list[dict[str, Any]]:
        """Make the windows match *modes*, adding and closing as needed."""
        from visualization.plotting.core import _add_axes

        wanted = [str(mode) or "2D" for mode in modes]
        while len(self._records) > len(wanted):
            record = self._records.pop()
            window = record.get("window")
            if window is not None:
                self.area.removeSubWindow(window)
                window.setParent(None)
        while len(self._records) < len(wanted):
            index = len(self._records)
            figure = Figure(figsize=(5.2, 4.2), dpi=100)
            canvas = FigureCanvas(figure)
            # Each window keeps its own navigation toolbar, hidden. Its zoom and pan modes register
            # their events on this canvas, so its buttons are right for this window and cannot be
            # moved to another; the main toolbar's buttons call into the one belonging to the
            # window in use, which is what lets a single set of buttons work in every panel.
            window = _PanelWindow(self._on_close)
            window.setWidget(canvas)
            navigation = NavigationToolbar(canvas, window)
            navigation.setVisible(False)
            window.setWindowTitle(translate("Panel {number}:").format(number=index + 1))
            window.setAttribute(Qt.WA_DeleteOnClose, False)
            self.area.addSubWindow(window)
            window.resize(*DEFAULT_PANEL_SIZE)
            self._records.append(
                {
                    "mode": wanted[index],
                    "figure": figure,
                    "canvas": canvas,
                    "toolbar": navigation,
                    "window": window,
                    "axes": _add_axes(figure, wanted[index], 111),
                    # A brand-new window is the one moment the view is framed. The flag is cleared
                    # once framed, so no later render, switch or rebuild frames it again.
                    "needs_fit": True,
                    # The placement the session held for this position, so a reopened session keeps its legends.
                    "legend": dict(
                        (getattr(app_state, "plot_panel_legends", None) or {}).get(str(index)) or {}
                    ),
                }
            )
        for record, mode in zip(self._records, wanted):
            if record.get("mode") != mode:
                # The mode changed: the figure is rebuilt with the projection that mode needs, which
                # is a new view - the limits of the old projection cannot apply to it.
                record["figure"].clf()
                record["axes"] = _add_axes(record["figure"], mode, 111)
                record["mode"] = mode
                record["needs_fit"] = True
        for record in self._records:
            window = record.get("window")
            if window is not None and not window.isVisible():
                window.show()
        return list(self._records)

    def tile(self) -> None:
        """Lay the windows out side by side, as Origin's tile command does."""
        if self._records:
            self.area.tileSubWindows()

    def arrange(self, kind: str = "grid") -> None:
        """Lay the windows out: beside each other, stacked, or on a grid.

        ``tile`` and ``cascade`` are the area's own arrangements; ``grid`` sizes the windows from
        the room actually available, which is what makes a handful of panels comparable at once.
        """
        if not self._records:
            return
        if kind == "tile":
            self.area.tileSubWindows()
            return
        if kind == "cascade":
            self.area.cascadeSubWindows()
            return
        self.grid()

    def grid(self) -> None:
        """Fill the area with a grid sized from the number of panels."""
        windows = [
            record.get("window")
            for record in self._records
            if record.get("window") is not None
        ]
        if not windows:
            return
        viewport = self.area.viewport()
        width = max(1, viewport.width())
        height = max(1, viewport.height())
        if (not self.area.isVisible() or width < 200 or height < 200) and self._grid_retries < 3:
            # The area has not been laid out yet - it was just added to the window - so a grid
            # computed now would size the children from a placeholder and leave them overlapping.
            # The arrangement is retried once, after the layout has given the area its real size.
            self._grid_retries += 1
            QTimer.singleShot(0, self.grid)
            return
        self._grid_retries = 0
        # A maximised child ignores setGeometry, so the windows are un-maximised first.
        for window in windows:
            if window.isMaximized():
                window.showNormal()
        columns = max(1, int(len(windows) ** 0.5 + 0.999))
        rows = max(1, -(-len(windows) // columns))
        cell_width = max(120, width // columns)
        cell_height = max(120, height // rows)
        for index, window in enumerate(windows):
            row, column = divmod(index, columns)
            window.setGeometry(
                column * cell_width, row * cell_height, cell_width, cell_height
            )

    def maximize(self) -> None:
        """Show the windows filled to the area."""
        for record in self._records:
            window = record.get("window")
            if window is not None:
                window.showMaximized()

    def show_filling_area(self) -> None:
        """Fill the area: one panel maximises, several share it on a grid."""
        if self.count() <= 1:
            self.maximize()
        else:
            self.grid()
        for record in self._records:
            window = record.get("window")
            if window is not None and not window.isVisible():
                window.show()

    def close_all(self) -> None:
        """Close every child window and forget it."""
        while self._records:
            record = self._records.pop()
            window = record.get("window")
            if window is not None:
                self.area.removeSubWindow(window)
                window.setParent(None)

    def active_index(self) -> int:
        """Which window is active, or -1 when none of them is (or there are none)."""
        active = self.area.activeSubWindow()
        if active is None:
            return -1
        for index, record in enumerate(self._records):
            if record.get("window") is active:
                return index
        return -1
