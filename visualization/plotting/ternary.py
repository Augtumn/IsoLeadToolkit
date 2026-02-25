"""Ternary plot helpers."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from scipy.stats import gmean

from core import app_state

logger = logging.getLogger(__name__)


def _apply_ternary_stretch(t_vals, l_vals, r_vals):
    """Apply ternary stretch transform based on current mode."""
    if not getattr(app_state, 'ternary_stretch', False):
        return t_vals, l_vals, r_vals

    factors = getattr(app_state, 'ternary_factors', [1.0, 1.0, 1.0])
    if not factors or len(factors) != 3:
        factors = [1.0, 1.0, 1.0]

    t_vals = np.asarray(t_vals, dtype=float) * float(factors[0])
    l_vals = np.asarray(l_vals, dtype=float) * float(factors[1])
    r_vals = np.asarray(r_vals, dtype=float) * float(factors[2])

    mode = getattr(app_state, 'ternary_stretch_mode', 'power')
    power = float(getattr(app_state, 'ternary_stretch_power', 0.5))

    def _minmax(vals):
        vmin = np.nanmin(vals)
        vmax = np.nanmax(vals)
        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax == vmin:
            return vals
        return (vals - vmin) / (vmax - vmin)

    if mode in ('minmax', 'hybrid'):
        t_vals = _minmax(t_vals)
        l_vals = _minmax(l_vals)
        r_vals = _minmax(r_vals)

    if mode in ('power', 'hybrid'):
        t_vals = np.power(np.maximum(t_vals, 0), power)
        l_vals = np.power(np.maximum(l_vals, 0), power)
        r_vals = np.power(np.maximum(r_vals, 0), power)

    return t_vals, l_vals, r_vals

def calculate_auto_ternary_factors() -> bool:
    """Calculate optimal scaling factors for the ternary plot using geometric means.

    This effectively centers the data in the ternary diagram (compositional centering).
    """
    try:
        if not hasattr(app_state, 'selected_ternary_cols') or len(app_state.selected_ternary_cols) != 3:
            logger.warning("Factors calc: invalid col selection")
            return False

        cols = app_state.selected_ternary_cols

        if app_state.active_subset_indices is not None:
            df = app_state.df_global.iloc[app_state.active_subset_indices].copy()
        else:
            df = app_state.df_global.copy()

        data = df[cols].apply(pd.to_numeric, errors='coerce').fillna(0.001).values
        data = np.maximum(data, 1e-6)

        gmeans = gmean(data, axis=0)

        factors = 1.0 / gmeans
        min_f = np.min(factors)
        if min_f > 0:
            factors = factors / min_f

        app_state.ternary_factors = factors.tolist()
        logger.info("Auto-Calculated Factors: %s", app_state.ternary_factors)
        return True

    except Exception as e:
        logger.error("Auto factor calculation failed: %s", e)
        return False
