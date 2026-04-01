"""Algorithm normalization and embedding computation helpers."""
from __future__ import annotations

import logging
import traceback

import numpy as np
import pandas as pd

from core import CONFIG, app_state, state_gateway
from ..core import _get_pb_columns, _get_subset_dataframe, get_pca_embedding, get_robust_pca_embedding, get_tsne_embedding, get_umap_embedding
from ..data import _get_analysis_data, _lazy_import_geochemistry
from .helpers import _data_cols, _df_global

logger = logging.getLogger(__name__)


def normalize_algorithm(algorithm: str) -> str:
    """Normalize legacy algorithm aliases to canonical names."""
    actual_algorithm = algorithm.strip().upper() if isinstance(algorithm, str) else str(algorithm)
    if actual_algorithm == 'ROBUSTPCA':
        return 'RobustPCA'
    if actual_algorithm in ('PB_MODELS_76', 'PB_MODELS_86'):
        return 'PB_EVOL_76' if actual_algorithm.endswith('_76') else 'PB_EVOL_86'
    if actual_algorithm in ('ISOCHRON1', 'ISOCHRON2'):
        return 'PB_EVOL_76' if actual_algorithm == 'ISOCHRON1' else 'PB_EVOL_86'
    return actual_algorithm


def resolve_target_dimensions(actual_algorithm: str):
    """Return target axes dimensionality for the algorithm."""
    return 'ternary' if actual_algorithm == 'TERNARY' else 2


def resolve_embedding_params(
    umap_params: dict | None,
    tsne_params: dict | None,
    pca_params: dict | None,
    robust_pca_params: dict | None,
) -> tuple[dict, dict, dict, dict]:
    """Fill missing embedding parameter dictionaries from CONFIG defaults."""
    if umap_params is None:
        umap_params = CONFIG['umap_params']
    if tsne_params is None:
        tsne_params = CONFIG['tsne_params']
    if pca_params is None:
        pca_params = CONFIG.get('pca_params', {'n_components': 2, 'random_state': 42})
    if robust_pca_params is None:
        robust_pca_params = CONFIG.get('robust_pca_params', {'n_components': 2, 'random_state': 42})
    return umap_params, tsne_params, pca_params, robust_pca_params


def _compute_v1v2_embedding():
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
        v1v2_params = getattr(app_state, 'v1v2_params', {})
        scale = v1v2_params.get('scale', 1.0)
        a = v1v2_params.get('a')
        b = v1v2_params.get('b')
        c = v1v2_params.get('c')

        results = calculate_all_parameters(
            pb206,
            pb207,
            pb208,
            calculate_ages=False,
            a=a,
            b=b,
            c=c,
            scale=scale,
        )
        v1 = results['V1']
        v2 = results['V2']
        embedding = np.column_stack((v1, v2))
        state_gateway.set_attrs({'last_embedding': embedding, 'last_embedding_type': 'V1V2'})
        return embedding
    except Exception as err:
        logger.error('V1V2 calculation failed: %s', err)
        return None


def _compute_geochem_embedding(actual_algorithm: str):
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
        t_ma = None
        if getattr(app_state, 'use_real_age_for_mu_kappa', False):
            age_col = getattr(app_state, 'mu_kappa_age_col', None)
            if age_col and age_col in df_subset.columns:
                t_ma = pd.to_numeric(df_subset[age_col], errors='coerce').values

        if t_ma is None:
            try:
                from data.geochemistry import engine, resolve_age_model

                current_model = getattr(engine, 'current_model_name', '')
                params = engine.get_parameters()
                age_model = resolve_age_model(params, current_model)
                is_geokit = 'Geokit' in current_model
                if age_model == 'two_stage':
                    t_ma = geochemistry.calculate_two_stage_age(pb206, pb207, params=params)
                elif is_geokit:
                    t_ma = geochemistry.calculate_single_stage_age(
                        pb206,
                        pb207,
                        params=params,
                        initial_age=params.get('T1'),
                    )
                else:
                    t_ma = geochemistry.calculate_single_stage_age(pb206, pb207, params=params)
            except Exception as age_err:
                logger.warning('Failed to compute model age: %s', age_err)
                return None

        if actual_algorithm == 'PB_MU_AGE':
            mu_vals = geochemistry.calculate_model_mu(pb206, pb207, t_ma)
            embedding = np.column_stack((t_ma, mu_vals))
        else:
            kappa_vals = geochemistry.calculate_model_kappa(pb208, pb206, t_ma)
            embedding = np.column_stack((t_ma, kappa_vals))
    else:
        if actual_algorithm in ('PB_EVOL_76', 'PLUMBOTECTONICS_76'):
            embedding = np.column_stack((pb206, pb207))
        else:
            embedding = np.column_stack((pb206, pb208))

    state_gateway.set_attrs({'last_embedding': embedding, 'last_embedding_type': actual_algorithm})
    return embedding


