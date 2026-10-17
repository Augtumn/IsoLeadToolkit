"""An action is one transaction.

Reported by review: dispatch wrote into the snapshot field by field and synced afterwards, with no rollback.
The marginal-KDE compute-options action writes max_points and then converts bw_adjust, so a bad bw_adjust left
the snapshot partly updated, the live state not updated at all, and the next dispatch reported the store's own
leftovers as a direct mutation - the very check that exists to catch outside writes.
"""
from __future__ import annotations

import pytest

from core import app_state
from core.state.store import StateStore


@pytest.fixture()
def store():
    return StateStore(app_state)


def test_a_failing_action_leaves_the_state_untouched(store) -> None:
    before = store.snapshot()

    with pytest.raises(ValueError):
        # Writes max_points first, then raises converting bw_adjust.
        store.dispatch(
            {"type": "SET_MARGINAL_KDE_COMPUTE_OPTIONS", "max_points": 999, "bw_adjust": "not-a-number"}
        )

    after = store.snapshot()
    assert after["marginal_kde_max_points"] == before["marginal_kde_max_points"], (
        "the field written before the failure is rolled back"
    )
    assert app_state.marginal_kde_max_points == before["marginal_kde_max_points"], (
        "and the live state agrees with the snapshot"
    )


def test_a_successful_action_still_applies(store) -> None:
    store.dispatch({"type": "SET_MARGINAL_KDE_COMPUTE_OPTIONS", "max_points": 1234, "bw_adjust": 1.5})
    assert store.snapshot()["marginal_kde_max_points"] == 1234
    assert app_state.marginal_kde_max_points == 1234
