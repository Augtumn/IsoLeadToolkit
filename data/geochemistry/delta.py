"""Delta calculations and V1-V2 projection."""
from __future__ import annotations
from typing import Any

import numpy as np

from .engine import (
    E1_DEFAULT,
    E2_DEFAULT,
    engine,
    _exp_evolution_term,
)


def calculate_deltas(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    Pb208_204_S: np.ndarray | float,
    t_Ma: np.ndarray | float | None,
    params: dict[str, Any] | None = None,
    T_mantle: float | None = None,
    use_two_stage: bool = False,
    E1: float | None = None,
    E2: float | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute the delta values (Δα, Δβ, Δγ).

    Deviation of the sample from the coeval mantle reference, in per mil.

    Args:
        T_mantle: start time of the mantle reference curve
        use_two_stage: use stage-2 parameters for the reference curve
        E1/E2: evolution parameters (PbIso model curve)

    Returns:
        (d_alpha, d_beta, d_gamma): deviation arrays
    """
    if params is None:
        params = engine.params

    l238 = params['lambda_238']
    l235 = params['lambda_235']
    l232 = params['lambda_232']

    mu_M = params['mu_M']
    omega_M = params['omega_M']
    v_M = params['v_M']

    E1_val = params.get('E1', E1_DEFAULT) if E1 is None else float(E1)
    E2_val = params.get('E2', E2_DEFAULT) if E2 is None else float(E2)

    if use_two_stage:
        T = T_mantle if T_mantle is not None else params['Tsec']
        a_ref, b_ref, c_ref = params['a1'], params['b1'], params['c1']
    else:
        T = T_mantle if T_mantle is not None else params['T2']
        a_ref, b_ref, c_ref = params['a0'], params['b0'], params['c0']

    # Normalize to arrays and handle bad values
    t = np.asarray(t_Ma, dtype=float) if t_Ma is not None else np.array(np.nan)
    Pb206 = np.asarray(Pb206_204_S)
    Pb207 = np.asarray(Pb207_204_S)
    Pb208 = np.asarray(Pb208_204_S)

    # Initialize results (NaN unless computed)
    d_alpha = np.full_like(Pb206, np.nan, dtype=float)
    d_beta = np.full_like(Pb207, np.nan, dtype=float)
    d_gamma = np.full_like(Pb208, np.nan, dtype=float)

    # Invalid-age checks
    if t.ndim == 0 and np.isnan(t):
        return d_alpha, d_beta, d_gamma

    valid_mask = ~np.isnan(t)
    if not np.any(valid_mask):
        return d_alpha, d_beta, d_gamma

    t_val = np.maximum(t, 0) * 1e6

    # Coeval mantle reference values
    ref206 = a_ref + mu_M * (_exp_evolution_term(l238, T, E1_val) - _exp_evolution_term(l238, t_val, E1_val))
    ref207 = b_ref + v_M * (_exp_evolution_term(l235, T, E1_val) - _exp_evolution_term(l235, t_val, E1_val))
    ref208 = c_ref + omega_M * (_exp_evolution_term(l232, T, E2_val) - _exp_evolution_term(l232, t_val, E2_val))

    # Deviation (per mil); ref and Pb broadcast via numpy - t and Pb shapes
    # must match or broadcast.

    with np.errstate(divide='ignore', invalid='ignore'):
        d_alpha = ((Pb206 / ref206) - 1) * 1000
        d_beta = ((Pb207 / ref207) - 1) * 1000
        d_gamma = ((Pb208 / ref208) - 1) * 1000

    return d_alpha, d_beta, d_gamma


def calculate_v1v2_coordinates(
    d_alpha: np.ndarray,
    d_beta: np.ndarray,
    d_gamma: np.ndarray,
    params: dict[str, Any] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """V1-V2 discriminant-diagram projection coordinates.

    Source: Zhu (1995).
    """
    if params is None:
        params = engine.params

    a, b, c = params['a'], params['b'], params['c']

    denom = 1 + b**2 + c**2

    d_alpha_p = ((1 + c**2) * d_alpha + b * (d_gamma - c * d_beta - a)) / denom
    d_beta_p = ((1 + b**2) * d_beta + c * (d_gamma - b * d_alpha - a)) / denom
    d_gamma_p = a + b * d_alpha_p + c * d_beta_p

    V1 = (b * d_gamma_p + d_alpha_p) / np.sqrt(1 + b**2)
    V2 = (np.sqrt(1 + b**2 + c**2) / np.sqrt(1 + b**2)) * d_beta_p

    return V1, V2
