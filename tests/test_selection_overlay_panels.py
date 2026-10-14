"""Each panel marks the sample where that panel drew it.

The overlay used to draw one panel-s data coordinates on every panel, which put a point that does
not exist into the other projections. The position now comes from the artist each panel drew for
the sample, and the caller-s coordinates are only the fallback for a single-figure window.
"""
from __future__ import annotations

import pytest

from visualization.selection_overlay import _panel_points


class _Collection:
    def __init__(self, points) -> None:
        self._points = list(points)

    def get_offsets(self):
        return list(self._points)


class _Axes:
    def __init__(self, name) -> None:
        self.name = name


class _State:
    def __init__(self, states) -> None:
        self.plot_panel_states = states


def _panel(axes, collection, mapping):
    return {
        "ax": axes,
        "collections": [collection],
        "sample_to_artist": mapping,
        "artist_to_sample": {(id(collection), position): sample for sample, (_a, position) in mapping.items()},
    }


def test_the_same_sample_is_marked_at_its_own_place_in_each_panel() -> None:
    """The two projections put the sample in different places, and each mark follows its own."""
    first_axes, second_axes = _Axes("2D"), _Axes("ternary")
    first, second = _Collection([(1.0, 1.0)]), _Collection([(7.0, 3.0)])
    state = _State([
        _panel(first_axes, first, {42: (id(first), 0)}),
        _panel(second_axes, second, {42: (id(second), 0)}),
    ])

    xs_a, ys_a = _panel_points(state, first_axes, [42], [0.0], [0.0])
    xs_b, ys_b = _panel_points(state, second_axes, [42], [0.0], [0.0])

    assert (xs_a, ys_a) == ([1.0], [1.0])
    assert (xs_b, ys_b) == ([7.0], [3.0]), "not the first panel's coordinates"
    assert xs_b != xs_a


def test_a_panel_without_the_sample_gets_no_point() -> None:
    """A panel that does not draw the sample must not invent one."""
    axes, other_axes = _Axes("2D"), _Axes("ternary")
    collection, other = _Collection([(2.0, 2.0)]), _Collection([(9.0, 9.0)])
    state = _State([
        _panel(axes, collection, {42: (id(collection), 0)}),
        _panel(other_axes, other, {}),
    ])

    xs, ys = _panel_points(state, other_axes, [42], [5.0], [5.0])

    assert (xs, ys) == ([], []), "no fabricated point"


def test_without_a_panel_record_the_caller_coordinates_are_used() -> None:
    """The ordinary single-figure window has no panel record; its own coordinates apply."""
    state = _State([])

    xs, ys = _panel_points(state, _Axes("2D"), [1], [3.0], [4.0])

    assert (xs, ys) == ([3.0], [4.0])


def test_a_sample_with_no_artist_is_left_out() -> None:
    axes = _Axes("2D")
    collection = _Collection([(1.0, 1.0)])
    state = _State([_panel(axes, collection, {42: (id(collection), 0)})])

    xs, ys = _panel_points(state, axes, [42, 99], [0.0], [0.0])

    assert (xs, ys) == ([1.0], [1.0]), "the sample that is drawn, and only it"
