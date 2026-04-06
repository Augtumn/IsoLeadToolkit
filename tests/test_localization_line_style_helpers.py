"""Tests for localization and line style helper migration paths."""

from __future__ import annotations

from types import SimpleNamespace

from core import app_state
from core import localization
from visualization import line_styles


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
