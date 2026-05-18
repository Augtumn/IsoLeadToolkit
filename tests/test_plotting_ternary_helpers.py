"""Tests for ternary plotting helpers."""

from __future__ import annotations

import numpy as np

from core import app_state
from visualization.plotting import ternary

class _FakeTernaryAxis:
    def __init__(self) -> None:
        self.limits: tuple[float, float, float, float, float, float] | None = None
        self.aspect: tuple[str, str] | None = None

    def set_ternary_lim(self, *limits: float) -> None:
        self.limits = tuple(float(v) for v in limits)

    def set_aspect(self, aspect: str, adjustable: str = "box") -> None:
        self.aspect = (aspect, adjustable)

def test_normalize_ternary_components_falls_back_to_equal_for_invalid_rows() -> None:
    t_norm, l_norm, r_norm = ternary.normalize_ternary_components(
        np.array([0.0, 1.0, -3.0], dtype=float),
        np.array([0.0, 2.0, 1.0], dtype=float),
        np.array([0.0, 3.0, 2.0], dtype=float),
    )

    np.testing.assert_allclose(
        np.column_stack([t_norm, l_norm, r_norm]),
        np.array(
            [
                [1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0],
                [1.0 / 6.0, 2.0 / 6.0, 3.0 / 6.0],
                [0.0, 1.0 / 3.0, 2.0 / 3.0],
            ],
            dtype=float,
        ),
        rtol=0.0,
        atol=1e-12,
    )

def test_configure_ternary_axis_uses_gateway_writes(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    axis = _FakeTernaryAxis()

    monkeypatch.setattr(ternary.state_gateway, "set_ternary_limit_mode", lambda value: calls.append(("mode", value)))

    setattr(app_state, "ternary_limit_mode", "max")

    limits = ternary.configure_ternary_axis(
        axis,
        np.array([0.2, 0.4], dtype=float),
        np.array([0.3, 0.4], dtype=float),
        np.array([0.5, 0.2], dtype=float),
        auto_zoom=False,
    )

    assert calls == [("mode", "max")]
    assert axis.limits == limits
    assert axis.aspect == ("equal", "box")



