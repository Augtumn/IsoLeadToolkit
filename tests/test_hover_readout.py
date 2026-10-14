"""The hover readout shows the tooltip; the mark belongs to the double click.

Asked for: hovering must not highlight - it was hit and miss - and the sample chosen by a double
click stays marked in every panel until it is cleared.
"""
from __future__ import annotations

from typing import Any

import pytest

from core import app_state
from ui.main_window_parts.canvas import MainWindowCanvasMixin
from visualization.event_handlers import pointer_events as pe


class _Collection:
    def __init__(self) -> None:
        self._sizes = [10.0, 10.0]

    def get_sizes(self):
        return list(self._sizes)

    def set_sizes(self, sizes):
        self._sizes = [float(size) for size in sizes]

    def get_linewidths(self):
        return [1.0, 1.0]

    def set_linewidths(self, widths):
        pass


class _Canvas:
    def __init__(self) -> None:
        self.ids = 0

    def draw_idle(self) -> None:
        self.ids += 1


class _Figure:
    def __init__(self) -> None:
        self.canvas = _Canvas()


class _Annotation:
    def __init__(self) -> None:
        self._visible = True

    def get_visible(self) -> bool:
        return self._visible

    def set_visible(self, visible) -> None:
        self._visible = bool(visible)


class _Gateway:
    def __init__(self) -> None:
        self.show_tooltip: Any = "unset"

    def set_show_tooltip(self, show: bool) -> None:
        self.show_tooltip = bool(show)


@pytest.fixture()
def readout(monkeypatch):
    collection = _Collection()
    pe._hover_highlighter.highlight(collection, 1)
    figure = _Figure()
    annotation = _Annotation()
    previous = (app_state.fig, app_state.annotation)
    app_state.fig = figure
    app_state.annotation = annotation
    try:
        yield collection, figure, annotation
    finally:
        pe._hover_highlighter.clear()
        app_state.fig, app_state.annotation = previous


def test_switching_the_readout_off_hides_the_tooltip(readout) -> None:
    _collection, _figure, annotation = readout

    assert pe.clear_hover_highlight() is True

    assert annotation.get_visible() is False, "the tooltip goes at once"


def test_switching_the_readout_off_keeps_the_marked_sample(readout) -> None:
    """The mark belongs to the double click, so the readout must not drop it."""
    collection, _figure, _annotation = readout

    pe.clear_hover_highlight()

    assert collection.get_sizes()[1] > 10.0, "the marked sample is still marked"


def test_clearing_twice_changes_nothing(readout) -> None:
    _collection, _figure, annotation = readout
    pe.clear_hover_highlight()
    annotation.set_visible(True)

    assert pe.clear_hover_highlight() is True, "the tooltip is shown again, so it is hidden again"


def test_the_switch_writes_the_state(readout, monkeypatch) -> None:
    gateway = _Gateway()
    monkeypatch.setattr("ui.main_window_parts.canvas.state_gateway", gateway, raising=False)
    host = MainWindowCanvasMixin.__new__(MainWindowCanvasMixin)

    host._toggle_hover_readout(True)
    assert gateway.show_tooltip is True

    host._toggle_hover_readout(False)
    assert gateway.show_tooltip is False


def test_switching_off_leaves_the_mark_alone(readout, monkeypatch) -> None:
    collection, _figure, _annotation = readout
    monkeypatch.setattr("ui.main_window_parts.canvas.state_gateway", _Gateway(), raising=False)
    host = MainWindowCanvasMixin.__new__(MainWindowCanvasMixin)

    host._toggle_hover_readout(False)

    assert collection.get_sizes()[1] > 10.0, "the chosen sample stays marked"
