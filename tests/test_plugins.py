"""Plugin manager, plugin behaviour and data-mixing tests."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import plugins.manager as manager_module
from plugins.api import PluginLoadError
from plugins.builtins.mixing_plugin import MixingModelPlugin
from plugins.builtins.neighborhood_plugin import (
    map_local_to_original,
    run_neighborhood_search,
)
from plugins.manager import PluginManager


_PLUGIN_SOURCE = '''
"""Temp user plugin used by tests."""
from typing import Any

from plugins.api import BasePlugin, PluginMeta


class TempPlugin(BasePlugin):
    meta = PluginMeta(
        name="temp_user_plugin",
        version="0.1",
        api_version="1.0",
        plugin_type="analysis",
        source="user",
    )

    def validate_environment(self) -> tuple[bool, str]:
        return True, "ok"

    def get_default_params(self) -> dict[str, Any]:
        return {"k": 1}

    def build_ui(self, parent=None, callback=None):
        return None
'''

_BUILTIN_STEMS = {
    "clustering_plugin",
    "endmember_plugin",
    "mixing_plugin",
    "neighborhood_plugin",
    "provenance_ml_plugin",
    "subset_plugin",
}


def test_discover_finds_builtins() -> None:
    names = PluginManager().discover()
    assert _BUILTIN_STEMS <= set(names)
    assert "__init__" not in names


def test_load_builtin_plugin_and_registry() -> None:
    manager = PluginManager()
    plugin = manager.load_plugin("subset_plugin")

    assert manager.is_loaded("subset_plugin") is True
    assert manager.get("subset_plugin") is plugin
    assert manager.get("subset_analysis") is plugin  # meta.name lookup
    assert manager.get_meta("subset_plugin").plugin_type == "analysis"

    status = manager.get_status()
    assert status["loaded"]["subset_plugin"]["source"] == "builtin"

    assert manager.unload_plugin("subset_plugin") is True
    assert manager.is_loaded("subset_plugin") is False
    assert manager.unload_plugin("subset_plugin") is False


def test_reload_plugin_returns_fresh_instance() -> None:
    manager = PluginManager()
    first = manager.load_plugin("subset_plugin")
    second = manager.reload_plugin("subset_plugin")
    assert second is not first
    assert manager.is_loaded("subset_plugin") is True


def test_unknown_plugin_raises() -> None:
    manager = PluginManager()
    with pytest.raises(PluginLoadError, match="not found"):
        manager.load_plugin("does_not_exist_plugin")
    assert manager.available == []


@pytest.mark.parametrize("name", sorted(PluginManager.RESERVED_NAMES))
def test_reserved_names_rejected(name: str) -> None:
    manager = PluginManager()
    with pytest.raises(PluginLoadError, match="reserved"):
        manager.load_plugin(name)
    assert manager.is_loaded(name) is False


def test_user_plugin_loaded_under_private_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "temp_user_plugin.py").write_text(_PLUGIN_SOURCE, encoding="utf-8")
    monkeypatch.setattr(manager_module, "_USER_PLUGIN_DIR", tmp_path)

    import plugins.api as real_api

    manager = PluginManager()
    try:
        plugin = manager.load_plugin("temp_user_plugin")
        assert plugin.meta.source == "user"
        assert plugin.get_default_params() == {"k": 1}
        # Namespaced module name keeps the real plugins.* modules intact.
        assert "plugins._loaded.temp_user_plugin" in sys.modules
        assert "plugins.temp_user_plugin" not in sys.modules
        assert sys.modules["plugins.api"] is real_api
    finally:
        sys.modules.pop("plugins._loaded.temp_user_plugin", None)


def test_user_file_named_api_cannot_shadow_real_module(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "api.py").write_text(
        "raise RuntimeError('must never be imported')", encoding="utf-8"
    )
    monkeypatch.setattr(manager_module, "_USER_PLUGIN_DIR", tmp_path)

    import plugins.api as real_api

    manager = PluginManager()
    with pytest.raises(PluginLoadError, match="reserved"):
        manager.load_plugin("api")
    assert sys.modules["plugins.api"] is real_api


def test_load_all_skips_reserved_and_broken_plugins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "api.py").write_text(
        "raise RuntimeError('must never be imported')", encoding="utf-8"
    )
    (tmp_path / "broken_plugin.py").write_text(
        "raise RuntimeError('boom')", encoding="utf-8"
    )
    monkeypatch.setattr(manager_module, "_USER_PLUGIN_DIR", tmp_path)

    manager = PluginManager()
    loaded = manager.load_all()
    assert "api" not in loaded
    assert "broken_plugin" not in loaded
    assert "boom" in (manager.failure_info("broken_plugin") or "")
    # Builtins are discovered and loaded alongside user plugins. Optional
    # dependencies (hdbscan) may be absent, so only assert dependency-free
    # builtins actually loaded.
    assert _BUILTIN_STEMS <= set(manager.discover())
    assert "subset_plugin" in loaded
    assert set(loaded) <= set(manager.discover())


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


calculate_mixing = MixingModelPlugin().calculate


def test_calculate_mixing_recovers_simple_two_endmember_weights() -> None:
    df = pd.DataFrame(
        {
            "Pb206_204": [0.0, 10.0, 2.0],
            "Pb207_204": [0.0, 10.0, 2.0],
        }
    )
    endmember_groups = {"EM_A": [0], "EM_B": [1]}
    mixture_groups = {"MX": [2]}

    results = calculate_mixing(
        df=df,
        endmember_groups=endmember_groups,
        mixture_groups=mixture_groups,
        columns=["Pb206_204", "Pb207_204"],
    )

    assert len(results) == 2
    weights = {item["endmember"]: item["weight"] for item in results}
    assert weights["EM_A"] == pytest.approx(0.8, rel=0.0, abs=1e-6)
    assert weights["EM_B"] == pytest.approx(0.2, rel=0.0, abs=1e-6)
    assert sum(weights.values()) == pytest.approx(1.0, rel=0.0, abs=1e-6)
    assert all(item["rmse"] == pytest.approx(0.0, rel=0.0, abs=1e-6) for item in results)


def test_calculate_mixing_raises_for_empty_endmember_group() -> None:
    df = pd.DataFrame({"x": [1.0], "y": [2.0]})

    with pytest.raises(ValueError, match="Endmember group 'EM_A' is empty"):
        calculate_mixing(
            df=df,
            endmember_groups={"EM_A": []},
            mixture_groups={"MX": [0]},
            columns=["x", "y"],
        )
