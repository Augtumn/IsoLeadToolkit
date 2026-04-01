"""Helpers for AppState initialization bootstrap."""
from __future__ import annotations

from typing import Any


def sync_overlay_kde_styles(state: Any) -> None:
    """Initialize KDE style defaults and mirror them into overlay line styles."""
    state.kde_style = {
        'alpha': 0.6,
        'levels': 10,
        'linewidth': 1.0,
        'fill': True
    }
    state.marginal_kde_style = {
        'alpha': 0.25,
        'linewidth': 1.0,
        'fill': True
    }
    state.overlay.line_styles.setdefault('kde_curve', {}).update({
        'linewidth': state.kde_style.get('linewidth', 1.0),
        'alpha': state.kde_style.get('alpha', 0.6),
        'fill': state.kde_style.get('fill', True),
        'levels': state.kde_style.get('levels', 10),
    })
    state.overlay.line_styles.setdefault('marginal_kde_curve', {}).update({
        'linewidth': state.marginal_kde_style.get('linewidth', 1.0),
        'alpha': state.marginal_kde_style.get('alpha', 0.25),
        'fill': state.marginal_kde_style.get('fill', True),
    })
    state.overlay._init_equation_styles()


def init_runtime_defaults(state: Any, config: dict[str, Any]) -> None:
    """Initialize runtime defaults for rendering, interaction, and styling."""
    # PCA/RobustPCA Dimension Selection
    state.pca_component_indices = [0, 1]
    state.last_pca_variance = None
    state.last_pca_components = None
    state.current_feature_names = []

    state.standardize_data = True
    state.show_ellipses = config.get('show_ellipses', False)
    state.show_kde = False
    state.show_marginal_kde = True

    state.marginal_kde_top_size = 15.0
    state.marginal_kde_right_size = 15.0
    state.marginal_kde_max_points = 5000
    state.ellipse_confidence = config.get('ellipse_confidence', 0.95)
    state.point_size = config['point_size']
    state.last_group_col = None
    state.render_mode = 'UMAP'
    state.active_subset_indices = None
    state.selected_2d_cols = []
    state.selected_3d_cols = []
    state.selected_ternary_cols = []
    state.ternary_stretch_power = 0.5
    state.ternary_stretch_mode = 'power'
    state.ternary_factors = [1.0, 1.0, 1.0]
    state.ternary_stretch = False
    state.ui_theme = 'Modern Light'
    state.available_groups = []
    state.visible_groups = None
    state.selected_2d_confirmed = False
    state.selected_3d_confirmed = False
    state.selected_ternary_confirmed = False
    state.selection_mode = False
    state.selection_tool = None
    state.draw_selection_ellipse = False
    state.selected_indices = set()
    state.selection_button = None
    state.rectangle_selector = None
    state.sample_coordinates = {}
    state.artist_to_sample = {}
    state.selection_overlay = None
    state.selection_ellipse = None
    state.marginal_axes = None
    state.paleo_label_refreshing = False
    state.overlay_label_refreshing = False
    state.adjust_text_in_progress = False
    state.mixing_groups = {'endmembers': {}, 'mixtures': {}}
    state.mixing_results = []
    state.mixing_calc_cols = []
    state.language = config.get('default_language', 'zh')
    state.language_labels = config.get('languages', {'zh': '中文', 'en': 'English'})
    state.language_listeners = []

    # Legend and color state
    state.current_palette = {}
    state.current_groups = []

    # Dynamic column configuration
    state.group_cols = []
    state.data_cols = []

    # File information
    state.file_path = None
    state.sheet_name = None
    state.recent_files = []

    # GUI components
    state.fig = None
    state.ax = None
    state.scatter_collections = []
    state.sample_index_map = {}
    state.annotation = None
    state.exported_indices = set()
    state.control_panel_button = None
    state.control_panel_ref = None
    state.initial_render_done = False

    # Tooltip configuration
    state.tooltip_columns = ['Lab No.', 'Discovery site', 'Period']
    state.show_tooltip = False

    # Plot style configuration
    state.plot_style_grid = False
    state.color_scheme = 'vibrant'
    state.custom_primary_font = ''
    state.custom_cjk_font = ''

    # Advanced style configuration
    state.plot_font_sizes = {
        'title': 14,
        'label': 12,
        'tick': 10,
        'legend': 10
    }
    state.show_plot_title = False
    state.custom_palettes = {}
    state.custom_shape_sets = {}
    state.v1_value = 0.0
    state.v2_value = 0.0
    state.plot_marker_size = 60
    state.plot_marker_alpha = 0.8
    state.plot_marker_shape = 'o'
    state.group_marker_map = {}

    # Common plot styling
    state.plot_figsize = config.get('figure_size', (13, 9))
    state.plot_dpi = config.get('figure_dpi', 130)
    state.plot_facecolor = '#ffffff'
    state.axes_facecolor = '#ffffff'
    state.grid_color = '#e2e8f0'
    state.grid_linewidth = 0.6
    state.grid_alpha = 0.7
    state.grid_linestyle = '--'
    state.minor_grid = False
    state.minor_grid_color = '#e2e8f0'
    state.minor_grid_linewidth = 0.4
    state.minor_grid_alpha = 0.4
    state.minor_grid_linestyle = ':'
    state.tick_direction = 'out'
    state.tick_length = 4.0
    state.tick_width = 0.8
    state.tick_color = '#1f2937'
    state.minor_ticks = False
    state.minor_tick_length = 2.5
    state.minor_tick_width = 0.6
    state.axis_linewidth = 1.0
    state.axis_line_color = '#1f2937'
    state.show_top_spine = True
    state.show_right_spine = True
    state.scatter_show_edge = True
    state.scatter_edgecolor = '#1e293b'
    state.scatter_edgewidth = 0.4
    state.label_color = '#1f2937'
    state.label_weight = 'normal'
    state.label_pad = 6.0
    state.title_color = '#111827'
    state.title_weight = 'bold'
    state.title_pad = 20.0
    state.adjust_text_force_text = (0.8, 1.0)
    state.adjust_text_force_static = (0.4, 0.6)
    state.adjust_text_expand = (1.08, 1.20)
    state.adjust_text_iter_lim = 120
    state.adjust_text_time_lim = 0.25
    state.saved_themes = {}
    state.last_2d_cols = None