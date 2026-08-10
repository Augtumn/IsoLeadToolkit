"""Tests for the neighborhood search builtin plugin."""

from __future__ import annotations

import numpy as np

from plugins.builtins.neighborhood_plugin import (
    map_local_to_original,
    run_neighborhood_search,
)


def _make_dataset() -> tuple[np.ndarray, np.ndarray]:
    """2D embedding with two tight clusters: 'A' (query) and 'B' (bg)."""
    rng = np.random.default_rng(42)
    query = rng.normal(0.0, 0.1, size=(4, 2))
    bg = rng.normal(5.0, 0.1, size=(6, 2))
    emb = np.vstack([query, bg])
    groups = np.array(["A"] * 4 + ["B"] * 6)
    return emb, groups


def test_search_basic_matching() -> None:
    emb, groups = _make_dataset()
    # Radius 0.5: clusters 5 units apart, nothing within radius
    result = run_neighborhood_search(emb, groups, "A", radius=0.5)
    assert result["query_count"] == 4
    assert result["background_count"] == 6
    assert result["matches"] == []
    assert result["total_matches"] == 0


def test_search_large_radius_matches_everything() -> None:
    emb, groups = _make_dataset()
    result = run_neighborhood_search(emb, groups, "A", radius=10.0)
    # Every query point finds all 6 background points
    assert len(result["matches"]) == 4
    assert result["total_matches"] == 4 * 6
    assert all(m["neighbor_count"] == 6 for m in result["matches"])
    assert result["avg_neighbors"] == 6.0


def test_search_radius_includes_boundary_exactly() -> None:
    # Two points exactly radius apart must be matched (<= radius)
    emb = np.array([[0.0, 0.0], [1.0, 0.0], [10.0, 10.0]])
    groups = np.array(["Q", "B", "B"])
    result = run_neighborhood_search(emb, groups, "Q", radius=1.0)
    assert result["total_matches"] == 1
    assert result["matches"][0]["neighbor_indices"] == [1]


def test_search_radius_exclusive_just_outside() -> None:
    emb = np.array([[0.0, 0.0], [1.001, 0.0]])
    groups = np.array(["Q", "B"])
    result = run_neighborhood_search(emb, groups, "Q", radius=1.0)
    assert result["total_matches"] == 0


def test_search_min_neighbors_filters() -> None:
    emb = np.array([[0.0, 0.0], [1.0, 0.0], [0.8, 0.0], [10.0, 10.0]])
    groups = np.array(["Q", "B", "B", "B"])
    # Query point has 2 bg points within radius 1.0
    result = run_neighborhood_search(emb, groups, "Q", radius=1.0, min_neighbors=2)
    assert len(result["matches"]) == 1
    assert result["matches"][0]["neighbor_count"] == 2
    # With min_neighbors=3 the query point is dropped
    result2 = run_neighborhood_search(emb, groups, "Q", radius=1.0, min_neighbors=3)
    assert result2["matches"] == []


def test_search_requires_both_groups() -> None:
    emb = np.array([[0.0, 0.0], [1.0, 0.0]])
    groups = np.array(["A", "A"])
    result = run_neighborhood_search(emb, groups, "A", radius=1.0)
    assert "error" in result
    assert "query and background" in result["error"]

    groups2 = np.array(["A", "B"])
    result2 = run_neighborhood_search(emb, groups2, "C", radius=1.0)
    assert "error" in result2


def test_search_summary_fields() -> None:
    emb = np.array([[0.0, 0.0], [0.2, 0.0], [0.5, 0.0]])
    groups = np.array(["Q", "Q", "B"])
    result = run_neighborhood_search(emb, groups, "Q", radius=1.0)
    assert result["radius"] == 1.0
    assert result["avg_neighbors"] == 1.0
    assert result["median_neighbors"] == 1.0
    assert result["query_indices"] == [0, 1]
    assert "summary" in result
    assert "query points" in result["summary"]


def test_map_local_to_original_with_subset() -> None:
    # Subset sliced embedding from original df of 10 rows, keeping [2, 5, 7]
    orig_indices = np.array([2, 5, 7])
    assert map_local_to_original(0, orig_indices) == 2
    assert map_local_to_original(1, orig_indices) == 5
    assert map_local_to_original(2, orig_indices) == 7


def test_map_local_to_original_without_subset() -> None:
    assert map_local_to_original(3, None) == 3
    assert map_local_to_original(0, None) == 0


def test_map_local_to_original_out_of_range() -> None:
    orig_indices = np.array([2, 5, 7])
    assert map_local_to_original(99, orig_indices) == 99
    assert map_local_to_original(-1, orig_indices) == -1
