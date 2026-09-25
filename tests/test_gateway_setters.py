"""Tests for explicit AppStateGateway setters (panel styles, overlay toggles)."""

import pytest

from core import app_state, state_gateway


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
def test_overlay_toggle_known_attr(attr: str) -> None:
    original_value = bool(getattr(app_state, attr, False))

    try:
        state_gateway.set_overlay_toggle(attr, not original_value)
        assert bool(getattr(app_state, attr)) is (not original_value)
    finally:
        state_gateway.set_overlay_toggle(attr, original_value)


def test_overlay_toggle_unknown_attr_ignored() -> None:
    fallback_attr = "_test_overlay_toggle_fallback"
    existed = hasattr(app_state, fallback_attr)
    original_value = bool(getattr(app_state, fallback_attr, False)) if existed else False

    try:
        state_gateway.set_overlay_toggle(fallback_attr, True)
        state_gateway.set_overlay_toggle(fallback_attr, False)
        if existed:
            assert getattr(app_state, fallback_attr) is original_value
        else:
            assert not hasattr(app_state, fallback_attr)
    finally:
        if existed:
            setattr(app_state, fallback_attr, original_value)
        elif hasattr(app_state, fallback_attr):
            delattr(app_state, fallback_attr)


def test_palette_and_marker_map_setter_syncs_snapshot() -> None:
    original_palette = dict(getattr(app_state, "current_palette", {}) or {})
    original_marker_map = dict(getattr(app_state, "group_marker_map", {}) or {})

    try:
        state_gateway.set_palette_and_marker_map({"GroupA": "#112233"}, {"GroupA": "s"})

        assert app_state.current_palette == {"GroupA": "#112233"}
        assert app_state.group_marker_map == {"GroupA": "s"}
        assert app_state.state_store.snapshot()["current_palette"] == {"GroupA": "#112233"}
        assert app_state.state_store.snapshot()["group_marker_map"] == {"GroupA": "s"}
    finally:
        state_gateway.set_palette_and_marker_map(original_palette, original_marker_map)


