"""Qt-based analysis plots and diagnostics."""
from __future__ import annotations

import logging
from typing import Any

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QDialog, QFileDialog, QPushButton, QVBoxLayout

from core import app_state, translate
from .data import _get_analysis_data

logger = logging.getLogger(__name__)


def _data_state() -> Any:
    return getattr(app_state, 'data', app_state)


def _data_cols() -> list[str]:
    return getattr(_data_state(), 'data_cols', app_state.data_cols)


def _create_plot_dialog(
    title: str,
    width: int = 800,
    height: int = 500,
    parent=None,
) -> tuple[QDialog, Figure, FigureCanvas]:
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(width, height)
    layout = QVBoxLayout(dialog)
    fig = Figure(figsize=(width / 100.0, height / 100.0), dpi=100)
    canvas = FigureCanvas(fig)
    layout.addWidget(canvas)

    save_btn = QPushButton(translate("Save"))

    def _save_chart() -> None:
        filters = ";;".join([
            translate("PNG Files (*.png)"),
            translate("PDF Files (*.pdf)"),
            translate("SVG Files (*.svg)"),
        ])
        path, _ = QFileDialog.getSaveFileName(
            dialog, translate("Save Chart"), "", filters,
        )
        if not path:
            return
        try:
            fig.savefig(path, dpi=150, bbox_inches='tight')
            logger.info(translate("Chart saved to: {path}").format(path=path))
        except Exception as e:
            logger.error("Failed to save chart: %s", e)

    save_btn.clicked.connect(_save_chart)
    layout.addWidget(save_btn)

    return dialog, fig, canvas


