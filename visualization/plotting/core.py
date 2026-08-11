"""Core embedding helpers and shared utilities."""
from __future__ import annotations

import logging
import itertools
from typing import Any

import numpy as np
import matplotlib.pyplot as plt

from core import CONFIG, app_state, state_gateway
from core.cache import build_embedding_cache_key
from .data import _lazy_import_ml, _get_analysis_data
from .rendering.common.state_access import (
    _active_subset_indices,
    _data_cols,
    _df_global,
)

logger = logging.getLogger(__name__)

Axes3D = None
mpltern = None


def _build_subset_key() -> str | int:
    subset_indices = _active_subset_indices()
    if subset_indices is None:
        return 'full'
    return hash(tuple(sorted(list(subset_indices))))


def _lazy_import_mplot3d() -> None:
    global Axes3D
    if Axes3D is None:
        from mpl_toolkits.mplot3d import Axes3D as _Axes3D  # noqa: F401
        Axes3D = _Axes3D

def _lazy_import_mpltern() -> None:
    global mpltern
    if mpltern is None:
        import mpltern as _mpltern
        mpltern = _mpltern

def _ensure_axes(dimensions: int | str = 2) -> Any | None:
    """Ensure the figure has the correct axes dimensionality."""
    if app_state.fig is None:
        return None

    current_name = getattr(app_state.ax, 'name', '') if app_state.ax is not None else ''

    if dimensions == 3:
        _lazy_import_mplot3d()
        if app_state.ax is None or current_name != '3d':
            try:
                app_state.fig.clf()
            except Exception:
                pass
            state_gateway.set_axis(app_state.fig.add_subplot(111, projection='3d'))
    elif dimensions == 'ternary':
        _lazy_import_mpltern()
        if app_state.ax is None or current_name != 'ternary':
            try:
                app_state.fig.clf()
            except Exception:
                pass
            state_gateway.set_axis(app_state.fig.add_subplot(111, projection='ternary'))
    else:
        if app_state.ax is None or current_name in ('3d', 'ternary'):
            try:
                app_state.fig.clf()
            except Exception:
                pass
            state_gateway.set_axis(app_state.fig.add_subplot(111))
    state_gateway.set_legend_ax(None)

    return app_state.ax


def get_umap_embedding(params: dict) -> np.ndarray | None:
    """Get or compute UMAP embedding with caching."""
    try:
        from .rendering.embedding.compute_algorithms import compute_umap_embedding

        subset_key = _build_subset_key()

        key = build_embedding_cache_key(app_state, 'umap', params, subset_key)
        cached = app_state.embedding_cache.get(key)
        if cached is not None:
            return cached

        X, _ = _get_analysis_data()
        if X is None or X.shape[0] == 0:
            logger.error("No data available for UMAP computation")
            return None

        embedding = compute_umap_embedding(X, params)
        if embedding is None:
            logger.error("UMAP computation failed")
            return None

        app_state.embedding_cache.set(key, embedding)
        state_gateway.set_last_embedding(embedding, 'UMAP')
        return embedding

    except Exception as e:
        logger.exception("UMAP computation failed: %s", e)
        return None

def get_tsne_embedding(params: dict) -> np.ndarray | None:
    """Get or compute t-SNE embedding with caching."""
    try:
        from .rendering.embedding.compute_algorithms import compute_tsne_embedding

        subset_key = _build_subset_key()

        key = build_embedding_cache_key(app_state, 'tsne', params, subset_key)
        cached = app_state.embedding_cache.get(key)
        if cached is not None:
            return cached

        X, _ = _get_analysis_data()
        if X is None or X.shape[0] == 0:
            logger.error("No data available for t-SNE computation")
            return None

        embedding = compute_tsne_embedding(X, params)
        if embedding is None:
            logger.error("t-SNE computation failed")
            return None

        app_state.embedding_cache.set(key, embedding)
        state_gateway.set_last_embedding(embedding, 'tSNE')
        return embedding

    except Exception as e:
        logger.exception("t-SNE computation failed: %s", e)
        return None