def test_panel_style_updates_known_key_and_unknown_key() -> None:
    original_plot_style_grid = bool(getattr(app_state, "plot_style_grid", False))
    original_plot_marker_size = int(getattr(app_state, "plot_marker_size", 60))
    original_plot_marker_alpha = float(getattr(app_state, "plot_marker_alpha", 0.8))
    original_show_plot_title = bool(getattr(app_state, "show_plot_title", False))
    original_plot_dpi = int(getattr(app_state, "plot_dpi", 130))
    original_custom_primary_font = str(getattr(app_state, "custom_primary_font", ""))
    original_custom_cjk_font = str(getattr(app_state, "custom_cjk_font", ""))
    original_plot_font_sizes = dict(getattr(app_state, "plot_font_sizes", {}) or {})
    original_plot_facecolor = str(getattr(app_state, "plot_facecolor", "#ffffff"))
    original_axes_facecolor = str(getattr(app_state, "axes_facecolor", "#ffffff"))
    original_grid_color = str(getattr(app_state, "grid_color", "#e2e8f0"))
    original_grid_linewidth = float(getattr(app_state, "grid_linewidth", 0.6))
    original_grid_alpha = float(getattr(app_state, "grid_alpha", 0.7))
    original_grid_linestyle = str(getattr(app_state, "grid_linestyle", "--"))
    original_tick_direction = str(getattr(app_state, "tick_direction", "out"))
    original_tick_color = str(getattr(app_state, "tick_color", "#1f2937"))
    original_tick_length = float(getattr(app_state, "tick_length", 4.0))
    original_tick_width = float(getattr(app_state, "tick_width", 0.8))
    original_axis_linewidth = float(getattr(app_state, "axis_linewidth", 1.0))
    original_axis_line_color = str(getattr(app_state, "axis_line_color", "#1f2937"))
    original_minor_ticks = bool(getattr(app_state, "minor_ticks", False))
    original_minor_tick_length = float(getattr(app_state, "minor_tick_length", 2.5))
    original_minor_tick_width = float(getattr(app_state, "minor_tick_width", 0.6))
    original_show_top_spine = bool(getattr(app_state, "show_top_spine", True))
    original_show_right_spine = bool(getattr(app_state, "show_right_spine", True))
    original_minor_grid = bool(getattr(app_state, "minor_grid", False))
    original_minor_grid_color = str(getattr(app_state, "minor_grid_color", "#e2e8f0"))
    original_minor_grid_linewidth = float(getattr(app_state, "minor_grid_linewidth", 0.4))
    original_minor_grid_alpha = float(getattr(app_state, "minor_grid_alpha", 0.4))
    original_minor_grid_linestyle = str(getattr(app_state, "minor_grid_linestyle", ":"))
    original_scatter_show_edge = bool(getattr(app_state, "scatter_show_edge", True))
    original_scatter_edgecolor = str(getattr(app_state, "scatter_edgecolor", "#1e293b"))
    original_scatter_edgewidth = float(getattr(app_state, "scatter_edgewidth", 0.4))
    original_label_color = str(getattr(app_state, "label_color", "#1f2937"))
    original_label_weight = str(getattr(app_state, "label_weight", "normal"))
    original_label_pad = float(getattr(app_state, "label_pad", 6.0))
    original_title_color = str(getattr(app_state, "title_color", "#111827"))
    original_title_weight = str(getattr(app_state, "title_weight", "bold"))
    original_title_pad = float(getattr(app_state, "title_pad", 20.0))
    original_legend_frame_on = bool(getattr(app_state, "legend_frame_on", True))
    original_legend_frame_alpha = float(getattr(app_state, "legend_frame_alpha", 0.95))
    original_legend_frame_facecolor = str(getattr(app_state, "legend_frame_facecolor", "#ffffff"))
    original_legend_frame_edgecolor = str(getattr(app_state, "legend_frame_edgecolor", "#cbd5f5"))
    original_adjust_text_force_text = tuple(
        getattr(app_state, "adjust_text_force_text", (0.8, 1.0)) or (0.8, 1.0)
    )
    original_adjust_text_force_static = tuple(
        getattr(app_state, "adjust_text_force_static", (0.4, 0.6)) or (0.4, 0.6)
    )
    original_adjust_text_expand = tuple(
        getattr(app_state, "adjust_text_expand", (1.08, 1.20)) or (1.08, 1.20)
    )
    original_adjust_text_iter_lim = int(getattr(app_state, "adjust_text_iter_lim", 120))
    original_adjust_text_time_lim = float(getattr(app_state, "adjust_text_time_lim", 0.25))
    fallback_attr = "_test_panel_style_unknown"
    existed = hasattr(app_state, fallback_attr)
    original_value = getattr(app_state, fallback_attr, None) if existed else None
    original_selection_mode = bool(getattr(app_state, "selection_mode", False))

    try:
        state_gateway.set_panel_style_updates(
            {
                "plot_style_grid": (not original_plot_style_grid),
                "plot_marker_size": 93,
                "plot_marker_alpha": 0.62,
                "show_plot_title": (not original_show_plot_title),
                "plot_dpi": 170,
                "custom_primary_font": "Calibri",
                "custom_cjk_font": "SimHei",
                "plot_font_sizes": {"title": 18, "label": 13, "tick": 11, "legend": 12},
                "plot_facecolor": "#fefce8",
                "axes_facecolor": "#f8fafc",
                "grid_color": "#334155",
                "grid_linewidth": 1.1,
                "grid_alpha": 0.66,
                "grid_linestyle": ":",
                "tick_direction": "in",
                "tick_color": "#0f172a",
                "tick_length": 5.2,
                "tick_width": 1.0,
                "axis_linewidth": 1.3,
                "axis_line_color": "#111827",
                "minor_ticks": True,
                "minor_tick_length": 3.2,
                "minor_tick_width": 0.9,
                "show_top_spine": False,
                "show_right_spine": False,
                "minor_grid": True,
                "minor_grid_color": "#94a3b8",
                "minor_grid_linewidth": 0.8,
                "minor_grid_alpha": 0.5,
                "minor_grid_linestyle": "-.",
                "scatter_show_edge": False,
                "scatter_edgecolor": "#334155",
                "scatter_edgewidth": 0.7,
                "label_color": "#1e293b",
                "label_weight": "bold",
                "label_pad": 10.0,
                "title_color": "#0f172a",
                "title_weight": "normal",
                "title_pad": 24.0,
                "legend_frame_on": False,
                "legend_frame_alpha": 0.7,
                "legend_frame_facecolor": "#f8fafc",
                "legend_frame_edgecolor": "#94a3b8",
                "adjust_text_force_text": (1.2, 1.4),
                "adjust_text_force_static": (0.7, 0.9),
                "adjust_text_expand": (1.3, 1.5),
                "adjust_text_iter_lim": 240,
                "adjust_text_time_lim": 0.75,
                fallback_attr: "ignored",
                "selection_mode": (not original_selection_mode),
            }
        )

        assert bool(getattr(app_state, "plot_style_grid", False)) is (not original_plot_style_grid)
        assert int(getattr(app_state, "plot_marker_size", 0)) == 93
        assert float(getattr(app_state, "plot_marker_alpha", 0.0)) == 0.62
        assert bool(getattr(app_state, "show_plot_title", False)) is (not original_show_plot_title)
        assert int(getattr(app_state, "plot_dpi", 0)) == 170
        assert str(getattr(app_state, "custom_primary_font", "")) == "Calibri"
        assert str(getattr(app_state, "custom_cjk_font", "")) == "SimHei"
        assert dict(getattr(app_state, "plot_font_sizes", {}) or {}) == {
            "title": 18,
            "label": 13,
            "tick": 11,
            "legend": 12,
        }
        assert str(getattr(app_state, "plot_facecolor", "")) == "#fefce8"
        assert str(getattr(app_state, "axes_facecolor", "")) == "#f8fafc"
        assert str(getattr(app_state, "grid_color", "")) == "#334155"
        assert float(getattr(app_state, "grid_linewidth", 0.0)) == 1.1
        assert float(getattr(app_state, "grid_alpha", 0.0)) == 0.66
        assert str(getattr(app_state, "grid_linestyle", "")) == ":"
        assert str(getattr(app_state, "tick_direction", "")) == "in"
        assert str(getattr(app_state, "tick_color", "")) == "#0f172a"
        assert float(getattr(app_state, "tick_length", 0.0)) == 5.2
        assert float(getattr(app_state, "tick_width", 0.0)) == 1.0
        assert float(getattr(app_state, "axis_linewidth", 0.0)) == 1.3
        assert str(getattr(app_state, "axis_line_color", "")) == "#111827"
        assert bool(getattr(app_state, "minor_ticks", False)) is True
        assert float(getattr(app_state, "minor_tick_length", 0.0)) == 3.2
        assert float(getattr(app_state, "minor_tick_width", 0.0)) == 0.9
        assert bool(getattr(app_state, "show_top_spine", True)) is False
        assert bool(getattr(app_state, "show_right_spine", True)) is False
        assert bool(getattr(app_state, "minor_grid", False)) is True
        assert str(getattr(app_state, "minor_grid_color", "")) == "#94a3b8"
        assert float(getattr(app_state, "minor_grid_linewidth", 0.0)) == 0.8
        assert float(getattr(app_state, "minor_grid_alpha", 0.0)) == 0.5
        assert str(getattr(app_state, "minor_grid_linestyle", "")) == "-."
        assert bool(getattr(app_state, "scatter_show_edge", True)) is False
        assert str(getattr(app_state, "scatter_edgecolor", "")) == "#334155"
        assert float(getattr(app_state, "scatter_edgewidth", 0.0)) == 0.7
        assert str(getattr(app_state, "label_color", "")) == "#1e293b"
        assert str(getattr(app_state, "label_weight", "")) == "bold"
        assert float(getattr(app_state, "label_pad", 0.0)) == 10.0
        assert str(getattr(app_state, "title_color", "")) == "#0f172a"
        assert str(getattr(app_state, "title_weight", "")) == "normal"
        assert float(getattr(app_state, "title_pad", 0.0)) == 24.0
        assert bool(getattr(app_state, "legend_frame_on", True)) is False
        assert float(getattr(app_state, "legend_frame_alpha", 0.0)) == 0.7
        assert str(getattr(app_state, "legend_frame_facecolor", "")) == "#f8fafc"
        assert str(getattr(app_state, "legend_frame_edgecolor", "")) == "#94a3b8"
        assert tuple(getattr(app_state, "adjust_text_force_text", ())) == (1.2, 1.4)
        assert tuple(getattr(app_state, "adjust_text_force_static", ())) == (0.7, 0.9)
        assert tuple(getattr(app_state, "adjust_text_expand", ())) == (1.3, 1.5)
        assert int(getattr(app_state, "adjust_text_iter_lim", 0)) == 240
        assert float(getattr(app_state, "adjust_text_time_lim", 0.0)) == 0.75
        assert bool(getattr(app_state, "selection_mode", False)) is original_selection_mode

        snapshot = app_state.state_store.snapshot()
        assert snapshot["plot_style_grid"] is (not original_plot_style_grid)
        assert snapshot["plot_marker_size"] == 93
        assert snapshot["plot_marker_alpha"] == 0.62
        assert snapshot["show_plot_title"] is (not original_show_plot_title)
        assert snapshot["plot_dpi"] == 170
        assert snapshot["custom_primary_font"] == "Calibri"
        assert snapshot["custom_cjk_font"] == "SimHei"
        assert snapshot["plot_font_sizes"] == {
            "title": 18,
            "label": 13,
            "tick": 11,
            "legend": 12,
        }
        assert snapshot["plot_facecolor"] == "#fefce8"
        assert snapshot["axes_facecolor"] == "#f8fafc"
        assert snapshot["grid_color"] == "#334155"
        assert snapshot["grid_linewidth"] == 1.1
        assert snapshot["grid_alpha"] == 0.66
        assert snapshot["grid_linestyle"] == ":"
        assert snapshot["tick_direction"] == "in"
        assert snapshot["tick_color"] == "#0f172a"
        assert snapshot["tick_length"] == 5.2
        assert snapshot["tick_width"] == 1.0
        assert snapshot["axis_linewidth"] == 1.3
        assert snapshot["axis_line_color"] == "#111827"
        assert snapshot["minor_ticks"] is True
        assert snapshot["minor_tick_length"] == 3.2
        assert snapshot["minor_tick_width"] == 0.9
        assert snapshot["show_top_spine"] is False
        assert snapshot["show_right_spine"] is False
        assert snapshot["minor_grid"] is True
        assert snapshot["minor_grid_color"] == "#94a3b8"
        assert snapshot["minor_grid_linewidth"] == 0.8
        assert snapshot["minor_grid_alpha"] == 0.5
        assert snapshot["minor_grid_linestyle"] == "-."
        assert snapshot["scatter_show_edge"] is False
        assert snapshot["scatter_edgecolor"] == "#334155"
        assert snapshot["scatter_edgewidth"] == 0.7
        assert snapshot["label_color"] == "#1e293b"
        assert snapshot["label_weight"] == "bold"
        assert snapshot["label_pad"] == 10.0
        assert snapshot["title_color"] == "#0f172a"
        assert snapshot["title_weight"] == "normal"
        assert snapshot["title_pad"] == 24.0
        assert snapshot["legend_frame_on"] is False
        assert snapshot["legend_frame_alpha"] == 0.7
        assert snapshot["legend_frame_facecolor"] == "#f8fafc"
        assert snapshot["legend_frame_edgecolor"] == "#94a3b8"
        assert snapshot["adjust_text_force_text"] == (1.2, 1.4)
        assert snapshot["adjust_text_force_static"] == (0.7, 0.9)
        assert snapshot["adjust_text_expand"] == (1.3, 1.5)
        assert snapshot["adjust_text_iter_lim"] == 240
        assert snapshot["adjust_text_time_lim"] == 0.75

        if existed:
            assert getattr(app_state, fallback_attr) == original_value
        else:
            assert not hasattr(app_state, fallback_attr)
    finally:
        state_gateway.set_plot_style_grid(original_plot_style_grid)
        state_gateway.set_plot_marker_size(original_plot_marker_size)
        state_gateway.set_plot_marker_alpha(original_plot_marker_alpha)
        state_gateway.set_show_plot_title(original_show_plot_title)
        state_gateway.set_plot_dpi(original_plot_dpi)
        state_gateway.set_custom_primary_font(original_custom_primary_font)
        state_gateway.set_custom_cjk_font(original_custom_cjk_font)
        state_gateway.set_plot_font_sizes(original_plot_font_sizes)
        state_gateway.set_plot_facecolor(original_plot_facecolor)
        state_gateway.set_axes_facecolor(original_axes_facecolor)
        state_gateway.set_grid_color(original_grid_color)
        state_gateway.set_grid_linewidth(original_grid_linewidth)
        state_gateway.set_grid_alpha(original_grid_alpha)
        state_gateway.set_grid_linestyle(original_grid_linestyle)
        state_gateway.set_tick_direction(original_tick_direction)
        state_gateway.set_tick_color(original_tick_color)
        state_gateway.set_tick_length(original_tick_length)
        state_gateway.set_tick_width(original_tick_width)
        state_gateway.set_axis_linewidth(original_axis_linewidth)
        state_gateway.set_axis_line_color(original_axis_line_color)
        state_gateway.set_minor_ticks(original_minor_ticks)
        state_gateway.set_minor_tick_length(original_minor_tick_length)
        state_gateway.set_minor_tick_width(original_minor_tick_width)
        state_gateway.set_show_top_spine(original_show_top_spine)
        state_gateway.set_show_right_spine(original_show_right_spine)
        state_gateway.set_minor_grid(original_minor_grid)
        state_gateway.set_minor_grid_color(original_minor_grid_color)
        state_gateway.set_minor_grid_linewidth(original_minor_grid_linewidth)
        state_gateway.set_minor_grid_alpha(original_minor_grid_alpha)
        state_gateway.set_minor_grid_linestyle(original_minor_grid_linestyle)
        state_gateway.set_scatter_show_edge(original_scatter_show_edge)
        state_gateway.set_scatter_edgecolor(original_scatter_edgecolor)
        state_gateway.set_scatter_edgewidth(original_scatter_edgewidth)
        state_gateway.set_label_color(original_label_color)
        state_gateway.set_label_weight(original_label_weight)
        state_gateway.set_label_pad(original_label_pad)
        state_gateway.set_title_color(original_title_color)
        state_gateway.set_title_weight(original_title_weight)
        state_gateway.set_title_pad(original_title_pad)
        state_gateway.set_legend_frame_on(original_legend_frame_on)
        state_gateway.set_legend_frame_alpha(original_legend_frame_alpha)
        state_gateway.set_legend_frame_facecolor(original_legend_frame_facecolor)
        state_gateway.set_legend_frame_edgecolor(original_legend_frame_edgecolor)
        state_gateway.set_adjust_text_force_text(original_adjust_text_force_text)
        state_gateway.set_adjust_text_force_static(original_adjust_text_force_static)
        state_gateway.set_adjust_text_expand(original_adjust_text_expand)
        state_gateway.set_adjust_text_iter_lim(original_adjust_text_iter_lim)
        state_gateway.set_adjust_text_time_lim(original_adjust_text_time_lim)
        state_gateway.set_selection_mode(original_selection_mode)
        if existed:
            setattr(app_state, fallback_attr, original_value)
        elif hasattr(app_state, fallback_attr):
            delattr(app_state, fallback_attr)


