"""UI behaviour against the real main window built by the composition root."""
from __future__ import annotations

from PyQt5.QtCore import Qt  # noqa: E402

from core import app_state, state_gateway  # noqa: E402


def test_the_window_provides_the_main_widgets(main_window) -> None:
    """The composition root builds the toolbar, the canvas and the legend panel."""
    assert main_window.toolbar is not None
    assert main_window._legend_list is not None
    assert main_window.legend_splitter is not None


def test_the_legend_panel_round_trip_on_the_real_window(main_window) -> None:
    """Outside -> inside -> outside must show the panel again (no stale cache)."""
    original = app_state.legend_location
    try:
        state_gateway.set_legend_location("outside_left")
        main_window._apply_legend_panel_layout()
        assert not main_window.legend_panel.isHidden()

        state_gateway.set_legend_location(None)
        main_window._apply_legend_panel_layout()
        assert main_window.legend_panel.isHidden()

        state_gateway.set_legend_location("outside_left")
        main_window._apply_legend_panel_layout()
        assert not main_window.legend_panel.isHidden()
    finally:
        state_gateway.set_legend_location(original)


def test_the_toolbar_has_no_empty_button(main_window) -> None:
    """Regression: a copied placeholder action used to become a blank button."""
    from PyQt5.QtWidgets import QToolButton

    for action in main_window.toolbar.actions():
        widget = main_window.toolbar.widgetForAction(action)
        if isinstance(widget, QToolButton):
            assert not (
                action.icon().isNull() and not action.text().strip()
            ), "an empty button reached the toolbar"


def test_the_legend_panel_layout_state_is_recorded_for_both_branches(main_window) -> None:
    """The cache must follow every branch, otherwise a later switch is a no-op."""
    original = app_state.legend_location
    try:
        state_gateway.set_legend_location("outside_right")
        main_window._apply_legend_panel_layout()
        assert main_window._legend_layout_state == ("outside_right", True)

        state_gateway.set_legend_location(None)
        main_window._apply_legend_panel_layout()
        assert main_window._legend_layout_state == (None, False)
    finally:
        state_gateway.set_legend_location(original)
