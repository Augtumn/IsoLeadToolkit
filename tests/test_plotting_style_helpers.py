"""Tests for plotting style facade helpers."""

from __future__ import annotations

from visualization.plotting.style import configure_constrained_layout


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
