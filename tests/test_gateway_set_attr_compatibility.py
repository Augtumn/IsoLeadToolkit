"""Compatibility checks for legacy state_gateway.set_attr routing."""

from __future__ import annotations

import pytest

from core import app_state, state_gateway


def test_group_and_data_columns_set_attr_compatibility() -> None:
    original_group_cols = list(getattr(app_state, "group_cols", []) or [])
    original_data_cols = list(getattr(app_state, "data_cols", []) or [])

    try:
        state_gateway.set_group_data_columns(["G0"], ["A", "B", "C"])

        state_gateway.set_attr("group_cols", ["G1", "G2"])
        assert app_state.group_cols == ["G1", "G2"]
        assert app_state.data_cols == ["A", "B", "C"]

        state_gateway.set_attr("data_cols", ["X", "Y"])
        assert app_state.group_cols == ["G1", "G2"]
        assert app_state.data_cols == ["X", "Y"]

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["group_cols"] == ["G1", "G2"]
        assert store_snapshot["data_cols"] == ["X", "Y"]
    finally:
        state_gateway.set_group_data_columns(original_group_cols, original_data_cols)


def test_tooltip_set_attr_compatibility() -> None:
    original_show_tooltip = bool(getattr(app_state, "show_tooltip", False))

    try:
        state_gateway.set_attr("show_tooltip", True)
        assert app_state.show_tooltip is True
        assert app_state.state_store.snapshot()["show_tooltip"] is True

        state_gateway.set_attr("show_tooltip", False)
        assert app_state.show_tooltip is False
        assert app_state.state_store.snapshot()["show_tooltip"] is False
    finally:
        state_gateway.set_show_tooltip(original_show_tooltip)


def test_export_image_options_set_attr_compatibility() -> None:
    original_options = dict(getattr(app_state, "export_image_options", {}) or {})

    try:
        state_gateway.set_attr(
            "export_image_options",
            {
                "preset_key": "ieee_single",
                "image_ext": "SVG",
                "dpi": 50,
                "bbox_tight": False,
                "pad_inches": -1.0,
                "transparent": True,
                "point_size": 13,
                "legend_size": 8,
            },
        )

        options = state_gateway.get_export_image_options()
        assert options["preset_key"] == "ieee_single"
        assert options["image_ext"] == "svg"
        assert options["dpi"] == 72
        assert options["bbox_tight"] is False
        assert options["pad_inches"] == 0.0
        assert options["transparent"] is True
        assert options["point_size"] == 13
        assert options["legend_size"] == 8
    finally:
        state_gateway.set_export_image_options(**original_options)


@pytest.mark.parametrize(
    "attr",
    [
        "show_model_curves",
        "show_plumbotectonics_curves",
        "show_paleoisochrons",
        "show_model_age_lines",
        "show_growth_curves",
        "show_isochrons",
    ],
)
def test_overlay_toggle_known_attr_compatibility(attr: str) -> None:
    original_value = bool(getattr(app_state, attr, False))

    try:
        state_gateway.set_overlay_toggle(attr, not original_value)
        assert bool(getattr(app_state, attr)) is (not original_value)
    finally:
        state_gateway.set_overlay_toggle(attr, original_value)


def test_overlay_toggle_fallback_attr_assignment() -> None:
    fallback_attr = "_test_overlay_toggle_fallback"
    existed = hasattr(app_state, fallback_attr)
    original_value = bool(getattr(app_state, fallback_attr, False)) if existed else False

    try:
        state_gateway.set_overlay_toggle(fallback_attr, True)
        assert getattr(app_state, fallback_attr) is True

        state_gateway.set_overlay_toggle(fallback_attr, False)
        assert getattr(app_state, fallback_attr) is False
    finally:
        if existed:
            setattr(app_state, fallback_attr, original_value)
        elif hasattr(app_state, fallback_attr):
            delattr(app_state, fallback_attr)


def test_point_size_set_attr_conversion() -> None:
    original_point_size = int(getattr(app_state, "point_size", 60))

    try:
        state_gateway.set_attr("point_size", "77")
        assert app_state.point_size == 77
        assert app_state.state_store.snapshot()["point_size"] == 77
    finally:
        state_gateway.set_point_size(original_point_size)


