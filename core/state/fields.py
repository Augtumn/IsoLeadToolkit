"""Declarative registry for the simple persisted state fields.

A field declared here carries its default value and its coercion; the four places that
used to be maintained by hand derive from the declaration instead:

* the store's initial snapshot (``snapshot_from_state``)
* the snapshot projection (``snapshot_from_store``)
* the write-back into app_state (``sync_fields``)
* the persistence whitelist (checked by tests/test_state_fields.py)

Missing one of them used to fail silently - see docs/ui_architecture_review.md item A.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

Coercer = Callable[[Any], Any]


# ── coercers (moved here from core/state/_normalizers.py) ───────────────

def _normalize_ternary_boundary_percent(percent: Any) -> float:
    return max(0.0, min(float(percent if percent is not None else 5.0), 30.0))


def _normalize_ternary_manual_limits(limits: Any) -> dict[str, float]:
    defaults = {
        "tmin": 0.0,
        "tmax": 1.0,
        "lmin": 0.0,
        "lmax": 1.0,
        "rmin": 0.0,
        "rmax": 1.0,
    }
    merged = dict(defaults)
    if isinstance(limits, dict):
        for key, value in limits.items():
            if key in merged and value is not None:
                merged[key] = max(0.0, min(float(value), 1.0))
    return merged


def _normalize_ternary_render_margin(margin: Any) -> float:
    return max(0.0, min(float(margin if margin is not None else 0.002), 0.05))


def _identity(value: Any) -> Any:
    return value


def _as_bool(value: Any) -> bool:
    return bool(value)


def _as_float(value: Any) -> float:
    return float(value)


def _as_str(value: Any) -> str:
    return str(value)


def _as_list(value: Any) -> list:
    return list(value) if value else []


def _as_stretch_mode(value: Any) -> str:
    return str(value or "power")


def _as_factors(value: Any) -> list:
    return list(value or [1.0, 1.0, 1.0])


@dataclass(frozen=True)
class StateField:
    """One persisted state field: its name, default value and coercion."""

    name: str
    default: Any
    coerce: Coercer = _identity

    def from_state(self, state: Any) -> Any:
        return self.coerce(getattr(state, self.name, self.default))

    def from_snapshot(self, snapshot: dict) -> Any:
        return self.coerce(snapshot.get(self.name, self.default))


TERNARY_MANUAL_LIMITS_DEFAULT = {
    "tmin": 0.0,
    "tmax": 1.0,
    "lmin": 0.0,
    "lmax": 1.0,
    "rmin": 0.0,
    "rmax": 1.0,
}

TERNARY_FIELDS: tuple[StateField, ...] = (
    StateField("ternary_auto_zoom", True, _as_bool),
    StateField("ternary_boundary_percent", 5.0, _normalize_ternary_boundary_percent),
    StateField("ternary_limit_mode", "min", _as_str),
    StateField("ternary_limit_anchor", "min", _as_str),
    StateField("ternary_manual_limits_enabled", False, _as_bool),
    StateField("ternary_manual_limits", TERNARY_MANUAL_LIMITS_DEFAULT, _normalize_ternary_manual_limits),
    StateField("ternary_render_margin", 0.002, _normalize_ternary_render_margin),
    StateField("ternary_stretch_mode", "power", _as_stretch_mode),
    StateField("ternary_stretch", False, _as_bool),
    StateField("ternary_factors", [1.0, 1.0, 1.0], _as_factors),
)

#: Every field whose plumbing comes from this registry.
SIMPLE_FIELDS: tuple[StateField, ...] = TERNARY_FIELDS


def snapshot_from_state(state: Any) -> dict[str, Any]:
    """Initial snapshot entries for the registered fields."""
    return {field.name: field.from_state(state) for field in SIMPLE_FIELDS}


def snapshot_from_store(snapshot: dict) -> dict[str, Any]:
    """Projection entries for the registered fields."""
    return {field.name: field.from_snapshot(snapshot) for field in SIMPLE_FIELDS}


def sync_fields(state: Any, snapshot: dict) -> None:
    """Write the registered fields from *snapshot* back onto *state*."""
    for field in SIMPLE_FIELDS:
        setattr(state, field.name, field.from_snapshot(snapshot))
