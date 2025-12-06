"""
Dimensionality Reduction Visualization
Handles UMAP and t-SNE embedding computation and plot rendering
"""
import traceback
import matplotlib
from config import CONFIG
from state import app_state
import umap
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
import seaborn as sns
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from matplotlib.patches import Ellipse
import numpy as np

sns.set_theme()


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

        app_state.fig.subplots_adjust(left=0.08, bottom=0.12, right=0.78, top=0.88)
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


def get_pca_embedding(params):
    """Get or compute PCA embedding with caching"""
    try:
        key = ('pca', params['n_components'], params['random_state'])
        
        if key in app_state.embedding_cache:
            print(f"[INFO] Using cached PCA embedding", flush=True)
            result = app_state.embedding_cache[key]
            if result is not None:
                return result
        
        print(f"[INFO] Computing PCA with params: {params}", flush=True)
        X = app_state.df_global[app_state.data_cols].values
        
        if X.shape[0] == 0:
            print(f"[ERROR] No data available for PCA computation", flush=True)
            return None
        
        reducer = PCA(
            n_components=params['n_components'],
            random_state=params['random_state']
        )
        
        embedding = reducer.fit_transform(X)
        app_state.embedding_cache[key] = embedding
        print(f"[INFO] PCA embedding computed: shape {embedding.shape}", flush=True)
        return embedding
        
    except Exception as e:
        print(f"[ERROR] PCA computation failed: {e}", flush=True)
        traceback.print_exc()
        return None


def get_umap_embedding(params):
    """Get or compute UMAP embedding with caching"""
    try:
        key = ('umap', params['n_neighbors'], params['min_dist'], params['random_state'])
        
        if key in app_state.embedding_cache:
            print(f"[INFO] Using cached UMAP embedding", flush=True)
            result = app_state.embedding_cache[key]
            if result is not None:
                return result
        
        print(f"[INFO] Computing UMAP with params: {params}", flush=True)
        X = app_state.df_global[app_state.data_cols].values
        
        if X.shape[0] == 0:
            print(f"[ERROR] No data available for UMAP computation", flush=True)
            return None
        
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
        print(f"[INFO] UMAP embedding computed: shape {embedding.shape}", flush=True)
        return embedding
        
    except Exception as e:
        print(f"[ERROR] UMAP computation failed: {e}", flush=True)
        traceback.print_exc()
        return None


