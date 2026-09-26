"""The legend display policy lives in one place (core.legend_state)."""
from __future__ import annotations

import pytest

from core.legend_state import (
    OUTSIDE_LEGEND_LOCATIONS,
    inline_legend_location,
    is_outside_legend_location,
    wants_docked_legend,
    wants_inline_legend,
)


@pytest.mark.parametrize("location", ["outside_left", "outside_right"])
def test_the_two_sides_are_docked(location: str) -> None:
    assert is_outside_legend_location(location)
    assert wants_docked_legend(location)


@pytest.mark.parametrize("location", [None, "", "upper right", "best", "outside_top"])
def test_only_the_two_known_sides_are_docked(location) -> None:
    """A new outside_* value must not silently become a docked side."""
    assert not wants_docked_legend(location)


@pytest.mark.parametrize("position", ["upper right", "lower left", "best"])
def test_inside_positions_want_an_inline_legend(position: str) -> None:
    assert inline_legend_location(position) == position
    assert wants_inline_legend(position)


@pytest.mark.parametrize("position", [None, "", "outside_left", "outside_right", "outside_top"])
def test_outside_values_want_no_inline_legend(position) -> None:
    assert inline_legend_location(position) is None
    assert not wants_inline_legend(position)


def test_both_legends_can_be_wanted_at_once() -> None:
    """Coexistence: the inline position and the docked side are independent."""
    assert wants_inline_legend("upper right")
    assert wants_docked_legend("outside_left")


def test_the_policy_set_is_the_documented_one() -> None:
    assert OUTSIDE_LEGEND_LOCATIONS == frozenset({"outside_left", "outside_right"})