def test_overlay_label_state_only_updates_known_keys() -> None:
    original_overlay_curve = list(getattr(app_state, "overlay_curve_label_data", []) or [])
    original_paleo = list(getattr(app_state, "paleoisochron_label_data", []) or [])
    original_plumbo = list(getattr(app_state, "plumbotectonics_label_data", []) or [])
    original_isoage = list(getattr(app_state, "plumbotectonics_isoage_label_data", []) or [])

    try:
        state_gateway.set_overlay_label_state(
            {
                "overlay_curve_label_data": [{"text": "A"}],
                "paleoisochron_label_data": [{"text": "B"}],
                "plumbotectonics_label_data": [{"text": "C"}],
                "plumbotectonics_isoage_label_data": [{"text": "D"}],
            }
        )

        assert app_state.overlay_curve_label_data == [{"text": "A"}]
        assert app_state.paleoisochron_label_data == [{"text": "B"}]
        assert app_state.plumbotectonics_label_data == [{"text": "C"}]
        assert app_state.plumbotectonics_isoage_label_data == [{"text": "D"}]

        snapshot = app_state.state_store.snapshot()
        assert snapshot["overlay_curve_label_data"] == [{"text": "A"}]
        assert snapshot["paleoisochron_label_data"] == [{"text": "B"}]
        assert snapshot["plumbotectonics_label_data"] == [{"text": "C"}]
        assert snapshot["plumbotectonics_isoage_label_data"] == [{"text": "D"}]
    finally:
        state_gateway.set_overlay_label_state(
            {
                "overlay_curve_label_data": original_overlay_curve,
                "paleoisochron_label_data": original_paleo,
                "plumbotectonics_label_data": original_plumbo,
                "plumbotectonics_isoage_label_data": original_isoage,
            }
        )


def test_overlay_label_state_ignores_unknown_keys() -> None:
    fallback_attr = "_test_overlay_label_state_unknown"
    existed = hasattr(app_state, fallback_attr)
    original_value = getattr(app_state, fallback_attr, None) if existed else None

    try:
        state_gateway.set_overlay_label_state({fallback_attr: [{"text": "x"}]})

        if existed:
            assert getattr(app_state, fallback_attr) == original_value
        else:
            assert not hasattr(app_state, fallback_attr)
    finally:
        if existed:
            setattr(app_state, fallback_attr, original_value)
        elif hasattr(app_state, fallback_attr):
            delattr(app_state, fallback_attr)
