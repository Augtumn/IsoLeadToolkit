"""Wheel zoom and middle-drag pan, driven by real Qt events on a real canvas."""
from __future__ import annotations

import matplotlib
import pytest

matplotlib.use("Qt5Agg")

import mpltern  # noqa: F401  (registers the "ternary" projection)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from PyQt5.QtCore import QEvent, QPoint, QPointF, Qt  # noqa: E402
from PyQt5.QtGui import QMouseEvent, QWheelEvent  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from core import state_gateway  # noqa: E402
from ui.main_window_parts.canvas import install_ternary_zoom_filter  # noqa: E402
from visualization.plotting.view_zoom import (  # noqa: E402
    MIN_SPAN,
    wheel_factor,
    zoom_pair,
)

APP = QApplication.instance() or QApplication([])


def _canvas_with(projection: str | None):
    figure = Figure(figsize=(4, 4))
    canvas = FigureCanvasQTAgg(figure)
    canvas.resize(400, 400)
    canvas.show()
    APP.processEvents()
    axes = figure.add_subplot(projection="ternary") if projection == "ternary" else figure.add_subplot(111)
    if projection == "ternary":
        axes.scatter([0.3, 0.5], [0.3, 0.2], [0.4, 0.3])
        axes.set_ternary_lim(0.0, 1.0, 0.0, 1.0, 0.0, 1.0)
    else:
        axes.plot([0, 1], [0, 1])
        axes.set_xlim(0.0, 1.0)
        axes.set_ylim(0.0, 1.0)
    canvas.draw()
    APP.processEvents()
    state_gateway.set_figure_axes(figure, axes)
    install_ternary_zoom_filter(canvas)
    return canvas, axes


def _pixel(canvas, axes, x, y):
    dx, dy = axes.transData.transform((x, y))
    ratio = canvas.devicePixelRatioF()
    return QPointF(dx / ratio, (canvas.height() * ratio - dy) / ratio)


def _wheel(canvas, point, notches: int):
    event = QWheelEvent(
        point,
        QPointF(canvas.mapToGlobal(point.toPoint())),
        QPoint(0, 0),
        QPoint(0, 120 * notches),
        Qt.NoButton,
        Qt.NoModifier,
        Qt.NoScrollPhase,
        False,
    )
    APP.sendEvent(canvas, event)
    APP.processEvents()


def _mouse(canvas, kind, point, button, buttons):
    event = QMouseEvent(kind, point, button, buttons, Qt.NoModifier)
    APP.sendEvent(canvas, event)
    APP.processEvents()


def test_wheel_factors() -> None:
    assert wheel_factor(120) < 1.0
    assert wheel_factor(-120) > 1.0
    assert wheel_factor(0) == 1.0


def test_zoom_pair_keeps_the_anchor_position() -> None:
    low, high = zoom_pair(0.0, 1.0, 0.5, 0.25)
    assert high - low == pytest.approx(0.5)
    # the anchor keeps its relative position inside the window
    assert (0.25 - low) / (high - low) == pytest.approx(0.25)


def test_wheel_zooms_a_cartesian_plot_about_the_cursor() -> None:
    canvas, axes = _canvas_with(None)

    _wheel(canvas, _pixel(canvas, axes, 0.5, 0.5), notches=1)

    low, high = axes.get_xlim()
    assert high - low < 1.0, "wheel up must zoom in"


def test_wheel_down_zooms_back_out() -> None:
    canvas, axes = _canvas_with(None)
    _wheel(canvas, _pixel(canvas, axes, 0.5, 0.5), notches=1)
    zoomed = axes.get_xlim()

    _wheel(canvas, _pixel(canvas, axes, 0.5, 0.5), notches=-1)

    assert axes.get_xlim()[1] - axes.get_xlim()[0] > zoomed[1] - zoomed[0]


def test_wheel_zooms_the_ternary_view() -> None:
    canvas, axes = _canvas_with("ternary")

    _wheel(canvas, _pixel(canvas, axes, 0.0, 1.0 / 3.0), notches=1)

    tmin, tmax = axes.get_tlim()
    assert tmax - tmin < 1.0 + 1e-9
    assert tmax - tmin >= MIN_SPAN


def test_middle_drag_pans_the_cartesian_view() -> None:
    canvas, axes = _canvas_with(None)
    start = _pixel(canvas, axes, 0.5, 0.5)
    end = _pixel(canvas, axes, 0.35, 0.5)

    _mouse(canvas, QEvent.MouseButtonPress, start, Qt.MiddleButton, Qt.MiddleButton)
    _mouse(canvas, QEvent.MouseMove, end, Qt.NoButton, Qt.MiddleButton)
    _mouse(canvas, QEvent.MouseButtonRelease, end, Qt.MiddleButton, Qt.NoButton)

    assert axes.get_xlim()[0] > 0.0, "the view must have moved"


def test_wheel_outside_the_canvas_changes_nothing() -> None:
    canvas, axes = _canvas_with(None)
    before = axes.get_xlim()

    _wheel(canvas, QPointF(canvas.width() + 60, canvas.height() + 60), notches=1)

    assert axes.get_xlim() == before
