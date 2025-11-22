"""
Dimensionality Reduction Visualization
Handles UMAP and t-SNE embedding computation and plot rendering
"""
import traceback
from config import CONFIG
from state import app_state
import umap
from sklearn.manifold import TSNE
import seaborn as sns

sns.set_theme(style="whitegrid")


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


def get_embedding(algorithm, umap_params=None, tsne_params=None):
    """Get embedding based on selected algorithm"""
    if algorithm == 'UMAP':
        return get_umap_embedding(umap_params or CONFIG['umap_params'])
    elif algorithm == 'tSNE':
        return get_tsne_embedding(tsne_params or CONFIG['tsne_params'])
    else:
        print(f"[ERROR] Unknown algorithm: {algorithm}")
        return None


def plot_embedding(group_col, algorithm, umap_params=None, tsne_params=None, size=60):
    """Update plot with specified algorithm and parameters"""
    try:
        print(f"[DEBUG] plot_embedding called: algorithm={algorithm}, group_col={group_col}, size={size}", flush=True)
        
        if app_state.ax is None or app_state.fig is None:
            print("[ERROR] Plot axes not initialized", flush=True)
            return False
        
        app_state.ax.clear()
        app_state.clear_plot_state()

        # Reserve space around the axes so the legend and titles are never clipped
        try:
            app_state.fig.subplots_adjust(left=0.08, bottom=0.12, right=0.78, top=0.9)
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
        
        print(f"[DEBUG] Using params - UMAP: {umap_params}, tSNE: {tsne_params}", flush=True)
        
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
        
        df_plot = app_state.df_global.copy()
        if group_col not in df_plot.columns:
            print(f"[ERROR] Column not found: {group_col}", flush=True)
            return False
        
        df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)
        
        unique_cats = sorted(df_plot[group_col].unique())
        print(f"[DEBUG] Unique categories in {group_col}: {unique_cats}", flush=True)
        palette = sns.color_palette("tab20", len(unique_cats))
        
        scatters = []
        for i, cat in enumerate(unique_cats):
            try:
                mask = df_plot[group_col] == cat
                indices = df_plot[mask].index.tolist()
                xs = embedding[mask, 0]
                ys = embedding[mask, 1]
                
                if len(xs) == 0:
                    continue
                
                sc = app_state.ax.scatter(
                    xs, ys, label=cat, color=palette[i], s=size,
                    alpha=0.88, edgecolors="#1e293b", linewidth=0.4, zorder=2
                )
                scatters.append(sc)
                app_state.scatter_collections.append(sc)
                
                # Store coordinate-to-index mapping with explicit float conversion
                for j, idx in enumerate(indices):
                    x_val = float(xs[j])
                    y_val = float(ys[j])
                    key = (round(x_val, 2), round(y_val, 2))
                    app_state.sample_index_map[key] = idx
                    
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
        else:  # tSNE
            title = f't-SNE (perplexity={tsne_params["perplexity"]}, lr={tsne_params["learning_rate"]})\nColored by {group_col}'
        
        app_state.ax.set_title(title, fontsize=13, color="#1f2937", pad=16)
        app_state.ax.set_xlabel('Dimension 1', color="#334155", fontsize=11)
        app_state.ax.set_ylabel('Dimension 2', color="#334155", fontsize=11)
        app_state.ax.tick_params(colors="#475569", labelsize=9)
        
        # Initialize annotation (always recreate after ax.clear())
        app_state.annotation = app_state.ax.annotate(
            "", xy=(0, 0), xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="yellow", alpha=0.8),
            arrowprops=dict(arrowstyle="->")
        )
        app_state.annotation.set_visible(False)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Plot update failed: {e}")
        traceback.print_exc()
        return False


# Keep backward compatibility
def plot_umap(group_col, params, size):
    """Deprecated: Use plot_embedding instead"""
    return plot_embedding(group_col, 'UMAP', umap_params=params, size=size)
