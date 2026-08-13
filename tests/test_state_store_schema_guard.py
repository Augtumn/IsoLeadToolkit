"""Guard tests: state-store snapshot schema must not drift from the tests."""

from __future__ import annotations

from core.state import StateStore, app_state
from core.state.store import _warn_direct_mutations
from tests.test_state_store import _snapshot_state


def test_store_snapshot_schema_matches_test_snapshot() -> None:
    """The manual test snapshot must cover every store snapshot key.

    When StateStore.snapshot() grows a key, the hand-maintained
    _snapshot_state() helper must grow with it, otherwise the state-store
    tests silently stop verifying part of the schema.
    """
    store_snapshot = app_state.state_store.snapshot()
    test_snapshot = _snapshot_state()
    missing_in_test = set(store_snapshot) - set(test_snapshot)
    assert not missing_in_test, (
        "test_state_store._snapshot_state() is missing keys also present in "
        f"StateStore.snapshot(): {sorted(missing_in_test)}"
    )


def test_warn_direct_mutations_flags_bypassed_writes(caplog) -> None:
    import logging

    from types import SimpleNamespace

    state = SimpleNamespace()
    state.plot_marker_size = 60
    state.selected_indices = {1, 2}
    snapshot = {
        "plot_marker_size": 60,
        "selected_indices": {1, 2},
        "overlay_artists": {"model_curve": []},
    }

    with caplog.at_level(logging.WARNING, logger="core.state.store"):
        # Runtime-exempt field divergence is not flagged.
        state.overlay_artists = {"model_curve": [object()]}
        _warn_direct_mutations(state, snapshot)
        assert "overlay_artists" not in caplog.text

        caplog.clear()
        # Bypassed scalar write IS flagged.
        state.plot_marker_size = 99
        _warn_direct_mutations(state, snapshot)
        assert "plot_marker_size" in caplog.text

        caplog.clear()
        # Bypassed set mutation IS flagged.
        state.selected_indices.add(3)
        _warn_direct_mutations(state, snapshot)
        assert "selected_indices" in caplog.text
