"""Builtin neighborhood search plugin — distance-based retrieval in embedding space."""
from __future__ import annotations
import logging
from typing import Any
import numpy as np
import pandas as pd
from plugins.api import BasePlugin, PluginMeta

logger = logging.getLogger(__name__)


def map_local_to_original(local_index: int, orig_indices: np.ndarray | None) -> int:
    """Map a subset-local index back to the original dataframe position.

    When a subset is active, embeddings are sliced with ``embedding[idx_list]``
    so positions inside the slice are local. This helper resolves a local
    position back to the original dataframe row index.

    Args:
        local_index: position inside the sliced (subset) array
        orig_indices: the ``idx_list`` used to slice, or None when no subset

    Returns:
        The original dataframe position; ``local_index`` itself when
        ``orig_indices`` is None or ``local_index`` is out of range.
    """
    if orig_indices is not None and 0 <= local_index < len(orig_indices):
        return int(orig_indices[local_index])
    return int(local_index)


def run_neighborhood_search(
    embedding: np.ndarray,
    group_series: np.ndarray,
    query_group: str,
    radius: float,
    min_neighbors: int = 1,
) -> dict[str, Any]:
    """Find background points within radius of query group points.
    
    Args:
        embedding: (n_samples, n_dims) embedding coordinates
        group_series: (n_samples,) group labels
        query_group: which group to use as query/test set
        radius: search radius in embedding space
        min_neighbors: minimum neighbors to report a point
        
    Returns:
        dict with 'matches', 'query_indices', 'neighbor_counts', 'summary'
    """
    mask_query = group_series == query_group
    query_idx = np.where(mask_query)[0]
    bg_idx = np.where(~mask_query)[0]
    
    if len(query_idx) == 0 or len(bg_idx) == 0:
        return {"error": "Need both query and background points"}
    
    query_emb = embedding[query_idx]
    bg_emb = embedding[bg_idx]
    
    # Compute pairwise distances: (n_query, n_bg)
    # Using efficient broadcasting
    dists = np.sqrt(((query_emb[:, None, :] - bg_emb[None, :, :]) ** 2).sum(axis=2))
    
    # Find matches within radius
    matches = []
    neighbor_counts = []
    for i, qi in enumerate(query_idx):
        within = np.where(dists[i] <= radius)[0]
        if len(within) >= min_neighbors:
            neighbor_counts.append(len(within))
            matches.append({
                "query_index": int(qi),
                "query_label": str(group_series[qi]),
                "neighbor_indices": bg_idx[within].tolist(),
                "neighbor_count": len(within),
                "distances": dists[i][within].tolist(),
            })
        else:
            neighbor_counts.append(0)
    
    avg_neighbors = float(np.mean(neighbor_counts)) if neighbor_counts else 0.0
    median_neighbors = float(np.median(neighbor_counts)) if neighbor_counts else 0.0
    
    return {
        "matches": matches,
        "query_indices": query_idx.tolist(),
        "query_count": len(query_idx),
        "background_count": len(bg_idx),
        "radius": float(radius),
        "avg_neighbors": avg_neighbors,
        "median_neighbors": median_neighbors,
        "total_matches": sum(len(m["neighbor_indices"]) for m in matches),
        "summary": f"{len(query_idx)} query points, {len(bg_idx)} bg. "
                   f"Radius={radius:.3f}, avg neighbors={avg_neighbors:.1f}, "
                   f"median={median_neighbors:.1f}",
    }


class NeighborhoodSearchPlugin(BasePlugin):
    meta = PluginMeta(
        name="neighborhood_search",
        version="1.0",
        api_version="1.0",
        plugin_type="analysis",
        author="IsotopesAnalyse",
        description="Distance-based neighborhood retrieval — find background points within radius of test set points",
        source="builtin",
    )
    
    def validate_environment(self) -> tuple[bool, str]:
        return True, "ok"
    
    def get_default_params(self) -> dict[str, Any]:
        return {"radius": 0.5, "min_neighbors": 1}
    
    def search(self, embedding, group_series, query_group, radius, **kwargs):
        return run_neighborhood_search(embedding, group_series, query_group, radius, **kwargs)
    
    def build_ui(self, parent=None, callback=None):
        from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QLabel, QPushButton
        from PyQt5.QtCore import Qt
        from core import translate
        
        group = QGroupBox(translate("Neighborhood Search"))
        group.setProperty('translate_key', 'Neighborhood Search')
        layout = QVBoxLayout()
        
        hint = QLabel(translate("Select a group as query set, find all other points within a search radius."))
        hint.setProperty('translate_key', 'Select a group as query set, find all other points within a search radius.')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        
        btn = QPushButton(translate("Run Neighborhood Search"))
        btn.setProperty('translate_key', 'Run Neighborhood Search')
        btn.setFixedWidth(200)
        if callback:
            btn.clicked.connect(callback)
        layout.addWidget(btn, 0, Qt.AlignHCenter)
        
        group.setLayout(layout)
        return group
