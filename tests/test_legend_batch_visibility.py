"""Batch legend controls: Select All and Invert Selection.

The per-row checkboxes already write ``visible_groups`` through the gateway; these two
buttons do the same thing for the whole list at once.  ``None`` means "every group is
visible" and an empty list means "nothing is visible" - the latter is a real state, so
unticking everything (or inverting a full selection) is allowed and shows an empty plot.
"""
from __future__ import annotations

import pandas as pd
import pytest
from PyQt5.QtCore import Qt

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


def test_invert_from_all_visible_shows_nothing(window) -> None:
    """An empty selection is a real selection, so inverting everything hides everything."""
    state_gateway.set_visible_groups(None)

    window.legend_invert_btn.click()

    assert _visible() == set(), "inverting a full selection hides every group"


def test_invert_from_nothing_shows_everything_again(window) -> None:
    state_gateway.set_visible_groups([])

    window.legend_invert_btn.click()

    assert _visible() is None, "the inverse of nothing visible is every group"


def test_unticking_the_last_group_leaves_nothing_visible(window) -> None:
    """The per-row checkbox path reaches the empty selection too."""
    frame = pd.DataFrame({"Group": list(GROUPS)})
    state_gateway.set_dataframe_and_source(frame, file_path=None, sheet_name=None)
    state_gateway.set_group_data_columns(["Group"], [])
    state_gateway.set_last_group_col("Group")
    state_gateway.sync_available_and_visible_groups(list(GROUPS))
    state_gateway.set_visible_groups(["C"])

    for group in GROUPS:
        window._on_group_checkbox_change(group, Qt.Unchecked)

    assert _visible() == set(), "unticking the last visible group must not re-show it"
    # The render that follows must not turn the empty selection back into "all visible".
    assert app_state.visible_groups == []


def test_both_buttons_are_present_and_labelled(window) -> None:
    assert window.legend_select_all_btn.text()
    assert window.legend_invert_btn.text()
    assert window.legend_select_all_btn.toolTip()
    assert window.legend_invert_btn.toolTip()
