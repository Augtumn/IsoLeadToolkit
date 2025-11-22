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
        self.point_size = CONFIG['point_size']
        self.last_group_col = None  # Will be set from data after loading
        
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
        
    def clear_plot_state(self):
        """Reset plot-specific state"""
        self.scatter_collections.clear()
        self.sample_index_map.clear()
        self.legend_to_scatter.clear()
        self.exported_indices.clear()
        self.annotation = None  # Clear annotation reference


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
radio_algo = None  # Algorithm selector (UMAP/tSNE)
