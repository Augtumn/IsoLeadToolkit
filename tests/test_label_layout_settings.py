"""Tests for visualization.plotting.label_layout settings normalization."""

from __future__ import annotations

from core import app_state, state_gateway
from visualization.plotting import label_layout


def _snapshot_adjust_text_state() -> dict[str, object]:
    return {
        "force_text": getattr(app_state, "adjust_text_force_text", (0.8, 1.0)),
        "force_static": getattr(app_state, "adjust_text_force_static", (0.4, 0.6)),
        "expand": getattr(app_state, "adjust_text_expand", (1.08, 1.20)),
        "iter_lim": getattr(app_state, "adjust_text_iter_lim", 120),
        "time_lim": getattr(app_state, "adjust_text_time_lim", 0.25),
    }


def _restore_adjust_text_state(snapshot: dict[str, object]) -> None:
    state_gateway.set_adjust_text_force_text(snapshot.get("force_text"))
    state_gateway.set_adjust_text_force_static(snapshot.get("force_static"))
    state_gateway.set_adjust_text_expand(snapshot.get("expand"))
    state_gateway.set_adjust_text_iter_lim(int(snapshot.get("iter_lim") or 120))
    state_gateway.set_adjust_text_time_lim(float(snapshot.get("time_lim") or 0.25))


def test_float_pair_normalizes_sequence_scalar_and_fallback() -> None:
    assert label_layout._float_pair((1, 2), (0.0, 0.0)) == (1.0, 2.0)
    assert label_layout._float_pair([3, 4, 5], (0.0, 0.0)) == (3.0, 4.0)
    assert label_layout._float_pair(6, (0.0, 0.0)) == (6.0, 6.0)
    assert label_layout._float_pair("bad", (0.8, 1.0)) == (0.8, 1.0)
    assert label_layout._float_pair((1, "bad"), (0.8, 1.0)) == (0.8, 1.0)


def test_resolve_adjust_text_settings_clamps_limits() -> None:
    snapshot = _snapshot_adjust_text_state()
    try:
        state_gateway.set_adjust_text_force_text((0.2, 0.3))
        state_gateway.set_adjust_text_force_static((2.0, 2.0))
        state_gateway.set_adjust_text_expand((1.2, 1.4))
        state_gateway.set_adjust_text_iter_lim(5000)
        state_gateway.set_adjust_text_time_lim(0.001)

        force_text, force_static, expand, iter_lim, time_lim = label_layout._resolve_adjust_text_settings()

        assert force_text == (0.2, 0.3)
        assert force_static == (2.0, 2.0)
        assert expand == (1.2, 1.4)
        assert iter_lim == 1000
        assert time_lim == 0.05

        state_gateway.set_adjust_text_iter_lim(-3)
        state_gateway.set_adjust_text_time_lim(3.5)

        _force_text, _force_static, _expand, iter_lim, time_lim = label_layout._resolve_adjust_text_settings()

        assert iter_lim == 10
        assert time_lim == 2.0
    finally:
        _restore_adjust_text_state(snapshot)
