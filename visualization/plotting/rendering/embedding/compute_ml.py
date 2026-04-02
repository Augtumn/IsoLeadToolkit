"""Embedding computation helpers for ML-based algorithms."""
from __future__ import annotations

import logging

import numpy as np

from core import state_gateway

from ...core import get_pca_embedding, get_robust_pca_embedding, get_tsne_embedding, get_umap_embedding

logger = logging.getLogger(__name__)


def apply_precomputed_embedding(
    actual_algorithm: str,
    precomputed_embedding: np.ndarray | None,
    precomputed_meta: dict | None,
) -> np.ndarray | None:
    """Apply precomputed embedding and associated metadata when available."""
    if precomputed_embedding is None or actual_algorithm not in ('UMAP', 'TSNE', 'PCA', 'RobustPCA'):
        return None

    embedding = np.asarray(precomputed_embedding)
    last_type = 'tSNE' if actual_algorithm == 'TSNE' else actual_algorithm
    state_gateway.set_attrs({'last_embedding': embedding, 'last_embedding_type': last_type})

    if isinstance(precomputed_meta, dict):
        state_gateway.set_pca_diagnostics(
            last_pca_variance=precomputed_meta.get('last_pca_variance'),
            last_pca_components=precomputed_meta.get('last_pca_components'),
            current_feature_names=precomputed_meta.get('current_feature_names'),
        )

    logger.debug('Using precomputed embedding for %s', actual_algorithm)
    return embedding


def compute_ml_embedding(
    actual_algorithm: str,
    *,
    umap_params: dict,
    tsne_params: dict,
    pca_params: dict,
    robust_pca_params: dict,
) -> np.ndarray | None:
    """Compute embedding for ML algorithms; return None when unsupported."""
    if actual_algorithm == 'UMAP':
        logger.debug('Computing UMAP embedding')
        return get_umap_embedding(umap_params)
    if actual_algorithm == 'TSNE':
        logger.debug('Computing tSNE embedding')
        return get_tsne_embedding(tsne_params)
    if actual_algorithm == 'PCA':
        logger.debug('Computing PCA embedding')
        return get_pca_embedding(pca_params)
    if actual_algorithm == 'RobustPCA':
        logger.debug('Computing Robust PCA embedding')
        return get_robust_pca_embedding(robust_pca_params)
    return None
