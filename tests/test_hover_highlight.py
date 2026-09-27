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
