"""
Application State Management
Centralized global state to avoid variable chaos
"""
from config import CONFIG


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
            
        # PCA/RobustPCA Dimension Selection
        self.pca_component_indices = [0, 1]  # Default to PC1 and PC2
        self.last_pca_variance = None  # Store explained variance ratio for scree plot
        self.last_pca_components = None  # Store PCA components (loadings)
        self.current_feature_names = []  # Store names of features used in analysis
        
        self.standardize_data = True  # Default to True for better PCA/RobustPCA performance
        self.show_ellipses = CONFIG.get('show_ellipses', False)
        self.ellipse_confidence = CONFIG.get('ellipse_confidence', 0.95)
        self.point_size = CONFIG['point_size']
        self.last_group_col = None  # Will be set from data after loading
        self.render_mode = 'UMAP'
        self.active_subset_indices = None  # If set, analysis is restricted to these indices
        self.selected_2d_cols = []
        self.selected_3d_cols = []
        self.available_groups = []
        self.visible_groups = None
        self.selected_2d_confirmed = False
        self.selected_3d_confirmed = False
        self.selection_mode = False
        self.selected_indices = set()
        self.selection_button = None
        self.rectangle_selector = None
        self.sample_coordinates = {}
        self.artist_to_sample = {}
        self.selection_overlay = None
        self.selection_ellipse = None  # Store the confidence ellipse for selected points
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