def _compute_ternary_embedding():
    cols = getattr(app_state, 'selected_ternary_cols', [])
    if not cols or len(cols) != 3:
        logger.error('Ternary columns not selected')
        return None

    try:
        _, indices = _get_analysis_data()
        if indices is None:
            return None

        df_global = _df_global()
        if df_global is None:
            return None

        df_subset = df_global.iloc[indices]

        c_top, c_left, c_right = cols
        missing = [col for col in cols if col not in df_subset.columns]
        if missing:
            logger.error('Missing columns for ternary plot: %s', missing)
            return None

        top_vals = pd.to_numeric(df_subset[c_top], errors='coerce').fillna(0).values
        left_vals = pd.to_numeric(df_subset[c_left], errors='coerce').fillna(0).values
        right_vals = pd.to_numeric(df_subset[c_right], errors='coerce').fillna(0).values

        embedding = np.column_stack((top_vals, left_vals, right_vals))
        state_gateway.set_attrs({'last_embedding': embedding, 'last_embedding_type': 'TERNARY'})

        if hasattr(app_state, 'ternary_manual_ranges'):
            del app_state.ternary_manual_ranges
        if hasattr(app_state, 'ternary_ranges'):
            del app_state.ternary_ranges
        return embedding
    except Exception as err:
        logger.error('Ternary calculation failed: %s', err)
        traceback.print_exc()
        return None


def compute_embedding(
    actual_algorithm: str,
    *,
    precomputed_embedding: np.ndarray | None,
    precomputed_meta: dict | None,
    umap_params: dict,
    tsne_params: dict,
    pca_params: dict,
    robust_pca_params: dict,
) -> np.ndarray | None:
    """Compute or reuse embedding for the normalized algorithm."""
    if precomputed_embedding is not None and actual_algorithm in ('UMAP', 'TSNE', 'PCA', 'RobustPCA'):
        embedding = np.asarray(precomputed_embedding)
        last_type = 'tSNE' if actual_algorithm == 'TSNE' else actual_algorithm
        state_gateway.set_attrs({'last_embedding': embedding, 'last_embedding_type': last_type})

        if isinstance(precomputed_meta, dict):
            if precomputed_meta.get('last_pca_variance') is not None:
                state_gateway.set_attr('last_pca_variance', precomputed_meta.get('last_pca_variance'))
            if precomputed_meta.get('last_pca_components') is not None:
                state_gateway.set_attr('last_pca_components', precomputed_meta.get('last_pca_components'))
            if precomputed_meta.get('current_feature_names') is not None:
                state_gateway.set_attr('current_feature_names', precomputed_meta.get('current_feature_names'))

        logger.debug('Using precomputed embedding for %s', actual_algorithm)
        return embedding

    if actual_algorithm == 'UMAP':
        logger.debug('Computing UMAP embedding')
        return get_umap_embedding(umap_params)
    if actual_algorithm == 'TSNE':
        logger.debug('Computing tSNE embedding')
        return get_tsne_embedding(tsne_params)
    if actual_algorithm == 'PCA':
        logger.debug('Computing PCA embedding')
        return get_pca_embedding(pca_params)
    if actual_algorithm == 'RobustPCA':
        logger.debug('Computing Robust PCA embedding')
        return get_robust_pca_embedding(robust_pca_params)
    if actual_algorithm == 'V1V2':
        logger.debug('Computing V1V2 embedding')
        return _compute_v1v2_embedding()
    if actual_algorithm in (
        'PB_EVOL_76',
        'PB_EVOL_86',
        'PB_MU_AGE',
        'PB_KAPPA_AGE',
        'PLUMBOTECTONICS_76',
        'PLUMBOTECTONICS_86',
    ):
        logger.debug('Computing Geochemistry embedding for %s', actual_algorithm)
        return _compute_geochem_embedding(actual_algorithm)
    if actual_algorithm == 'TERNARY':
        logger.debug('Computing Ternary embedding')
        return _compute_ternary_embedding()

    logger.error('Unknown algorithm: %s', actual_algorithm)
    return None
