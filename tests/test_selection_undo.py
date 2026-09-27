"""Ctrl+Z restores the selection lost by Delete or Escape."""
from __future__ import annotations

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

from core import app_state, state_gateway
from core.state.selection_history import SelectionHistory


def test_undo_returns_the_previous_selection() -> None:
    history = SelectionHistory()

    history.push([1, 2, 3])

    assert history.undo() == [1, 2, 3]
    assert history.undo() is None


def test_the_stack_is_bounded() -> None:
    history = SelectionHistory(depth=2)
    for indices in ([1], [2], [3]):
        history.push(indices)

    assert history.depth == 2
    assert history.undo() == [3]
    assert history.undo() == [2]
    assert history.undo() is None


def test_pushing_the_same_selection_twice_keeps_one_entry() -> None:
    history = SelectionHistory()
    history.push([5])
    history.push([5])

    assert history.depth == 1


def test_an_empty_history_restores_nothing() -> None:
    assert SelectionHistory().undo() is None


def test_delete_then_undo_restores_the_selection(main_window) -> None:
    state_gateway.set_selected_indices([4, 5])
    main_window._history().clear()
    main_window.setFocus(Qt.ShortcutFocusReason)
    QTest.qWait(10)

    QTest.keyClick(main_window, Qt.Key_Delete)
    assert not app_state.selected_indices, "Delete removes the selection"

    QTest.keyClick(main_window, Qt.Key_Z, Qt.ControlModifier)

    assert list(app_state.selected_indices) == [4, 5]


def test_escape_then_undo_restores_the_selection(main_window) -> None:
    state_gateway.set_selection_tool(None)
    state_gateway.set_selected_indices([9])
    main_window._history().clear()
    main_window.setFocus(Qt.ShortcutFocusReason)
    QTest.qWait(10)

    QTest.keyClick(main_window, Qt.Key_Escape)
    assert not app_state.selected_indices

    QTest.keyClick(main_window, Qt.Key_Z, Qt.ControlModifier)

    assert list(app_state.selected_indices) == [9]


def test_ctrl_z_in_a_text_field_leaves_the_selection_alone(main_window) -> None:
    """Undo inside a text field belongs to the field, not to the plot."""
    state_gateway.set_selected_indices([11])
    search = main_window.legend_search_edit
    search.setText("Group")
    search.setFocus(Qt.ShortcutFocusReason)
    main_window.activateWindow()
    QTest.qWait(10)

    QTest.keyClick(search, Qt.Key_Z, Qt.ControlModifier)

    assert list(app_state.selected_indices) == [11]
