"""Backward-compatible re-exports — implementation lives in plugins."""
from __future__ import annotations

from plugins.builtins.clustering_plugin import (
    is_hdbscan_available,
    run_hdbscan_clustering,
)
