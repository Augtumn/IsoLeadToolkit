"""The panels declare their widgets once, and the reset follows the declaration.

Three panels used to set their widget attributes one assignment per line in reset_state - thirty, fifty-four and
twenty-one lines. They are one table each now, naming every widget and its fallback, and a shared helper applies it
so a reset cannot forget a member. The reads did not move, which is what makes it safe.

Each table is pinned by name: dropping a widget from a declaration fails here before it fails in the application.
"""
from __future__ import annotations

import pathlib

import pytest

from ui.panels.data.build import _WIDGET_DEFAULTS as DATA
from ui.panels.display.build import _WIDGET_DEFAULTS as DISPLAY
from ui.panels.geochemistry.overlays import _WIDGET_DEFAULTS as GEOCHEM
from ui.panels.widget_state import reset_widget_state


class _Host:
    pass

#: data panel
EXPECTED_DATA = (
    'algo_combo',
    'algo_group',
    'group_placeholder_label',
    'group_radio_group',
    'group_radio_layout',
    'metric_combo',
    'pca_group',
    'pca_x_spin',
    'pca_y_spin',
    'plumbotectonics_model_keys',
    'render_combo',
    'robust_pca_group',
    'rpca_x_spin',
    'rpca_y_spin',
    'spinboxes',
    'ternary_auto_zoom_check',
    'ternary_group',
    'ternary_limit_mode_combo',
    'ternary_limit_spins',
    'ternary_manual_limits_check',
    'ternary_render_margin_spin',
    'tooltip_check',
    'tsne_group',
    'twod_group',
    'umap_group',
    'v1v2_group',
    'v1v2_t1_spin',
    'v1v2_t2_spin',
    'xaxis_combo',
    'yaxis_combo',
)

#: display panel
EXPECTED_DISPLAY = (
    '_search_edit',
    '_search_hidden_pages',
    '_search_match_label',
    '_section_toolbox',
    'adjust_expand_x_spin',
    'adjust_expand_y_spin',
    'adjust_force_static_x_spin',
    'adjust_force_static_y_spin',
    'adjust_force_text_x_spin',
    'adjust_force_text_y_spin',
    'adjust_iter_lim_spin',
    'adjust_time_lim_spin',
    'axes_bg_edit',
    'axis_line_color_edit',
    'axis_linewidth_spin',
    'cjk_font_combo',
    'figure_bg_edit',
    'figure_dpi_spin',
    'font_size_spins',
    'grid_alpha_spin',
    'grid_check',
    'grid_color_edit',
    'grid_style_combo',
    'grid_width_spin',
    'label_color_edit',
    'label_pad_spin',
    'label_weight_combo',
    'marker_alpha_spin',
    'marker_size_spin',
    'minor_grid_alpha_spin',
    'minor_grid_check',
    'minor_grid_color_edit',
    'minor_grid_style_combo',
    'minor_grid_width_spin',
    'minor_tick_length_spin',
    'minor_tick_width_spin',
    'minor_ticks_check',
    'primary_font_combo',
    'scatter_edge_check',
    'scatter_edgecolor_edit',
    'scatter_edgewidth_spin',
    'show_right_spine_check',
    'show_title_check',
    'show_top_spine_check',
    'theme_load_combo',
    'theme_name_edit',
    'tick_color_edit',
    'tick_dir_combo',
    'tick_length_spin',
    'tick_width_spin',
    'title_color_edit',
    'title_pad_spin',
    'title_weight_combo',
    'ui_theme_combo',
)

#: geochemistry panel
EXPECTED_GEOCHEMISTRY = (
    'calc_isochron_btn',
    'geochem_plot_group',
    'isochron_settings_btn',
    'isochron_swatch',
    'modeling_show_growth_curve_check',
    'modeling_show_isochron_check',
    'modeling_show_model_age_check',
    'modeling_show_model_check',
    'modeling_show_paleoisochron_check',
    'modeling_show_plumbotectonics_check',
    'modeling_use_real_age_check',
    'mu_kappa_age_button',
    'mu_kappa_age_label',
    'mu_kappa_age_title_label',
    'paleo_step_spin',
    'plumbotectonics_model_combo',
    'plumbotectonics_model_label',
    'show_isochron_check',
    'show_model_age_check',
    'show_model_check',
    'show_paleoisochron_check',
)

DECLARATIONS = {"data": (DATA, EXPECTED_DATA), "display": (DISPLAY, EXPECTED_DISPLAY), "geochemistry": (GEOCHEM, EXPECTED_GEOCHEMISTRY)}


@pytest.mark.parametrize("label", sorted(DECLARATIONS))
def test_the_declaration_names_the_measured_widgets(label: str) -> None:
    defaults, expected = DECLARATIONS[label]
    assert sorted(defaults) == sorted(expected)


@pytest.mark.parametrize("label", sorted(DECLARATIONS))
def test_a_reset_sets_every_declared_widget(label: str) -> None:
    defaults, _expected = DECLARATIONS[label]
    host = _Host()
    reset_widget_state(host, defaults)
    for name, default in defaults.items():
        assert getattr(host, name) == (default() if callable(default) else default), name


@pytest.mark.parametrize("label", sorted(DECLARATIONS))
def test_mutable_defaults_are_fresh_on_every_reset(label: str) -> None:
    defaults, _expected = DECLARATIONS[label]
    mutables = [name for name, default in defaults.items() if callable(default)]
    host = _Host()
    reset_widget_state(host, defaults)
    for name in mutables:
        first = getattr(host, name)
        reset_widget_state(host, defaults)
        assert getattr(host, name) is not first, name + " must get a fresh object per reset"


@pytest.mark.parametrize("label", sorted(DECLARATIONS))
def test_the_mixin_reset_calls_the_shared_helper(label: str) -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    modules = {"data": "ui/panels/data/build.py", "display": "ui/panels/display/build.py",
               "geochemistry": "ui/panels/geochemistry/overlays.py"}
    source = (root / modules[label]).read_text(encoding="utf-8").replace("\r\n", "\n")
    start = source.index("def reset_state")
    end = source.index("\n    def ", start + 1)
    assert "reset_widget_state(self, _WIDGET_DEFAULTS)" in source[start:end]
