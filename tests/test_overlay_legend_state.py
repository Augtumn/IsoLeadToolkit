"""Tests for OverlayState and LegendState runtime behavior."""

from __future__ import annotations

from core.legend_state import DEFAULT_LEGEND_FRAME_ALPHA, LegendState
from core.overlay_state import OverlayState


def test_overlay_state_clear_artists_resets_runtime_tracking() -> None:
    overlay = OverlayState()
    overlay.overlay_artists = {"curves": ["line_1"]}
    overlay.overlay_curve_label_data = [{"text": "curve"}]
    overlay.paleoisochron_label_data = [{"text": "paleo"}]
    overlay.plumbotectonics_label_data = [{"text": "plumbo"}]
    overlay.plumbotectonics_isoage_label_data = [{"text": "isoage"}]

    overlay.clear_artists()

    assert overlay.overlay_artists == {}
    assert overlay.overlay_curve_label_data == []
    assert overlay.paleoisochron_label_data == []
    assert overlay.plumbotectonics_label_data == []
    assert overlay.plumbotectonics_isoage_label_data == []


def test_overlay_state_init_equation_styles_creates_style_key_entry() -> None:
    overlay = OverlayState()
    overlay.equation_overlays = [
        {
            "id": "eq_custom",
            "label": "y=2x+1",
            "expression": "2*x+1",
            "color": "#0ea5e9",
            "linewidth": 1.6,
            "linestyle": "-.",
            "alpha": 0.72,
        }
    ]

    overlay._init_equation_styles()

    style_key = overlay.equation_overlays[0].get("style_key")
    assert style_key == "equation:eq_custom"
    assert style_key in overlay.line_styles
    assert overlay.line_styles[style_key]["color"] == "#0ea5e9"
    assert overlay.line_styles[style_key]["linewidth"] == 1.6
    assert overlay.line_styles[style_key]["linestyle"] == "-."
    assert overlay.line_styles[style_key]["alpha"] == 0.72


def test_legend_state_defaults_are_stable() -> None:
    legend = LegendState()

    assert legend.legend_position is None
    assert legend.legend_columns == 0
    assert legend.legend_offset == (0.0, 0.0)
    assert legend.legend_location == "outside_left"
    assert legend.legend_display_mode == "inline"
    assert legend.legend_frame_alpha == DEFAULT_LEGEND_FRAME_ALPHA
    assert legend.hidden_groups == set()
    assert legend.legend_to_scatter == {}
    assert legend.legend_update_callback is None
