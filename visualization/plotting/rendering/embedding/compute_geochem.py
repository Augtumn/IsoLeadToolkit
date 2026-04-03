"""Embedding computation helpers for geochemistry workflows."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from core import app_state, state_gateway

from ...core import _get_pb_columns, _get_subset_dataframe
from ...data import _get_analysis_data, _lazy_import_geochemistry
from ..common.state_access import _data_cols

logger = logging.getLogger(__name__)


def compute_v1v2_embedding() -> np.ndarray | None:
    """Compute V1V2 embedding from selected Pb isotope columns."""
    geochemistry, calculate_all_parameters = _lazy_import_geochemistry()
    if calculate_all_parameters is None:
        logger.error('V1V2 module not loaded')
        return None

    x_data, _ = _get_analysis_data()
    if x_data is None:
        return None

    cols = _data_cols()
    col_206 = '206Pb/204Pb' if '206Pb/204Pb' in cols else None
    col_207 = '207Pb/204Pb' if '207Pb/204Pb' in cols else None
    col_208 = '208Pb/204Pb' if '208Pb/204Pb' in cols else None

    if not (col_206 and col_207 and col_208):
        logger.error(
            "Could not identify isotope columns in %s. Please ensure columns '206Pb/204Pb', '207Pb/204Pb', '208Pb/204Pb' are selected.",
            cols,
        )
        return None

    idx_206 = cols.index(col_206)
    idx_207 = cols.index(col_207)
    idx_208 = cols.index(col_208)

    pb206 = x_data[:, idx_206]
    pb207 = x_data[:, idx_207]
    pb208 = x_data[:, idx_208]

    try:
        v1v2_params = state_gateway.get_v1v2_params()
        results = calculate_all_parameters(
            pb206,
            pb207,
            pb208,
            calculate_ages=False,
            a=v1v2_params.get('a'),
            b=v1v2_params.get('b'),
            c=v1v2_params.get('c'),
            scale=v1v2_params.get('scale', 1.0),
        )
        embedding = np.column_stack((results['V1'], results['V2']))
        state_gateway.set_last_embedding(embedding, 'V1V2')
        return embedding
    except Exception as err:
        logger.error('V1V2 calculation failed: %s', err)
        return None


def _resolve_model_age(geochemistry, pb206: np.ndarray, pb207: np.ndarray) -> np.ndarray | None:
    """Resolve model age series for Mu/Kappa charts."""
    t_ma = None
    if getattr(app_state, 'use_real_age_for_mu_kappa', False):
        df_subset, _ = _get_subset_dataframe()
        if df_subset is not None:
            age_col = getattr(app_state, 'mu_kappa_age_col', None)
            if age_col and age_col in df_subset.columns:
                t_ma = pd.to_numeric(df_subset[age_col], errors='coerce').values

    if t_ma is not None:
        return t_ma

    try:
        from data.geochemistry import engine, resolve_age_model

        current_model = getattr(engine, 'current_model_name', '')
        params = engine.get_parameters()
        age_model = resolve_age_model(params, current_model)
        is_geokit = 'Geokit' in current_model
        if age_model == 'two_stage':
            return geochemistry.calculate_two_stage_age(pb206, pb207, params=params)
        if is_geokit:
            return geochemistry.calculate_single_stage_age(
                pb206,
                pb207,
                params=params,
                initial_age=params.get('T1'),
            )
        return geochemistry.calculate_single_stage_age(pb206, pb207, params=params)
    except Exception as age_err:
        logger.warning('Failed to compute model age: %s', age_err)
        return None


def compute_geochem_embedding(actual_algorithm: str) -> np.ndarray | None:
    """Compute embedding for geochemistry-based render modes."""
    geochemistry, _ = _lazy_import_geochemistry()
    if geochemistry is None:
        logger.error('Geochemistry module not loaded')
        return None

    df_subset, _ = _get_subset_dataframe()
    if df_subset is None:
        return None

    col_206, col_207, col_208 = _get_pb_columns(df_subset.columns)
    if not (col_206 and col_207 and col_208):
        logger.error('Geochemistry plots require 206Pb/204Pb, 207Pb/204Pb, 208Pb/204Pb columns.')
        return None

    pb206 = pd.to_numeric(df_subset[col_206], errors='coerce').values
    pb207 = pd.to_numeric(df_subset[col_207], errors='coerce').values
    pb208 = pd.to_numeric(df_subset[col_208], errors='coerce').values

    if actual_algorithm in ('PB_MU_AGE', 'PB_KAPPA_AGE'):
        t_ma = _resolve_model_age(geochemistry, pb206, pb207)
        if t_ma is None:
            return None

        if actual_algorithm == 'PB_MU_AGE':
            embedding = np.column_stack((t_ma, geochemistry.calculate_model_mu(pb206, pb207, t_ma)))
        else:
            embedding = np.column_stack((t_ma, geochemistry.calculate_model_kappa(pb208, pb206, t_ma)))
    else:
        if actual_algorithm in ('PB_EVOL_76', 'PLUMBOTECTONICS_76'):
            embedding = np.column_stack((pb206, pb207))
        else:
            embedding = np.column_stack((pb206, pb208))

    state_gateway.set_last_embedding(embedding, actual_algorithm)
    return embedding
