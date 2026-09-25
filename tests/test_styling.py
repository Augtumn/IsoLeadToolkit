"""Styling / style-manager and localization line-style helper tests."""

from types import SimpleNamespace

import matplotlib.pyplot as plt

from core import app_state, localization
from visualization import line_styles, style_manager
from visualization.plotting.styling.core import (
    _apply_axis_text_style,
    _enforce_plot_style,
)


def test_set_language_uses_gateway_and_notifies(monkeypatch) -> None:
    calls: list[str] = []

    fake_state = SimpleNamespace(language="zh", notify_language_change=lambda: calls.append("notify"))

    class _FakeGateway:
        @staticmethod
        def set_language_code(code: str) -> None:
            calls.append(f"gateway:{code}")
            setattr(fake_state, "language", code)

    monkeypatch.setattr(localization, "validate_language", lambda _lang: True)
    monkeypatch.setattr(localization, "ensure_language", lambda _lang: None)

    import core.state as state_pkg

    monkeypatch.setattr(state_pkg, "app_state", fake_state)
    monkeypatch.setattr(state_pkg, "state_gateway", _FakeGateway())

    ok = localization.set_language("en")

    assert ok is True
    assert fake_state.language == "en"
    assert calls == ["gateway:en", "notify"]


def test_set_language_rejects_invalid_language() -> None:
    assert localization.set_language("__invalid__") is False


def test_ensure_line_style_global_state_writes_via_gateway(monkeypatch) -> None:
    original_line_styles = dict(getattr(app_state, "line_styles", {}) or {})
    writes: list[dict[str, object]] = []
    try:
        setattr(app_state, "line_styles", {})

        def _fake_set_line_styles(styles: object) -> None:
            style_dict = dict(styles or {})
            writes.append(style_dict)
            setattr(app_state, "line_styles", style_dict)

        monkeypatch.setattr(line_styles.state_gateway, "set_line_styles", _fake_set_line_styles)

        resolved = line_styles.ensure_line_style(
            app_state,
            "model_curve",
            {"linewidth": 1.5, "linestyle": "-", "alpha": 0.8},
        )

        assert writes
        assert app_state.line_styles["model_curve"]["linewidth"] == 1.5
        assert resolved["linestyle"] == "-"
    finally:
        setattr(app_state, "line_styles", original_line_styles)


def test_ensure_line_style_custom_state_avoids_gateway(monkeypatch) -> None:
    custom_state = SimpleNamespace()

    def _raise_if_called(_styles: object) -> None:
        raise AssertionError("gateway should not be used for custom state objects")

    monkeypatch.setattr(line_styles.state_gateway, "set_line_styles", _raise_if_called)

    resolved = line_styles.ensure_line_style(custom_state, "isochron", {"linewidth": 2.0, "alpha": 0.9})

    assert custom_state.line_styles["isochron"]["linewidth"] == 2.0
    assert resolved["alpha"] == 0.9


def test_resolve_line_style_ignores_empty_color_override() -> None:
    state = SimpleNamespace(line_styles={"model_curve": {"color": "", "linewidth": 2.4}})

    resolved = line_styles.resolve_line_style(
        state,
        "model_curve",
        {"color": "#ef4444", "linewidth": 1.0, "linestyle": "--"},
    )

    assert resolved["color"] == "#ef4444"
    assert resolved["linewidth"] == 2.4
    assert resolved["linestyle"] == "--"


def test_apply_custom_style_delegates_to_style_manager_instance(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_apply_style(show_grid, color_scheme, primary_font, cjk_font, font_sizes):
        captured["show_grid"] = show_grid
        captured["color_scheme"] = color_scheme
        captured["primary_font"] = primary_font
        captured["cjk_font"] = cjk_font
        captured["font_sizes"] = font_sizes

    monkeypatch.setattr(style_manager.style_manager_instance, "apply_style", _fake_apply_style)

    style_manager.apply_custom_style(
        show_grid=True,
        color_scheme="bright",
        primary_font="Arial",
        cjk_font="Microsoft YaHei",
        font_sizes={"title": 13.0},
    )

    assert captured == {
        "show_grid": True,
        "color_scheme": "bright",
        "primary_font": "Arial",
        "cjk_font": "Microsoft YaHei",
        "font_sizes": {"title": 13.0},
    }


def _snapshot_style_state() -> dict[str, object]:
    keys = [
        "fig",
        "label_color",
        "label_weight",
        "label_pad",
        "title_color",
        "title_weight",
        "plot_style_grid",
        "grid_color",
        "grid_linewidth",
        "grid_alpha",
        "grid_linestyle",
        "minor_ticks",
        "minor_grid",
        "tick_direction",
        "tick_length",
        "tick_width",
        "tick_color",
        "minor_tick_length",
        "minor_tick_width",
        "axis_linewidth",
        "axis_line_color",
        "show_top_spine",
        "show_right_spine",
    ]
    return {key: getattr(app_state, key, None) for key in keys}


def _restore_style_state(snapshot: dict[str, object]) -> None:
    for key, value in snapshot.items():
        setattr(app_state, key, value)


def test_apply_axis_text_style_updates_axis_labels_and_title() -> None:
    snapshot = _snapshot_style_state()
    fig, ax = plt.subplots()
    try:
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.set_title("Title")

        setattr(app_state, "label_color", "#112233")
        setattr(app_state, "label_weight", "bold")
        setattr(app_state, "label_pad", 9.0)
        setattr(app_state, "title_color", "#334455")
        setattr(app_state, "title_weight", "normal")

        _apply_axis_text_style(ax)

        assert ax.xaxis.label.get_color() == "#112233"
        assert ax.yaxis.label.get_color() == "#112233"
        assert ax.xaxis.label.get_fontweight() == "bold"
        assert ax.yaxis.label.get_fontweight() == "bold"
        assert ax.xaxis.labelpad == 9.0
        assert ax.yaxis.labelpad == 9.0
        assert ax.title.get_color() == "#334455"
        assert ax.title.get_fontweight() == "normal"
    finally:
        plt.close(fig)
        _restore_style_state(snapshot)


def test_enforce_plot_style_applies_spine_visibility_and_tick_direction() -> None:
    snapshot = _snapshot_style_state()
    fig, ax = plt.subplots()
    try:
        setattr(app_state, "fig", fig)
        setattr(app_state, "plot_style_grid", False)
        setattr(app_state, "minor_ticks", False)
        setattr(app_state, "minor_grid", False)
        setattr(app_state, "tick_direction", "in")
        setattr(app_state, "tick_length", 6.0)
        setattr(app_state, "tick_width", 1.1)
        setattr(app_state, "tick_color", "#222222")
        setattr(app_state, "minor_tick_length", 3.0)
        setattr(app_state, "minor_tick_width", 0.7)
        setattr(app_state, "axis_linewidth", 1.3)
        setattr(app_state, "axis_line_color", "#123456")
        setattr(app_state, "show_top_spine", False)
        setattr(app_state, "show_right_spine", True)

        _enforce_plot_style(ax)

        assert ax.spines["top"].get_visible() is False
        assert ax.spines["right"].get_visible() is True
        assert ax.spines["left"].get_linewidth() == 1.3
        assert ax.spines["left"].get_edgecolor() != (0.0, 0.0, 0.0, 0.0)
        assert fig.patch.get_facecolor() is not None
    finally:
        plt.close(fig)
        _restore_style_state(snapshot)
