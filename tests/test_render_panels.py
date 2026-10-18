"""One render cycle drawing several independent figures.

The use case is driven with stand-in window records, a stand-in dispatcher and a stand-in
gateway, so what is checked is the panel loop: every panel is drawn in its own mode, into its
own figure and axes, and each panel keeps the artists and both directions of the sample map that
belong to it - that bookkeeping is what the hover linking is built on.
"""
from __future__ import annotations

from typing import Any

import pytest

from core.panel_record import PanelRecord

from application.use_cases.render_plot import RenderPlotUseCase


class _FakeState:
    def __init__(self, windows=None) -> None:
        self.scatter_collections: list[Any] = []
        self.artist_to_sample: dict[tuple[int, int], int] = {}
        self.plot_panel_states: list[dict] = []
        self.plot_panel_windows: list[dict] = list(windows or [])
        self.fig: Any = "initial-figure"


class _FakeGateway:
    def __init__(self) -> None:
        self.axes: list[Any] = []
        self.figures: list[Any] = []

    def set_axis(self, axis) -> None:
        self.axes.append(axis)

    def set_figure(self, figure) -> None:
        self.figures.append(figure)


@pytest.fixture()
def use_case(monkeypatch):
    gateway = _FakeGateway()
    monkeypatch.setattr("core.state_gateway", gateway, raising=False)
    case = RenderPlotUseCase.__new__(RenderPlotUseCase)
    return case, gateway


def _windows(count):
    return [PanelRecord({"figure": f"figure-{i}", "axes": f"axes-{i}"}) for i in range(count)]


def test_every_panel_is_drawn_in_its_own_mode_and_figure(use_case) -> None:
    case, gateway = use_case
    windows = _windows(2)
    case._state = _FakeState(windows)
    seen: list[tuple[str, Any]] = []

    def dispatch(group_col, selected_2d, selected_3d, mode=None):
        seen.append((mode, case._state.fig))
        case._state.artist_to_sample = {(id(windows[len(seen) - 1]), 0): 0}
        case._state.scatter_collections = [object()]
        return True, False

    case._dispatch_render = dispatch
    rendered, pending = case._render_panels(
        ["2D", "Ternary"], "Site", ["a", "b"], ["a", "b", "c"]
    )

    assert [mode for mode, _figure in seen] == ["2D", "Ternary"], "each panel gets its mode"
    assert rendered is True and pending is False
    assert gateway.axes == ["axes-0", "axes-1", "axes-0"], "the first panel is left active"
    assert gateway.figures == ["figure-0", "figure-1", "figure-0"], (
        "each panel is drawn into its own figure, and the first is left active"
    )
    assert [state["mode"] for state in case._state.plot_panel_states] == ["2D", "Ternary"]


def test_the_reverse_map_is_recorded_for_each_panel(use_case) -> None:
    case, _gateway = use_case
    windows = _windows(2)
    case._state = _FakeState(windows)
    calls = {"n": 0}

    def dispatch(group_col, selected_2d, selected_3d, mode=None):
        index = calls["n"]
        calls["n"] += 1
        case._state.artist_to_sample = {(id(windows[index]), 5): 42}
        case._state.scatter_collections = [object()]
        return True, False

    case._dispatch_render = dispatch

    case._render_panels(["2D", "2D"], "Site", ["a", "b"], ["a", "b", "c"])

    first, second = case._state.plot_panel_states
    assert first["sample_to_artist"] == {42: (id(windows[0]), 5)}
    assert second["sample_to_artist"] == {42: (id(windows[1]), 5)}


def test_a_partial_failure_still_draws_the_other_panels(use_case) -> None:
    case, _gateway = use_case
    case._state = _FakeState(_windows(2))
    modes: list[str] = []

    def dispatch(group_col, selected_2d, selected_3d, mode=None):
        modes.append(mode)
        case._state.artist_to_sample = {}
        case._state.scatter_collections = []
        return mode == "2D", False

    case._dispatch_render = dispatch

    rendered, pending = case._render_panels(
        ["2D", "3D"], "Site", ["a", "b"], ["a", "b", "c"]
    )

    assert modes == ["2D", "3D"], "a failing panel does not stop the next one"
    assert rendered is True, "one panel drew, so the cycle counts as rendered"
    assert pending is False


def test_without_a_window_for_every_panel_nothing_is_half_drawn(use_case) -> None:
    case, _gateway = use_case
    case._state = _FakeState(_windows(1))
    called: list[str] = []
    case._dispatch_render = lambda *a, **k: called.append("x") or (True, False)

    assert case._render_panels(["2D", "2D"], "Site", ["a", "b"], ["a", "b", "c"]) == (False, False)
    assert called == [], "nothing is drawn when the windows do not match the panels"
    assert case._state.plot_panel_states == []
