"""Per-panel legend placement is state: a session keeps the legends where the user put them.

Reported by the architecture health check: the panel records hold a legend placement (frame, position, location,
offset) and the renderer applies it per panel, but it was the one thing a session did not carry - the panels come
back on load and their legends went to the defaults.
"""
from __future__ import annotations

import pytest

from core import app_state, state_gateway
from core.persistence.schema import SESSION_FIELDS
from core.state.fields import REGISTERED


@pytest.fixture()
def restored_state():
    original = state_gateway.snapshot()
    yield
    state_gateway.restore_snapshot(original)


def test_the_field_is_registered_and_persisted() -> None:
    assert "plot_panel_legends" in REGISTERED
    assert "plot_panel_legends" in SESSION_FIELDS


def test_a_write_copies_the_placement(restored_state) -> None:
    """The caller keeps its dict; changing it must not reach the stored placement."""
    placement = {"0": {"legend_position": "upper left"}}
    state_gateway.set_plot_panel_legends(placement)

    placement["0"]["legend_position"] = "MUTATED"
    assert app_state.plot_panel_legends["0"]["legend_position"] == "upper left"


def test_the_placement_reaches_the_snapshot(restored_state) -> None:
    state_gateway.set_plot_panel_legends({"1": {"legend_location": "outside right"}})
    snapshot = app_state.state_store.snapshot()
    assert snapshot["plot_panel_legends"] == {"1": {"legend_location": "outside right"}}


def test_a_file_with_junk_entries_is_normalised(restored_state) -> None:
    """A hand-edited file must not put a stranger in the renderer path."""
    payload = {
        "plot_panel_legends": {
            "0": {"legend_position": "lower right"},
            "bad": "not a dict",
            3: {"legend_location": "outside left"},
        }
    }
    assert app_state.state_store.restore_snapshot(payload) is True
    assert app_state.plot_panel_legends == {
        "0": {"legend_position": "lower right"},
        "3": {"legend_location": "outside left"},
    }
