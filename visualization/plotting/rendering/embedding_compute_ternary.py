"""Embedding computation helpers for ternary rendering."""
from __future__ import annotations

import logging
import traceback

import numpy as np
import pandas as pd

from core import app_state, state_gateway

from ..data import _get_analysis_data
from .state_access import _df_global

logger = logging.getLogger(__name__)


def compute_ternary_embedding() -> np.ndarray | None:
    """Compute ternary embedding from selected ternary columns."""
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
