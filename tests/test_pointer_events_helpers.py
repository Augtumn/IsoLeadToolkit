"""Tests for visualization.event_handlers.pointer_events helpers."""

from __future__ import annotations

from core import app_state
from visualization.event_handlers import pointer_events


class _DummyScatter:
    def __init__(self, hit: bool, index: int = 0) -> None:
        self._hit = hit
        self._index = index

    def contains(self, _event):
        if not self._hit:
            return False, {}
        return True, {"ind": [self._index]}


def _snapshot_pointer_state() -> dict[str, object]:
    return {
        "scatter_collections": list(getattr(app_state, "scatter_collections", []) or []),
        "artist_to_sample": dict(getattr(app_state, "artist_to_sample", {}) or {}),
        "sample_coordinates": dict(getattr(app_state, "sample_coordinates", {}) or {}),
    }


def _restore_pointer_state(snapshot: dict[str, object]) -> None:
    setattr(app_state, "scatter_collections", list(snapshot.get("scatter_collections", []) or []))
    setattr(app_state, "artist_to_sample", dict(snapshot.get("artist_to_sample", {}) or {}))
    setattr(app_state, "sample_coordinates", dict(snapshot.get("sample_coordinates", {}) or {}))


def test_resolve_sample_index_prefers_scatter_hit_mapping() -> None:
    snapshot = _snapshot_pointer_state()
    try:
        scatter = _DummyScatter(hit=True, index=0)
        setattr(app_state, "scatter_collections", [scatter])
        setattr(app_state, "artist_to_sample", {(id(scatter), 0): 42})

        sample_idx = pointer_events._resolve_sample_index(object())

        assert sample_idx == 42
    finally:
        _restore_pointer_state(snapshot)


def test_resolve_sample_index_falls_back_to_nearest_lookup(monkeypatch) -> None:
    snapshot = _snapshot_pointer_state()
    try:
        setattr(app_state, "scatter_collections", [])
        setattr(app_state, "sample_coordinates", {1: (1.0, 2.0)})
        monkeypatch.setattr(
            pointer_events.SELECTION_USE_CASE,
            "nearest_sample_index",
            lambda _coords, x, y: 7 if (x, y) == (1.5, 2.5) else None,
        )
        event = type("_Evt", (), {"xdata": 1.5, "ydata": 2.5})()

        sample_idx = pointer_events._resolve_sample_index(event)

        assert sample_idx == 7
    finally:
        _restore_pointer_state(snapshot)


def test_resolve_sample_index_returns_none_without_coordinates() -> None:
    snapshot = _snapshot_pointer_state()
    try:
        setattr(app_state, "scatter_collections", [])
        event = type("_Evt", (), {"xdata": None, "ydata": None})()

        sample_idx = pointer_events._resolve_sample_index(event)

        assert sample_idx is None
    finally:
        _restore_pointer_state(snapshot)
