"""Tests for style manager module-level compatibility exports."""

from __future__ import annotations

from visualization import style_manager


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
