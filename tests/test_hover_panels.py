"""A mark set by a double click appears in every panel.

The mark is per sample, not per group: the sample chosen is marked in each figure that draws it,
and each panel keeps its own artist for it. Hovering is not involved - it only shows the tooltip.
"""
from __future__ import annotations

import pytest

from core import app_state
from visualization.event_handlers import pointer_events as pe


class _Collection:
    def __init__(self, samples) -> None:
        self.samples = list(samples)
        self._sizes = [10.0 for _ in self.samples]
        self._widths = [1.0 for _ in self.samples]

    def get_sizes(self):
        return list(self._sizes)

    def set_sizes(self, sizes):
        self._sizes = [float(size) for size in sizes]

    def get_linewidths(self):
        return list(self._widths)

    def set_linewidths(self, widths):
        self._widths = [float(width) for width in widths]

    def contains(self, event):
        if event is None:
            return False, {}
        return True, {"ind": [getattr(event, "index", 0)]}


class _Event:
    def __init__(self, axes, index=0) -> None:
        self.inaxes = axes
        self.index = index
        self.xdata = 0.0
        self.ydata = 0.0


@pytest.fixture()
def panels(monkeypatch):
    """Two panels drawing the same samples, with their own collection each."""
    first, second = _Collection([0, 1]), _Collection([0, 1])
    states = [
        {"mode": "2D", "ax": f"axes-{index}", "collections": [collection],
         "artist_to_sample": {(id(collection), j): j for j in range(2)},
         "sample_to_artist": {j: (id(collection), j) for j in range(2)}}
        for index, collection in enumerate((first, second))
    ]
    previous = list(app_state.plot_panel_states)
    app_state.plot_panel_states[:] = states
    try:
        yield states, first, second
    finally:
        app_state.plot_panel_states[:] = previous
        pe._hover_highlighter.clear()


def test_the_targets_cover_every_panel(panels) -> None:
    _states, first, second = panels

    targets = pe._panel_highlight_targets(1)

    assert (first, 1) in targets and (second, 1) in targets


def test_marking_a_sample_marks_it_in_every_panel(panels) -> None:
    _states, first, second = panels

    assert pe._hover_highlighter.highlight_sample(1, pe._panel_highlight_targets(1)) is True

    assert first.get_sizes()[1] > 10.0 and second.get_sizes()[1] > 10.0
    assert first.get_sizes()[0] == 10.0 and second.get_sizes()[0] == 10.0, "only that sample"


def test_the_mark_thickens_the_outline_too(panels) -> None:
    _states, first, second = panels

    pe._hover_highlighter.highlight_sample(1, pe._panel_highlight_targets(1))

    assert first.get_linewidths()[1] > 1.0 and second.get_linewidths()[1] > 1.0


def test_clearing_restores_every_panel(panels) -> None:
    _states, first, second = panels
    pe._hover_highlighter.highlight_sample(1, pe._panel_highlight_targets(1))

    assert pe._hover_highlighter.clear() is True

    assert first.get_sizes() == [10.0, 10.0] and second.get_sizes() == [10.0, 10.0]
    assert first.get_linewidths() == [1.0, 1.0] and second.get_linewidths() == [1.0, 1.0]


def test_a_sample_no_panel_draws_clears_rather_than_leaving_a_stale_mark(panels) -> None:
    _states, first, _second = panels
    pe._hover_highlighter.highlight_sample(1, pe._panel_highlight_targets(1))

    assert pe._hover_highlighter.highlight_sample(99, []) is True
    assert first.get_sizes() == [10.0, 10.0]
