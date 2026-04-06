"""Dataframe alignment/filtering helpers for embedding rendering."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from core import app_state, state_gateway

from ..common.state_access import _active_subset_indices, _df_global

logger = logging.getLogger(__name__)


def _reset_plot_dataframe(
    df_source: pd.DataFrame,
    embedding: np.ndarray,
    actual_algorithm: str,
    group_col: str,
) -> pd.DataFrame | None:
    base = df_source
    if group_col not in base.columns:
        return None

    base[group_col] = base[group_col].fillna('Unknown').astype(str)

    try:
        if actual_algorithm == 'TERNARY':
            base['_emb_t'] = embedding[:, 0]
            base['_emb_l'] = embedding[:, 1]
            base['_emb_r'] = embedding[:, 2]
        elif actual_algorithm in ('PCA', 'RobustPCA') and hasattr(app_state, 'pca_component_indices'):
            idx_x = app_state.pca_component_indices[0]
            idx_y = app_state.pca_component_indices[1]

            n_comps = embedding.shape[1]
            if idx_x >= n_comps:
                idx_x = 0
            if idx_y >= n_comps:
                idx_y = 1 if n_comps > 1 else 0

            base['_emb_x'] = embedding[:, idx_x]
            base['_emb_y'] = embedding[:, idx_y]
            logger.debug('Plotting components %d and %d', idx_x + 1, idx_y + 1)
        else:
            base['_emb_x'] = embedding[:, 0]
            base['_emb_y'] = embedding[:, 1]
    except Exception as emb_error:
        logger.error('Unable to align embedding with data: %s', emb_error)
        return None

    return base


def prepare_plot_dataframe(
    group_col: str,
    actual_algorithm: str,
    embedding: np.ndarray,
) -> tuple[pd.DataFrame, list[str]] | None:
    """Prepare plotting dataframe and apply visibility filters."""
    df_global = _df_global()
    if df_global is None:
        logger.error('No data available for plotting')
        return None

    subset_indices = _active_subset_indices()
    if subset_indices is not None:
        indices_to_plot = sorted(list(subset_indices))
        df_source = df_global.iloc[indices_to_plot].copy()
    else:
        df_source = df_global.copy()

    if embedding.shape[0] != len(df_source):
        logger.error('Embedding size %d does not match data size %d', embedding.shape[0], len(df_source))
        return None

    df_plot = _reset_plot_dataframe(df_source, embedding, actual_algorithm, group_col)
    if df_plot is None:
        logger.error('Unable to prepare plotting data for column: %s', group_col)
        return None

    all_groups = sorted(df_plot[group_col].unique())
    state_gateway.sync_available_and_visible_groups(all_groups)

    visible_groups = app_state.visible_groups
    if visible_groups is not None:
        allowed = set(visible_groups)
        mask = df_plot[group_col].isin(allowed)
        if not allowed:
            df_plot = df_plot[mask].copy()
        elif not mask.any():
            logger.info('No data matches the selected legend filter; showing all groups instead.')
            state_gateway.set_visible_groups(None)
        else:
            df_plot = df_plot[mask].copy()
            if df_plot.empty:
                logger.info('Filtered plot data is empty; showing all groups instead.')
                df_plot = _reset_plot_dataframe(df_source, embedding, actual_algorithm, group_col)
                if df_plot is None:
                    return None
                state_gateway.set_visible_groups(None)
                state_gateway.sync_available_and_visible_groups(sorted(df_plot[group_col].unique()))

    unique_cats = sorted(df_plot[group_col].unique())
    logger.debug('Unique categories in %s: %s', group_col, unique_cats)
    return df_plot, unique_cats
