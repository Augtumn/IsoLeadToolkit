"""Unit tests for visualization.plotting helpers (column heuristics, style, ternary, isochron, lazy imports)."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from core import app_state, state_gateway
from visualization.plotting import data as plotting_data, ternary
from visualization.plotting.core import _ensure_axes, _get_pb_columns
from visualization.plotting.isochron import resolve_isochron_errors
from visualization.plotting.style import configure_constrained_layout


def _snapshot_axes_state() -> dict[str, object]:
    return {
        "fig": getattr(app_state, "fig", None),
        "ax": getattr(app_state, "ax", None),
        "legend_ax": getattr(app_state, "legend_ax", None),
    }


def _restore_axes_state(snapshot: dict[str, object]) -> None:
    setattr(app_state, "fig", snapshot.get("fig"))
    setattr(app_state, "ax", snapshot.get("ax"))
    setattr(app_state, "legend_ax", snapshot.get("legend_ax"))


def test_ensure_axes_returns_none_when_figure_missing() -> None:
    snapshot = _snapshot_axes_state()
    try:
        setattr(app_state, "fig", None)
        setattr(app_state, "ax", None)

        result = _ensure_axes()

        assert result is None
    finally:
        _restore_axes_state(snapshot)


def test_ensure_axes_switches_between_2d_and_3d() -> None:
    snapshot = _snapshot_axes_state()
    fig = plt.figure()
    try:
        setattr(app_state, "fig", fig)
        setattr(app_state, "ax", None)
        setattr(app_state, "legend_ax", object())

        ax2d = _ensure_axes(2)
        assert ax2d is not None
        assert getattr(ax2d, "name", "") != "3d"
        assert getattr(app_state, "legend_ax", None) is None

        ax3d = _ensure_axes(3)
        assert ax3d is not None
        assert getattr(ax3d, "name", "") == "3d"
        assert getattr(app_state, "legend_ax", None) is None

        ax2d_again = _ensure_axes(2)
        assert ax2d_again is not None
        assert getattr(ax2d_again, "name", "") != "3d"
    finally:
        plt.close(fig)
        _restore_axes_state(snapshot)


def test_get_pb_columns_prefers_exact_names() -> None:
    columns = ["206Pb/204Pb", "foo", "207Pb/204Pb", "208Pb/204Pb"]

    pb206, pb207, pb208 = _get_pb_columns(columns)

    assert pb206 == "206Pb/204Pb"
    assert pb207 == "207Pb/204Pb"
    assert pb208 == "208Pb/204Pb"


def test_get_pb_columns_uses_heuristic_when_exact_missing() -> None:
    columns = ["sample_206_204", "ratio_207_204", "value_208-204"]

    pb206, pb207, pb208 = _get_pb_columns(columns)

    assert pb206 == "sample_206_204"
    assert pb207 == "ratio_207_204"
    assert pb208 == "value_208-204"


def test_lazy_import_geochemistry_loads_once_and_reuses_cache() -> None:
    snapshot = {
        "module": plotting_data._geochemistry,
        "calculate": plotting_data._calculate_all_parameters,
        "checked": plotting_data._geochem_checked,
    }
    try:
        plotting_data._geochemistry = None
        plotting_data._calculate_all_parameters = None
        plotting_data._geochem_checked = False

        module_1, calc_1 = plotting_data._lazy_import_geochemistry()
        module_2, calc_2 = plotting_data._lazy_import_geochemistry()

        assert module_1 is not None
        assert callable(calc_1)
        assert plotting_data._geochem_checked is True
        assert module_2 is module_1
        assert calc_2 is calc_1
    finally:
        plotting_data._geochemistry = snapshot["module"]
        plotting_data._calculate_all_parameters = snapshot["calculate"]
        plotting_data._geochem_checked = bool(snapshot["checked"])


def _snapshot_isochron_error_state() -> dict[str, object]:
    return {
        "mode": getattr(app_state, "isochron_error_mode", "fixed"),
        "sx_col": getattr(app_state, "isochron_sx_col", ""),
        "sy_col": getattr(app_state, "isochron_sy_col", ""),
        "rxy_col": getattr(app_state, "isochron_rxy_col", ""),
        "sx_value": getattr(app_state, "isochron_sx_value", 0.001),
        "sy_value": getattr(app_state, "isochron_sy_value", 0.001),
        "rxy_value": getattr(app_state, "isochron_rxy_value", 0.0),
    }


def _restore_isochron_error_state(snapshot: dict[str, object]) -> None:
    mode = str(snapshot.get("mode") or "fixed")
    if mode == "columns":
        state_gateway.set_isochron_error_columns(
            str(snapshot.get("sx_col") or ""),
            str(snapshot.get("sy_col") or ""),
            str(snapshot.get("rxy_col") or ""),
        )
        return
    state_gateway.set_isochron_error_fixed(
        float(snapshot.get("sx_value") or 0.001),
        float(snapshot.get("sy_value") or 0.001),
        float(snapshot.get("rxy_value") or 0.0),
    )


def test_resolve_isochron_errors_uses_columns_when_available() -> None:
    snapshot = _snapshot_isochron_error_state()
    try:
        state_gateway.set_isochron_error_columns("sx", "sy", "rxy")
        df = pd.DataFrame({"sx": [0.1, 0.2], "sy": [0.3, 0.4], "rxy": [0.5, 0.6]})

        sx, sy, rxy = resolve_isochron_errors(df, size=2)

        np.testing.assert_allclose(sx, np.array([0.1, 0.2], dtype=float), rtol=0.0, atol=1e-12)
        np.testing.assert_allclose(sy, np.array([0.3, 0.4], dtype=float), rtol=0.0, atol=1e-12)
        np.testing.assert_allclose(rxy, np.array([0.5, 0.6], dtype=float), rtol=0.0, atol=1e-12)
    finally:
        _restore_isochron_error_state(snapshot)


def test_resolve_isochron_errors_falls_back_to_fixed_when_columns_missing() -> None:
    snapshot = _snapshot_isochron_error_state()
    try:
        state_gateway.set_isochron_error_fixed(0.011, 0.022, 0.033)
        state_gateway.set_isochron_error_columns("missing_sx", "missing_sy", "missing_rxy")
        df = pd.DataFrame({"x": [1, 2, 3]})

        sx, sy, rxy = resolve_isochron_errors(df, size=3)

        np.testing.assert_allclose(sx, np.array([0.011, 0.011, 0.011], dtype=float), rtol=0.0, atol=1e-12)
        np.testing.assert_allclose(sy, np.array([0.022, 0.022, 0.022], dtype=float), rtol=0.0, atol=1e-12)
        np.testing.assert_allclose(rxy, np.array([0.033, 0.033, 0.033], dtype=float), rtol=0.0, atol=1e-12)
    finally:
        _restore_isochron_error_state(snapshot)


def test_configure_constrained_layout_prefers_layout_engine_api() -> None:
    class _LayoutEngine:
        def __init__(self) -> None:
            self.kwargs = None

        def set(self, **kwargs) -> None:
            self.kwargs = kwargs

    class _Figure:
        def __init__(self) -> None:
            self.calls: list[tuple[str, object]] = []
            self.engine = _LayoutEngine()

        def set_layout_engine(self, value: str) -> None:
            self.calls.append(("set_layout_engine", value))

        def get_layout_engine(self):
            self.calls.append(("get_layout_engine", None))
            return self.engine

        def set_constrained_layout(self, value: bool) -> None:
            self.calls.append(("set_constrained_layout", value))

        def set_constrained_layout_pads(self, **kwargs) -> None:
            self.calls.append(("set_constrained_layout_pads", kwargs))

    fig = _Figure()

    configure_constrained_layout(fig)

    assert ("set_layout_engine", "constrained") in fig.calls
    assert fig.engine.kwargs == {
        "w_pad": 0.02,
        "h_pad": 0.02,
        "wspace": 0.02,
        "hspace": 0.02,
    }
    assert all(
        name not in {"set_constrained_layout", "set_constrained_layout_pads"}
        for name, _value in fig.calls
    )


def test_configure_constrained_layout_falls_back_to_legacy_api() -> None:
    class _Figure:
        def __init__(self) -> None:
            self.calls: list[tuple[str, object]] = []

        def set_layout_engine(self, _value: str) -> None:
            raise RuntimeError("layout engine unsupported")

        def set_constrained_layout(self, value: bool) -> None:
            self.calls.append(("set_constrained_layout", value))

        def set_constrained_layout_pads(self, **kwargs) -> None:
            self.calls.append(("set_constrained_layout_pads", kwargs))

    fig = _Figure()

    configure_constrained_layout(fig, w_pad=0.1, h_pad=0.2, wspace=0.3, hspace=0.4)

    assert fig.calls == [
        ("set_constrained_layout", True),
        (
            "set_constrained_layout_pads",
            {
                "w_pad": 0.1,
                "h_pad": 0.2,
                "wspace": 0.3,
                "hspace": 0.4,
            },
        ),
    ]


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
