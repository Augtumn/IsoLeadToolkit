"""Framing the data so the points fill the window.

The toolbar's fit action zooms every panel to its own points. The arithmetic is checked on real
Matplotlib axes with real collections, so no window is needed.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from ui.main_window_parts.canvas import MainWindowCanvasMixin
from visualization.plotting.view_fit import scatter_bounds as _scatter_bounds


@pytest.fixture()
def axes():
    figure = plt.figure(figsize=(4, 3))
    axis = figure.add_subplot(111)
    try:
        yield axis
    finally:
        plt.close(figure)


def test_the_bounds_come_from_the_drawn_points(axes) -> None:
    axes.scatter([1.0, 2.0, 3.0], [10.0, 20.0, 30.0])

    xs, ys, zs = _scatter_bounds(axes)

    assert (min(xs), max(xs)) == (1.0, 3.0)
    assert (min(ys), max(ys)) == (10.0, 30.0)
    assert zs == []


def test_points_that_are_not_finite_are_left_out(axes) -> None:
    axes.scatter([1.0, float("nan"), 3.0], [1.0, 2.0, float("inf")])

    xs, ys, _zs = _scatter_bounds(axes)

    assert xs == [1.0] and ys == [1.0]


def test_fitting_frames_the_points_with_a_margin(axes) -> None:
    axes.scatter([0.0, 10.0], [0.0, 100.0])

    assert MainWindowCanvasMixin._fit_one_axes("2D", axes) is True

    x0, x1 = axes.get_xlim()
    y0, y1 = axes.get_ylim()
    assert x0 < 0.0 and x1 > 10.0, "the points fit inside the view"
    assert y0 < 0.0 and y1 > 100.0
    assert x1 - x0 < 12.0, "and it is a fit, not a free-for-all"


def test_a_single_point_still_gets_a_window(axes) -> None:
    axes.scatter([5.0], [5.0])

    assert MainWindowCanvasMixin._fit_one_axes("2D", axes) is True

    x0, x1 = axes.get_xlim()
    assert x1 > x0, "a degenerate span is widened rather than left at zero width"


def test_an_empty_axes_is_not_touched(axes) -> None:
    before = axes.get_xlim()

    assert MainWindowCanvasMixin._fit_one_axes("2D", axes) is False

    assert axes.get_xlim() == before


def test_a_ternary_panel_is_given_the_whole_triangle(axes) -> None:
    """A ternary diagram has no data limits to fit; the full triangle is its widest view."""
    calls: list[tuple] = []

    class _Ternary:
        name = "ternary"

        def set_ternary_lim(self, *limits) -> None:
            calls.append(limits)

    assert MainWindowCanvasMixin._fit_one_axes("Ternary", _Ternary()) is True
    assert calls == [(0.0, 1.0, 0.0, 1.0, 0.0, 1.0)]
