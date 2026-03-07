"""
Mixing model calculations for endmember contributions.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Any


def _solve_simplex_weights(endmember_matrix: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, float]:
    """Solve for non-negative weights summing to 1."""
    endmember_matrix = np.asarray(endmember_matrix, dtype=float)
    target = np.asarray(target, dtype=float)

    if endmember_matrix.ndim != 2:
        raise ValueError("Endmember matrix must be 2D.")
    if target.ndim != 1:
        raise ValueError("Target must be 1D.")

    n_endmembers = endmember_matrix.shape[1]
    if n_endmembers == 0:
        raise ValueError("No endmembers available.")
    if n_endmembers == 1:
        weights = np.array([1.0], dtype=float)
        residual = float(np.linalg.norm(endmember_matrix[:, 0] - target))
        return weights, residual

    def obj(w):
        return np.sum((endmember_matrix @ w - target) ** 2)

    x0 = np.full(n_endmembers, 1.0 / n_endmembers, dtype=float)
    bounds = [(0.0, 1.0)] * n_endmembers

    try:
        from scipy.optimize import minimize

        constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}]
        res = minimize(obj, x0, bounds=bounds, constraints=constraints)
        if res.success:
            weights = res.x
            residual = float(np.sqrt(obj(weights)))
            return weights, residual
    except Exception:
        pass

    # Fallback: unconstrained least squares + clip + normalize
    try:
        weights, *_ = np.linalg.lstsq(endmember_matrix, target, rcond=None)
        weights = np.clip(weights, 0.0, None)
        total = float(weights.sum())
        if total > 0:
            weights = weights / total
        else:
            weights = x0
        residual = float(np.sqrt(obj(weights)))
        return weights, residual
    except Exception as err:
        raise ValueError(f"Mixing solve failed: {err}") from err


def calculate_mixing(
    df: pd.DataFrame,
    endmember_groups: dict[str, list[int]],
    mixture_groups: dict[str, list[int]],
    columns: list[str],
) -> list[dict[str, Any]]:
    """Calculate mixing proportions for each mixture group."""
    if df is None or df.empty:
        raise ValueError("No data available.")
    if not columns:
        raise ValueError("No columns selected.")
    if not endmember_groups:
        raise ValueError("No endmember groups provided.")
    if not mixture_groups:
        raise ValueError("No mixture groups provided.")

    results = []
    endmember_names = list(endmember_groups.keys())
    endmember_means = []

    for name in endmember_names:
        indices = list(endmember_groups.get(name, []))
        if not indices:
            raise ValueError(f"Endmember group '{name}' is empty.")
        values = df.iloc[indices][columns].apply(pd.to_numeric, errors='coerce')
        endmember_means.append(values.mean(axis=0).to_numpy())

    endmember_matrix = np.column_stack(endmember_means)

    for mix_name, mix_indices in mixture_groups.items():
        if not mix_indices:
            continue
        mix_values = df.iloc[list(mix_indices)][columns].apply(pd.to_numeric, errors='coerce')
        target = mix_values.mean(axis=0).to_numpy()

        weights, residual = _solve_simplex_weights(endmember_matrix, target)
        for name, weight in zip(endmember_names, weights):
            results.append({
                'mixture': mix_name,
                'endmember': name,
                'weight': float(weight),
                'rmse': float(residual),
                'columns': list(columns),
            })

    return results
