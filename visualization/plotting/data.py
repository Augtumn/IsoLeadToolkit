"""Shared data helpers and lazy imports for plotting."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from core import app_state

logger = logging.getLogger(__name__)

TSNE = None
PCA = None
MinCovDet = None
StandardScaler = None
SimpleImputer = None

_geochemistry = None
_calculate_all_parameters = None
_geochem_checked = False


def _lazy_import_ml() -> None:
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


def _lazy_import_geochemistry() -> tuple[Any | None, Any | None]:
    """Lazy-load the geochemistry module. Returns (module, calculate_all_parameters)."""
    global _geochemistry, _calculate_all_parameters, _geochem_checked
    if _geochem_checked:
        return _geochemistry, _calculate_all_parameters
    _geochem_checked = True
    try:
        from data import geochemistry as _geochemistry_mod
        from data.geochemistry import calculate_all_parameters as _calc
    except ImportError as err:
        logger.warning(
            "Geochemistry module not found. V1V2 algorithm will not be available: %s",
            err,
        )
        _geochemistry = None
        _calculate_all_parameters = None
    else:
        _geochemistry = _geochemistry_mod
        _calculate_all_parameters = _calc
    return _geochemistry, _calculate_all_parameters


def _get_analysis_data() -> tuple[np.ndarray | None, list[int] | None]:
    """Helper to get the data subset for analysis (all or selected)."""
    subset_indices = _active_subset_indices()
    data_cols = _data_cols()
    df_global = _df_global()

    if df_global is None or df_global.empty:
        logger.warning("No source dataframe available for analysis data")
        return None, None

    if not data_cols:
        logger.warning("No numeric columns selected for analysis")
        return None, None

    missing = [col for col in data_cols if col not in df_global.columns]
    if missing:
        logger.warning("Missing analysis columns: %s", missing)
        return None, None

    if subset_indices is not None:
        indices = sorted(list(subset_indices))
        if not indices:
            return None, None
        X = df_global.iloc[indices][data_cols].values
    else:
        X = df_global[data_cols].values
        indices = list(range(len(df_global)))

    try:
        X = pd.to_numeric(pd.DataFrame(X).stack(), errors='coerce').unstack().values
    except Exception as e:
        logger.error("Data contains non-numeric values: %s", e)
        return None, None

    if np.isnan(X).any():
        logger.warning("Missing values detected in data. Imputing with 0.")
        try:
            _lazy_import_ml()
            imputer = SimpleImputer(strategy='constant', fill_value=0)
            X = imputer.fit_transform(X)
        except Exception as e:
            logger.error("Imputation failed: %s. Dropping incomplete rows as fallback.", e)
            mask = ~np.isnan(X).any(axis=1)
            X = X[mask]
            indices = [indices[i] for i in range(len(indices)) if mask[i]]

    return X, indices


# NOTE: this import deliberately lives at the end of the module. Importing
# ``rendering.common.state_access`` triggers ``rendering/common/__init__.py``,
# which transitively pulls in ``geochem/model_overlays.py``; that module
# re-imports names from this one (``plotting.data``), so the import must run
# only after every definition above already exists to avoid a
# partially-initialized-module lookup failure.
from .rendering.common.state_access import (
    _active_subset_indices,
    _data_cols,
    _df_global,
)

