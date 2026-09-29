"""Batch legend controls: Select All and Invert Selection.

The per-row checkboxes already write ``visible_groups`` through the gateway; these two
buttons do the same thing for the whole list at once.
"""
from __future__ import annotations

import pytest

from core import app_state, state_gateway

GROUPS = ["A", "B", "C"]


@pytest.fixture()
def window(main_window):
    state_gateway.sync_available_and_visible_groups(list(GROUPS))
    main_window.legend_select_all_btn.setEnabled(True)
    yield main_window
    state_gateway.set_visible_groups(None)


def _visible():
    """The visible groups; None means "everything is visible"."""
    return None if app_state.visible_groups is None else set(app_state.visible_groups)


def test_select_all_shows_every_group_again(window) -> None:
    state_gateway.set_visible_groups(["A"])
    assert _visible() == {"A"}

    window.legend_select_all_btn.click()

    assert _visible() is None, "None is how the state says every group is visible"


def test_invert_swaps_visible_and_hidden(window) -> None:
    state_gateway.set_visible_groups(["A"])

    window.legend_invert_btn.click()

    assert _visible() == {"B", "C"}


def test_invert_twice_returns_to_the_starting_selection(window) -> None:
    state_gateway.set_visible_groups(["A", "B"])

    window.legend_invert_btn.click()
    window.legend_invert_btn.click()

    assert _visible() == {"A", "B"}


def test_invert_from_all_visible_keeps_a_non_empty_selection(window) -> None:
    """An empty selection cannot be expressed, so the state deliberately stays put."""
    state_gateway.set_visible_groups(None)

    window.legend_invert_btn.click()

    assert _visible() is None


def test_both_buttons_are_present_and_labelled(window) -> None:
    assert window.legend_select_all_btn.text()
    assert window.legend_invert_btn.text()
    assert window.legend_select_all_btn.toolTip()
    assert window.legend_invert_btn.toolTip()
