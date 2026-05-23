"""Builtin HDBSCAN clustering plugin."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from plugins.api import BasePlugin, PluginMeta

logger = logging.getLogger(__name__)

_HDBSCAN = None
_HDBSCAN_CHECKED = False


def _lazy_import_hdbscan() -> Any:
    """Lazy import HDBSCAN; returns class or None if unavailable."""
    global _HDBSCAN, _HDBSCAN_CHECKED
    if _HDBSCAN_CHECKED:
        return _HDBSCAN
    _HDBSCAN_CHECKED = True
    try:
        from hdbscan import HDBSCAN as _HDBSCANCls
        _HDBSCAN = _HDBSCANCls
    except ImportError as err:
        logger.warning("hdbscan not available: %s", err)
        _HDBSCAN = None
    return _HDBSCAN


def is_hdbscan_available() -> bool:
    """Return True if hdbscan can be imported."""
    return _lazy_import_hdbscan() is not None


def run_hdbscan_clustering(
    embedding: np.ndarray,
    min_cluster_size: int = 5,
    min_samples: int | None = None,
    cluster_selection_epsilon: float = 0.0,
    metric: str = "euclidean",
    alpha: float = 1.0,
) -> dict[str, Any] | None:
    """Run HDBSCAN clustering on an embedding array.

    Args:
        embedding: (n_samples, n_dims) array from UMAP, t-SNE, PCA, etc.
        min_cluster_size: Minimum number of points to form a cluster.
        min_samples: Number of points in a neighbourhood for core points.
            Defaults to *min_cluster_size* when None.
        cluster_selection_epsilon: Distance threshold to merge micro-clusters
            during cluster extraction.  Larger values produce fewer clusters.
        metric: Distance metric (euclidean, manhattan, cosine, ...).
        alpha: Clustering smoothness (1.0 = default).

    Returns:
        dict with keys *labels*, *probabilities*, *n_clusters*,
        *n_noise*, *cluster_sizes*, or None on failure.
    """
    HDBSCAN = _lazy_import_hdbscan()
    if HDBSCAN is None:
        logger.warning("HDBSCAN is not installed.")
        return None

    data = np.asarray(embedding, dtype=float)
    if data.ndim != 2 or data.shape[0] < 2:
        logger.warning("Invalid embedding shape for clustering: %s", data.shape)
        return None

    try:
        clusterer = HDBSCAN(
            min_cluster_size=max(2, int(min_cluster_size)),
            min_samples=(
                max(1, int(min_samples))
                if min_samples is not None
                else max(2, int(min_cluster_size))
            ),
            cluster_selection_epsilon=float(cluster_selection_epsilon),
            metric=str(metric),
            alpha=float(alpha),
            core_dist_n_jobs=1,
        )
        labels = clusterer.fit_predict(data)
        probs = clusterer.probabilities_

        unique, counts = np.unique(labels, return_counts=True)
        n_noise = int(np.sum(labels == -1))
        cluster_ids = unique[unique >= 0]

        logger.info(
            "HDBSCAN: n_samples=%d, n_clusters=%d, n_noise=%d",
            data.shape[0], len(cluster_ids), n_noise,
        )

        return {
            "labels": labels.tolist(),
            "probabilities": probs.tolist(),
            "n_clusters": int(len(cluster_ids)),
            "n_noise": n_noise,
            "cluster_sizes": {
                int(cid): int(counts[i])
                for i, cid in enumerate(unique)
                if cid >= 0
            },
        }
    except Exception as err:
        logger.exception("HDBSCAN clustering failed: %s", err)
        return None


class ClusteringPlugin(BasePlugin):
    meta = PluginMeta(
        name="hdbscan_clustering",
        version="1.0",
        api_version="1.0",
        plugin_type="analysis",
        author="IsotopesAnalyse",
        description="HDBSCAN density-based clustering for outlier detection",
        source="builtin",
    )

    def validate_environment(self) -> tuple[bool, str]:
        if is_hdbscan_available():
            return True, "ok"
        return False, "hdbscan package not installed"

    def get_default_params(self) -> dict[str, Any]:
        return {"min_cluster_size": 5, "min_samples": None}

    def build_ui(self, parent=None, callback=None):
        """Return the HDBSCAN Clustering QGroupBox section."""
        from PyQt5.QtCore import Qt
        from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QPushButton
        from core import translate

        group = QGroupBox(translate("HDBSCAN Clustering"))
        group.setProperty('translate_key', 'HDBSCAN Clustering')
        layout = QVBoxLayout()

        hint = QLabel(
            translate("Cluster the current embedding (UMAP, t-SNE, PCA, etc.) using HDBSCAN.")
        )
        hint.setProperty(
            'translate_key',
            'Cluster the current embedding (UMAP, t-SNE, PCA, etc.) using HDBSCAN.',
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        btn = QPushButton(translate("Run HDBSCAN Clustering"))
        btn.setProperty('translate_key', 'Run HDBSCAN Clustering')
        btn.setFixedWidth(200)
        if callback is not None:
            btn.clicked.connect(callback)
        layout.addWidget(btn, 0, Qt.AlignHCenter)

        group.setLayout(layout)
        return group

    def run(self, *args, **kwargs):
        return run_hdbscan_clustering(*args, **kwargs)