def get_pca_embedding(params: dict) -> np.ndarray | None:
    """Get or compute PCA embedding with caching."""
    try:
        from .rendering.embedding.compute_algorithms import compute_pca_embedding

        subset_key = _build_subset_key()

        key = build_embedding_cache_key(app_state, 'pca', params, subset_key)
        cached = app_state.embedding_cache.get(key)
        if cached is not None:
            return cached

        X, _ = _get_analysis_data()
        if X is None or X.shape[0] == 0:
            logger.error("No data available for PCA computation")
            return None

        result = compute_pca_embedding(X, params)
        if result is None:
            logger.error("PCA computation failed")
            return None

        embedding = result["embedding"]
        diagnostics: dict[str, Any] = {
            "last_pca_components": result.get("components"),
            "current_feature_names": _data_cols(),
        }
        variance = result.get("variance")
        if variance is not None:
            diagnostics["last_pca_variance"] = variance
        state_gateway.set_pca_diagnostics(**diagnostics)

        app_state.embedding_cache.set(key, embedding)
        state_gateway.set_last_embedding(embedding, 'PCA')
        return embedding

    except Exception as e:
        logger.exception("PCA computation failed: %s", e)
        return None

def get_robust_pca_embedding(params: dict) -> np.ndarray | None:
    """Get or compute Robust PCA (via MinCovDet) embedding with caching."""
    try:
        from .rendering.embedding.compute_algorithms import compute_robust_pca_embedding

        subset_key = _build_subset_key()

        key = build_embedding_cache_key(app_state, 'robust_pca', params, subset_key)
        cached = app_state.embedding_cache.get(key)
        if cached is not None:
            return cached

        X, _ = _get_analysis_data()
        if X is None or X.shape[0] == 0:
            logger.error("No data available for Robust PCA computation")
            return None

        result = compute_robust_pca_embedding(X, params)
        if result is None:
            logger.error("Robust PCA computation failed")
            return None

        embedding = result["embedding"]
        diagnostics: dict[str, Any] = {
            "last_pca_components": result.get("components"),
            "current_feature_names": _data_cols(),
        }
        variance = result.get("variance")
        if variance is not None:
            diagnostics["last_pca_variance"] = variance
        state_gateway.set_pca_diagnostics(**diagnostics)

        app_state.embedding_cache.set(key, embedding)
        state_gateway.set_last_embedding(embedding, 'RobustPCA')
        return embedding

    except Exception as e:
        logger.exception("Robust PCA computation failed: %s", e)
        return None

def _build_group_palette(unique_cats: list[Any]) -> dict[Any, str]:
    """Build or reuse a stable group -> color mapping."""
    palette = dict(getattr(app_state, 'current_palette', {}) or {})

    prop_cycle = plt.rcParams.get('axes.prop_cycle', None)
    cycle_colors = []
    if prop_cycle is not None:
        try:
            cycle_colors = prop_cycle.by_key().get('color', [])
        except Exception:
            cycle_colors = []

    color_cycle = itertools.cycle(cycle_colors if cycle_colors else ['#333333'])
    changed = False

    for cat in unique_cats:
        if cat not in palette or not palette.get(cat):
            palette[cat] = next(color_cycle)
            changed = True

    # Keep StateStore snapshot and runtime palette in sync.
    if changed or not isinstance(getattr(app_state, 'current_palette', None), dict):
        state_gateway.set_current_palette(palette)

    return {cat: palette.get(cat, '#333333') for cat in unique_cats}

def _get_subset_dataframe() -> tuple[Any | None, list[int] | None]:
    """Return the active subset of the dataframe and its indices."""
    df_global = _df_global()
    subset_indices = _active_subset_indices()

    if df_global is None:
        return None, None

    if subset_indices is not None:
        indices = sorted(list(subset_indices))
        if not indices:
            return None, None
        return df_global.iloc[indices].copy(), indices

    return df_global.copy(), list(range(len(df_global)))

def _get_pb_columns(columns: list[str]) -> tuple[str | None, str | None, str | None]:
    """Find Pb isotope ratio columns with a best-effort heuristic."""
    col_206 = "206Pb/204Pb" if "206Pb/204Pb" in columns else None
    col_207 = "207Pb/204Pb" if "207Pb/204Pb" in columns else None
    col_208 = "208Pb/204Pb" if "208Pb/204Pb" in columns else None

    if col_206 and col_207 and col_208:
        return col_206, col_207, col_208

    for col in columns:
        low = str(col).lower()
        if col_206 is None and "206" in low and "204" in low:
            col_206 = col
        if col_207 is None and "207" in low and "204" in low:
            col_207 = col
        if col_208 is None and "208" in low and "204" in low:
            col_208 = col

    return col_206, col_207, col_208



