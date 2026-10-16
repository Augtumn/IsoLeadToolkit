"""Embedding plotting: the entry point for the embedding family of modes.

The render sequence is the pipeline's and each mode's own parts are its adapter's. What stays here is
the entry point the rest of the application calls: it gathers one render's context and runs it.
"""
from __future__ import annotations

import logging

from core import app_state

logger = logging.getLogger(__name__)


def plot_embedding(
    group_col: str,
    algorithm: str,
    umap_params: dict | None = None,
    tsne_params: dict | None = None,
    pca_params: dict | None = None,
    robust_pca_params: dict | None = None,
    size: int = 60,
    precomputed_embedding=None,
    precomputed_meta: dict | None = None,
) -> bool:
    """Update plot with specified algorithm and parameters"""
    from .adapters import register_adapters
    from .common.state_access import _active_subset_indices
    from .context import build_context
    from .pipeline import run
    from .registry import adapter_for

    register_adapters()
    context = build_context(
        str(algorithm),
        group_col=group_col,
        figure=app_state.fig,
        axes=app_state.ax,
        columns_ternary=tuple(app_state.selected_ternary_cols or ()),
        point_size=size,
        show_marginal_kde=bool(app_state.show_marginal_kde),
        umap_params=umap_params,
        tsne_params=tsne_params,
        pca_params=pca_params,
        robust_pca_params=robust_pca_params,
        precomputed_embedding=precomputed_embedding,
        precomputed_meta=precomputed_meta,
        subset_indices=_active_subset_indices(),
    )
    return bool(run(adapter_for(context.mode), context))
