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
        self.pca_params = CONFIG.get('pca_params', {}).copy()
        self.show_ellipses = CONFIG.get('show_ellipses', False)
        self.point_size = CONFIG['point_size']
        self.last_group_col = None  # Will be set from data after loading
        self.render_mode = 'UMAP'
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
        self.language = CONFIG.get('default_language', 'zh')
        self.language_labels = CONFIG.get('languages', {'zh': '中文', 'en': 'English'})
        self.language_listeners = []
        
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
        
    def clear_plot_state(self):
        """Reset plot-specific state"""
        self.scatter_collections.clear()
        self.sample_index_map.clear()
        self.legend_to_scatter.clear()
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
