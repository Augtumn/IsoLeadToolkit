"""Keyboard interaction on the real main window.

Escape cancels the selection tool (then the selection), Delete removes the selected
samples, Ctrl+F jumps to the legend search box - and none of them fire while the user is
typing in a text field.
"""
from __future__ import annotations

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

from core import app_state, state_gateway


@pytest.fixture()
def window(main_window):
    main_window.show()
    main_window.activateWindow()
    QTest.qWaitForWindowExposed(main_window)
    yield main_window
    state_gateway.set_selection_tool(None)
    state_gateway.clear_selected_indices()


def test_escape_cancels_the_active_selection_tool(window) -> None:
    state_gateway.set_selection_tool("rect")

    QTest.keyClick(window, Qt.Key_Escape)

    assert app_state.selection_tool is None


def test_escape_then_clears_the_selection(window) -> None:
    state_gateway.set_selection_tool(None)
    state_gateway.set_selected_indices([1, 2, 3])

    QTest.keyClick(window, Qt.Key_Escape)

    assert not app_state.selected_indices


def test_delete_removes_the_selected_samples(window) -> None:
    state_gateway.set_selected_indices([4, 5])

    QTest.keyClick(window, Qt.Key_Delete)

    assert not app_state.selected_indices


def test_delete_in_the_search_box_does_not_touch_the_selection(window) -> None:
    """Typing in a text field must keep its keys: this is the detail that matters."""
    state_gateway.set_selected_indices([7, 8])
    search = window.legend_search_edit
    search.setFocus(Qt.ShortcutFocusReason)
    search.setText("Group")
    window.activateWindow()
    QTest.qWait(10)

    QTest.keyClick(search, Qt.Key_Delete)

    assert app_state.selected_indices, "Delete while typing must not remove samples"


def test_escape_in_the_search_box_only_clears_the_text(window) -> None:
    search = window.legend_search_edit
    search.setText("Group")
    search.setFocus(Qt.ShortcutFocusReason)
    window.activateWindow()
    QTest.qWait(10)

    QTest.keyClick(search, Qt.Key_Escape)

    assert search.text() == ""


def test_ctrl_f_focuses_the_legend_search_box(window) -> None:
    window.legend_search_edit.setText("")
    window.setFocus(Qt.ShortcutFocusReason)
    QTest.qWait(10)

    QTest.keyClick(window, Qt.Key_F, Qt.ControlModifier)

    assert window.legend_search_edit.hasFocus()
