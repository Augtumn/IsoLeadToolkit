"""Adding one axes to a figure, with the projection a mode needs.

Panels are independent figures, one axes each; this is the helper that gives a figure its axes,
and the figure is a real Matplotlib figure on the Agg backend, so no window is needed.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pytest

from visualization.plotting.core import _add_axes


@pytest.fixture()
def figure():
    fig = plt.figure(figsize=(4, 3))
    try:
        yield fig
    finally:
        plt.close(fig)


def test_a_plain_mode_gets_an_ordinary_axes(figure) -> None:
    axis = _add_axes(figure, "2D", 111)

    assert getattr(axis, "name", "") != "ternary"
    assert len(figure.axes) == 1


def test_a_ternary_mode_gets_a_ternary_axes(figure) -> None:
    axis = _add_axes(figure, "Ternary", 111)

    assert getattr(axis, "name", "") == "ternary"


def test_a_3d_mode_gets_a_3d_axes(figure) -> None:
    axis = _add_axes(figure, "3D", 111)

    assert getattr(axis, "name", "") == "3d"


def test_the_position_is_honoured(figure) -> None:
    first = _add_axes(figure, "2D", 121)
    second = _add_axes(figure, "2D", 122)

    assert first is not second
    assert first.get_position().x0 < second.get_position().x0
