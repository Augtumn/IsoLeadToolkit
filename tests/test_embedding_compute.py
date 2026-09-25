"""Embedding computation and algorithm-helper tests."""

from typing import cast

import numpy as np
import pandas as pd

from core import CONFIG, app_state
from visualization.plotting.rendering.embedding import dataframe as dataframe_helpers
from visualization.plotting.rendering.embedding.algorithm import (
    normalize_algorithm,
    resolve_embedding_params,
    resolve_target_dimensions,
)
from visualization.plotting.rendering.embedding.compute_algorithms import (
    compute_pca_embedding,
    compute_robust_pca_embedding,
    compute_tsne_embedding,
    compute_umap_embedding,
)


def test_normalize_algorithm_handles_alternate_names() -> None:
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


def test_prepare_plot_dataframe_filters_to_visible_groups(monkeypatch) -> None:
    df = pd.DataFrame({"group": ["A", "B"], "value": [1.0, 2.0]})
    embedding = np.array([[0.0, 0.1], [1.0, 1.1]], dtype=float)

    captured: dict[str, object] = {"set_visible_calls": []}
    monkeypatch.setattr(dataframe_helpers, "_df_global", lambda: df)
    monkeypatch.setattr(dataframe_helpers, "_active_subset_indices", lambda: None)
    monkeypatch.setattr(
        dataframe_helpers.state_gateway,
        "sync_available_and_visible_groups",
        lambda groups: captured.update({"synced_groups": list(groups)}),
    )
    monkeypatch.setattr(
        dataframe_helpers.state_gateway,
        "set_visible_groups",
        lambda value: cast(list[object], captured["set_visible_calls"]).append(value),
    )

    original_visible_groups = getattr(app_state, "visible_groups", None)
    try:
        setattr(app_state, "visible_groups", {"A"})

        result = dataframe_helpers.prepare_plot_dataframe("group", "UMAP", embedding)

        assert result is not None
        df_plot, unique_cats = result
        assert list(df_plot["group"]) == ["A"]
        assert unique_cats == ["A"]
        assert captured["synced_groups"] == ["A", "B"]
        assert captured["set_visible_calls"] == []
    finally:
        setattr(app_state, "visible_groups", original_visible_groups)


def test_prepare_plot_dataframe_resets_invalid_visible_filter(monkeypatch) -> None:
    df = pd.DataFrame({"group": ["A", "B"], "value": [1.0, 2.0]})
    embedding = np.array([[0.0, 0.1], [1.0, 1.1]], dtype=float)

    captured: dict[str, object] = {"set_visible_calls": []}
    monkeypatch.setattr(dataframe_helpers, "_df_global", lambda: df)
    monkeypatch.setattr(dataframe_helpers, "_active_subset_indices", lambda: None)
    monkeypatch.setattr(dataframe_helpers.state_gateway, "sync_available_and_visible_groups", lambda _groups: None)
    monkeypatch.setattr(
        dataframe_helpers.state_gateway,
        "set_visible_groups",
        lambda value: cast(list[object], captured["set_visible_calls"]).append(value),
    )

    original_visible_groups = getattr(app_state, "visible_groups", None)
    try:
        setattr(app_state, "visible_groups", {"Z"})

        result = dataframe_helpers.prepare_plot_dataframe("group", "UMAP", embedding)

        assert result is not None
        df_plot, unique_cats = result
        assert sorted(list(df_plot["group"])) == ["A", "B"]
        assert unique_cats == ["A", "B"]
        assert captured["set_visible_calls"] == [None]
    finally:
        setattr(app_state, "visible_groups", original_visible_groups)
