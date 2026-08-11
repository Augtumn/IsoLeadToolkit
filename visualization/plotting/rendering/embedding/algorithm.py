"""Algorithm normalization and embedding computation helpers."""
from __future__ import annotations

import logging

import numpy as np

from core import CONFIG

from .compute_geochem import compute_geochem_embedding, compute_v1v2_embedding
from .compute_ml import apply_precomputed_embedding, compute_ml_embedding
from .compute_ternary import compute_ternary_embedding

logger = logging.getLogger(__name__)


def _resolve_legacy_aliases(value: str) -> str | None:
    """Map legacy render-mode/algorithm aliases to canonical names.

    Shared by :func:`normalize_algorithm` and the legend module's
    ``normalize_render_mode`` so the PB_MODELS / ISOCHRON alias mapping
    lives in exactly one place. Returns ``None`` when *value* is not a
    legacy alias (callers apply their own case convention).

    Note: *value* must already be normalized to the caller's case
    convention (upper for algorithms, verbatim for legend render modes).
    """
    if value in ('PB_MODELS_76', 'PB_MODELS_86'):
        return 'PB_EVOL_76' if value.endswith('_76') else 'PB_EVOL_86'
    if value in ('ISOCHRON1', 'ISOCHRON2'):
        return 'PB_EVOL_76' if value == 'ISOCHRON1' else 'PB_EVOL_86'
    return None


def normalize_algorithm(algorithm: str) -> str:
    """Normalize legacy algorithm aliases to canonical names."""
    actual_algorithm = algorithm.strip().upper() if isinstance(algorithm, str) else str(algorithm)
    if actual_algorithm == 'ROBUSTPCA':
        return 'RobustPCA'
    canonical = _resolve_legacy_aliases(actual_algorithm)
    if canonical is not None:
        return canonical
    return actual_algorithm


def resolve_target_dimensions(actual_algorithm: str) -> int | str:
    """Return target axes dimensionality for the algorithm."""
    return 'ternary' if actual_algorithm == 'TERNARY' else 2


def resolve_embedding_params(
    umap_params: dict | None,
    tsne_params: dict | None,
    pca_params: dict | None,
    robust_pca_params: dict | None,
) -> tuple[dict, dict, dict, dict]:
    """Fill missing embedding parameter dictionaries from CONFIG defaults."""
    if umap_params is None:
        umap_params = CONFIG['umap_params']
    if tsne_params is None:
        tsne_params = CONFIG['tsne_params']
    if pca_params is None:
        pca_params = CONFIG.get('pca_params', {'n_components': 2, 'random_state': 42})
    if robust_pca_params is None:
        robust_pca_params = CONFIG.get('robust_pca_params', {'n_components': 2, 'random_state': 42})
    return umap_params, tsne_params, pca_params, robust_pca_params


def compute_embedding(
    actual_algorithm: str,
    *,
    precomputed_embedding: np.ndarray | None,
    precomputed_meta: dict | None,
    umap_params: dict,
    tsne_params: dict,
    pca_params: dict,
    robust_pca_params: dict,
) -> np.ndarray | None:
    """Compute or reuse embedding for the normalized algorithm."""
    embedding = apply_precomputed_embedding(actual_algorithm, precomputed_embedding, precomputed_meta)
    if embedding is not None:
        return embedding

    embedding = compute_ml_embedding(
        actual_algorithm,
        umap_params=umap_params,
        tsne_params=tsne_params,
        pca_params=pca_params,
        robust_pca_params=robust_pca_params,
    )
    if embedding is not None:
        return embedding

    if actual_algorithm == 'V1V2':
        logger.debug('Computing V1V2 embedding')
        return compute_v1v2_embedding()
    if actual_algorithm in (
        'PB_EVOL_76',
        'PB_EVOL_86',
        'PB_MU_AGE',
        'PB_KAPPA_AGE',
        'PLUMBOTECTONICS_76',
        'PLUMBOTECTONICS_86',
    ):
        logger.debug('Computing Geochemistry embedding for %s', actual_algorithm)
        return compute_geochem_embedding(actual_algorithm)
    if actual_algorithm == 'TERNARY':
        logger.debug('Computing Ternary embedding')
        return compute_ternary_embedding()

    logger.error('Unknown algorithm: %s', actual_algorithm)
    return None
