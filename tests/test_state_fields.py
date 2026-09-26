"""The declarative field registry: one declaration, four consumers.

A registered field must reach the persistence whitelist, the store snapshot, the
snapshot projection and the write-back; missing one of them used to be silent.
"""
from __future__ import annotations

import pytest

from core import app_state
from core.persistence.schema import SESSION_FIELDS, UI_STATE_FIELDS
from core.state.coercers import (
    _normalize_ternary_boundary_percent,
    _normalize_ternary_manual_limits,
    _normalize_ternary_render_margin,
)
from core.state.fields import (
    SIMPLE_FIELDS,
    snapshot_from_state,
    snapshot_from_store,
    sync_fields,
)

REGISTERED = {field.name for field in SIMPLE_FIELDS}
PERSISTED = set(SESSION_FIELDS) | set(UI_STATE_FIELDS)


def test_the_registry_covers_a_large_part_of_the_state() -> None:
    assert len(SIMPLE_FIELDS) >= 100, len(SIMPLE_FIELDS)


def test_every_registered_field_is_persisted() -> None:
    missing = REGISTERED - PERSISTED
    assert not missing, f"registered but not persisted: {sorted(missing)}"


@pytest.mark.parametrize(
    "name",
    ["data_version", "selection_mode", "embedding_task_running", "current_plot_title"],
)
def test_transient_fields_stay_out_of_the_registry(name: str) -> None:
    """Runtime bookkeeping is not persisted on purpose and stays explicit."""
    assert name not in REGISTERED


def test_the_store_snapshot_carries_every_registered_field() -> None:
    snapshot = app_state.state_store.snapshot()
    missing = REGISTERED - set(snapshot)
    assert not missing, f"missing from the snapshot: {sorted(missing)}"


def test_the_projection_matches_the_snapshot() -> None:
    """snapshot_from_store() must reproduce what the store actually projects."""
    snapshot = app_state.state_store.snapshot()
    for name, value in snapshot_from_store(snapshot).items():
        assert value == snapshot[name], f"{name}: {value!r} != {snapshot[name]!r}"


def test_the_initial_snapshot_matches_the_live_state() -> None:
    for name, value in snapshot_from_state(app_state).items():
        assert value == getattr(app_state, name), f"{name}: {value!r} != live value"


def _perturb(value):
    """A different value of the same shape, so the field's copy() accepts it."""
    if isinstance(value, bool):
        return not value
    if isinstance(value, (int, float)):
        return value + 1
    if isinstance(value, str):
        return "__probe__"
    if value is None:
        return "__probe__"
    if isinstance(value, list):
        return [] if value else ["__probe__"]
    if isinstance(value, dict):
        return {} if value else {"probe": 1}
    if isinstance(value, tuple):
        return () if value else ("__probe__",)
    return "__probe__"


def test_sync_fields_writes_every_registered_field_back() -> None:
    """Perturb every registered field, sync once, expect the snapshot values back."""
    snapshot = app_state.state_store.snapshot()
    fields_to_restore = [name for name in REGISTERED if hasattr(app_state, name)]
    originals = {name: getattr(app_state, name) for name in fields_to_restore}
    try:
        for name in fields_to_restore:
            setattr(app_state, name, _perturb(originals[name]))

        sync_fields(app_state, snapshot)

        for name in fields_to_restore:
            assert getattr(app_state, name) == snapshot[name], name
    finally:
        for name, value in originals.items():
            setattr(app_state, name, value)


@pytest.mark.parametrize(
    "given, expected",
    [(None, 5.0), (-3, 0.0), (12.5, 12.5), (99, 30.0)],
)
def test_boundary_percent_is_clamped(given, expected) -> None:
    assert _normalize_ternary_boundary_percent(given) == pytest.approx(expected)


@pytest.mark.parametrize("given, expected", [(None, 0.002), (-1, 0.0), (0.01, 0.01), (1.0, 0.05)])
def test_render_margin_is_clamped(given, expected) -> None:
    assert _normalize_ternary_render_margin(given) == pytest.approx(expected)


def test_manual_limits_are_merged_and_clamped() -> None:
    assert _normalize_ternary_manual_limits({"tmin": -1, "tmax": 2, "unknown": 5}) == {
        "tmin": 0.0,
        "tmax": 1.0,
        "lmin": 0.0,
        "lmax": 1.0,
        "rmin": 0.0,
        "rmax": 1.0,
    }


def test_manual_limits_tolerate_junk() -> None:
    assert _normalize_ternary_manual_limits(None)["tmax"] == 1.0
    assert _normalize_ternary_manual_limits("nonsense")["tmin"] == 0.0
