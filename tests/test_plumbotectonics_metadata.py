"""Tests for plumbotectonics metadata helpers."""

from __future__ import annotations

from visualization.plotting.geochem import plumbotectonics_metadata as metadata


def test_get_plumbotectonics_variants_uses_label_and_fallback(monkeypatch) -> None:
    sections = [
        {"label": "Variant A"},
        {"label": ""},
        {},
    ]
    monkeypatch.setattr(metadata, "_load_plumbotectonics_data", lambda: sections)

    assert metadata.get_plumbotectonics_variants() == [
        ("0", "Variant A"),
        ("1", "Model 2"),
        ("2", "Model 3"),
    ]


def test_get_plumbotectonics_group_entries_builds_unique_keys() -> None:
    section = {
        "groups": [
            {"name": "Mantle Arc"},
            {"name": "Mantle Arc"},
            {"name": ""},
        ]
    }

    entries = metadata.get_plumbotectonics_group_entries(section=section)

    assert [item["key"] for item in entries] == ["mantle_arc", "mantle_arc_2", "group_3"]
    assert [item["style_key"] for item in entries] == [
        "plumbotectonics_curve:mantle_arc",
        "plumbotectonics_curve:mantle_arc_2",
        "plumbotectonics_curve:group_3",
    ]


def test_get_plumbotectonics_group_palette_cycles_colors(monkeypatch) -> None:
    section = {
        "groups": [
            {"name": "G1"},
            {"name": "G2"},
            {"name": "G3"},
        ]
    }
    monkeypatch.setattr(metadata, "_overlay_palette", lambda: ["#111111", "#222222"])

    palette = metadata.get_plumbotectonics_group_palette(section=section)

    assert palette == {
        "plumbotectonics_curve:g1": "#111111",
        "plumbotectonics_curve:g2": "#222222",
        "plumbotectonics_curve:g3": "#111111",
    }


def test_get_overlay_default_color_uses_index_map(monkeypatch) -> None:
    monkeypatch.setattr(metadata, "_overlay_palette", lambda: ["#111111", "#222222"])

    assert metadata.get_overlay_default_color("model_curve") == "#111111"
    assert metadata.get_overlay_default_color("paleoisochron") == "#222222"
    assert metadata.get_overlay_default_color("model_age_line") == "#111111"
    assert metadata.get_overlay_default_color("unknown") == "#111111"


def test_plumbotectonics_marker_keyword_mapping() -> None:
    assert metadata._plumbotectonics_marker("Mantle") == "o"
    assert metadata._plumbotectonics_marker("下地壳") == "s"
    assert metadata._plumbotectonics_marker("Upper Crust") == "^"
    assert metadata._plumbotectonics_marker("Orogene belt") == "D"
    assert metadata._plumbotectonics_marker("Other") == "o"
