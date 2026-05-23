"""Builtin HDBSCAN clustering plugin."""
from __future__ import annotations
from typing import Any

from plugins.api import BasePlugin, PluginMeta
from data.clustering import is_hdbscan_available, run_hdbscan_clustering


class ClusteringPlugin(BasePlugin):
    meta = PluginMeta(
        name="hdbscan_clustering",
        version="1.0",
        api_version="1.0",
        plugin_type="analysis",
        author="IsotopesAnalyse",
        description="HDBSCAN density-based clustering for outlier detection",
    )

    def validate_environment(self) -> tuple[bool, str]:
        if is_hdbscan_available():
            return True, "ok"
        return False, "hdbscan package not installed"

    def get_default_params(self) -> dict[str, Any]:
        return {"min_cluster_size": 5, "min_samples": None}

    def run(self, df, columns, **kwargs):
        return run_hdbscan_clustering(df, columns, **kwargs)
