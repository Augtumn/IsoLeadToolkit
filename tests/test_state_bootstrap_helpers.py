"""Tests for core.state.bootstrap helper defaults."""

from __future__ import annotations

from core.state.bootstrap import DEFAULT_ELLIPSE_CONFIDENCE, init_runtime_defaults


class _DummyState:
    pass


def test_init_runtime_defaults_uses_named_ellipse_confidence_default() -> None:
    state = _DummyState()

    init_runtime_defaults(state, config={"point_size": 60})

    assert state.ellipse_confidence == DEFAULT_ELLIPSE_CONFIDENCE


def test_init_runtime_defaults_honors_ellipse_confidence_override() -> None:
    state = _DummyState()

    init_runtime_defaults(state, config={"point_size": 60, "ellipse_confidence": 0.91})

    assert state.ellipse_confidence == 0.91
