"""Tests for visualization.events render mode synchronization helper."""

from __future__ import annotations

from core import app_state, state_gateway
from visualization import events


class _DummyVar:
    def __init__(self) -> None:
        self.value = None
        self.calls = 0

    def set(self, value) -> None:
        self.value = value
        self.calls += 1


class _DummyPanel:
    def __init__(self, var: _DummyVar) -> None:
        self.radio_vars = {"render_mode": var}


def test_sync_render_mode_updates_state_and_panel_var() -> None:
    original_mode = getattr(app_state, "render_mode", "2D")
    original_panel = getattr(app_state, "control_panel_ref", None)
    try:
        state_gateway.set_render_mode("2D")
        dummy_var = _DummyVar()
        setattr(app_state, "control_panel_ref", _DummyPanel(dummy_var))

        events._sync_render_mode("PCA")

        assert app_state.render_mode == "PCA"
        assert dummy_var.value == "PCA"
        assert dummy_var.calls == 1
    finally:
        setattr(app_state, "control_panel_ref", original_panel)
        state_gateway.set_render_mode(str(original_mode))


def test_sync_render_mode_noop_when_mode_unchanged() -> None:
    original_mode = getattr(app_state, "render_mode", "2D")
    original_panel = getattr(app_state, "control_panel_ref", None)
    try:
        state_gateway.set_render_mode("2D")
        dummy_var = _DummyVar()
        setattr(app_state, "control_panel_ref", _DummyPanel(dummy_var))

        events._sync_render_mode("2D")

        assert app_state.render_mode == "2D"
        assert dummy_var.calls == 0
    finally:
        setattr(app_state, "control_panel_ref", original_panel)
        state_gateway.set_render_mode(str(original_mode))
