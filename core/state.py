"""
Application State Management
Centralized global state to avoid variable chaos
"""
from .config import CONFIG


class AppState:
    """Centralized application state"""
    def __init__(self):
        self.df_global = None
        self.embedding_cache = {}
        self.algorithm = 'UMAP'  # Default algorithm: always start with UMAP
        self.umap_params = CONFIG['umap_params'].copy()
        self.tsne_params = CONFIG['tsne_params'].copy()
        self.pca_params = CONFIG.get('pca_params', {'n_components': 2, 'random_state': 42}).copy()
        self.robust_pca_params = CONFIG.get('robust_pca_params', {'n_components': 2, 'random_state': 42, 'support_fraction': 0.75}).copy()
        if 'support_fraction' not in self.robust_pca_params:
            self.robust_pca_params['support_fraction'] = 0.75
        
        # V1V2 Parameters
        self.v1v2_params = {
            'a': 0.0,
            'b': 2.0367,
            'c': -6.143,
            'scale': 1.0
        }

        # Geochemistry plot toggles
        self.show_model_curves = True
        self.show_paleoisochrons = True
        self.show_model_age_lines = True
        self.show_equation_overlays = False
        self.equation_overlays = [
            {
                'id': 'eq_206_208',
                'label': 'y=1.0049x+20.259',
                'latex': r"y=1.0049x+20.259",
                'expression': '1.0049*x+20.259',
                'slope': 1.0049,
                'intercept': 20.259,
                'enabled': True,
                'color': '#ef4444',
                'linewidth': 1.0,
                'linestyle': '--',
                'alpha': 0.85
            },
            {
                'id': 'eq_identity',
                'label': 'y=x',
                'latex': r"y=x",
                'expression': 'x',
                'slope': 1.0,
                'intercept': 0.0,
                'enabled': True,
                'color': '#ef4444',
                'linewidth': 1.0,
                'linestyle': '--',
                'alpha': 0.85
            }
        ]
        self.line_styles = {
            'model_curve': {
                'color': None,
                'linewidth': 1.2,
                'linestyle': '-',
                'alpha': 0.8
            },
            'growth_curve': {
                'color': None,
                'linewidth': 1.2,
                'linestyle': ':',
                'alpha': 0.6
            },
            'paleoisochron': {
                'color': '#94a3b8',
                'linewidth': 0.9,
                'linestyle': '--',
                'alpha': 0.85
            },
            'model_age_line': {
                'color': '#cbd5f5',
                'linewidth': 0.7,
                'linestyle': '-',
                'alpha': 0.7
            },
            'isochron': {
                'color': None,
                'linewidth': 1.5,
                'linestyle': '-',
                'alpha': 0.8
            }
        }
        self.paleoisochron_min_age = 0
        self.paleoisochron_max_age = 3000
        self.paleoisochron_step = 1000
        self.paleoisochron_ages = list(
            range(self.paleoisochron_max_age, self.paleoisochron_min_age - 1, -self.paleoisochron_step)
        )
        self.model_curve_models = None  # None means all preset models
            
        # PCA/RobustPCA Dimension Selection
        self.pca_component_indices = [0, 1]  # Default to PC1 and PC2
        self.last_pca_variance = None  # Store explained variance ratio for scree plot
        self.last_pca_components = None  # Store PCA components (loadings)
        self.current_feature_names = []  # Store names of features used in analysis
        
        self.standardize_data = True  # Default to True for better PCA/RobustPCA performance
        self.show_ellipses = CONFIG.get('show_ellipses', False)
        self.show_kde = False  # Global KDE toggle for 2D plots
        self.show_marginal_kde = True  # Marginal KDE for 2D plots
        self.kde_style = {
            'alpha': 0.6,
            'levels': 10,
            'linewidth': 1.0,
            'fill': True
        }
        self.marginal_kde_style = {
            'alpha': 0.25,
            'linewidth': 1.0,
            'fill': True
        }
        self.ellipse_confidence = CONFIG.get('ellipse_confidence', 0.95)
        self.point_size = CONFIG['point_size']
        self.last_group_col = None  # Will be set from data after loading
        self.render_mode = 'UMAP'
        self.active_subset_indices = None  # If set, analysis is restricted to these indices
        self.selected_2d_cols = []
        self.selected_3d_cols = []
        self.selected_ternary_cols = []
        self.ternary_stretch_power = 0.5
        self.ternary_stretch_mode = 'power'  # power | minmax | hybrid
        self.ternary_factors = [1.0, 1.0, 1.0] # Scaling factors for Top, Left, Right
        self.ternary_stretch = False # Whether to apply min-max stretching
        self.ui_theme = 'Modern Light' # Default UI theme
        self.available_groups = []
        self.visible_groups = None
        self.selected_2d_confirmed = False
        self.selected_3d_confirmed = False
        self.selected_ternary_confirmed = False
        self.selection_mode = False # Deprecated in favor of selection_tool, but kept for compatibility if needed
        self.selection_tool = None # None, 'export', 'ellipse'
        self.draw_selection_ellipse = False
        self.selected_indices = set()
        self.selection_button = None
        self.rectangle_selector = None
        self.sample_coordinates = {}
        self.artist_to_sample = {}
        self.selection_overlay = None
        self.selection_ellipse = None  # Store the confidence ellipse for selected points
        self.marginal_axes = None  # (top_ax, right_ax) for marginal KDE
        self.paleoisochron_label_data = []  # Track paleoisochron labels for updates
        self.paleo_label_refreshing = False
        self.mixing_groups = {'endmembers': {}, 'mixtures': {}}
        self.mixing_results = []
        self.mixing_calc_cols = []
        self.language = CONFIG.get('default_language', 'zh')
        self.language_labels = CONFIG.get('languages', {'zh': '中文', 'en': 'English'})
        self.language_listeners = []
        
        # Legend and Color State
        self.current_palette = {}  # Map group name to hex color
        self.current_groups = []   # List of current groups in order
        
        # Dynamic column configuration (populated from data)
        self.group_cols = []  # Available grouping columns from data
        self.data_cols = []   # Data columns for visualization
        
        # File information
        self.file_path = None  # Current data file path
        self.sheet_name = None  # Current sheet name for xlsx
        
        # GUI components
        self.fig = None
        self.ax = None
        self.scatter_collections = []
        self.sample_index_map = {}
        self.annotation = None
        self.legend_to_scatter = {}
        self.exported_indices = set()
        self.control_panel_button = None
        self.control_panel_ref = None
        self.initial_render_done = False
        
        # Tooltip configuration
        self.tooltip_columns = ['Lab No.', 'Discovery site', 'Period']  # Default columns
        self.show_tooltip = False

        # Plot Style Configuration
        self.plot_style_grid = False
        self.color_scheme = 'vibrant'
        self.custom_primary_font = '' # User selected primary font
        self.custom_cjk_font = ''     # User selected CJK font
        
        # Advanced Style Configuration
        self.plot_font_sizes = {
            'title': 14,
            'label': 12,
            'tick': 10,
            'legend': 10
        }
        self.show_plot_title = False
        self.legend_columns = 0  # 0 means auto
        self.plot_marker_size = 60
        self.plot_marker_alpha = 0.8
        # Common plot styling
        self.plot_figsize = CONFIG.get('figure_size', (13, 9))
        self.plot_dpi = CONFIG.get('figure_dpi', 130)
        self.plot_facecolor = '#ffffff'
        self.axes_facecolor = '#ffffff'
        self.grid_color = '#e2e8f0'
        self.grid_linewidth = 0.6
        self.grid_alpha = 0.7
        self.grid_linestyle = '--'
        self.minor_grid = False
        self.minor_grid_color = '#e2e8f0'
        self.minor_grid_linewidth = 0.4
        self.minor_grid_alpha = 0.4
        self.minor_grid_linestyle = ':'
        self.tick_direction = 'out'  # in | out | inout
        self.tick_length = 4.0
        self.tick_width = 0.8
        self.tick_color = '#1f2937'
        self.minor_ticks = False
        self.minor_tick_length = 2.5
        self.minor_tick_width = 0.6
        self.axis_linewidth = 1.0
        self.axis_line_color = '#1f2937'
        self.show_top_spine = True
        self.show_right_spine = True
        self.scatter_edgecolor = '#1e293b'
        self.scatter_edgewidth = 0.4
        self.model_curve_width = 1.2
        self.paleoisochron_width = 0.9
        self.model_age_line_width = 0.7
        self.isochron_line_width = 1.5
        self.label_color = '#1f2937'
        self.label_weight = 'normal'
        self.label_pad = 6.0
        self.title_color = '#111827'
        self.title_weight = 'bold'
        self.title_pad = 20.0
        self.legend_location = 'outside_right'
        self.legend_frame_on = True
        self.legend_frame_alpha = 0.95
        self.legend_frame_facecolor = '#ffffff'
        self.legend_frame_edgecolor = '#cbd5f5'
        self.saved_themes = {} # Dictionary to store user themes
        self.last_2d_cols = None
        
    def clear_plot_state(self):
        """Reset plot-specific state"""
        self.scatter_collections.clear()
        self.sample_index_map.clear()
        self.legend_to_scatter.clear()
        self.group_to_scatter = {}  # Map group name to scatter artist
        self.exported_indices.clear()
        self.annotation = None  # Clear annotation reference
        self.sample_coordinates.clear()
        self.artist_to_sample.clear()
        if self.selection_overlay is not None:
            try:
                self.selection_overlay.remove()
            except Exception:
                pass
        self.selection_overlay = None

    def register_language_listener(self, callback):
        """Register a callback to be invoked when language changes."""
        if callback and callback not in self.language_listeners:
            self.language_listeners.append(callback)

    def notify_language_change(self):
        """Notify registered listeners about language changes."""
        for callback in list(self.language_listeners):
            try:
                callback()
            except Exception:
                pass


# Global state instance
app_state = AppState()

# Global widget references for callbacks
# UMAP parameters
slider_n = None
slider_d = None
slider_r = None
slider_s = None

# t-SNE parameters
slider_p = None  # perplexity
slider_lr = None  # learning_rate

# Common controls
radio_g = None
radio_render_mode = None  # Render mode selector (UMAP/tSNE/2D/3D)
