"""The hovered point is drawn larger, and only redrawn when that changes."""
from __future__ import annotations

import pytest

from visualization.plotting.highlight import HOVER_SCALE, HoverHighlighter


class _FakeCollection:
    """Records set_sizes() calls, like a scatter collection would."""

    def __init__(self, sizes):
        self._sizes = list(sizes)
        self.writes: list[list[float]] = []

    def get_sizes(self):
        return self._sizes

    def set_sizes(self, sizes):
        self.writes.append(list(sizes))
        self._sizes = list(sizes)


def test_highlighting_enlarges_exactly_one_point() -> None:
    collection = _FakeCollection([10.0, 10.0, 10.0])
    highlighter = HoverHighlighter()

    assert highlighter.highlight(collection, 1) is True

    assert collection.get_sizes()[1] == pytest.approx(10.0 * HOVER_SCALE)
    assert collection.get_sizes()[0] == pytest.approx(10.0)
    assert collection.get_sizes()[2] == pytest.approx(10.0)


def test_the_same_point_is_not_rewritten() -> None:
    collection = _FakeCollection([10.0, 10.0])
    highlighter = HoverHighlighter()
    highlighter.highlight(collection, 0)
    writes = len(collection.writes)

    assert highlighter.highlight(collection, 0) is False
    assert len(collection.writes) == writes, "no redraw for an unchanged hover"


def test_moving_to_another_point_restores_the_first() -> None:
    collection = _FakeCollection([10.0, 10.0])
    highlighter = HoverHighlighter()
    highlighter.highlight(collection, 0)

    assert highlighter.highlight(collection, 1) is True

    sizes = collection.get_sizes()
    assert sizes[0] == pytest.approx(10.0), "the old point is back to its base size"
    assert sizes[1] == pytest.approx(10.0 * HOVER_SCALE)


def test_clearing_restores_the_base_sizes() -> None:
    collection = _FakeCollection([5.0, 7.0])
    highlighter = HoverHighlighter()
    highlighter.highlight(collection, 1)

    assert highlighter.clear() is True

    assert collection.get_sizes() == [5.0, 7.0]
    assert highlighter.current is None


def test_clearing_without_a_highlight_is_a_no_op() -> None:
    highlighter = HoverHighlighter()

    assert highlighter.clear() is False


def test_a_collection_without_sizes_is_ignored() -> None:
    collection = _FakeCollection([])
    highlighter = HoverHighlighter()

    assert highlighter.highlight(collection, 0) is False
    assert collection.writes == []


def test_an_out_of_range_index_is_ignored() -> None:
    collection = _FakeCollection([4.0])
    highlighter = HoverHighlighter()

    assert highlighter.highlight(collection, 5) is False


# --- Several panels showing the same sample ---------------------------------------------
# The identity used across panels is the sample index (the row of the data), so the cursor
# can sit in one panel while every other panel highlights the sample it draws.


def test_one_sample_is_highlighted_in_every_panel() -> None:
    first = _FakeCollection([10.0, 10.0, 10.0])
    second = _FakeCollection([20.0, 20.0])
    highlighter = HoverHighlighter()

    assert highlighter.highlight_sample(2, [(first, 2), (second, 0)]) is True

    assert first.get_sizes() == [10.0, 10.0, pytest.approx(10.0 * HOVER_SCALE)]
    assert second.get_sizes() == [pytest.approx(20.0 * HOVER_SCALE), 20.0]
    assert highlighter.current_sample == 2


def test_the_highlight_is_restored_in_every_panel() -> None:
    first = _FakeCollection([10.0, 10.0])
    second = _FakeCollection([20.0, 20.0])
    highlighter = HoverHighlighter()
    highlighter.highlight_sample(1, [(first, 1), (second, 1)])

    assert highlighter.clear() is True

    assert first.get_sizes() == [10.0, 10.0]
    assert second.get_sizes() == [20.0, 20.0]
    assert highlighter.current_sample is None


def test_moving_inside_the_same_sample_asks_for_no_redraw() -> None:
    first = _FakeCollection([10.0, 10.0])
    highlighter = HoverHighlighter()
    assert highlighter.highlight_sample(0, [(first, 0)]) is True

    assert highlighter.highlight_sample(0, [(first, 0)]) is False


def test_a_sample_no_panel_draws_clears_the_highlight() -> None:
    first = _FakeCollection([10.0, 10.0])
    highlighter = HoverHighlighter()
    highlighter.highlight_sample(0, [(first, 0)])

    assert highlighter.highlight_sample(7, []) is True

    assert first.get_sizes() == [10.0, 10.0]
    assert highlighter.current_sample is None


def test_a_panel_that_cannot_draw_the_sample_is_skipped() -> None:
    first = _FakeCollection([10.0, 10.0])
    too_short = _FakeCollection([20.0])
    highlighter = HoverHighlighter()

    assert highlighter.highlight_sample(1, [(first, 1), (too_short, 5)]) is True

    assert first.get_sizes()[1] == pytest.approx(10.0 * HOVER_SCALE)
    assert too_short.get_sizes() == [20.0], "an out-of-range index is skipped, not fatal"


def test_every_panel_is_restored_when_the_highlight_moves_on() -> None:
    first = _FakeCollection([10.0, 10.0])
    second = _FakeCollection([20.0, 20.0])
    highlighter = HoverHighlighter()
    highlighter.highlight_sample(0, [(first, 0), (second, 0)])

    assert highlighter.highlight_sample(1, [(first, 1), (second, 1)]) is True

    assert first.get_sizes() == [10.0, pytest.approx(10.0 * HOVER_SCALE)]
    assert second.get_sizes() == [20.0, pytest.approx(20.0 * HOVER_SCALE)]
