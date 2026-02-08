"""Shared data helpers for plotting."""
import numpy as np
from core.state import app_state
from core.config import CONFIG

TSNE = None
PCA = None
MinCovDet = None
StandardScaler = None
SimpleImputer = None


def _lazy_import_ml():
    global TSNE, PCA, MinCovDet, StandardScaler, SimpleImputer
    if PCA is None:
        from sklearn.decomposition import PCA as _PCA
        PCA = _PCA
    if TSNE is None:
        from sklearn.manifold import TSNE as _TSNE
        TSNE = _TSNE
    if MinCovDet is None:
        from sklearn.covariance import MinCovDet as _MinCovDet
        MinCovDet = _MinCovDet
    if StandardScaler is None:
        from sklearn.preprocessing import StandardScaler as _StandardScaler
        StandardScaler = _StandardScaler
    if SimpleImputer is None:
        from sklearn.impute import SimpleImputer as _SimpleImputer
        SimpleImputer = _SimpleImputer


def _get_analysis_data():
    """Helper to get the data subset for analysis (all or selected)."""
    if app_state.active_subset_indices is not None:
        indices = sorted(list(app_state.active_subset_indices))
        if not indices:
            return None, None
        X = app_state.df_global.iloc[indices][app_state.data_cols].values
    else:
        X = app_state.df_global[app_state.data_cols].values
        indices = list(range(len(app_state.df_global)))

    try:
        X = X.astype(float)
    except ValueError as e:
        print(f"[ERROR] Data contains non-numeric values: {e}", flush=True)
        return None, None

    if np.isnan(X).any():
        print("[WARN] Missing values detected in data. Imputing with 0.", flush=True)
        try:
            _lazy_import_ml()
            imputer = SimpleImputer(strategy='constant', fill_value=0)
            X = imputer.fit_transform(X)
        except Exception as e:
            print(f"[ERROR] Imputation failed: {e}. Dropping incomplete rows as fallback.", flush=True)
            mask = ~np.isnan(X).any(axis=1)
            X = X[mask]
            indices = [indices[i] for i in range(len(indices)) if mask[i]]

    return X, indices
