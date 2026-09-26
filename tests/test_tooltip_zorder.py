"""The hover tooltip stays above every data layer."""
from __future__ import annotations

import matplotlib
import pytest

matplotlib.use("Agg")

from matplotlib.figure import Figure  # noqa: E402
from PyQt5.QtWidgets import QApplication, QListWidget  # noqa: E402

from core import state_gateway  # noqa: E402
from ui.main_window_parts.legend_core import (  # noqa: E402
    MainWindowLegendCoreMixin,
    raise_tooltip_above_data,
)

_APP = QApplication.instance() or QApplication([])


def _scene(annotation_zorder: float = 15, data_zorder: float = 40):
    figure = Figure()
    axes = figure.add_subplot(111)
    axes.scatter([1.0], [1.0], zorder=data_zorder)
    annotation = axes.annotate(
        "tooltip",
        xy=(0, 0),
        bbox=dict(boxstyle="round"),
        arrowprops=dict(arrowstyle="->"),
        zorder=annotation_zorder,
    )
    return figure, axes, annotation


def test_the_tooltip_is_raised_above_every_data_layer() -> None:
    _figure, axes, annotation = _scene()

    raise_tooltip_above_data(axes, annotation)

    assert annotation.get_zorder() > 40
    assert annotation.arrow_patch.get_zorder() == 40, "the arrow stays just below the box"


def test_raising_twice_does_not_inflate_the_zorder() -> None:
    _figure, axes, annotation = _scene()

    raise_tooltip_above_data(axes, annotation)
    first = annotation.get_zorder()
    raise_tooltip_above_data(axes, annotation)

    assert annotation.get_zorder() == first


def test_missing_axes_or_tooltip_is_ignored() -> None:
    _figure, axes, annotation = _scene()

    raise_tooltip_above_data(None, annotation)
    raise_tooltip_above_data(axes, None)

    assert annotation.get_zorder() == 15


class _Host(MainWindowLegendCoreMixin):
    """An empty legend list is enough: the inner pass returns early."""


def test_the_legend_order_pass_leaves_the_tooltip_on_top() -> None:
    """Group z-orders are reassigned from the legend order; the tooltip follows."""
    figure, axes, annotation = _scene()
    state_gateway.set_figure_axes(figure, axes)
    state_gateway.set_annotation(annotation)
    host = _Host()
    host._legend_list = QListWidget()

    host._apply_legend_z_order()

    assert annotation.get_zorder() > 40, "the legend pass must not bury the tooltip"


def test_bring_to_front_keeps_the_tooltip_on_top() -> None:
    """Raising a group also runs the legend pass, so the tooltip survives it."""
    figure, axes, annotation = _scene()
    state_gateway.set_figure_axes(figure, axes)
    state_gateway.set_annotation(annotation)

    axes.collections[0].set_zorder(99)  # what _bring_to_front() does to a group

    class _Host2(MainWindowLegendCoreMixin):
        pass

    host = _Host2()
    host._legend_list = QListWidget()
    host._apply_legend_z_order()

    assert annotation.get_zorder() > axes.collections[0].get_zorder()


@pytest.mark.parametrize("data_zorder", [5, 15, 60, 1000])
def test_the_tooltip_wins_at_any_data_zorder(data_zorder: float) -> None:
    _figure, axes, annotation = _scene(data_zorder=data_zorder)

    raise_tooltip_above_data(axes, annotation)

    assert annotation.get_zorder() > data_zorder
