"""Core embedding helpers and shared utilities."""
from __future__ import annotations

import logging
import itertools
from typing import Any

import numpy as np
import matplotlib.pyplot as plt

from core import CONFIG, app_state, state_gateway
from core.cache import build_embedding_cache_key
from . import data as data_utils
from .data import _lazy_import_ml, _get_analysis_data

logger = logging.getLogger(__name__)

umap = None
Axes3D = None
Ellipse = None
mpltern = None


def _data_state() -> Any:
    return getattr(app_state, 'data', app_state)


def _data_cols() -> list[str]:
    return getattr(_data_state(), 'data_cols', app_state.data_cols)


def _df_global() -> Any:
    return getattr(_data_state(), 'df_global', app_state.df_global)


def _active_subset_indices() -> Any:
    return getattr(_data_state(), 'active_subset_indices', app_state.active_subset_indices)


def _build_subset_key() -> str | int:
    subset_indices = _active_subset_indices()
    if subset_indices is None:
        return 'full'
    return hash(tuple(sorted(list(subset_indices))))


def _lazy_import_umap():
    global umap
    if umap is None:
        import umap as _umap
        umap = _umap

def _lazy_import_mplot3d():
    global Axes3D
    if Axes3D is None:
        from mpl_toolkits.mplot3d import Axes3D as _Axes3D  # noqa: F401
        Axes3D = _Axes3D

def _lazy_import_ellipse():
    global Ellipse
    if Ellipse is None:
        from matplotlib.patches import Ellipse as _Ellipse
        Ellipse = _Ellipse

def _lazy_import_mpltern():
    global mpltern
    if mpltern is None:
        import mpltern as _mpltern
        mpltern = _mpltern

def _ensure_axes(dimensions=2):
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
        _lazy_import_umap()

        subset_key = _build_subset_key()

        key = build_embedding_cache_key(app_state, 'umap', params, subset_key)
        cached = app_state.embedding_cache.get(key)
        if cached is not None:
            return cached

        X, _ = _get_analysis_data()
        if X is None or X.shape[0] == 0:
            logger.error("No data available for UMAP computation")
            return None

        reducer = umap.UMAP(**params)
        embedding = reducer.fit_transform(X)
        app_state.embedding_cache.set(key, embedding)
        state_gateway.set_attrs({'last_embedding': embedding, 'last_embedding_type': 'UMAP'})
        return embedding

    except Exception as e:
        logger.exception("UMAP computation failed: %s", e)
        return None

def get_tsne_embedding(params: dict) -> np.ndarray | None:
    """Get or compute t-SNE embedding with caching."""
    try:
        _lazy_import_ml()

        subset_key = _build_subset_key()

        key = build_embedding_cache_key(app_state, 'tsne', params, subset_key)
        cached = app_state.embedding_cache.get(key)
        if cached is not None:
            return cached

        X, _ = _get_analysis_data()
        if X is None or X.shape[0] == 0:
            logger.error("No data available for t-SNE computation")
            return None

        n_samples = X.shape[0]
        perplexity = float(params.get('perplexity', 30))
        if n_samples <= 1:
            logger.error("Not enough samples for t-SNE")
            return None
        if perplexity >= n_samples:
            perplexity = max(2, n_samples - 1)

        learning_rate = max(float(params.get('learning_rate', 200)), 10)

        reducer = data_utils.TSNE(
            n_components=params.get('n_components', 2),
            perplexity=perplexity,
            learning_rate=learning_rate,
            random_state=params.get('random_state', 42),
            verbose=0,
            n_jobs=-1
        )

        embedding = reducer.fit_transform(X)
        app_state.embedding_cache.set(key, embedding)
        state_gateway.set_attrs({'last_embedding': embedding, 'last_embedding_type': 'tSNE'})
        return embedding

    except Exception as e:
        logger.exception("t-SNE computation failed: %s", e)
        return None

def get_pca_embedding(params: dict) -> np.ndarray | None:
    """Get or compute PCA embedding with caching."""
    try:
        _lazy_import_ml()
        subset_key = _build_subset_key()

        key = build_embedding_cache_key(app_state, 'pca', params, subset_key)
        cached = app_state.embedding_cache.get(key)
        if cached is not None:
            return cached

        X, _ = _get_analysis_data()
        if X is None or X.shape[0] == 0:
            logger.error("No data available for PCA computation")
            return None

        scaler = data_utils.StandardScaler()
        try:
            X_scaled = scaler.fit_transform(X)
            if np.isnan(X_scaled).any():
                X_scaled = np.nan_to_num(X_scaled)
        except Exception:
            X_scaled = X

        reducer = data_utils.PCA(
            n_components=params.get('n_components', 2),
            random_state=params.get('random_state', 42)
        )

        embedding = reducer.fit_transform(X_scaled)
        state_gateway.set_pca_diagnostics(
            last_pca_variance=reducer.explained_variance_ratio_,
            last_pca_components=reducer.components_,
            current_feature_names=_data_cols(),
        )

        app_state.embedding_cache.set(key, embedding)
        state_gateway.set_attrs({'last_embedding': embedding, 'last_embedding_type': 'PCA'})
        return embedding

    except Exception as e:
        logger.exception("PCA computation failed: %s", e)
        return None

