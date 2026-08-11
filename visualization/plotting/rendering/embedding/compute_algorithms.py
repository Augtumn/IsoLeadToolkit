"""Pure embedding algorithm computations shared by the sync and async paths.

These functions implement only the numerical algorithm math (UMAP, t-SNE,
PCA, Robust PCA via MinCovDet). They have no access to the cache, state
gateway, signals, or UI — callers are responsible for caching, progress
reporting, and state updates.

Heavy dependencies (umap, sklearn) are imported lazily inside each function
so importing this module never pulls them in.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

__all__ = [
    'compute_pca_embedding',
    'compute_robust_pca_embedding',
    'compute_tsne_embedding',
    'compute_umap_embedding',
]


def compute_umap_embedding(x: np.ndarray, params: dict[str, Any]) -> np.ndarray | None:
    """Compute a UMAP embedding from ``x``.

    Args:
        x: (n_samples, n_features) input array.
        params: UMAP constructor keyword arguments.

    Returns:
        (n_samples, n_components) embedding array, or None for degenerate input.
    """
    if x is None or x.size == 0 or x.shape[0] == 0:
        return None

    import umap

    reducer = umap.UMAP(**params)
    return reducer.fit_transform(x)


def compute_tsne_embedding(x: np.ndarray, params: dict[str, Any]) -> np.ndarray | None:
    """Compute a t-SNE embedding from ``x`` with perplexity/learning-rate clamps.

    Args:
        x: (n_samples, n_features) input array.
        params: TSNE parameters (n_components, perplexity, learning_rate,
            random_state). Unknown keys are ignored.

    Returns:
        (n_samples, n_components) embedding array, or None for degenerate input.
    """
    if x is None or x.size == 0 or x.shape[0] == 0:
        return None

    n_samples = x.shape[0]
    if n_samples <= 1:
        logger.error("Not enough samples for t-SNE")
        return None

    perplexity = float(params.get('perplexity', 30))
    if perplexity >= n_samples:
        perplexity = max(2, n_samples - 1)

    learning_rate = max(float(params.get('learning_rate', 200)), 10)

    from sklearn.manifold import TSNE

    reducer = TSNE(
        n_components=params.get('n_components', 2),
        perplexity=perplexity,
        learning_rate=learning_rate,
        random_state=params.get('random_state', 42),
        verbose=0,
        n_jobs=-1,
    )
    return reducer.fit_transform(x)


def compute_pca_embedding(x: np.ndarray, params: dict[str, Any]) -> dict[str, Any] | None:
    """Compute a standard-scaled PCA embedding from ``x``.

    Args:
        x: (n_samples, n_features) input array.
        params: PCA parameters (n_components, random_state).

    Returns:
        dict with "embedding" plus "variance" (explained_variance_ratio_)
        and "components" (components_), or None for degenerate input.
    """
    if x is None or x.size == 0 or x.shape[0] == 0:
        return None

    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    try:
        x_scaled = scaler.fit_transform(x)
        if np.isnan(x_scaled).any():
            x_scaled = np.nan_to_num(x_scaled)
    except Exception:
        x_scaled = x

    reducer = PCA(
        n_components=params.get('n_components', 2),
        random_state=params.get('random_state', 42),
    )
    embedding = reducer.fit_transform(x_scaled)
    return {
        "embedding": embedding,
        "variance": reducer.explained_variance_ratio_,
        "components": reducer.components_,
    }


def compute_robust_pca_embedding(x: np.ndarray, params: dict[str, Any]) -> dict[str, Any] | None:
    """Compute a Robust PCA embedding via MinCovDet with a PCA fallback.

    When ``n_samples <= n_features`` the covariance estimate is unreliable,
    so a plain PCA embedding is returned instead (mirroring the previous
    behavior of the sync and async embedding paths).

    Args:
        x: (n_samples, n_features) input array.
        params: Robust PCA parameters (n_components, random_state,
            support_fraction).

    Returns:
        dict with "embedding" plus optional "variance" and "components", or
        None for degenerate input. "variance" is omitted when the eigval sum
        is not positive.
    """
    if x is None or x.size == 0 or x.shape[0] == 0:
        return None

    from sklearn.covariance import MinCovDet
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    try:
        x_scaled = scaler.fit_transform(x)
        if np.isnan(x_scaled).any():
            x_scaled = np.nan_to_num(x_scaled)
    except Exception:
        x_scaled = x

    if x_scaled.shape[0] <= x_scaled.shape[1]:
        reducer = PCA(
            n_components=params.get('n_components', 2),
            random_state=params.get('random_state', 42),
        )
        embedding = reducer.fit_transform(x_scaled)
        return {
            "embedding": embedding,
            "variance": reducer.explained_variance_ratio_,
            "components": reducer.components_,
        }

    support_fraction = params.get('support_fraction', 0.75)
    mcd = MinCovDet(
        random_state=params.get('random_state', 42),
        support_fraction=support_fraction,
    )
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

    result: dict[str, Any] = {"embedding": embedding, "components": components.T}
    if eigvals.sum() > 0:
        result["variance"] = eigvals[:n_components] / eigvals.sum()
    return result
