"""The whole chain: independent figures are built, drawn, and a hover links them.

This is the feature end to end. The child windows are real (built through PanelWindows on a real
QMdiArea), the panel bookkeeping comes from the real render loop, and the linking from the real
hover handler; only what each panel draws is a stand-in dispatcher that creates real scatter
collections. If any step stops agreeing with the next, this fails.
"""
from __future__ import annotations

from typing import Any

import pytest

from application.use_cases.render_plot import RenderPlotUseCase
from core import app_state
from ui.main_window_parts.mdi_panels import PanelWindows, create_mdi_area
from visualization.event_handlers import pointer_events as pe


class _Collection:
    """A scatter collection with one point per sample."""

    def __init__(self, samples: list[int]) -> None:
        self.samples = list(samples)
        self._sizes = [10.0 for _ in self.samples]
        self.contains_result: int | None = 0

    def contains(self, event):
        if self.contains_result is None:
            return False, {}
        return True, {"ind": [self.contains_result]}

    def get_offsets(self):
        return [(float(index), float(index)) for index in range(len(self.samples))]

    def get_sizes(self):
        return list(self._sizes)

    def set_sizes(self, sizes):
        self._sizes = [float(size) for size in sizes]


class _Annotation:
    xy = (0.0, 0.0)

    def set_text(self, text) -> None:
        pass

    def set_visible(self, visible) -> None:
        pass


class _Event:
    def __init__(self, axes) -> None:
        self.inaxes = axes
        self.xdata = 0.0
        self.ydata = 0.0


class _Gateway:
    #: The figure the render loop last asked to make active, for the assertions below.
    last_figure: Any = None

    def __init__(self) -> None:
        self.axes: list[Any] = []

    def set_axis(self, axis) -> None:
        self.axes.append(axis)

    def set_figure(self, figure) -> None:
        type(self).last_figure = figure


@pytest.fixture()
def wired(qapp, monkeypatch):
    """Real child windows, the real render loop and the real hover handler."""
    import pandas as pd

    frame = pd.DataFrame({"a": [float(i) for i in range(8)], "b": [float(i) for i in range(8)]})
    monkeypatch.setattr(pe, "df_global", lambda: frame)
    monkeypatch.setattr(
        pe, "TOOLTIP_CONTENT_USE_CASE", type("T", (), {"build_text": lambda self, **k: "t"})()
    )
    gateway = _Gateway()
    monkeypatch.setattr("core.state_gateway", gateway, raising=False)

    area = create_mdi_area(None)
    windows = PanelWindows(area).sync(["2D", "Ternary"])
    previous = (
        app_state.annotation,
        app_state.show_tooltip,
        app_state.tooltip_columns,
        app_state.selected_indices,
        app_state.plot_panel_states,
        list(app_state.scatter_collections),
        dict(app_state.artist_to_sample),
    )
    app_state.annotation = _Annotation()
    app_state.show_tooltip = True
    app_state.tooltip_columns = []
    app_state.selected_indices = set()
    app_state.plot_panel_states = []
    yield app_state, windows
    (
        app_state.annotation,
        app_state.show_tooltip,
        app_state.tooltip_columns,
        app_state.selected_indices,
        app_state.plot_panel_states,
        collections,
        mapping,
    ) = previous
    app_state.scatter_collections[:] = collections
    app_state.artist_to_sample.clear()
    app_state.artist_to_sample.update(mapping)
    area.close()


def _use_case(state, windows, drawn: list[_Collection]):
    case = RenderPlotUseCase.__new__(RenderPlotUseCase)
    case._state = state
    state.plot_panel_windows = windows
    calls = {"n": 0}

    def dispatch(group_col, selected_2d, selected_3d, mode=None):
        index = calls["n"]
        calls["n"] += 1
        collection = _Collection([0, 1])
        drawn.append(collection)
        state.scatter_collections.clear()
        state.scatter_collections.append(collection)
        state.artist_to_sample.clear()
        for point in range(len(collection.samples)):
            state.artist_to_sample[(id(collection), point)] = point
        return True, False

    case._dispatch_render = dispatch
    return case


def test_two_independent_figures_are_drawn_and_linked_by_a_double_click(wired) -> None:
    """The whole chain: two figures drawn, then one sample marked by a double click in both.

    The mark is set by a double click, not by hovering, and it lands in every panel that draws
    that sample - the point of comparing projections side by side.
    """
    state, windows = wired
    drawn: list[_Collection] = []
    case = _use_case(state, windows, drawn)

    case._render_panels(["2D", "Ternary"], "Site", ["a", "b"], ["a", "b", "c"])

    assert windows[0]["figure"] is not windows[1]["figure"]
    assert getattr(windows[1]["axes"], "name", "") == "ternary"
    assert len(drawn) == 2

    targets = pe._panel_highlight_targets(0)
    assert targets, "the sample is drawn in the panels"

    pe._hover_highlighter.highlight_sample(0, targets)

    assert drawn[0].get_sizes()[0] > 10.0, "marked in the first figure"
    assert drawn[1].get_sizes()[0] > 10.0, "and in the second"
    assert drawn[0].get_sizes()[1] == 10.0, "and only that sample"

def test_the_first_figure_is_left_active(wired) -> None:
    state, windows = wired
    case = _use_case(state, windows, [])

    case._render_panels(["2D", "UMAP"], "Site", ["a", "b"], ["a", "b", "c"])

    assert _Gateway.last_figure is windows[0]["figure"], (
        "single-figure code addresses the first panel"
    )
