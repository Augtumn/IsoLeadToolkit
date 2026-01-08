"""
Dimensionality Reduction Visualization
Handles UMAP and t-SNE embedding computation and plot rendering
"""
import traceback
import matplotlib
from config import CONFIG
from state import app_state
# Import events module for selection overlay refresh
try:
    from events import refresh_selection_overlay
except ImportError:
    refresh_selection_overlay = None

import umap
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.covariance import MinCovDet
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
import seaborn as sns
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from matplotlib.patches import Ellipse
import numpy as np

# Import V1V2 calculation logic
try:
    from V1V2 import calculate_all_parameters
except ImportError:
    print("[WARN] V1V2 module not found. V1V2 algorithm will not be available.", flush=True)
    calculate_all_parameters = None

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk
import itertools
from style_manager import apply_custom_style

# sns.set_theme()
# Use custom style manager to avoid dependency issues and ensure CJK support

def _apply_current_style():
    """Apply the current plot style and color scheme from app_state."""
    
    # Grid
    show_grid = getattr(app_state, 'plot_style_grid', False)
        
    # Color scheme
    color_scheme = getattr(app_state, 'color_scheme', 'vibrant')
    
    # Custom Fonts
    primary_font = getattr(app_state, 'custom_primary_font', '')
    cjk_font = getattr(app_state, 'custom_cjk_font', '')
    
    # Font Sizes
    font_sizes = getattr(app_state, 'plot_font_sizes', None)
    
    # Apply styles using our custom manager
    try:
        apply_custom_style(show_grid, color_scheme, primary_font, cjk_font, font_sizes)
    except Exception as e:
        print(f"[WARN] Failed to apply styles: {e}", flush=True)
        # Fallback
        apply_custom_style(False, 'vibrant')
    
    # Update figure background if it exists
    # Note: We don't set facecolors here anymore because ax.clear() would reset them.
    # Instead, we rely on _enforce_plot_style() called after clearing.
    pass

def _enforce_plot_style(ax):
    """Enforce style settings on the specific axes instance."""
    if ax is None:
        return

    # Enforce grid
    show_grid = getattr(app_state, 'plot_style_grid', False)
    ax.grid(show_grid)
    
    # Enforce facecolors from current rcParams
    if app_state.fig is not None:
        app_state.fig.patch.set_facecolor(plt.rcParams.get('figure.facecolor', 'white'))
    
    ax.set_facecolor(plt.rcParams.get('axes.facecolor', 'white'))