def get_tsne_embedding(params):
    """Get or compute t-SNE embedding with caching"""
    try:
        X = app_state.df_global[app_state.data_cols].values
        
        if X.shape[0] == 0:
            print(f"[ERROR] No data available for t-SNE computation", flush=True)
            return None
        
        # Adjust perplexity based on sample size (must be < n_samples)
        n_samples = X.shape[0]
        perplexity = min(params['perplexity'], (n_samples - 1) // 3)
        perplexity = max(perplexity, 5)  # Minimum perplexity of 5
        
        # Use adjusted perplexity in cache key
        key = ('tsne', perplexity, params['learning_rate'], params['random_state'])
        
        if key in app_state.embedding_cache:
            print(f"[INFO] Using cached t-SNE embedding", flush=True)
            result = app_state.embedding_cache[key]
            if result is not None:
                return result
        
        print(f"[INFO] Computing t-SNE with perplexity={perplexity}, learning_rate={params['learning_rate']}", flush=True)
        
        # Validate learning_rate
        learning_rate = max(params['learning_rate'], 10)
        
        reducer = TSNE(
            n_components=params['n_components'],
            perplexity=perplexity,
            learning_rate=learning_rate,
            random_state=params['random_state'],
            verbose=0
        )
        
        embedding = reducer.fit_transform(X)
        app_state.embedding_cache[key] = embedding
        print(f"[INFO] t-SNE embedding computed: shape {embedding.shape}", flush=True)
        return embedding
        
    except Exception as e:
        print(f"[ERROR] t-SNE computation failed: {e}", flush=True)
        traceback.print_exc()
        return None


def get_embedding(algorithm, umap_params=None, tsne_params=None, pca_params=None):
    """Get embedding based on selected algorithm"""
    if algorithm == 'UMAP':
        return get_umap_embedding(umap_params or CONFIG['umap_params'])
    elif algorithm == 'tSNE':
        return get_tsne_embedding(tsne_params or CONFIG['tsne_params'])
    elif algorithm == 'PCA':
        return get_pca_embedding(pca_params or CONFIG.get('pca_params', {'n_components': 2, 'random_state': 42}))
    else:
        print(f"[ERROR] Unknown algorithm: {algorithm}")
        return None


def plot_embedding(group_col, algorithm, umap_params=None, tsne_params=None, pca_params=None, size=60):
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

        app_state.ax.clear()
        app_state.clear_plot_state()

        # Reserve space around the axes so the legend and titles are never clipped
        try:
            app_state.fig.subplots_adjust(left=0.08, bottom=0.12, right=0.78, top=0.88)
        except Exception:
            pass

        app_state.fig.patch.set_facecolor("#f8fafc")
        app_state.ax.set_facecolor("#ffffff")
        app_state.ax.grid(True, color="#e2e8f0", linewidth=0.7, alpha=0.8)
        app_state.ax.set_axisbelow(True)
        for spine in app_state.ax.spines.values():
            spine.set_color("#cbd5f5")
            spine.set_linewidth(1.0)
        
        # Ensure parameters are provided
        if umap_params is None:
            umap_params = CONFIG['umap_params']
        if tsne_params is None:
            tsne_params = CONFIG['tsne_params']
        if pca_params is None:
            pca_params = CONFIG.get('pca_params', {'n_components': 2, 'random_state': 42})
        
        print(f"[DEBUG] Using params - UMAP: {umap_params}, tSNE: {tsne_params}, PCA: {pca_params}", flush=True)
        
        # Get embedding based on algorithm - normalize algorithm name
        embedding = None
        actual_algorithm = algorithm.strip().upper() if isinstance(algorithm, str) else str(algorithm)
        
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
        else:
            print(f"[ERROR] Unknown algorithm: {algorithm}", flush=True)
            return False
            
        if embedding is None:
            print(f"[ERROR] Failed to compute {algorithm} embedding", flush=True)
            return False
        
        if app_state.df_global is None or len(app_state.df_global) == 0:
            print("[ERROR] No data to plot", flush=True)
            return False
        
        if embedding.shape[0] != len(app_state.df_global):
            print(f"[ERROR] Embedding size {embedding.shape[0]} does not match data size {len(app_state.df_global)}", flush=True)
            return False
        
        def _reset_plot_dataframe():
            base = app_state.df_global.copy()
            if group_col not in base.columns:
                return None
            base[group_col] = base[group_col].fillna('Unknown').astype(str)
            try:
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
        palette = sns.color_palette("tab20", len(unique_cats))
        
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
                
                sc = app_state.ax.scatter(
                    xs, ys, label=cat, color=palette[i], s=size,
                    alpha=0.88, edgecolors="#1e293b", linewidth=0.4, zorder=2
                )
                scatters.append(sc)
                app_state.scatter_collections.append(sc)
                
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
            legend = app_state.ax.legend(
                title=group_col, bbox_to_anchor=(1.02, 1), loc='upper left',
                fontsize=9, title_fontsize=10, frameon=True, fancybox=True
            )

            try:
                legend.set_bbox_to_anchor((1.02, 1), transform=app_state.ax.transAxes)
            except Exception:
                pass

            frame = legend.get_frame()
            frame.set_facecolor("#ffffff")
            frame.set_edgecolor("#cbd5f5")
            frame.set_alpha(0.95)
            
            for leg_patch, sc in zip(legend.get_patches(), scatters):
                app_state.legend_to_scatter[leg_patch] = sc
        except Exception as e:
            print(f"[WARN] Legend creation error: {e}", flush=True)
        
        # Build title with algorithm info
        if actual_algorithm == 'UMAP':
            title = f'UMAP (n_neighbors={umap_params["n_neighbors"]}, min_dist={umap_params["min_dist"]})\nColored by {group_col}'
        elif actual_algorithm == 'TSNE':
            title = f't-SNE (perplexity={tsne_params["perplexity"]}, lr={tsne_params["learning_rate"]})\nColored by {group_col}'
        elif actual_algorithm == 'PCA':
            title = f'PCA (n_components={pca_params["n_components"]})\nColored by {group_col}'
        else:
            title = f'{actual_algorithm}\nColored by {group_col}'
        
        app_state.ax.set_title(title, fontsize=13, color="#1f2937", pad=26)
        app_state.ax.set_xlabel('Dimension 1', color="#334155", fontsize=11)
        app_state.ax.set_ylabel('Dimension 2', color="#334155", fontsize=11)
        app_state.ax.tick_params(colors="#475569", labelsize=9)
        
        # Initialize annotation (always recreate after ax.clear())
        app_state.annotation = app_state.ax.annotate(
            "", xy=(0, 0), xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="yellow", alpha=0.8),
            arrowprops=dict(arrowstyle="->"),
            zorder=15
        )
        app_state.annotation.set_visible(False)
        try:
            if app_state.annotation.arrow_patch is not None:
                app_state.annotation.arrow_patch.set_zorder(14)
        except Exception:
            pass
        
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

        app_state.ax.clear()
        app_state.clear_plot_state()

        try:
            app_state.fig.subplots_adjust(left=0.08, bottom=0.12, right=0.78, top=0.88)
        except Exception:
            pass

        app_state.fig.patch.set_facecolor("#f8fafc")
        app_state.ax.set_facecolor("#ffffff")
        app_state.ax.grid(True, color="#e2e8f0", linewidth=0.7, alpha=0.8)
        app_state.ax.set_axisbelow(True)
        for spine in app_state.ax.spines.values():
            spine.set_color("#cbd5f5")
            spine.set_linewidth(1.0)

        unique_cats = sorted(df_plot[group_col].unique())
        palette = sns.color_palette("tab20", len(unique_cats))

        scatters = []

        for i, cat in enumerate(unique_cats):
            subset = df_plot[df_plot[group_col] == cat]
            if subset.empty:
                continue

            xs = subset[data_columns[0]].astype(float).values
            ys = subset[data_columns[1]].astype(float).values
            indices = subset.index.tolist()

            sc = app_state.ax.scatter(
                xs,
                ys,
                label=cat,
                color=palette[i],
                s=size,
                alpha=0.88,
                edgecolors="#1e293b",
                linewidth=0.4,
                zorder=2
            )
            app_state.scatter_collections.append(sc)
            scatters.append(sc)

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
            legend = app_state.ax.legend(
                title=group_col,
                bbox_to_anchor=(1.02, 1),
                loc='upper left',
                fontsize=9,
                title_fontsize=10,
                frameon=True,
                fancybox=True
            )
            legend.set_bbox_to_anchor((1.02, 1), transform=app_state.ax.transAxes)
            frame = legend.get_frame()
            frame.set_facecolor("#ffffff")
            frame.set_edgecolor("#cbd5f5")
            frame.set_alpha(0.95)
        except Exception as legend_err:
            print(f"[WARN] 2D legend creation error: {legend_err}", flush=True)
        else:
            try:
                for leg_patch, sc in zip(legend.get_patches(), scatters):
                    app_state.legend_to_scatter[leg_patch] = sc
            except Exception:
                pass

        title = (
            f"2D Scatter Plot ({data_columns[0]} vs {data_columns[1]})\n"
            f"Colored by {group_col}"
        )
        app_state.ax.set_title(title, fontsize=13, color="#1f2937", pad=26)
        app_state.ax.set_xlabel(data_columns[0], color="#334155", fontsize=11)
        app_state.ax.set_ylabel(data_columns[1], color="#334155", fontsize=11)
        app_state.ax.tick_params(colors="#475569", labelsize=9)

        app_state.annotation = app_state.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="yellow", alpha=0.8),
            arrowprops=dict(arrowstyle="->"),
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

        df_plot = app_state.df_global.dropna(subset=data_columns).copy()
        if df_plot.empty:
            print("[WARN] No complete rows available for the selected 3D columns", flush=True)
            return False

        if group_col not in df_plot.columns:
            print(f"[ERROR] Column not found: {group_col}", flush=True)
            return False

        df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)

        app_state.ax.clear()
        app_state.clear_plot_state()

        app_state.fig.patch.set_facecolor("#f8fafc")
        app_state.ax.set_facecolor("#ffffff")
        app_state.ax.grid(True, color="#e2e8f0", linewidth=0.7, alpha=0.6)

        unique_cats = sorted(df_plot[group_col].unique())
        palette = sns.color_palette("tab20", len(unique_cats))

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
            legend = app_state.ax.legend(
                title=group_col,
                bbox_to_anchor=(1.02, 1),
                loc='upper left',
                fontsize=9,
                title_fontsize=10,
                frameon=True,
                fancybox=True
            )
            legend.set_bbox_to_anchor((1.02, 1), transform=app_state.ax.transAxes)
            frame = legend.get_frame()
            frame.set_facecolor("#ffffff")
            frame.set_edgecolor("#cbd5f5")
            frame.set_alpha(0.95)
        except Exception as legend_err:
            print(f"[WARN] 3D legend creation error: {legend_err}", flush=True)

        title = (
            f"3D Scatter Plot ({data_columns[0]}, {data_columns[1]}, {data_columns[2]})\n"
            f"Colored by {group_col}"
        )
        app_state.ax.set_title(title, fontsize=13, color="#1f2937", pad=16)
        app_state.ax.set_xlabel(data_columns[0], color="#334155", fontsize=11)
        app_state.ax.set_ylabel(data_columns[1], color="#334155", fontsize=11)
        app_state.ax.set_zlabel(data_columns[2], color="#334155", fontsize=11)

        # Disable 2D annotations for 3D renderings
        app_state.annotation = None
        return True

    except Exception as err:
        print(f"[ERROR] 3D plot failed: {err}", flush=True)
        traceback.print_exc()
        return False
