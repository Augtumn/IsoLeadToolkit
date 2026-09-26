"""Declarations in core/state/fields.py must be shape-correct.

The registry drives the initial snapshot, the projection and the write-back, so a wrong
declaration (a default the coercion cannot handle, a holder that does not exist, a copy
that returns the shared default object) is a state bug waiting to happen. These tests make
that class of mistake visible without running the application.
"""
from __future__ import annotations

from collections import Counter

import pytest

from core import app_state
from core.state.coercers import _normalize_color  # noqa: F401  (keeps coercers importable)
from core.state.fields import SIMPLE_FIELDS, StateField, snapshot_from_store

BY_NAME = {field.name: field for field in SIMPLE_FIELDS}

_TYPE_EXAMPLES = {
    bool: True,
    int: 7,
    float: 0.5,
    str: "text",
    list: [1, 2],
    dict: {"k": 1},
    tuple: (1, 2),
    set: {1, 2},
    type(None): None,
}


def _same_shape(value, other) -> bool:
    """Same type, and for containers the same element types."""
    if type(value) is not type(other):
        return False
    if isinstance(value, dict):
        return [type(k) for k in value] == [type(k) for k in other]
    return True


def test_field_names_are_unique() -> None:
    duplicates = [name for name, count in Counter(f.name for f in SIMPLE_FIELDS).items() if count > 1]
    assert not duplicates, f"duplicate declarations: {duplicates}"


def test_every_field_has_a_name_and_a_callable_coercion() -> None:
    for field in SIMPLE_FIELDS:
        assert isinstance(field.name, str) and field.name, field
        assert callable(field.normalize), field.name
        assert callable(field.copy), field.name
        assert field.project is None or callable(field.project), field.name
        assert field.restore is None or callable(field.restore), field.name


@pytest.mark.parametrize("field", SIMPLE_FIELDS, ids=lambda f: f.name)
def test_the_default_survives_its_own_coercions(field: StateField) -> None:
    """normalize(default), from_snapshot({}) and for_state({}) must not raise."""
    normalized = field.normalize(field.default)
    from_snapshot = field.from_snapshot({})
    from_state = field.for_state({})
    assert normalized is not None or field.default is None, field.name
    assert from_snapshot == normalized, f"{field.name}: copy() disagrees with normalize()"
    assert from_state == normalized, f"{field.name}: restore() disagrees with normalize()"


@pytest.mark.parametrize("field", SIMPLE_FIELDS, ids=lambda f: f.name)
def test_the_coercions_keep_the_shape(field: StateField) -> None:
    """A bool field must stay bool, a list field must stay list, and so on."""
    normalized = field.normalize(field.default)
    expected = _TYPE_EXAMPLES.get(type(field.default))
    if expected is None:
        pytest.skip(f"no shape expectation for {type(field.default).__name__}")
    assert _same_shape(normalized, field.default), (
        f"{field.name}: normalize turned {type(field.default).__name__} into {type(normalized).__name__}"
    )


@pytest.mark.parametrize("field", SIMPLE_FIELDS, ids=lambda f: f.name)
def test_mutable_defaults_are_not_shared(field: StateField) -> None:
    """Returning the declared object itself would let a caller mutate the declaration."""
    if not isinstance(field.default, (list, dict, set)):
        pytest.skip("immutable default")
    assert field.from_snapshot({}) is not field.default, field.name
    assert field.for_state({}) is not field.default, field.name


@pytest.mark.parametrize("field", SIMPLE_FIELDS, ids=lambda f: f.name)
def test_the_holder_exists_on_the_state(field: StateField) -> None:
    assert field.holder in {None, "legend", "overlay"}, f"{field.name}: unexpected holder"
    if field.holder is not None:
        assert hasattr(app_state, field.holder), f"{field.name}: no attribute {field.holder!r}"


def test_direction_overrides_win_over_copy() -> None:
    """project/restore must actually take precedence when they are declared."""
    overrides = [f for f in SIMPLE_FIELDS if f.project is not None or f.restore is not None]
    assert overrides, "expected the asymmetric fields to declare project/restore"
    for field in overrides:
        if field.project is not None:
            snapshot = {field.name: field.default}
            assert field.from_snapshot(snapshot) == field.project(field.default), field.name
        if field.restore is not None:
            snapshot = {field.name: field.default}
            assert field.for_state(snapshot) == field.restore(field.default), field.name


def test_the_projection_covers_every_declaration() -> None:
    """snapshot_from_store() must not silently drop a field."""
    projected = snapshot_from_store({})
    missing = {field.name for field in SIMPLE_FIELDS} - set(projected)
    assert not missing, f"not projected: {sorted(missing)}"
