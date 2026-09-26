"""Legend panel: it must come back when the outside side is selected again.

Also covers the inline/docked coexistence: selecting one no longer clears the other.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PyQt5")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtWidgets import (  # noqa: E402
    QApplication,
    QListWidget,
    QSplitter,
    QWidget,
)

from core import app_state, state_gateway  # noqa: E402
import ui.panels.legend.actions as legend_actions  # noqa: E402
from ui.main_window_parts.setup import MainWindowSetupMixin  # noqa: E402

_APP = QApplication.instance() or QApplication([])

_ACTIONS_CLASS = next(
    value
    for value in vars(legend_actions).values()
    if isinstance(value, type) and hasattr(value, "_on_legend_inside_position_change")
)


class _LayoutHost(MainWindowSetupMixin):
    """Only the splitter, the panel and the list are needed for the layout pass."""


class _ActionsHost(_ACTIONS_CLASS):
    """Records the button states instead of touching the real buttons."""

    def _set_legend_inside_position_button(self, position):
        self.inside_button = position

    def _set_legend_outside_position_button(self, position):
        self.outside_button = position

    def _on_change(self):
        self.changed = getattr(self, "changed", 0) + 1


@pytest.fixture()
def layout_host():
    splitter = QSplitter(Qt.Horizontal)
    panel, plot = QWidget(), QWidget()
    splitter.addWidget(panel)
    splitter.addWidget(plot)
    host = _LayoutHost()
    host.legend_splitter = splitter
    host.legend_panel = panel
    host.plot_container = plot
    host._legend_list = QListWidget()
    original = app_state.legend_location
    yield host
    state_gateway.set_legend_location(original)


def test_the_panel_reappears_after_going_inside_and_back(layout_host) -> None:
    """Regression: the "inside" branch left the layout cache stale."""
    state_gateway.set_legend_location("outside_left")
    layout_host._apply_legend_panel_layout()
    assert layout_host.legend_panel.isVisible() or not layout_host.legend_panel.isHidden()

    state_gateway.set_legend_location(None)
    layout_host._apply_legend_panel_layout()
    assert layout_host.legend_panel.isHidden(), "the panel hides for an inside legend"

    state_gateway.set_legend_location("outside_left")
    layout_host._apply_legend_panel_layout()
    assert not layout_host.legend_panel.isHidden(), "selecting the same side again must show it"


def test_switching_sides_reorders_the_splitter(layout_host) -> None:
    state_gateway.set_legend_location("outside_left")
    layout_host._apply_legend_panel_layout()
    assert layout_host.legend_splitter.indexOf(layout_host.legend_panel) == 0

    state_gateway.set_legend_location("outside_right")
    layout_host._apply_legend_panel_layout()
    assert layout_host.legend_splitter.indexOf(layout_host.legend_panel) == 1


def test_an_inside_position_keeps_the_outside_location() -> None:
    host = _ActionsHost()
    state_gateway.set_legend_location("outside_left")
    state_gateway.set_legend_position(None)

    host._on_legend_inside_position_change("upper right")

    assert app_state.legend_position == "upper right"
    assert app_state.legend_location == "outside_left", "the docked legend must survive"


def test_an_outside_location_keeps_the_inside_position() -> None:
    host = _ActionsHost()
    state_gateway.set_legend_position("upper right")
    state_gateway.set_legend_location(None)

    host._on_legend_outside_position_change("outside_left")

    assert app_state.legend_location == "outside_left"
    assert app_state.legend_position == "upper right", "the inline legend must survive"

    state_gateway.set_legend_position(None)
    state_gateway.set_legend_location("outside_left")


def test_clicking_the_same_position_twice_still_toggles_it_off() -> None:
    host = _ActionsHost()
    state_gateway.set_legend_position("upper right")

    host._on_legend_inside_position_change("upper right")

    assert app_state.legend_position is None
