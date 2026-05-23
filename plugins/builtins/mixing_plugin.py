"""Builtin mixing model plugin."""
from __future__ import annotations
from typing import Any

import numpy as np
import pandas as pd

from plugins.api import BasePlugin, PluginMeta


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

    def obj(w: np.ndarray) -> float:
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


def calculate_mixing_with_uncertainty(
    df: pd.DataFrame,
    endmember_groups: dict[str, list[int]],
    mixture_groups: dict[str, list[int]],
    columns: list[str],
    n_samples: int = 1000,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Calculate mixing proportions with Monte Carlo error propagation.

    For each mixture group, this function:
      1. Computes the mean and standard deviation of endmember and mixture values.
      2. Draws *n_samples* random realisations from normal distributions
         N(mean, std) for each endmember and the mixture target.
      3. Solves the simplex-constrained least-squares mixing for each
         realisation.
      4. Aggregates the resulting weight distributions into summary statistics.

    Args:
        df: Input DataFrame containing the data.
        endmember_groups: Mapping of endmember group names to row index lists.
        mixture_groups: Mapping of mixture group names to row index lists.
        columns: List of column names (isotope ratios) to use for the mixing
            calculation.
        n_samples: Number of Monte Carlo samples to draw (default 1000).
        seed: Random seed for reproducibility (default 42).

    Returns:
        A list of dictionaries, one per (mixture, endmember) pair, with keys:
            mixture (str): Name of the mixture group.
            endmember (str): Name of the endmember group.
            weight_mean (float): Mean weight across Monte Carlo samples.
            weight_std (float): Standard deviation of the weight.
            weight_5th (float): 5th percentile of the weight distribution.
            weight_95th (float): 95th percentile of the weight distribution.
            rmse (float): Root-mean-square error of the mean prediction.
            columns (list[str]): The columns used for the calculation.

    Raises:
        ValueError: If the input data, columns, or groups are invalid.
    """
    if df is None or df.empty:
        raise ValueError("No data available.")
    if not columns:
        raise ValueError("No columns selected.")
    if not endmember_groups:
        raise ValueError("No endmember groups provided.")
    if not mixture_groups:
        raise ValueError("No mixture groups provided.")

    rng = np.random.default_rng(seed)
    endmember_names = list(endmember_groups.keys())
    results: list[dict[str, Any]] = []

    # Pre-compute endmember stats (mean, std) for each group
    endmember_stats: list[tuple[np.ndarray, np.ndarray]] = []
    for name in endmember_names:
        indices = list(endmember_groups.get(name, []))
        if not indices:
            raise ValueError(f"Endmember group '{name}' is empty.")
        values = df.iloc[indices][columns].apply(pd.to_numeric, errors='coerce')
        em_mean = values.mean(axis=0).to_numpy()
        em_std = values.std(axis=0, ddof=0).to_numpy()
        endmember_stats.append((em_mean, em_std))

    # Ensure mean-only endmember matrix for RMSE calculation
    endmember_matrix = np.column_stack([m for m, _ in endmember_stats])

    for mix_name, mix_indices in mixture_groups.items():
        if not mix_indices:
            continue

        mix_values = df.iloc[list(mix_indices)][columns].apply(
            pd.to_numeric, errors='coerce'
        )
        mix_mean = mix_values.mean(axis=0).to_numpy()
        mix_std = mix_values.std(axis=0, ddof=0).to_numpy()

        # Monte Carlo loop
        mc_weights: list[np.ndarray] = []
        mc_residuals: list[float] = []

        for _ in range(n_samples):
            # Sample endmembers
            sampled_ems: list[np.ndarray] = []
            for em_mean, em_std in endmember_stats:
                safe_std = np.maximum(em_std, 1e-10)
                sampled = rng.normal(em_mean, safe_std)
                sampled_ems.append(sampled)
            em_matrix = np.column_stack(sampled_ems)

            # Sample mixture target
            safe_std = np.maximum(mix_std, 1e-10)
            sampled_target = rng.normal(mix_mean, safe_std)

            # Solve
            weights, residual = _solve_simplex_weights(em_matrix, sampled_target)
            mc_weights.append(weights)
            mc_residuals.append(residual)

        mc_array = np.array(mc_weights)  # shape (n_samples, n_endmembers)

        # Compute deterministic RMSE (mean-values fit) for reference
        _, det_residual = _solve_simplex_weights(endmember_matrix, mix_mean)

        for i, name in enumerate(endmember_names):
            w = mc_array[:, i]
            results.append({
                'mixture': mix_name,
                'endmember': name,
                'weight_mean': float(np.mean(w)),
                'weight_std': float(np.std(w, ddof=1)),
                'weight_5th': float(np.percentile(w, 5)),
                'weight_95th': float(np.percentile(w, 95)),
                'rmse': float(det_residual),
                'columns': list(columns),
            })

    return results


class MixingModelPlugin(BasePlugin):
    meta = PluginMeta(
        name="mixing",
        version="1.0",
        api_version="1.0",
        plugin_type="analysis",
        author="IsotopesAnalyse",
        description="Endmember mixing proportion solver with Monte Carlo uncertainty",
    )

    def validate_environment(self) -> tuple[bool, str]:
        return True, "ok"

    def get_default_params(self) -> dict[str, Any]:
        return {}

    def calculate(self, df, endmember_groups, mixture_groups, columns, **kwargs):
        return calculate_mixing(df, endmember_groups, mixture_groups, columns)

    def calculate_with_uncertainty(self, df, endmember_groups, mixture_groups, columns, **kwargs):
        return calculate_mixing_with_uncertainty(
            df, endmember_groups, mixture_groups, columns, **kwargs
        )
