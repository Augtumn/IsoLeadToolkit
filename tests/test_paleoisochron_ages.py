"""The paleoisochron ages are derived from min/max/step, never stored beside them.

Reported by the architecture health check: the ages were persisted next to the three controls they come from, so a
session file could hold a list the controls did not describe. Measuring found a second problem: the panel recomputed
the list only when the step changed, so changing min or max left the ages describing the old range.
"""
from __future__ import annotations

import pytest

from core import app_state, state_gateway
from core.overlay_state import paleoisochron_age_list
from core.persistence.schema import SESSION_FIELDS, UI_STATE_FIELDS


@pytest.fixture()
def restored_state():
    original = state_gateway.snapshot()
    yield
    state_gateway.restore_snapshot(original)


@pytest.mark.parametrize(
    ("minimum", "maximum", "step", "expected"),
    [
        (0, 3000, 1000, [3000, 2000, 1000, 0]),
        (0, 2500, 1000, [2500, 1500, 500, 0]),
        (2000, 0, 1000, [2000, 1000, 0]),
        (0, 3000, 0, []),
    ],
)
def test_the_ages_follow_the_three_controls(minimum, maximum, step, expected) -> None:
    assert paleoisochron_age_list(minimum, maximum, step) == expected


def test_changing_a_limit_recomputes_the_ages(restored_state) -> None:
    state_gateway.set_paleoisochron_max_age(3000)
    state_gateway.set_paleoisochron_step(1000)
    state_gateway.set_paleoisochron_min_age(0)
    assert list(app_state.paleoisochron_ages) == [3000, 2000, 1000, 0]

    state_gateway.set_paleoisochron_min_age(500)
    assert 500 in app_state.paleoisochron_ages, "the new limit is described by the list"

    state_gateway.set_paleoisochron_max_age(2000)
    assert max(app_state.paleoisochron_ages) == 2000


def test_a_contradictory_list_from_a_file_is_replaced(restored_state) -> None:
    payload = {
        "paleoisochron_min_age": 100,
        "paleoisochron_max_age": 400,
        "paleoisochron_step": 100,
        "paleoisochron_ages": [9999],
    }
    assert app_state.state_store.restore_snapshot(payload) is True
    assert list(app_state.paleoisochron_ages) == [400, 300, 200, 100]


def test_the_derived_value_is_not_persisted() -> None:
    persisted = set(SESSION_FIELDS) | set(UI_STATE_FIELDS)
    assert "paleoisochron_ages" not in persisted, "it is recomputed on load"
    assert {"paleoisochron_min_age", "paleoisochron_max_age", "paleoisochron_step"} <= persisted

