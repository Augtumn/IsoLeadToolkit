"""Qt-level ternary zoom test: real widgets, real Qt mouse events."""
from __future__ import annotations

import matplotlib
import pytest

matplotlib.use("Qt5Agg")

import mpltern  # noqa: F401
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QApplication

from core import app_state, state_gateway
from ui.main_window_parts.canvas import install_ternary_zoom_filter

APP = QApplication.instance() or QApplication([])


def _send(canvas, kind, point, buttons, button):
    event = QMouseEvent(
        {"press": QEvent.MouseButtonPress, "move": QEvent.MouseMove,
         "release": QEvent.MouseButtonRelease}[kind],
        QPointF(point), button, buttons, Qt.NoModifier,
    )
    APP.sendEvent(canvas, event)
    APP.processEvents()


def _pixel(canvas, axes, x, y):
    display_x, display_y = axes.transData.transform((x, y))
    ratio = canvas.devicePixelRatioF()
    return QPoint(int(display_x / ratio), int((canvas.height() * ratio - display_y) / ratio))


@pytest.fixture()
def qt_ternary():
    figure = Figure(figsize=(4, 4))
    canvas = FigureCanvasQTAgg(figure)
    canvas.resize(400, 400)
    canvas.show()
    APP.processEvents()
    axes = figure.add_subplot(projection="ternary")
    axes.scatter([0.2, 0.5], [0.3, 0.25], [0.5, 0.25])
    canvas.draw()
    APP.processEvents()
    state_gateway.set_figure_axes(figure, axes)
    state_gateway.set_ternary_manual_limits({})
    state_gateway.set_ternary_manual_limits_enabled(False)
    state_gateway.set_ternary_auto_zoom(True)
    install_ternary_zoom_filter(canvas)
    return canvas, axes


def test_qt_drag_zooms_the_ternary_axes(qt_ternary) -> None:
    canvas, axes = qt_ternary
    start = _pixel(canvas, axes, 0.0, 1.0 / 3.0)
    end = _pixel(canvas, axes, 0.0, 2.0 / 3.0)

    _send(canvas, "press", start, Qt.LeftButton, Qt.LeftButton)
    _send(canvas, "move", end, Qt.LeftButton, Qt.NoButton)
    _send(canvas, "release", end, Qt.NoButton, Qt.LeftButton)

    limits = dict(app_state.ternary_manual_limits or {})
    assert limits.get("tmin") == pytest.approx(1 / 6, abs=0.02), limits
    assert limits.get("tmax") == pytest.approx(2 / 3, abs=0.02), limits
    assert app_state.ternary_manual_limits_enabled is True


def test_qt_drag_outside_the_canvas_does_nothing(qt_ternary) -> None:
    canvas, axes = qt_ternary
    outside = QPoint(canvas.width() + 50, canvas.height() + 50)
    _send(canvas, "press", outside, Qt.LeftButton, Qt.LeftButton)
    _send(canvas, "release", outside, Qt.NoButton, Qt.LeftButton)
    assert app_state.ternary_manual_limits_enabled is False


def test_qt_drag_on_a_cartesian_figure_does_nothing() -> None:
    figure = Figure()
    canvas = FigureCanvasQTAgg(figure)
    canvas.resize(300, 300)
    canvas.show()
    axes = figure.add_subplot(111)
    axes.plot([0, 1], [0, 1])
    canvas.draw()
    state_gateway.set_figure_axes(figure, axes)
    state_gateway.set_ternary_manual_limits_enabled(False)
    install_ternary_zoom_filter(canvas)

    point = QPoint(150, 150)
    _send(canvas, "press", point, Qt.LeftButton, Qt.LeftButton)
    _send(canvas, "release", point, Qt.NoButton, Qt.LeftButton)
    assert app_state.ternary_manual_limits_enabled is False


def test_unrelated_widget_press_does_not_start_a_gesture(qt_ternary) -> None:
    """Regression: a press on a panel widget was accepted as a gesture start.

    The real-run log showed a QCheckBox press accepted with canvas data
    coordinates because the old global-position fallback mapped unrelated
    widgets into the canvas.
    """
    from PyQt5.QtWidgets import QWidget

    canvas, _axes = qt_ternary
    checkbox = QWidget()
    checkbox.resize(50, 20)
    checkbox.show()
    APP.processEvents()

    point = QPoint(10, 10)
    limits_before = dict(app_state.ternary_manual_limits or {})
    _send(checkbox, "press", point, Qt.LeftButton, Qt.LeftButton)
    _send(checkbox, "release", point, Qt.NoButton, Qt.LeftButton)

    assert app_state.ternary_manual_limits_enabled is False
    assert dict(app_state.ternary_manual_limits or {}) == limits_before

def test_release_seen_twice_still_applies_the_zoom(qt_ternary) -> None:
    """Regression: the first (unmappable) release copy cleared the gesture.

    Real-run logs show every release delivered twice — first to the native
    QWindow (pos() cannot be mapped by the old code), then to the canvas.
    The old handler reset the pending press on the QWindow copy, so the
    canvas copy was a no-op and the zoom never applied.
    """
    from PyQt5.QtWidgets import QWidget

    canvas, axes = qt_ternary
    start = _pixel(canvas, axes, 0.0, 1.0 / 3.0)
    end = _pixel(canvas, axes, 0.0, 2.0 / 3.0)

    _send(canvas, "press", start, Qt.LeftButton, Qt.LeftButton)

    # Simulate the native QWindow copy: an event on an object the filter
    # cannot map to canvas coordinates must not conclude (or clear) the drag.
    native = QWidget()  # unrelated top-level: _data_coords() returns None
    _send(native, "release", QPoint(5, 5), Qt.NoButton, Qt.LeftButton)

    _send(canvas, "release", end, Qt.NoButton, Qt.LeftButton)

    limits = dict(app_state.ternary_manual_limits or {})
    assert limits.get("tmin") == pytest.approx(1 / 6, abs=0.02), limits
    assert limits.get("tmax") == pytest.approx(2 / 3, abs=0.02), limits
    assert app_state.ternary_manual_limits_enabled is True
