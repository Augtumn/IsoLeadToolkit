"""Tests for embedding algorithm normalization helpers."""

from __future__ import annotations

from core import CONFIG
from visualization.plotting.rendering.embedding.algorithm import (
    normalize_algorithm,
    resolve_embedding_params,
    resolve_target_dimensions,
)


def test_normalize_algorithm_handles_legacy_aliases() -> None:
    assert normalize_algorithm("robustpca") == "RobustPCA"
    assert normalize_algorithm("PB_MODELS_76") == "PB_EVOL_76"
    assert normalize_algorithm("PB_MODELS_86") == "PB_EVOL_86"
    assert normalize_algorithm("ISOCHRON1") == "PB_EVOL_76"
    assert normalize_algorithm("ISOCHRON2") == "PB_EVOL_86"


def test_resolve_target_dimensions_for_ternary_and_default() -> None:
    assert resolve_target_dimensions("TERNARY") == "ternary"
    assert resolve_target_dimensions("UMAP") == 2


def test_resolve_embedding_params_defaults_and_passthrough() -> None:
    umap, tsne, pca, robust = resolve_embedding_params(None, None, None, None)
    assert umap == CONFIG["umap_params"]
    assert tsne == CONFIG["tsne_params"]
    assert pca == CONFIG.get("pca_params", {"n_components": 2, "random_state": 42})
    assert robust == CONFIG.get("robust_pca_params", {"n_components": 2, "random_state": 42})

    u0 = {"n_neighbors": 15}
    t0 = {"perplexity": 20}
    p0 = {"n_components": 3}
    r0 = {"n_components": 3}
    umap2, tsne2, pca2, robust2 = resolve_embedding_params(u0, t0, p0, r0)
    assert umap2 is u0
    assert tsne2 is t0
    assert pca2 is p0
    assert robust2 is r0