def test_ui_theme_set_attr_conversion() -> None:
    original_theme = str(getattr(app_state, "ui_theme", "Modern Light"))

    try:
        state_gateway.set_attr("ui_theme", 123)
        assert app_state.ui_theme == "123"
        assert app_state.state_store.snapshot()["ui_theme"] == "123"
    finally:
        state_gateway.set_ui_theme(original_theme)


def test_language_set_attr_conversion() -> None:
    original_language = str(getattr(app_state, "language", "zh"))

    try:
        state_gateway.set_attr("language", 123)
        assert app_state.language == "123"
        assert app_state.state_store.snapshot()["language"] == "123"
    finally:
        state_gateway.set_language_code(original_language)


def test_legend_preferences_set_attr_compatibility() -> None:
    original_color_scheme = str(getattr(app_state, "color_scheme", "vibrant"))
    original_position = getattr(app_state, "legend_position", None)
    original_location = getattr(app_state, "legend_location", "outside_left")
    original_columns = int(getattr(app_state, "legend_columns", 0))
    original_nudge_step = float(getattr(app_state, "legend_nudge_step", 0.02))
    original_offset = tuple(getattr(app_state, "legend_offset", (0.0, 0.0)) or (0.0, 0.0))

    try:
        state_gateway.set_attr("color_scheme", 777)
        state_gateway.set_attr("legend_position", "upper left")
        state_gateway.set_attr("legend_location", "outside_right")
        state_gateway.set_attr("legend_columns", "4")
        state_gateway.set_attr("legend_nudge_step", "0.125")
        state_gateway.set_attr("legend_offset", [0.2, -0.1])

        assert app_state.color_scheme == "777"
        assert app_state.legend_position == "upper left"
        assert app_state.legend_location == "outside_right"
        assert app_state.legend_columns == 4
        assert app_state.legend_nudge_step == 0.125
        assert app_state.legend_offset == (0.2, -0.1)

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["color_scheme"] == "777"
        assert store_snapshot["legend_position"] == "upper left"
        assert store_snapshot["legend_location"] == "outside_right"
        assert store_snapshot["legend_columns"] == 4
        assert store_snapshot["legend_nudge_step"] == 0.125
        assert store_snapshot["legend_offset"] == (0.2, -0.1)
    finally:
        state_gateway.set_color_scheme(original_color_scheme)
        state_gateway.set_legend_position(original_position)
        state_gateway.set_legend_location(original_location)
        state_gateway.set_legend_columns(original_columns)
        state_gateway.set_legend_nudge_step(original_nudge_step)
        state_gateway.set_legend_offset(original_offset)


def test_recent_files_set_attr_compatibility() -> None:
    original_recent_files = list(getattr(app_state, "recent_files", []) or [])

    try:
        state_gateway.set_attr("recent_files", ["d:/tmp/a.xlsx", "d:/tmp/b.csv"])
        assert app_state.recent_files == ["d:/tmp/a.xlsx", "d:/tmp/b.csv"]
        assert app_state.state_store.snapshot()["recent_files"] == ["d:/tmp/a.xlsx", "d:/tmp/b.csv"]
    finally:
        state_gateway.set_recent_files(original_recent_files)


def test_line_styles_set_attr_compatibility() -> None:
    original_line_styles = dict(getattr(app_state, "line_styles", {}) or {})

    try:
        state_gateway.set_attr("line_styles", {"model_curve": {"linewidth": 2.4}})
        assert app_state.line_styles["model_curve"]["linewidth"] == 2.4
        assert app_state.state_store.snapshot()["line_styles"]["model_curve"]["linewidth"] == 2.4
    finally:
        state_gateway.set_line_styles(original_line_styles)


def test_saved_themes_set_attr_compatibility() -> None:
    original_saved_themes = dict(getattr(app_state, "saved_themes", {}) or {})

    try:
        state_gateway.set_attr("saved_themes", {"demo": {"color_scheme": "vibrant"}})
        assert app_state.saved_themes["demo"]["color_scheme"] == "vibrant"
        assert app_state.state_store.snapshot()["saved_themes"]["demo"]["color_scheme"] == "vibrant"
    finally:
        state_gateway.set_saved_themes(original_saved_themes)


def test_confidence_level_set_attr_conversion() -> None:
    original_level = float(getattr(app_state, "confidence_level", 0.95))

    try:
        state_gateway.set_attr("confidence_level", "0.91")
        assert app_state.confidence_level == 0.91
    finally:
        state_gateway.set_confidence_level(original_level)
