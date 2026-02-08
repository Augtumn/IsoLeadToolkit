"""Analysis plots and diagnostics."""
import numpy as np
import pandas as pd
import tkinter as tk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core.state import app_state
from .plotting_data import _lazy_import_ml, _get_analysis_data, PCA, TSNE


def show_scree_plot(parent_window=None):
    """Display a scree plot of the explained variance for the last PCA run."""
    if not hasattr(app_state, 'last_pca_variance') or app_state.last_pca_variance is None:
        print("[WARN] No PCA variance data available. Run PCA first.", flush=True)
        return

    variance_ratio = app_state.last_pca_variance
    n_components = len(variance_ratio)
    components = range(1, n_components + 1)
    cumulative_variance = np.cumsum(variance_ratio)

    window = tk.Toplevel(parent_window)
    window.title("Scree Plot - Explained Variance")
    window.geometry("600x450")

    fig = Figure(figsize=(6, 4), dpi=100)
    ax1 = fig.add_subplot(111)

    ax1.bar(components, variance_ratio, alpha=0.6, color='b', label='Individual Variance')
    ax1.set_xlabel('Principal Component')
    ax1.set_ylabel('Explained Variance Ratio', color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.set_xticks(components)
    ax1.set_ylim(0, 1.05)

    ax2 = ax1.twinx()
    ax2.plot(components, cumulative_variance, marker='o', color='r', label='Cumulative Variance')
    ax2.set_ylabel('Cumulative Variance Ratio', color='r')
    ax2.tick_params(axis='y', labelcolor='r')
    ax2.set_ylim(0, 1.05)

    ax1.grid(True, axis='x', alpha=0.3)
    ax2.grid(True, axis='y', alpha=0.3)

    ax1.set_title('Scree Plot')
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _on_close():
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

    window = tk.Toplevel(parent_window)
    window.title("PCA Loadings")
    window.geometry("800x600")

    fig = Figure(figsize=(8, 6), dpi=100)
    ax = fig.add_subplot(111)

    im = ax.imshow(components, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Loading Value')

    ax.set_xticks(np.arange(len(feature_names)))
    ax.set_yticks(np.arange(len(comp_names)))

    ax.set_xticklabels(feature_names, rotation=45, ha="right")
    ax.set_yticklabels(comp_names)

    for i in range(len(comp_names)):
        for j in range(len(feature_names)):
            ax.text(j, i, f"{components[i, j]:.2f}", ha="center", va="center", color="k" if abs(components[i, j]) < 0.5 else "w")

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
    X, _ = _get_analysis_data()

    if X is None:
        return

    cols = app_state.data_cols
    if not cols:
        return

    n_dims = embedding.shape[1]
    dim_names = [f"Dim {i+1}" for i in range(n_dims)]

    correlations = []
    for i in range(n_dims):
        dim_corrs = []
        dim_data = embedding[:, i]
        for j in range(X.shape[1]):
            feat_data = X[:, j]
            corr = np.corrcoef(dim_data, feat_data)[0, 1]
            if np.isnan(corr):
                corr = 0
            dim_corrs.append(corr)
        correlations.append(dim_corrs)

    correlations = np.array(correlations)

    window = tk.Toplevel(parent_window)
    window.title(f"Feature Correlation with {getattr(app_state, 'last_embedding_type', 'Embedding')} Axes")
    window.geometry("800x400")

    fig = Figure(figsize=(8, 4), dpi=100)
    ax = fig.add_subplot(111)

    im = ax.imshow(correlations, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Correlation Coefficient')

    ax.set_yticks(np.arange(n_dims))
    ax.set_yticklabels(dim_names)

    ax.set_xticks(np.arange(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha="right")

    for i in range(n_dims):
        for j in range(len(cols)):
            ax.text(j, i, f"{correlations[i, j]:.2f}", ha="center", va="center", color="k" if abs(correlations[i, j]) < 0.5 else "w")

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

    n_samples = X.shape[0]
    max_samples = 1000

    if n_samples > max_samples:
        indices = np.random.choice(n_samples, max_samples, replace=False)
        X_sub = X[indices]
        emb_sub = embedding[indices]
    else:
        X_sub = X
        emb_sub = embedding

    from scipy.spatial.distance import pdist

    d_original = pdist(X_sub)
    d_embedding = pdist(emb_sub)

    from scipy.stats import spearmanr
    corr, _ = spearmanr(d_original, d_embedding)

    window = tk.Toplevel(parent_window)
    window.title(f"Shepard Diagram ({getattr(app_state, 'last_embedding_type', 'Embedding')})")
    window.geometry("600x600")

    fig = Figure(figsize=(6, 6), dpi=100)
    ax = fig.add_subplot(111)

    if len(d_original) > 5000:
        plot_indices = np.random.choice(len(d_original), 5000, replace=False)
        ax.scatter(d_original[plot_indices], d_embedding[plot_indices], alpha=0.1, s=5, c='k')
    else:
        ax.scatter(d_original, d_embedding, alpha=0.2, s=10, c='k')

    xlims = (0, np.max(d_original))
    ylims = (0, np.max(d_embedding))

    diag_max = max(xlims[1], ylims[1])
    ax.plot([0, diag_max], [0, diag_max], 'r--', alpha=0.5, label='x=y')

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

    df_corr = pd.DataFrame(X, columns=cols).corr()

    window = tk.Toplevel(parent_window)
    window.title("Correlation Heatmap")
    window.geometry("700x600")

    fig = Figure(figsize=(7, 6), dpi=100)
    ax = fig.add_subplot(111)

    im = ax.imshow(df_corr, cmap='coolwarm', vmin=-1, vmax=1)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Correlation Coefficient')

    ax.set_xticks(np.arange(len(cols)))
    ax.set_yticks(np.arange(len(cols)))

    ax.set_xticklabels(cols, rotation=45, ha="right")
    ax.set_yticklabels(cols)

    for i in range(len(cols)):
        for j in range(len(cols)):
            ax.text(j, i, f"{df_corr.iloc[i, j]:.2f}", ha="center", va="center", color="k")

    ax.set_title("Feature Correlation Matrix")
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
