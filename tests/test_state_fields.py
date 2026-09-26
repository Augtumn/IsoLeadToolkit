"""The declarative field registry: one declaration, four consumers.

A registered field must reach the persistence whitelist, the store snapshot, the
snapshot projection and the write-back; missing one of them used to be silent.
"""
from __future__ import annotations

import pytest

from core import app_state
from core.persistence.schema import SESSION_FIELDS, UI_STATE_FIELDS
from core.state.fields import (
    SIMPLE_FIELDS,
    _normalize_ternary_boundary_percent,
    _normalize_ternary_manual_limits,
    _normalize_ternary_render_margin,
    snapshot_from_state,
    snapshot_from_store,
    sync_fields,
)

REGISTERED = {field.name for field in SIMPLE_FIELDS}


def test_the_registry_is_not_empty() -> None:
    assert len(SIMPLE_FIELDS) >= 8, "the ternary group is the migrated baseline"


def test_every_registered_field_is_persisted() -> None:
    persisted = set(SESSION_FIELDS) | set(UI_STATE_FIELDS)
    missing = REGISTERED - persisted
    assert not missing, f"registered but not persisted: {sorted(missing)}"


def test_the_store_snapshot_carries_every_registered_field() -> None:
    snapshot = app_state.state_store.snapshot()
    missing = REGISTERED - set(snapshot)
    assert not missing, f"missing from the snapshot: {sorted(missing)}"


def test_the_projection_matches_the_snapshot() -> None:
    """snapshot_from_store() must reproduce what the store actually projects."""
    snapshot = app_state.state_store.snapshot()
    projected = snapshot_from_store(snapshot)
    for name, value in projected.items():
        assert value == snapshot[name], f"{name}: {value!r} != {snapshot[name]!r}"


def test_the_initial_snapshot_matches_the_live_state() -> None:
    initial = snapshot_from_state(app_state)
    for name, value in initial.items():
        assert value == getattr(app_state, name), f"{name}: {value!r} != live value"


def test_sync_fields_writes_every_registered_field_back() -> None:
    """Perturb, sync once, expect the snapshot values back."""
    snapshot = app_state.state_store.snapshot()
    originals = {name: getattr(app_state, name) for name in REGISTERED}
    try:
        for name in REGISTERED:
            setattr(app_state, name, "__probe__")

        sync_fields(app_state, snapshot)

        for name in REGISTERED:
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
    limits = _normalize_ternary_manual_limits({"tmin": -1, "tmax": 2, "unknown": 5})
    assert limits == {
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
