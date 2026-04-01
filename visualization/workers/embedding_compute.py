"""Embedding computation helpers used by background workers."""
from __future__ import annotations

import logging
from typing import Any, Callable

import numpy as np

logger = logging.getLogger(__name__)


def normalize_algorithm_name(algorithm: str) -> str:
    """Normalize algorithm names to runtime identifiers used by worker compute."""
    normalized = str(algorithm).strip()
    upper = normalized.upper()
    if upper == 'TSNE':
        return 'tSNE'
    if upper == 'ROBUSTPCA':
        return 'RobustPCA'
    if upper == 'UMAP':
        return 'UMAP'
    return normalized


def _compute_umap(x: np.ndarray, params: dict[str, Any], report: Callable[[int, str], None]) -> dict[str, Any]:
    report(20, 'umap_init')
    import umap

    reducer = umap.UMAP(**params)
    report(40, 'umap_fit')
    embedding = reducer.fit_transform(x)
    return {'embedding': embedding, 'meta': {}}


def _compute_tsne(x: np.ndarray, params: dict[str, Any], report: Callable[[int, str], None]) -> dict[str, Any] | None:
    report(20, 'tsne_init')
    from sklearn.manifold import TSNE

    n_samples = x.shape[0]
    perplexity = float(params.get('perplexity', 30))
    if n_samples <= 1:
        return None
    if perplexity >= n_samples:
        perplexity = max(2, n_samples - 1)

    learning_rate = max(float(params.get('learning_rate', 200)), 10)
    reducer = TSNE(
        n_components=params.get('n_components', 2),
        perplexity=perplexity,
        learning_rate=learning_rate,
        random_state=params.get('random_state', 42),
        verbose=0,
        n_jobs=-1,
    )
    report(45, 'tsne_fit')
    embedding = reducer.fit_transform(x)
    return {'embedding': embedding, 'meta': {}}


def _scale_or_fallback(x: np.ndarray) -> np.ndarray:
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    try:
        x_scaled = scaler.fit_transform(x)
        if np.isnan(x_scaled).any():
            x_scaled = np.nan_to_num(x_scaled)
        return x_scaled
    except Exception:
        return x


def _compute_pca(
    x: np.ndarray,
    params: dict[str, Any],
    feature_names: list[str],
    report: Callable[[int, str], None],
) -> dict[str, Any]:
    report(20, 'pca_scale')
    from sklearn.decomposition import PCA

    x_scaled = _scale_or_fallback(x)

    reducer = PCA(
        n_components=params.get('n_components', 2),
        random_state=params.get('random_state', 42),
    )
    report(50, 'pca_fit')
    embedding = reducer.fit_transform(x_scaled)
    return {
        'embedding': embedding,
        'meta': {
            'last_pca_variance': reducer.explained_variance_ratio_,
            'last_pca_components': reducer.components_,
            'current_feature_names': feature_names,
        },
    }


def _compute_robust_pca(
    x: np.ndarray,
    params: dict[str, Any],
    feature_names: list[str],
    report: Callable[[int, str], None],
) -> dict[str, Any]:
    report(20, 'robust_scale')
    from sklearn.covariance import MinCovDet
    from sklearn.decomposition import PCA

    x_scaled = _scale_or_fallback(x)

    meta: dict[str, Any] = {'current_feature_names': feature_names}
    if x_scaled.shape[0] <= x_scaled.shape[1]:
        reducer = PCA(
            n_components=params.get('n_components', 2),
            random_state=params.get('random_state', 42),
        )
        report(50, 'robust_fallback_pca_fit')
        embedding = reducer.fit_transform(x_scaled)
        meta['last_pca_variance'] = reducer.explained_variance_ratio_
        meta['last_pca_components'] = reducer.components_
        return {'embedding': embedding, 'meta': meta}

    support_fraction = params.get('support_fraction', 0.75)
    mcd = MinCovDet(
        random_state=params.get('random_state', 42),
        support_fraction=support_fraction,
    )
    report(40, 'robust_mcd_fit')
    mcd.fit(x_scaled)

    cov = mcd.covariance_
    mean = mcd.location_
    eigvals, eigvecs = np.linalg.eigh(cov)
    order = np.argsort(eigvals)[::-1]
    eigvecs = eigvecs[:, order]
    eigvals = eigvals[order]
    n_components = params.get('n_components', 2)
    components = eigvecs[:, :n_components]
    embedding = (x_scaled - mean) @ components

    if eigvals.sum() > 0:
        meta['last_pca_variance'] = eigvals[:n_components] / eigvals.sum()
    meta['last_pca_components'] = components.T
    return {'embedding': embedding, 'meta': meta}


def compute_embedding_payload(
    algorithm: str,
    x: np.ndarray,
    params: dict[str, Any],
    feature_names: list[str],
    report: Callable[[int, str], None],
) -> dict[str, Any] | None:
    """Compute embedding and metadata payload for a normalized algorithm name."""
    if algorithm == 'UMAP':
        return _compute_umap(x, params, report)
    if algorithm == 'tSNE':
        return _compute_tsne(x, params, report)
    if algorithm == 'PCA':
        return _compute_pca(x, params, feature_names, report)
    if algorithm == 'RobustPCA':
        return _compute_robust_pca(x, params, feature_names, report)
    return None
