"""Tests for shared pure embedding algorithm computations."""

from __future__ import annotations

import numpy as np

from visualization.plotting.rendering.embedding.compute_algorithms import (
    compute_pca_embedding,
    compute_robust_pca_embedding,
    compute_tsne_embedding,
    compute_umap_embedding,
)


def test_compute_pca_embedding_shape_and_finite() -> None:
    x = np.random.RandomState(0).normal(size=(50, 4))
    result = compute_pca_embedding(x, {"n_components": 2, "random_state": 42})

    assert result is not None
    embedding = result["embedding"]
    assert embedding.shape == (50, 2)
    assert np.isfinite(embedding).all()
    assert result["variance"].shape == (2,)
    assert result["components"].shape == (2, 4)


def test_compute_tsne_embedding_clamps_perplexity_for_small_samples() -> None:
    x = np.random.RandomState(1).normal(size=(3, 4))
    # perplexity=30 is invalid for 3 samples; the clamp must make it work.
    result = compute_tsne_embedding(
        x, {"n_components": 2, "perplexity": 30, "learning_rate": 200, "random_state": 42}
    )

    assert result is not None
    assert result.shape == (3, 2)
    assert np.isfinite(result).all()


def test_compute_tsne_embedding_returns_none_for_single_sample() -> None:
    x = np.random.RandomState(2).normal(size=(1, 4))
    assert compute_tsne_embedding(x, {"n_components": 2}) is None


def test_compute_umap_embedding_shape() -> None:
    x = np.random.RandomState(3).normal(size=(30, 5))
    result = compute_umap_embedding(
        x, {"n_components": 2, "n_neighbors": 5, "min_dist": 0.1, "random_state": 42}
    )

    assert result is not None
    assert result.shape == (30, 2)
    assert np.isfinite(result).all()


def test_compute_robust_pca_embedding_falls_back_when_samples_leq_features() -> None:
    x = np.random.RandomState(4).normal(size=(5, 10))
    result = compute_robust_pca_embedding(x, {"n_components": 2, "random_state": 42})

    assert result is not None
    assert result["embedding"].shape == (5, 2)
    assert np.isfinite(result["embedding"]).all()
    assert result["variance"].shape == (2,)
    assert result["components"].shape == (2, 10)


def test_compute_pca_embedding_returns_none_for_empty_input() -> None:
    x = np.empty((0, 4))
    assert compute_pca_embedding(x, {"n_components": 2}) is None