def show_scree_plot(parent_window=None):
    """Display a scree plot of the explained variance for the last PCA run."""
    if not hasattr(app_state, 'last_pca_variance') or app_state.last_pca_variance is None:
        print("[WARN] No PCA variance data available. Run PCA first.", flush=True)
        return

    variance_ratio = app_state.last_pca_variance
    n_components = len(variance_ratio)
    components = range(1, n_components + 1)
    cumulative_variance = np.cumsum(variance_ratio)

    # Create a new Toplevel window
    window = tk.Toplevel(parent_window)
    window.title("Scree Plot - Explained Variance")
    window.geometry("600x450")
    
    # Create figure using Figure object directly to avoid global pyplot state
    fig = Figure(figsize=(6, 4), dpi=100)
    ax1 = fig.add_subplot(111)
    
    # Bar plot for individual variance
    ax1.bar(components, variance_ratio, alpha=0.6, color='b', label='Individual Variance')
    ax1.set_xlabel('Principal Component')
    ax1.set_ylabel('Explained Variance Ratio', color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.set_xticks(components)
    ax1.set_ylim(0, 1.05)

    # Line plot for cumulative variance
    ax2 = ax1.twinx()
    ax2.plot(components, cumulative_variance, marker='o', color='r', label='Cumulative Variance')
    ax2.set_ylabel('Cumulative Variance Ratio', color='r')
    ax2.tick_params(axis='y', labelcolor='r')
    ax2.set_ylim(0, 1.05)
    
    # Add grid
    ax1.grid(True, axis='x', alpha=0.3)
    ax2.grid(True, axis='y', alpha=0.3)
    
    ax1.set_title('Scree Plot')
    fig.tight_layout()

    # Embed in Tkinter
    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _on_close():
        # No need to call plt.close(fig) since we didn't use plt interface
        window.destroy()
        
    window.protocol("WM_DELETE_WINDOW", _on_close)


def show_pca_loadings(parent_window=None):
    """Display a heatmap of PCA loadings (components)."""
    if not hasattr(app_state, 'last_pca_components') or app_state.last_pca_components is None:
        print("[WARN] No PCA components data available. Run PCA first.", flush=True)
        return

    components = app_state.last_pca_components
    feature_names = app_state.current_feature_names
    
    if not feature_names or len(feature_names) != components.shape[1]:
        print("[WARN] Feature names mismatch or missing.", flush=True)
        feature_names = [f"Feature {i+1}" for i in range(components.shape[1])]

    n_comps = components.shape[0]
    comp_names = [f"PC{i+1}" for i in range(n_comps)]

    # Create a new Toplevel window
    window = tk.Toplevel(parent_window)
    window.title("PCA Loadings")
    window.geometry("800x600")
    
    fig = Figure(figsize=(8, 6), dpi=100)
    ax = fig.add_subplot(111)
    
    # Create heatmap
    # We transpose so features are rows (easier to read if many features) or keep as is?
    # Usually Features x PCs is better for reading if many features.
    # Let's do PCs on Y axis, Features on X axis as standard loadings matrix
    
    im = ax.imshow(components, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
    
    # Add colorbar
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Loading Value')
    
    # Set ticks
    ax.set_xticks(np.arange(len(feature_names)))
    ax.set_yticks(np.arange(len(comp_names)))
    
    ax.set_xticklabels(feature_names, rotation=45, ha="right")
    ax.set_yticklabels(comp_names)
    
    # Loop over data dimensions and create text annotations.
    for i in range(len(comp_names)):
        for j in range(len(feature_names)):
            text = ax.text(j, i, f"{components[i, j]:.2f}",
                           ha="center", va="center", color="k" if abs(components[i, j]) < 0.5 else "w")

    ax.set_title("PCA Loadings (Feature Contribution to Components)")
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def show_embedding_correlation(parent_window=None):
    """Display correlation between original features and embedding dimensions."""
    if not hasattr(app_state, 'last_embedding') or app_state.last_embedding is None:
        print("[WARN] No embedding data available. Run an analysis first.", flush=True)
        return

    embedding = app_state.last_embedding
    # Get original data (scaled or raw? usually raw is better for interpretation)
    X, _ = _get_analysis_data()
    
    if X is None:
        return
        
    cols = app_state.data_cols
    if not cols:
        return

    # Calculate correlation between each feature and the embedding dimensions
    # embedding is N x 2 (usually)
    # X is N x D
    
    n_dims = embedding.shape[1]
    dim_names = [f"Dim {i+1}" for i in range(n_dims)]
    
    correlations = []
    for i in range(n_dims):
        dim_corrs = []
        dim_data = embedding[:, i]
        for j in range(X.shape[1]):
            feat_data = X[:, j]
            # Use Spearman correlation as relationships might be non-linear
            # But Pearson is faster and standard for "linear" correlation heatmaps
            # Let's use Pearson for consistency with the other heatmap, or Spearman?
            # UMAP/t-SNE are non-linear, so Spearman is probably better.
            # However, numpy corrcoef is Pearson.
            # Let's stick to Pearson for simplicity and speed, or use pandas if available.
            
            # Manual Pearson calculation to avoid pandas dependency if possible, 
            # but we used pandas in show_correlation_heatmap.
            # Let's use numpy corrcoef.
            corr = np.corrcoef(dim_data, feat_data)[0, 1]
            if np.isnan(corr): corr = 0
            dim_corrs.append(corr)
        correlations.append(dim_corrs)
    
    correlations = np.array(correlations) # Shape (n_dims, n_features)
    
    # Create window
    window = tk.Toplevel(parent_window)
    window.title(f"Feature Correlation with {getattr(app_state, 'last_embedding_type', 'Embedding')} Axes")
    window.geometry("800x400")
    
    fig = Figure(figsize=(8, 4), dpi=100)
    ax = fig.add_subplot(111)
    
    # Plot heatmap
    # Rows: Dimensions, Cols: Features
    im = ax.imshow(correlations, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
    
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Correlation Coefficient')
    
    ax.set_yticks(np.arange(n_dims))
    ax.set_yticklabels(dim_names)
    
    ax.set_xticks(np.arange(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha="right")
    
    # Annotate
    for i in range(n_dims):
        for j in range(len(cols)):
            text = ax.text(j, i, f"{correlations[i, j]:.2f}",
                           ha="center", va="center", color="k" if abs(correlations[i, j]) < 0.5 else "w")
                           
    ax.set_title(f"Correlation: Features vs {getattr(app_state, 'last_embedding_type', 'Embedding')} Dimensions")
    fig.tight_layout()
    
    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def show_shepard_diagram(parent_window=None):
    """Display a Shepard diagram (Distance Plot) to evaluate embedding quality."""
    if not hasattr(app_state, 'last_embedding') or app_state.last_embedding is None:
        print("[WARN] No embedding data available.", flush=True)
        return

    embedding = app_state.last_embedding
    X, _ = _get_analysis_data()
    
    if X is None:
        return

    # Sampling for performance if N is large
    n_samples = X.shape[0]
    max_samples = 1000 # Limit to 1000 points (approx 500k pairs)
    
    if n_samples > max_samples:
        indices = np.random.choice(n_samples, max_samples, replace=False)
        X_sub = X[indices]
        emb_sub = embedding[indices]
    else:
        X_sub = X
        emb_sub = embedding
        
    from scipy.spatial.distance import pdist
    
    # Calculate pairwise distances
    # Original space (Euclidean)
    # Note: If using UMAP/t-SNE, they might use different metrics, but Euclidean is standard for input
    d_original = pdist(X_sub)
    
    # Embedding space
    d_embedding = pdist(emb_sub)
    
    # Calculate correlation (Spearman is better for rank preservation)
    from scipy.stats import spearmanr
    corr, _ = spearmanr(d_original, d_embedding)
    
    # Create window
    window = tk.Toplevel(parent_window)
    window.title(f"Shepard Diagram ({getattr(app_state, 'last_embedding_type', 'Embedding')})")
    window.geometry("600x600")
    
    fig = Figure(figsize=(6, 6), dpi=100)
    ax = fig.add_subplot(111)
    
    # Scatter plot
    # Downsample pairs for plotting if too many
    if len(d_original) > 5000:
        plot_indices = np.random.choice(len(d_original), 5000, replace=False)
        ax.scatter(d_original[plot_indices], d_embedding[plot_indices], alpha=0.1, s=5, c='k')
    else:
        ax.scatter(d_original, d_embedding, alpha=0.2, s=10, c='k')
        
    # Add diagonal line for reference
    # Since scales might differ, we plot y=x but also set aspect to equal to make units consistent
    # However, if scales are vastly different (e.g. 100 vs 1), equal aspect will hide data.
    # Let's just plot the diagonal across the visible range if we want to show correlation trend,
    # OR if the user specifically asked for "consistent units", we should try to normalize or use equal aspect.
    # Given "Shepard 图的横纵坐标单位不一致，建议把对角线显示出来", the user likely wants to see
    # how far points deviate from the identity line y=x.
    
    # Find the common range to draw the diagonal
    # Use the actual data limits to avoid forcing the axes to expand to a square
    xlims = (0, np.max(d_original))
    ylims = (0, np.max(d_embedding))
    
    # Plot diagonal line y=x
    # We plot it long enough to cover the potential intersection, but we won't let it dictate the view
    diag_max = max(xlims[1], ylims[1])
    ax.plot([0, diag_max], [0, diag_max], 'r--', alpha=0.5, label='x=y')
    
    # Explicitly set the limits to the data range so the plot doesn't zoom out to show the full diagonal line
    ax.set_xlim(left=0, right=xlims[1] * 1.05)
    ax.set_ylim(bottom=0, top=ylims[1] * 1.05)
    
    ax.legend()
        
    ax.set_xlabel("Original Distance")
    ax.set_ylabel("Embedding Distance")
    ax.set_title(f"Shepard Diagram\nSpearman Correlation: {corr:.3f}")
    
    fig.tight_layout()
    
    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def show_correlation_heatmap(parent_window=None):
    """Display a correlation heatmap of the current dataset."""
    X, _ = _get_analysis_data()
    if X is None:
        print("[WARN] No data available for correlation analysis.", flush=True)
        return
        
    cols = app_state.data_cols
    if not cols:
        return

    # Calculate correlation matrix
    # X is numpy array, need to convert to DataFrame for easy corr
    import pandas as pd
    df_corr = pd.DataFrame(X, columns=cols).corr()

    # Create a new Toplevel window
    window = tk.Toplevel(parent_window)
    window.title("Correlation Heatmap")
    window.geometry("700x600")
    
    fig = Figure(figsize=(7, 6), dpi=100)
    ax = fig.add_subplot(111)
    
    # Create heatmap
    im = ax.imshow(df_corr, cmap='coolwarm', vmin=-1, vmax=1)
    
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Correlation Coefficient')
    
    ax.set_xticks(np.arange(len(cols)))
    ax.set_yticks(np.arange(len(cols)))
    
    ax.set_xticklabels(cols, rotation=45, ha="right")
    ax.set_yticklabels(cols)
    
    # Annotate
    for i in range(len(cols)):
        for j in range(len(cols)):
            text = ax.text(j, i, f"{df_corr.iloc[i, j]:.2f}",
                           ha="center", va="center", color="k")

    ax.set_title("Feature Correlation Matrix")
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def _ensure_axes(dimensions=2):
    """Ensure the Matplotlib axis matches the requested dimensionality."""
    try:
        current_name = getattr(app_state.ax, 'name', '') if app_state.ax is not None else ''
        if dimensions == 3:
            if current_name != '3d':
                if app_state.ax is not None:
                    try:
                        app_state.ax.remove()
                    except Exception:
                        pass
                app_state.ax = app_state.fig.add_subplot(111, projection='3d')
        else:
            if current_name == '3d' or app_state.ax is None:
                if app_state.ax is not None and current_name == '3d':
                    try:
                        app_state.ax.remove()
                    except Exception:
                        pass
                app_state.ax = app_state.fig.add_subplot(111)

        # app_state.fig.subplots_adjust(left=0.05, bottom=0.08, right=0.98, top=0.88)
        pass
    except Exception as axis_err:
        print(f"[WARN] Unable to configure axes: {axis_err}", flush=True)


def draw_confidence_ellipse(x, y, ax, n_std=2.4477, facecolor='none', **kwargs):
    """
    Create a plot of the covariance confidence ellipse of *x* and *y*.
    n_std=2.4477 corresponds to a 95% confidence interval for a 2D distribution.
    """
    if x.size < 2 or y.size < 2:
        return

    cov = np.cov(x, y)
    pearson = cov[0, 1]/np.sqrt(cov[0, 0] * cov[1, 1])
    
    ell_radius_x = np.sqrt(1 + pearson)
    ell_radius_y = np.sqrt(1 - pearson)
    
    ellipse = Ellipse((0, 0), width=ell_radius_x * 2, height=ell_radius_y * 2,
                      facecolor=facecolor, **kwargs)

    scale_x = np.sqrt(cov[0, 0]) * n_std
    mean_x = np.mean(x)
    scale_y = np.sqrt(cov[1, 1]) * n_std
    mean_y = np.mean(y)

    transf = (
        matplotlib.transforms.Affine2D()
        .rotate_deg(45)
        .scale(scale_x, scale_y)
        .translate(mean_x, mean_y)
    )

    ellipse.set_transform(transf + ax.transData)
    return ax.add_patch(ellipse)


def _get_analysis_data():
    """Helper to get the data subset for analysis (all or selected)."""
    if app_state.active_subset_indices is not None:
        # Filter by active subset
        indices = sorted(list(app_state.active_subset_indices))
        if not indices:
            return None, None
        X = app_state.df_global.iloc[indices][app_state.data_cols].values
    else:
        # Use full dataset
        X = app_state.df_global[app_state.data_cols].values
        indices = list(range(len(app_state.df_global)))

    # Ensure data is numeric (float)
    try:
        X = X.astype(float)
    except ValueError as e:
        print(f"[ERROR] Data contains non-numeric values: {e}", flush=True)
        return None, None

    # Handle NaNs: Impute missing values instead of dropping rows
    if np.isnan(X).any():
        print("[WARN] Missing values detected in data. Imputing with 0.", flush=True)
        try:
            imputer = SimpleImputer(strategy='constant', fill_value=0)
            X = imputer.fit_transform(X)
        except Exception as e:
            print(f"[ERROR] Imputation failed: {e}. Dropping incomplete rows as fallback.", flush=True)
            mask = ~np.isnan(X).any(axis=1)
            X = X[mask]
            indices = [indices[i] for i in range(len(indices)) if mask[i]]

    return X, indices


def get_robust_pca_embedding(params):
    """Get or compute Robust PCA (via MinCovDet) embedding with caching"""
    try:
        # Note: Robust PCA depends on the data subset, so we include a hash of indices in the key if subset is active
        subset_key = 'full'
        if app_state.active_subset_indices is not None:
            subset_key = hash(tuple(sorted(list(app_state.active_subset_indices))))
            
        key = ('robust_pca', params['n_components'], params['random_state'], params.get('support_fraction', 0.75), subset_key)
        
        if key in app_state.embedding_cache:
            print(f"[DEBUG] Cache HIT for Robust PCA. Key: {key}", flush=True)
            result = app_state.embedding_cache[key]
            if result is not None:
                return result
        
        print(f"[DEBUG] Cache MISS for Robust PCA. Computing with params: {params}", flush=True)
        X, _ = _get_analysis_data()
        
        if X is None or X.shape[0] == 0:
            print(f"[ERROR] No data available for Robust PCA computation", flush=True)
            return None
            
        print(f"[DEBUG] Robust PCA Input Data Shape: {X.shape}", flush=True)
            
        # Standardize features
        scaler = StandardScaler()
        try:
            X_scaled = scaler.fit_transform(X)
            if np.isnan(X_scaled).any():
                print("[WARN] NaNs detected in scaled data (likely constant columns). Replacing with 0.", flush=True)
                X_scaled = np.nan_to_num(X_scaled)
        except Exception:
            X_scaled = X

        # MinCovDet requires n_samples > n_features. 
        # If not met, fallback to standard PCA with a warning.
        if X_scaled.shape[0] <= X_scaled.shape[1]:
            print(f"[WARN] Not enough samples ({X_scaled.shape[0]}) for Robust PCA (needs > {X_scaled.shape[1]} features). Falling back to standard PCA.", flush=True)
            reducer = PCA(
                n_components=params['n_components'],
                random_state=params['random_state']
            )
            embedding = reducer.fit_transform(X_scaled)
        else:
            try:
                # 1. Estimate robust covariance
                # support_fraction=0.75 ensures we use enough data points to be stable but robust
                # Remove n_jobs=-1 to avoid potential multiprocess overhead/errors on small data
                support_fraction = params.get('support_fraction', 0.75)
                mcd = MinCovDet(random_state=params['random_state'], support_fraction=support_fraction)
                try:
                    mcd.fit(X_scaled)
                except Exception:
                    # If fit fails (e.g. singular covariance), try adding minute noise
                    print("[INFO] MinCovDet failed, retrying with regularization...", flush=True)
                    noise = np.random.RandomState(params['random_state']).normal(0, 1e-5, X_scaled.shape)
                    mcd.fit(X_scaled + noise)
                
                # 2. Get robust covariance and location
                robust_cov = mcd.covariance_
                robust_location = mcd.location_
                
                # 3. Center data using robust location
                X_centered = X_scaled - robust_location
                
                # 4. Eigendecomposition of robust covariance
                eigvals, eigvecs = np.linalg.eigh(robust_cov)
                
                # 5. Sort eigenvectors by eigenvalues in descending order
                idx = eigvals.argsort()[::-1]
                eigvecs = eigvecs[:, idx]
                
                # 6. Project data onto top components
                # Note: We project the centered data
                embedding = np.dot(X_centered, eigvecs[:, :params['n_components']])
                
                # Calculate explained variance ratio for Robust PCA
                # Total variance is sum of all eigenvalues
                total_variance = np.sum(eigvals)
                if total_variance > 0:
                    explained_variance_ratio = eigvals[idx][:params['n_components']] / total_variance
                    app_state.last_pca_variance = explained_variance_ratio
                else:
                    app_state.last_pca_variance = None
                
                # Store components (loadings)
                # eigvecs columns are eigenvectors, so we transpose to match sklearn PCA.components_ shape (n_components, n_features)
                app_state.last_pca_components = eigvecs[:, :params['n_components']].T
                app_state.current_feature_names = app_state.data_cols
                    
                print("[INFO] Robust PCA computed successfully (MCD method).", flush=True)
            
            except Exception as mcd_err:
                print(f"[WARN] Robust PCA (MCD) failed: {mcd_err}. Falling back to standard PCA.", flush=True)
                reducer = PCA(
                    n_components=params['n_components'],
                    random_state=params['random_state']
                )
                embedding = reducer.fit_transform(X_scaled)
                app_state.last_pca_variance = reducer.explained_variance_ratio_
                app_state.last_pca_components = reducer.components_
                app_state.current_feature_names = app_state.data_cols

        app_state.embedding_cache[key] = embedding
        app_state.last_embedding = embedding
        app_state.last_embedding_type = 'RobustPCA'
        print(f"[DEBUG] Robust PCA embedding computed: shape {embedding.shape}", flush=True)
        return embedding
        
    except Exception as e:
        print(f"[ERROR] Robust PCA computation failed: {e}", flush=True)
        traceback.print_exc()
        return None


def get_pca_embedding(params):
    """Get or compute PCA embedding with caching"""
    try:
        subset_key = 'full'
        if app_state.active_subset_indices is not None:
            subset_key = hash(tuple(sorted(list(app_state.active_subset_indices))))

        key = ('pca', params['n_components'], params['random_state'], subset_key)
        
        if key in app_state.embedding_cache:
            print(f"[DEBUG] Cache HIT for PCA. Key: {key}", flush=True)
            result = app_state.embedding_cache[key]
            if result is not None:
                return result
        
        print(f"[DEBUG] Cache MISS for PCA. Computing with params: {params}", flush=True)
        X, _ = _get_analysis_data()
        
        if X is None or X.shape[0] == 0:
            print(f"[ERROR] No data available for PCA computation", flush=True)
            return None
            
        print(f"[DEBUG] PCA Input Data Shape: {X.shape}", flush=True)
        
        # Standardize features by removing the mean and scaling to unit variance
        # This is critical for PCA to work correctly on data with different scales
        # Handle constant columns to avoid NaNs
        scaler = StandardScaler()
        try:
            X_scaled = scaler.fit_transform(X)
            # Replace NaNs (from constant columns) with 0
            if np.isnan(X_scaled).any():
                print("[WARN] NaNs detected in scaled data (likely constant columns). Replacing with 0.", flush=True)
                X_scaled = np.nan_to_num(X_scaled)
        except Exception as scale_err:
            print(f"[WARN] Scaling failed: {scale_err}. Using raw data.", flush=True)
            X_scaled = X

        reducer = PCA(
            n_components=params['n_components'],
            random_state=params['random_state']
        )
        
        embedding = reducer.fit_transform(X_scaled)
        
        # Store explained variance for scree plot
        app_state.last_pca_variance = reducer.explained_variance_ratio_
        # Store components (loadings)
        app_state.last_pca_components = reducer.components_
        app_state.current_feature_names = app_state.data_cols
        
        app_state.embedding_cache[key] = embedding
        app_state.last_embedding = embedding
        app_state.last_embedding_type = 'PCA'
        print(f"[DEBUG] PCA embedding computed: shape {embedding.shape}", flush=True)
        return embedding
        
    except Exception as e:
        print(f"[ERROR] PCA computation failed: {e}", flush=True)
        traceback.print_exc()
        return None


def get_umap_embedding(params):
    """Get or compute UMAP embedding with caching"""
    try:
        subset_key = 'full'
        if app_state.active_subset_indices is not None:
            subset_key = hash(tuple(sorted(list(app_state.active_subset_indices))))

        key = ('umap', params['n_neighbors'], params['min_dist'], params['random_state'], subset_key)
        
        if key in app_state.embedding_cache:
            print(f"[DEBUG] Cache HIT for UMAP. Key: {key}", flush=True)
            result = app_state.embedding_cache[key]
            if result is not None:
                return result
        
        print(f"[DEBUG] Cache MISS for UMAP. Computing with params: {params}", flush=True)
        X, _ = _get_analysis_data()
        
        if X is None or X.shape[0] == 0:
            print(f"[ERROR] No data available for UMAP computation", flush=True)
            return None
        
        print(f"[DEBUG] UMAP Input Data Shape: {X.shape}", flush=True)
        
        # Validate parameters
        n_neighbors = min(params['n_neighbors'], X.shape[0] - 1)
        n_neighbors = max(n_neighbors, 2)
        
        reducer = umap.UMAP(
            n_neighbors=n_neighbors,
            min_dist=max(params['min_dist'], 0.0),
            random_state=params['random_state'],
            n_components=params['n_components'],
            transform_seed=params['random_state']
        )
        
        embedding = reducer.fit_transform(X)
        app_state.embedding_cache[key] = embedding
        app_state.last_embedding = embedding
        app_state.last_embedding_type = 'UMAP'
        print(f"[DEBUG] UMAP embedding computed: shape {embedding.shape}", flush=True)
        return embedding
        
    except Exception as e:
        print(f"[ERROR] UMAP computation failed: {e}", flush=True)
        traceback.print_exc()
        return None


def get_tsne_embedding(params):
    """Get or compute t-SNE embedding with caching"""
    try:
        X, _ = _get_analysis_data()
        
        if X is None or X.shape[0] == 0:
            print(f"[ERROR] No data available for t-SNE computation", flush=True)
            return None
        
        # Adjust perplexity based on sample size (must be < n_samples)
        n_samples = X.shape[0]
        perplexity = min(params['perplexity'], (n_samples - 1) // 3)
        perplexity = max(perplexity, 5)  # Minimum perplexity of 5
        
        subset_key = 'full'
        if app_state.active_subset_indices is not None:
            subset_key = hash(tuple(sorted(list(app_state.active_subset_indices))))

        # Use adjusted perplexity in cache key
        key = ('tsne', perplexity, params['learning_rate'], params['random_state'], subset_key)
        
        if key in app_state.embedding_cache:
            print(f"[DEBUG] Cache HIT for t-SNE. Key: {key}", flush=True)
            result = app_state.embedding_cache[key]
            if result is not None:
                return result
        
        print(f"[DEBUG] Cache MISS for t-SNE. Computing with params: {params}, adjusted_perplexity={perplexity}", flush=True)
        
        # Validate learning_rate
        learning_rate = max(params['learning_rate'], 10)
        
        reducer = TSNE(
            n_components=params['n_components'],
            perplexity=perplexity,
            learning_rate=learning_rate,
            random_state=params['random_state'],
            verbose=0,
            n_jobs=-1
        )
        
        embedding = reducer.fit_transform(X)
        app_state.embedding_cache[key] = embedding
        app_state.last_embedding = embedding
        app_state.last_embedding_type = 'tSNE'
        print(f"[DEBUG] t-SNE embedding computed: shape {embedding.shape}", flush=True)
        return embedding
        
    except Exception as e:
        print(f"[ERROR] t-SNE computation failed: {e}", flush=True)
        traceback.print_exc()
        return None


def get_embedding(algorithm, umap_params=None, tsne_params=None, pca_params=None, robust_pca_params=None):
    """Get embedding based on selected algorithm"""
    if algorithm == 'UMAP':
        return get_umap_embedding(umap_params or CONFIG['umap_params'])
    elif algorithm == 'tSNE':
        return get_tsne_embedding(tsne_params or CONFIG['tsne_params'])
    elif algorithm == 'PCA':
        return get_pca_embedding(pca_params or CONFIG.get('pca_params', {'n_components': 2, 'random_state': 42}))
    elif algorithm == 'RobustPCA':
        return get_robust_pca_embedding(robust_pca_params or CONFIG.get('robust_pca_params', {'n_components': 2, 'random_state': 42}))
    else:
        print(f"[ERROR] Unknown algorithm: {algorithm}")
        return None


def plot_embedding(group_col, algorithm, umap_params=None, tsne_params=None, pca_params=None, robust_pca_params=None, size=60):
    """Update plot with specified algorithm and parameters"""
    try:
        print(f"[DEBUG] plot_embedding called: algorithm={algorithm}, group_col={group_col}, size={size}", flush=True)
        
        if app_state.fig is None:
            print("[ERROR] Plot axes not initialized", flush=True)
            return False

        _ensure_axes(dimensions=2)

        if app_state.ax is None:
            print("[ERROR] Failed to configure 2D axes", flush=True)
            return False

        # Apply style before clearing
        _apply_current_style()

        app_state.ax.clear()
        _enforce_plot_style(app_state.ax)
        app_state.clear_plot_state()

        # Reserve space around the axes so the legend and titles are never clipped
        # try:
        #     app_state.fig.subplots_adjust(left=0.05, bottom=0.08, right=0.85, top=0.88)
        # except Exception:
        #     pass

        # Manual styling removed in favor of scienceplots
        # app_state.fig.patch.set_facecolor("#f8fafc")
        # app_state.ax.set_facecolor("#ffffff")
        # app_state.ax.grid(True, color="#e2e8f0", linewidth=0.7, alpha=0.8)
        # app_state.ax.set_axisbelow(True)
        # for spine in app_state.ax.spines.values():
        #     spine.set_color("#cbd5f5")
        #     spine.set_linewidth(1.0)
        
        # Ensure parameters are provided
        if umap_params is None:
            umap_params = CONFIG['umap_params']
        if tsne_params is None:
            tsne_params = CONFIG['tsne_params']
        if pca_params is None:
            pca_params = CONFIG.get('pca_params', {'n_components': 2, 'random_state': 42})
        if robust_pca_params is None:
            robust_pca_params = CONFIG.get('robust_pca_params', {'n_components': 2, 'random_state': 42})
        
        print(f"[DEBUG] Using params - UMAP: {umap_params}, tSNE: {tsne_params}, PCA: {pca_params}, RobustPCA: {robust_pca_params}", flush=True)
        
        # Get embedding based on algorithm - normalize algorithm name
        embedding = None
        actual_algorithm = algorithm.strip().upper() if isinstance(algorithm, str) else str(algorithm)
        if actual_algorithm == 'ROBUSTPCA':
            actual_algorithm = 'RobustPCA' # Keep case for display
        
        print(f"[DEBUG] Actual algorithm (normalized): {actual_algorithm}", flush=True)
        
        if actual_algorithm == 'UMAP':
            print(f"[DEBUG] Computing UMAP embedding", flush=True)
            embedding = get_umap_embedding(umap_params)
        elif actual_algorithm == 'TSNE':
            print(f"[DEBUG] Computing tSNE embedding", flush=True)
            embedding = get_tsne_embedding(tsne_params)
        elif actual_algorithm == 'PCA':
            print(f"[DEBUG] Computing PCA embedding", flush=True)
            embedding = get_pca_embedding(pca_params)
        elif actual_algorithm == 'RobustPCA':
            print(f"[DEBUG] Computing Robust PCA embedding", flush=True)
            embedding = get_robust_pca_embedding(robust_pca_params)
        elif actual_algorithm == 'V1V2':
            print(f"[DEBUG] Computing V1V2 embedding", flush=True)
            # V1V2 requires specific columns: 206Pb/204Pb, 207Pb/204Pb, 208Pb/204Pb
            # We need to find these columns in the dataset
            # Heuristic: Look for columns containing "206", "207", "208"
            
            if calculate_all_parameters is None:
                print("[ERROR] V1V2 module not loaded", flush=True)
                return False
                
            # Get data subset
            X, indices = _get_analysis_data()
            if X is None:
                return False
                
            # We need to map the columns in X to the required isotopes
            # app_state.data_cols contains the column names corresponding to columns in X
            cols = app_state.data_cols
            
            # Exact matching for prescribed headers
            col_206 = "206Pb/204Pb" if "206Pb/204Pb" in cols else None
            col_207 = "207Pb/204Pb" if "207Pb/204Pb" in cols else None
            col_208 = "208Pb/204Pb" if "208Pb/204Pb" in cols else None
            
            if not (col_206 and col_207 and col_208):
                print(f"[ERROR] Could not identify isotope columns in {cols}. Please ensure columns '206Pb/204Pb', '207Pb/204Pb', '208Pb/204Pb' are selected.", flush=True)
                return False
            
            # Extract data
            idx_206 = cols.index(col_206)
            idx_207 = cols.index(col_207)
            idx_208 = cols.index(col_208)
            
            pb206 = X[:, idx_206]
            pb207 = X[:, idx_207]
            pb208 = X[:, idx_208]
            
            try:
                # Get V1V2 parameters from state
                v1v2_params = getattr(app_state, 'v1v2_params', {})
                scale = v1v2_params.get('scale', 1.0)
                a = v1v2_params.get('a', 0.0)
                b = v1v2_params.get('b', 2.0367)
                c = v1v2_params.get('c', -6.143)

                results = calculate_all_parameters(
                    pb206, pb207, pb208, 
                    calculate_ages=False,
                    a=a, b=b, c=c, scale=scale
                )
                v1 = results['V1']
                v2 = results['V2']
                embedding = np.column_stack((v1, v2))
                app_state.last_embedding = embedding
                app_state.last_embedding_type = 'V1V2'
            except Exception as e:
                print(f"[ERROR] V1V2 calculation failed: {e}", flush=True)
                return False
        else:
            print(f"[ERROR] Unknown algorithm: {algorithm}", flush=True)
            return False
            
        if embedding is None:
            print(f"[ERROR] Failed to compute {algorithm} embedding", flush=True)
            return False
        
        # Determine which data subset we are plotting
        if app_state.active_subset_indices is not None:
            indices_to_plot = sorted(list(app_state.active_subset_indices))
            df_source = app_state.df_global.iloc[indices_to_plot].copy()
        else:
            indices_to_plot = list(range(len(app_state.df_global)))
            df_source = app_state.df_global.copy()

        if embedding.shape[0] != len(df_source):
            print(f"[ERROR] Embedding size {embedding.shape[0]} does not match data size {len(df_source)}", flush=True)
            return False
        
        def _reset_plot_dataframe():
            base = df_source
            if group_col not in base.columns:
                return None
            base[group_col] = base[group_col].fillna('Unknown').astype(str)
            try:
                # Use selected components for PCA/RobustPCA if available
                if actual_algorithm in ('PCA', 'RobustPCA') and hasattr(app_state, 'pca_component_indices'):
                    idx_x = app_state.pca_component_indices[0]
                    idx_y = app_state.pca_component_indices[1]
                    
                    # Ensure indices are within bounds
                    n_comps = embedding.shape[1]
                    if idx_x >= n_comps: idx_x = 0
                    if idx_y >= n_comps: idx_y = 1 if n_comps > 1 else 0
                    
                    base['_emb_x'] = embedding[:, idx_x]
                    base['_emb_y'] = embedding[:, idx_y]
                    print(f"[DEBUG] Plotting components {idx_x+1} and {idx_y+1}", flush=True)
                else:
                    base['_emb_x'] = embedding[:, 0]
                    base['_emb_y'] = embedding[:, 1]
            except Exception as emb_error:
                print(f"[ERROR] Unable to align embedding with data: {emb_error}", flush=True)
                return None
            return base

        df_plot = _reset_plot_dataframe()
        if df_plot is None:
            print(f"[ERROR] Unable to prepare plotting data for column: {group_col}", flush=True)
            return False
        if group_col not in df_plot.columns:
            print(f"[ERROR] Column not found: {group_col}", flush=True)
            return False

        all_groups = sorted(df_plot[group_col].unique())
        app_state.available_groups = all_groups

        visible_groups = app_state.visible_groups
        if visible_groups:
            allowed = set(visible_groups)
            mask = df_plot[group_col].isin(allowed)
            if not mask.any():
                print("[INFO] No data matches the selected legend filter; showing all groups instead.", flush=True)
                app_state.visible_groups = None
            else:
                df_plot = df_plot[mask].copy()
                if df_plot.empty:
                    print("[INFO] Filtered 3D data is empty; showing all groups instead.", flush=True)
                    df_plot = _reset_plot_dataframe()
                    if df_plot is None:
                        return False
                    app_state.visible_groups = None
                    app_state.available_groups = sorted(df_plot[group_col].unique())

        unique_cats = sorted(df_plot[group_col].unique())
        print(f"[DEBUG] Unique categories in {group_col}: {unique_cats}", flush=True)
        
        # Logic to preserve colors if possible
        if not hasattr(app_state, 'current_palette'):
            app_state.current_palette = {}
            
        # Generate a default palette for all categories using current style cycle
        prop_cycle = plt.rcParams['axes.prop_cycle']
        cycle_colors = prop_cycle.by_key()['color']
        color_cycle = itertools.cycle(cycle_colors)
        default_palette = [next(color_cycle) for _ in range(len(unique_cats))]
        
        new_palette = {}
        
        for i, cat in enumerate(unique_cats):
            if cat in app_state.current_palette:
                new_palette[cat] = app_state.current_palette[cat]
            else:
                new_palette[cat] = matplotlib.colors.to_hex(default_palette[i])
        
        app_state.current_palette = new_palette
        app_state.current_groups = unique_cats
        
        scatters = []
        for i, cat in enumerate(unique_cats):
            try:
                subset = df_plot[df_plot[group_col] == cat]
                if subset.empty:
                    continue
                indices = subset.index.tolist()
                xs = subset['_emb_x'].to_numpy(dtype=float, copy=False)
                ys = subset['_emb_y'].to_numpy(dtype=float, copy=False)
                
                if len(xs) == 0:
                    continue
                
                # Use marker size/alpha from state if available, else default
                marker_size = getattr(app_state, 'plot_marker_size', size)
                marker_alpha = getattr(app_state, 'plot_marker_alpha', 0.88)
                
                color = app_state.current_palette[cat]
                sc = app_state.ax.scatter(
                    xs, ys, label=cat, color=color, s=marker_size,
                    alpha=marker_alpha, edgecolors="#1e293b", linewidth=0.4, zorder=2,
                    picker=5
                )
                scatters.append(sc)
                app_state.scatter_collections.append(sc)
                app_state.group_to_scatter[cat] = sc
                
                # Note: Group-level ellipses are disabled in favor of selection-based ellipses
                # to avoid clutter with large datasets.
                # if app_state.show_ellipses:
                #     try:
                #         draw_confidence_ellipse(xs, ys, app_state.ax, edgecolor=palette[i], zorder=1)
                #     except Exception as e:
                #         print(f"[WARN] Failed to draw ellipse for group {cat}: {e}", flush=True)

                # Store coordinate-to-index mapping with explicit float conversion
                for j, idx in enumerate(indices):
                    x_val = float(xs[j])
                    y_val = float(ys[j])
                    key = (round(x_val, 2), round(y_val, 2))
                    app_state.sample_index_map[key] = idx
                    app_state.sample_coordinates[idx] = (x_val, y_val)
                    app_state.artist_to_sample[(id(sc), j)] = idx
                    
            except Exception as e:
                print(f"[WARN] Error plotting category {cat}: {e}", flush=True)
                continue
        
        if not scatters:
            print("[ERROR] No data points plotted", flush=True)
            return False
        
        print(f"[INFO] Plot rendered: {len(scatters)} groups, {len(app_state.sample_index_map)} points", flush=True)
        
        # Create legend
        try:
            # Only show matplotlib legend if item count is reasonable
            if len(unique_cats) <= 30:
                ncol = app_state.legend_columns if getattr(app_state, 'legend_columns', 0) > 0 else (2 if len(unique_cats) > 15 else 1)
                legend = app_state.ax.legend(
                    title=group_col, bbox_to_anchor=(1.01, 1), loc='upper left',
                    frameon=True, fancybox=True,
                    ncol=ncol
                )

                try:
                    legend.set_bbox_to_anchor((1.01, 1), transform=app_state.ax.transAxes)
                except Exception:
                    pass

                frame = legend.get_frame()
                frame.set_facecolor("#ffffff")
                frame.set_edgecolor("#cbd5f5")
                frame.set_alpha(0.95)
                
                for leg_patch, sc in zip(legend.get_patches(), scatters):
                    app_state.legend_to_scatter[leg_patch] = sc
            else:
                print("[INFO] Too many categories for standard legend. Use Control Panel legend.", flush=True)
        except Exception as e:
            print(f"[WARN] Legend creation error: {e}", flush=True)
        
        # Build title with algorithm info
        subset_info = " (Subset)" if app_state.active_subset_indices is not None else ""
        
        if actual_algorithm == 'UMAP':
            title = f'UMAP{subset_info} (n_neighbors={umap_params["n_neighbors"]}, min_dist={umap_params["min_dist"]})\nColored by {group_col}'
        elif actual_algorithm == 'TSNE':
            title = f't-SNE{subset_info} (perplexity={tsne_params["perplexity"]}, lr={tsne_params["learning_rate"]})\nColored by {group_col}'
        elif actual_algorithm == 'PCA':
            title = f'PCA{subset_info} (n_components={pca_params["n_components"]})\nColored by {group_col}'
        elif actual_algorithm == 'RobustPCA':
            title = f'Robust PCA{subset_info} (n_components={robust_pca_params["n_components"]})\nColored by {group_col}'
        elif actual_algorithm == 'V1V2':
            title = f'V1-V2 Diagram{subset_info}\nColored by {group_col}'
        else:
            title = f'{actual_algorithm}{subset_info}\nColored by {group_col}'
        
        # Smart Title Font Logic
        # If title contains CJK characters, prioritize the CJK font to avoid mojibake
        title_font_dict = {}
        
        has_cjk = any('\u4e00' <= char <= '\u9fff' for char in title)
        if has_cjk:
            cjk_font = getattr(app_state, 'custom_cjk_font', '')
            if cjk_font:
                title_font_dict['fontname'] = cjk_font
            else:
                # Try to find a preferred CJK font from config that is installed
                # This is a best-effort fallback if user hasn't selected one
                try:
                    available = {f.name for f in font_manager.fontManager.ttflist}
                    for f in CONFIG.get('preferred_plot_fonts', []):
                        if f in available:
                            title_font_dict['fontname'] = f
                            break
                except Exception:
                    pass

        app_state.ax.set_title(title, pad=20, **title_font_dict)
        
        # Set axis labels
        if actual_algorithm == 'V1V2':
            app_state.ax.set_xlabel("V1")
            app_state.ax.set_ylabel("V2")
        elif actual_algorithm in ('PCA', 'RobustPCA') and hasattr(app_state, 'pca_component_indices'):
            idx_x = app_state.pca_component_indices[0] + 1
            idx_y = app_state.pca_component_indices[1] + 1
            app_state.ax.set_xlabel(f"PC{idx_x}")
            app_state.ax.set_ylabel(f"PC{idx_y}")
        else:
            app_state.ax.set_xlabel(f"{actual_algorithm} Dimension 1")
            app_state.ax.set_ylabel(f"{actual_algorithm} Dimension 2")
        
        app_state.ax.tick_params()
        
        # Adjust layout to prevent overlap
        try:
            # app_state.fig.tight_layout()
            # Re-adjust margins after tight_layout to ensure legend space
            # app_state.fig.subplots_adjust(left=0.05, bottom=0.08, right=0.85, top=0.88)
            pass
        except Exception:
            pass
        
        # Initialize annotation (always recreate after ax.clear())
        app_state.annotation = app_state.ax.annotate(
            "", xy=(0, 0), xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#cbd5e1", alpha=0.95),
            arrowprops=dict(arrowstyle="->", color="#475569"),
            zorder=15
        )
        app_state.annotation.set_visible(False)
        try:
            if app_state.annotation.arrow_patch is not None:
                app_state.annotation.arrow_patch.set_zorder(14)
        except Exception:
            pass
        
        # Restore selection overlay if available
        if refresh_selection_overlay:
            try:
                refresh_selection_overlay()
            except Exception as e:
                print(f"[WARN] Failed to restore selection overlay: {e}", flush=True)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Plot update failed: {e}")
        traceback.print_exc()
        return False


# Keep backward compatibility
def plot_umap(group_col, params, size):
    """Deprecated: Use plot_embedding instead"""
    return plot_embedding(group_col, 'UMAP', umap_params=params, size=size)


def plot_2d_data(group_col, data_columns, size=60):
    """Render a 2D scatter plot using selected raw measurement columns."""
    try:
        if app_state.fig is None:
            print("[ERROR] Plot figure not initialized", flush=True)
            return False

        if not data_columns or len(data_columns) != 2:
            print("[ERROR] Exactly two data columns are required for a 2D scatter plot", flush=True)
            return False

        if app_state.df_global is None or len(app_state.df_global) == 0:
            print("[WARN] No data available for plotting", flush=True)
            return False

        missing = [col for col in data_columns if col not in app_state.df_global.columns]
        if missing:
            print(f"[ERROR] Missing columns for 2D plot: {missing}", flush=True)
            return False

        _ensure_axes(dimensions=2)

        if app_state.ax is None:
            print("[ERROR] Failed to configure 2D axes", flush=True)
            return False

        # Determine which data subset we are plotting
        if app_state.active_subset_indices is not None:
            indices_to_plot = sorted(list(app_state.active_subset_indices))
            df_plot = app_state.df_global.iloc[indices_to_plot].dropna(subset=data_columns).copy()
        else:
            df_plot = app_state.df_global.dropna(subset=data_columns).copy()

        if df_plot.empty:
            print("[WARN] No complete rows available for the selected 2D columns", flush=True)
            return False

        if group_col not in df_plot.columns:
            print(f"[ERROR] Column not found: {group_col}", flush=True)
            return False

        df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)

        all_groups = sorted(df_plot[group_col].unique())
        app_state.available_groups = all_groups

        visible_groups = app_state.visible_groups
        if visible_groups:
            allowed = set(visible_groups)
            mask = df_plot[group_col].isin(allowed)
            if not mask.any():
                print("[INFO] No 2D data matches the selected legend filter; reverting to all groups.", flush=True)
                app_state.visible_groups = None
            else:
                df_plot = df_plot[mask].copy()
                if df_plot.empty:
                    print("[INFO] Filtered 2D data is empty; reverting to all groups.", flush=True)
                    df_plot = app_state.df_global.dropna(subset=data_columns).copy()
                    df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)
                    app_state.visible_groups = None
                    all_groups = sorted(df_plot[group_col].unique())
                    app_state.available_groups = all_groups

        # Apply style before clearing
        _apply_current_style()

        app_state.ax.clear()
        _enforce_plot_style(app_state.ax)
        app_state.clear_plot_state()

        try:
            # app_state.fig.subplots_adjust(left=0.05, bottom=0.08, right=0.85, top=0.88)
            pass
        except Exception:
            pass

        # Manual styling removed in favor of scienceplots
        # app_state.fig.patch.set_facecolor("#f8fafc")
        # app_state.ax.set_facecolor("#ffffff")
        # app_state.ax.grid(True, color="#e2e8f0", linewidth=0.7, alpha=0.8)
        # app_state.ax.set_axisbelow(True)
        # for spine in app_state.ax.spines.values():
        #     spine.set_color("#cbd5f5")
        #     spine.set_linewidth(1.0)

        unique_cats = sorted(df_plot[group_col].unique())
        
        # Logic to preserve colors if possible
        if not hasattr(app_state, 'current_palette'):
            app_state.current_palette = {}
            
        # Generate a default palette for all categories using current style cycle
        prop_cycle = plt.rcParams['axes.prop_cycle']
        cycle_colors = prop_cycle.by_key()['color']
        color_cycle = itertools.cycle(cycle_colors)
        default_palette = [next(color_cycle) for _ in range(len(unique_cats))]
        
        new_palette = {}
        
        for i, cat in enumerate(unique_cats):
            if cat in app_state.current_palette:
                new_palette[cat] = app_state.current_palette[cat]
            else:
                new_palette[cat] = matplotlib.colors.to_hex(default_palette[i])
        
        app_state.current_palette = new_palette
        app_state.current_groups = unique_cats

        scatters = []

        for i, cat in enumerate(unique_cats):
            subset = df_plot[df_plot[group_col] == cat]
            if subset.empty:
                continue

            xs = subset[data_columns[0]].astype(float).values
            ys = subset[data_columns[1]].astype(float).values
            indices = subset.index.tolist()
            
            color = app_state.current_palette[cat]

            sc = app_state.ax.scatter(
                xs,
                ys,
                label=cat,
                color=color,
                s=size,
                alpha=0.88,
                edgecolors="#1e293b",
                linewidth=0.4,
                zorder=2
            )
            app_state.scatter_collections.append(sc)
            scatters.append(sc)
            app_state.group_to_scatter[cat] = sc

            # Note: Group-level ellipses are disabled in favor of selection-based ellipses
            # if app_state.show_ellipses:
            #     try:
            #         draw_confidence_ellipse(xs, ys, app_state.ax, edgecolor=palette[i], zorder=1)
            #     except Exception as e:
            #         print(f"[WARN] Failed to draw ellipse for group {cat}: {e}", flush=True)

            for j, idx in enumerate(indices):
                key = (round(float(xs[j]), 3), round(float(ys[j]), 3))
                app_state.sample_index_map[key] = idx
                app_state.sample_coordinates[idx] = (float(xs[j]), float(ys[j]))
                app_state.artist_to_sample[(id(sc), j)] = idx

        if not app_state.scatter_collections:
            print("[ERROR] No points were plotted in 2D", flush=True)
            return False

        try:
            if len(unique_cats) <= 30:
                ncol = app_state.legend_columns if getattr(app_state, 'legend_columns', 0) > 0 else (2 if len(unique_cats) > 15 else 1)
                legend = app_state.ax.legend(
                    title=group_col,
                    bbox_to_anchor=(1.01, 1),
                    loc='upper left',
                    frameon=True,
                    fancybox=True,
                    ncol=ncol
                )
                legend.set_bbox_to_anchor((1.01, 1), transform=app_state.ax.transAxes)
                frame = legend.get_frame()
                frame.set_facecolor("#ffffff")
                frame.set_edgecolor("#cbd5f5")
                frame.set_alpha(0.95)
                
                for leg_patch, sc in zip(legend.get_patches(), scatters):
                    app_state.legend_to_scatter[leg_patch] = sc
            else:
                print("[INFO] Too many categories for standard legend. Use Control Panel legend.", flush=True)
        except Exception as legend_err:
            print(f"[WARN] 2D legend creation error: {legend_err}", flush=True)

        subset_info = " (Subset)" if app_state.active_subset_indices is not None else ""
        title = (
            f"2D Scatter Plot{subset_info} ({data_columns[0]} vs {data_columns[1]})\n"
            f"Colored by {group_col}"
        )
        app_state.ax.set_title(title, pad=20)
        app_state.ax.set_xlabel(data_columns[0])
        app_state.ax.set_ylabel(data_columns[1])
        app_state.ax.tick_params()
        
        # Adjust layout to prevent overlap
        try:
            # app_state.fig.tight_layout()
            # app_state.fig.subplots_adjust(left=0.05, bottom=0.08, right=0.85, top=0.88)
            pass
        except Exception:
            pass


        app_state.annotation = app_state.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#cbd5e1", alpha=0.95),
            arrowprops=dict(arrowstyle="->", color="#475569"),
            zorder=15
        )
        app_state.annotation.set_visible(False)
        try:
            if app_state.annotation.arrow_patch is not None:
                app_state.annotation.arrow_patch.set_zorder(14)
        except Exception:
            pass

        return True

    except Exception as err:
        print(f"[ERROR] 2D plot failed: {err}", flush=True)
        traceback.print_exc()
        return False


def plot_3d_data(group_col, data_columns, size=60):
    """Render a 3D scatter plot using selected raw measurement columns."""
    try:
        if app_state.fig is None:
            print("[ERROR] Plot figure not initialized", flush=True)
            return False

        if not data_columns or len(data_columns) != 3:
            print("[ERROR] Exactly three data columns are required for a 3D scatter plot", flush=True)
            return False

        if app_state.df_global is None or len(app_state.df_global) == 0:
            print("[WARN] No data available for plotting", flush=True)
            return False

        missing = [col for col in data_columns if col not in app_state.df_global.columns]
        if missing:
            print(f"[ERROR] Missing columns for 3D plot: {missing}", flush=True)
            return False

        _ensure_axes(dimensions=3)

        if app_state.ax is None:
            print("[ERROR] Failed to configure 3D axes", flush=True)
            return False

        # Determine which data subset we are plotting
        if app_state.active_subset_indices is not None:
            indices_to_plot = sorted(list(app_state.active_subset_indices))
            df_plot = app_state.df_global.iloc[indices_to_plot].dropna(subset=data_columns).copy()
        else:
            df_plot = app_state.df_global.dropna(subset=data_columns).copy()

        if df_plot.empty:
            print("[WARN] No complete rows available for the selected 3D columns", flush=True)
            return False

        if group_col not in df_plot.columns:
            print(f"[ERROR] Column not found: {group_col}", flush=True)
            return False

        df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)

        # Apply style before clearing
        _apply_current_style()

        app_state.ax.clear()
        _enforce_plot_style(app_state.ax)
        app_state.clear_plot_state()

        # Manual styling removed in favor of scienceplots
        # app_state.fig.patch.set_facecolor("#f8fafc")
        # app_state.ax.set_facecolor("#ffffff")
        # app_state.ax.grid(True, color="#e2e8f0", linewidth=0.7, alpha=0.6)

        unique_cats = sorted(df_plot[group_col].unique())
        
        # Generate a default palette for all categories using current style cycle
        prop_cycle = plt.rcParams['axes.prop_cycle']
        cycle_colors = prop_cycle.by_key()['color']
        color_cycle = itertools.cycle(cycle_colors)
        palette = [next(color_cycle) for _ in range(len(unique_cats))]
        
        # Store palette for UI
        app_state.current_groups = unique_cats
        app_state.current_palette = {cat: matplotlib.colors.to_hex(palette[i]) for i, cat in enumerate(unique_cats)}

        for i, cat in enumerate(unique_cats):
            subset = df_plot[df_plot[group_col] == cat]
            if subset.empty:
                continue

            xs = subset[data_columns[0]].astype(float).values
            ys = subset[data_columns[1]].astype(float).values
            zs = subset[data_columns[2]].astype(float).values

            sc = app_state.ax.scatter(
                xs,
                ys,
                zs,
                label=cat,
                color=palette[i],
                s=size,
                alpha=0.85,
                edgecolors='#1e293b',
                linewidth=0.3,
                zorder=2
            )
            app_state.scatter_collections.append(sc)

        if not app_state.scatter_collections:
            print("[ERROR] No points were plotted in 3D", flush=True)
            return False

        try:
            if len(unique_cats) <= 30:
                ncol = app_state.legend_columns if getattr(app_state, 'legend_columns', 0) > 0 else (2 if len(unique_cats) > 15 else 1)
                legend = app_state.ax.legend(
                    title=group_col,
                    bbox_to_anchor=(1.01, 1),
                    loc='upper left',
                    frameon=True,
                    fancybox=True,
                    ncol=ncol
                )
                legend.set_bbox_to_anchor((1.01, 1), transform=app_state.ax.transAxes)
                frame = legend.get_frame()
                frame.set_facecolor("#ffffff")
                frame.set_edgecolor("#cbd5f5")
                frame.set_alpha(0.95)
            else:
                print("[INFO] Too many categories for standard legend. Use Control Panel legend.", flush=True)
        except Exception as legend_err:
            print(f"[WARN] 3D legend creation error: {legend_err}", flush=True)

        subset_info = " (Subset)" if app_state.active_subset_indices is not None else ""
        title = (
            f"3D Scatter Plot{subset_info} ({data_columns[0]}, {data_columns[1]}, {data_columns[2]})\n"
            f"Colored by {group_col}"
        )
        app_state.ax.set_title(title, pad=20)
        app_state.ax.set_xlabel(data_columns[0])
        app_state.ax.set_ylabel(data_columns[1])
        app_state.ax.set_zlabel(data_columns[2])
        
        # Adjust layout to prevent overlap
        try:
            # app_state.fig.tight_layout()
            # app_state.fig.subplots_adjust(left=0.05, bottom=0.08, right=0.85, top=0.88)
            pass
        except Exception:
            pass

        # Disable 2D annotations for 3D renderings
        app_state.annotation = None
        return True

    except Exception as err:
        print(f"[ERROR] 3D plot failed: {err}", flush=True)
        traceback.print_exc()
        return False
