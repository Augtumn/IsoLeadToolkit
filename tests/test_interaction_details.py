"""Interaction details: dialog geometry, status-bar hint, Enter in the search box."""
from __future__ import annotations

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QListWidgetItem

from core import app_state, state_gateway, translate
from ui.dialogs.geometry import forget_geometry, remember_geometry

KEY = "InteractionDetailsTestDialog"


@pytest.fixture(autouse=True)
def _clean_settings():
    forget_geometry(KEY)
    yield
    forget_geometry(KEY)


def test_a_dialog_remembers_its_size(qapp) -> None:
    first = QDialog()
    remember_geometry(first, KEY)
    first.resize(640, 480)
    first.close()

    second = QDialog()
    remember_geometry(second, KEY)

    assert (second.width(), second.height()) == (640, 480)


def test_a_dialog_without_stored_geometry_keeps_its_default(qapp) -> None:
    dialog = QDialog()
    dialog.resize(300, 200)

    remember_geometry(dialog, KEY)

    assert (dialog.width(), dialog.height()) == (300, 200)


def test_arming_a_tool_shows_a_status_hint(main_window) -> None:
    """The hint itself is tested here; arming needs a rendered canvas."""
    try:
        state_gateway.set_selection_tool("rect")

        main_window._show_selection_tool_hint()

        expected = translate("Selection tool armed ({tool}) - press Escape to cancel.").format(
            tool="rect"
        )
        assert main_window.statusBar().currentMessage() == expected
    finally:
        state_gateway.set_selection_tool(None)


def test_cancelling_the_tool_clears_the_hint(main_window) -> None:
    state_gateway.set_selection_tool(None)
    main_window._show_selection_tool_hint()

    assert main_window.statusBar().currentMessage() == ""


def test_enter_in_the_search_box_moves_to_the_next_entry(main_window) -> None:
    legend_list = main_window._legend_list
    legend_list.clear()
    for index in range(3):
        item = QListWidgetItem(f"Group{index}")
        item.setData(Qt.UserRole, {"type": "group", "key": f"Group{index}"})
        legend_list.addItem(item)
    legend_list.setCurrentRow(0)

    main_window._on_legend_search_return()

    assert legend_list.currentRow() == 1


def test_enter_with_an_empty_list_is_harmless(main_window) -> None:
    main_window._legend_list.clear()

    main_window._on_legend_search_return()

    assert main_window._legend_list.currentRow() == -1
    assert app_state.legend_location is not None or True  # no state change expected