def get_robust_pca_embedding(params: dict) -> np.ndarray | None:
    """Get or compute Robust PCA (via MinCovDet) embedding with caching."""
    try:
        _lazy_import_ml()

        subset_key = _build_subset_key()

        key = build_embedding_cache_key(app_state, 'robust_pca', params, subset_key)
        cached = app_state.embedding_cache.get(key)
        if cached is not None:
            return cached

        X, _ = _get_analysis_data()
        if X is None or X.shape[0] == 0:
            logger.error("No data available for Robust PCA computation")
            return None

        scaler = data_utils.StandardScaler()
        try:
            X_scaled = scaler.fit_transform(X)
            if np.isnan(X_scaled).any():
                X_scaled = np.nan_to_num(X_scaled)
        except Exception:
            X_scaled = X

        if X_scaled.shape[0] <= X_scaled.shape[1]:
            reducer = data_utils.PCA(
                n_components=params.get('n_components', 2),
                random_state=params.get('random_state', 42)
            )
            embedding = reducer.fit_transform(X_scaled)
            state_gateway.set_attrs(
                {
                    'last_pca_variance': reducer.explained_variance_ratio_,
                    'last_pca_components': reducer.components_,
                }
            )
        else:
            support_fraction = params.get('support_fraction', 0.75)
            mcd = data_utils.MinCovDet(random_state=params.get('random_state', 42), support_fraction=support_fraction)
            mcd.fit(X_scaled)
            cov = mcd.covariance_
            mean = mcd.location_
            eigvals, eigvecs = np.linalg.eigh(cov)
            order = np.argsort(eigvals)[::-1]
            eigvecs = eigvecs[:, order]
            eigvals = eigvals[order]
            n_components = params.get('n_components', 2)
            components = eigvecs[:, :n_components]
            embedding = (X_scaled - mean) @ components
            if eigvals.sum() > 0:
                state_gateway.set_pca_diagnostics(last_pca_variance=eigvals[:n_components] / eigvals.sum())
            state_gateway.set_pca_diagnostics(last_pca_components=components.T)

        state_gateway.set_pca_diagnostics(current_feature_names=_data_cols())
        app_state.embedding_cache.set(key, embedding)
        state_gateway.set_attrs({'last_embedding': embedding, 'last_embedding_type': 'RobustPCA'})
        return embedding

    except Exception as e:
        logger.exception("Robust PCA computation failed: %s", e)
        return None

def get_embedding(
    algorithm: str,
    umap_params: dict | None = None,
    tsne_params: dict | None = None,
    pca_params: dict | None = None,
    robust_pca_params: dict | None = None,
) -> np.ndarray | None:
    """Get embedding based on selected algorithm"""
    if algorithm == 'UMAP':
        return get_umap_embedding(umap_params or CONFIG['umap_params'])
    elif algorithm == 'tSNE':
        return get_tsne_embedding(tsne_params or CONFIG['tsne_params'])
    elif algorithm == 'PCA':
        return get_pca_embedding(pca_params or CONFIG.get('pca_params', {'n_components': 2, 'random_state': 42}))
    elif algorithm == 'RobustPCA':
        return get_robust_pca_embedding(robust_pca_params or CONFIG.get('robust_pca_params', {'n_components': 2, 'random_state': 42}))
    else:
        logger.error("Unknown algorithm: %s", algorithm)
        return None

def _build_group_palette(unique_cats):
    """Build or reuse a stable group -> color mapping."""
    if not hasattr(app_state, 'current_palette'):
        state_gateway.set_current_palette({})

    prop_cycle = plt.rcParams.get('axes.prop_cycle', None)
    cycle_colors = []
    if prop_cycle is not None:
        try:
            cycle_colors = prop_cycle.by_key().get('color', [])
        except Exception:
            cycle_colors = []

    color_cycle = itertools.cycle(cycle_colors if cycle_colors else ['#333333'])

    for cat in unique_cats:
        if cat not in app_state.current_palette or not app_state.current_palette.get(cat):
            app_state.current_palette[cat] = next(color_cycle)

    return {cat: app_state.current_palette[cat] for cat in unique_cats}

def _get_subset_dataframe():
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

def _get_pb_columns(columns):
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

def _find_age_column(columns):
    """Find an age column for Mu/Kappa plots."""
    candidates = [
        "Age (Ma)",
        "Age(Ma)",
        "Age_Ma",
        "Age",
        "age",
        "t_ma",
        "t"
    ]
    for name in candidates:
        if name in columns:
            return name
    for col in columns:
        low = str(col).lower()
        if "age" in low:
            return col
    return None



