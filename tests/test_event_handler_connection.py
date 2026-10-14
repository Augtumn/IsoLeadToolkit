"""Event handlers are connected per canvas.

A window that shows several figures gives each one its own canvas, and a matplotlib handler
connected to one canvas never sees another's events - so the connection has to be per canvas.
The single-figure path is unchanged: with no canvas given, the active figure's is used.
"""
from __future__ import annotations

from typing import Any

import pytest

from ui.app_parts import plotting as plotting_part


class _Canvas:
    def __init__(self, name: str = "canvas") -> None:
        self.name = name
        self.connected: list[str] = []

    def mpl_connect(self, event: str, handler) -> int:
        self.connected.append(event)
        return len(self.connected)


class _Figure:
    def __init__(self, canvas: _Canvas) -> None:
        self.canvas = canvas


class _Host:
    """The mixin's host: it only needs the method and the module-level state."""

    _connect_event_handlers = plotting_part.Qt5AppPlottingMixin._connect_event_handlers


@pytest.fixture()
def active_figure(monkeypatch):
    canvas = _Canvas("active")
    monkeypatch.setattr(plotting_part, "app_state", type("S", (), {"fig": _Figure(canvas)})(), raising=False)
    return canvas


def test_it_connects_the_three_interactions(active_figure) -> None:
    assert _Host()._connect_event_handlers() is True

    assert active_figure.connected == [
        "motion_notify_event",
        "button_press_event",
        "button_press_event",
    ], "hover, click and legend click"


def test_a_given_canvas_is_the_one_connected(active_figure) -> None:
    """Each figure of a multi-figure window passes its own canvas."""
    other = _Canvas("second")

    assert _Host()._connect_event_handlers(other) is True

    assert other.connected, "the canvas that was passed in is connected"
    assert not active_figure.connected, "and the active one is left alone"


def test_without_any_canvas_it_reports_instead_of_raising(monkeypatch) -> None:
    monkeypatch.setattr(plotting_part, "app_state", type("S", (), {"fig": None})(), raising=False)

    assert _Host()._connect_event_handlers() is False
