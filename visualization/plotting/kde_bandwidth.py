"""Least-squares cross-validation (LSCV) bandwidth selection for Gaussian KDEs.

Scott's and Silverman's rules are rules of thumb: they assume a normal shape and ignore the
sample. LSCV instead minimises an estimate of the integrated squared error between the KDE and
the true density,

    CV(h) = (1/(n^2 h^d)) * sum_ij K*((x_i - x_j)/h)
            - (2/(n(n-1) h^d)) * sum_{i!=j} K((x_i - x_j)/h),

where K is the Gaussian kernel and K* its convolution with itself (a Gaussian with twice the
variance). It is the standard data-driven choice when the sample is small and not normal -
archaeological groups, typically - at the cost of an O(n^2) evaluation.

Both entry points return scipy's *covariance factor* (bandwidth divided by the data standard
deviation), which is what gaussian_kde and seaborn expect.
"""
from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

_FACTOR_MIN = 0.05
_FACTOR_MAX = 3.0
_FACTOR_STEPS = 32


def _lscv_objective(factor: float, values: np.ndarray) -> float:
    """The LSCV criterion at one covariance factor (rows are observations)."""
    n, d = values.shape
    if n < 2:
        return float("inf")
    std = float(np.mean(np.std(values, axis=0)))
    if not np.isfinite(std) or std <= 0.0:
        return float("inf")
    h = max(factor * std, 1e-12)
    diff = (values[:, None, :] - values[None, :, :]) / h
    sq = np.sum(diff * diff, axis=-1)

    kernel = np.exp(-0.5 * sq) / (2.0 * np.pi) ** (d / 2.0)
    convolved = np.exp(-0.25 * sq) / (4.0 * np.pi) ** (d / 2.0)
    np.fill_diagonal(convolved, 0.0)

    first = float(np.sum(convolved)) / (n * n)
    second = 2.0 * float(np.sum(kernel) - np.trace(kernel)) / (n * (n - 1))
    return (first - second) / (h ** d)


def lscv_factor(values, max_points: int = 800) -> float:
    """Covariance factor minimising the LSCV criterion for *values*.

    Large samples are subsampled: the criterion is O(n^2) and its minimum is stable well
    before that, while a redraw must stay quick.
    """
    data = np.asarray(values, dtype=float)
    if data.ndim == 1:
        data = data[:, None]
    data = data[np.isfinite(data).all(axis=1)]
    if data.shape[0] < 2:
        return 1.0
    if data.shape[0] > max_points:
        rng = np.random.default_rng(0)
        data = data[rng.choice(data.shape[0], max_points, replace=False)]

    factors = np.geomspace(_FACTOR_MIN, _FACTOR_MAX, _FACTOR_STEPS)
    scores = [_lscv_objective(float(f), data) for f in factors]
    if not np.any(np.isfinite(scores)):
        return 1.0
    best = float(factors[int(np.nanargmin(scores))])
    logger.info("LSCV bandwidth factor %.4f (n=%d, d=%d)", best, data.shape[0], data.shape[1])
    return best


def lscv_bw_method(max_points: int = 800):
    """A callable for scipy's gaussian_kde(bw_method=...), using LSCV."""

    def _method(kde):
        return lscv_factor(np.asarray(kde.dataset).T, max_points=max_points)

    return _method