def show_scree_plot(parent_window=None) -> None:
    """Display a scree plot of the explained variance for the last PCA run."""
    if not hasattr(app_state, 'last_pca_variance') or app_state.last_pca_variance is None:
        logger.warning("No PCA variance data available. Run PCA first.")
        return

    variance_ratio = app_state.last_pca_variance
    n_components = len(variance_ratio)
    components = range(1, n_components + 1)
    cumulative_variance = np.cumsum(variance_ratio)

    dialog, fig, canvas = _create_plot_dialog(
        translate("Scree Plot - Explained Variance"),
        600,
        450,
        parent_window,
    )
    ax1 = fig.add_subplot(111)

    ax1.bar(
        components,
        variance_ratio,
        alpha=0.6,
        color='b',
        label=translate("Individual Variance"),
    )
    ax1.set_xlabel(translate("Principal Component"))
    ax1.set_ylabel(translate("Explained Variance Ratio"), color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.set_xticks(list(components))
    ax1.set_ylim(0, 1.05)

    ax2 = ax1.twinx()
    ax2.plot(
        components,
        cumulative_variance,
        marker='o',
        color='r',
        label=translate("Cumulative Variance"),
    )
    ax2.set_ylabel(translate("Cumulative Variance Ratio"), color='r')
    ax2.tick_params(axis='y', labelcolor='r')
    ax2.set_ylim(0, 1.05)

    ax1.grid(True, axis='x', alpha=0.3)
    ax2.grid(True, axis='y', alpha=0.3)

    ax1.set_title(translate("Scree Plot"))
    fig.tight_layout()
    canvas.draw()
    dialog.exec_()


def show_pca_loadings(parent_window=None) -> None:
    """Display a heatmap of PCA loadings (components)."""
    if not hasattr(app_state, 'last_pca_components') or app_state.last_pca_components is None:
        logger.warning("No PCA components data available. Run PCA first.")
        return

    components = app_state.last_pca_components
    feature_names = app_state.current_feature_names

    if not feature_names or len(feature_names) != components.shape[1]:
        logger.warning("Feature names mismatch or missing.")
        feature_names = [
            translate("Feature {index}").format(index=i + 1)
            for i in range(components.shape[1])
        ]

    n_comps = components.shape[0]
    comp_names = [f"PC{i + 1}" for i in range(n_comps)]

    dialog, fig, canvas = _create_plot_dialog(
        translate("PCA Loadings"),
        800,
        600,
        parent_window,
    )
    ax = fig.add_subplot(111)

    im = ax.imshow(components, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(translate("Loading Value"))

    ax.set_xticks(np.arange(len(feature_names)))
    ax.set_yticks(np.arange(len(comp_names)))

    ax.set_xticklabels(feature_names, rotation=45, ha="right")
    ax.set_yticklabels(comp_names)

    for i in range(len(comp_names)):
        for j in range(len(feature_names)):
            ax.text(
                j,
                i,
                f"{components[i, j]:.2f}",
                ha="center",
                va="center",
                color="k" if abs(components[i, j]) < 0.5 else "w",
            )

    ax.set_title(translate("PCA Loadings (Feature Contribution to Components)"))
    fig.tight_layout()
    canvas.draw()
    dialog.exec_()


def show_embedding_correlation(parent_window=None) -> None:
    """Display correlation between original features and embedding dimensions."""
    if not hasattr(app_state, 'last_embedding') or app_state.last_embedding is None:
        logger.warning("No embedding data available. Run an analysis first.")
        return

    embedding = app_state.last_embedding
    X, _ = _get_analysis_data()

    if X is None:
        return

    cols = _data_cols()
    if not cols:
        return

    n_dims = embedding.shape[1]
    dim_names = [translate("Dim {index}").format(index=i + 1) for i in range(n_dims)]

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

    embedding_type = getattr(app_state, 'last_embedding_type', 'Embedding')
    title = translate("Feature Correlation with {embedding} Axes").format(embedding=embedding_type)
    dialog, fig, canvas = _create_plot_dialog(title, 800, 400, parent_window)
    ax = fig.add_subplot(111)

    im = ax.imshow(correlations, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(translate("Correlation Coefficient"))

    ax.set_yticks(np.arange(n_dims))
    ax.set_yticklabels(dim_names)

    ax.set_xticks(np.arange(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha="right")

    for i in range(n_dims):
        for j in range(len(cols)):
            ax.text(j, i, f"{correlations[i, j]:.2f}", ha="center", va="center",
                    color="k" if abs(correlations[i, j]) < 0.5 else "w")

    ax.set_title(
        translate("Correlation: Features vs {embedding} Dimensions").format(embedding=embedding_type)
    )
    fig.tight_layout()
    canvas.draw()
    dialog.exec_()


def show_shepard_diagram(parent_window=None) -> None:
    """Display a Shepard diagram (Distance Plot) to evaluate embedding quality."""
    if not hasattr(app_state, 'last_embedding') or app_state.last_embedding is None:
        logger.warning("No embedding data available.")
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

    embedding_type = getattr(app_state, 'last_embedding_type', 'Embedding')
    title = translate("Shepard Diagram ({embedding})").format(embedding=embedding_type)
    dialog, fig, canvas = _create_plot_dialog(title, 600, 600, parent_window)
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

    ax.set_xlabel(translate("Original Distance"))
    ax.set_ylabel(translate("Embedding Distance"))
    ax.set_title(
        translate("Shepard Diagram\nSpearman Correlation: {value}").format(value=f"{corr:.3f}")
    )

    fig.tight_layout()
    canvas.draw()
    dialog.exec_()


def show_correlation_heatmap(parent_window=None) -> None:
    """Display a correlation heatmap of the current dataset."""
    X, _ = _get_analysis_data()
    if X is None:
        logger.warning("No data available for correlation analysis.")
        return

    cols = _data_cols()
    if not cols:
        return

    df_corr = pd.DataFrame(X, columns=cols).corr()

    dialog, fig, canvas = _create_plot_dialog(
        translate("Correlation Heatmap"),
        700,
        600,
        parent_window,
    )
    ax = fig.add_subplot(111)

    im = ax.imshow(df_corr, cmap='coolwarm', vmin=-1, vmax=1)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(translate("Correlation Coefficient"))

    ax.set_xticks(np.arange(len(cols)))
    ax.set_yticks(np.arange(len(cols)))

    ax.set_xticklabels(cols, rotation=45, ha="right")
    ax.set_yticklabels(cols)

    for i in range(len(cols)):
        for j in range(len(cols)):
            ax.text(j, i, f"{df_corr.iloc[i, j]:.2f}", ha="center", va="center", color="k")

    ax.set_title(translate("Feature Correlation Matrix"))
    fig.tight_layout()
    canvas.draw()
    dialog.exec_()

