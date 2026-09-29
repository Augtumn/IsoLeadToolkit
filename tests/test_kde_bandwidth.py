"""Least-squares cross-validation bandwidth selection.

LSCV is offered as an option beside Scott and Silverman. These tests pin down what it must
guarantee (a usable factor, deterministic, fast enough for a redraw) and deliberately do not
claim more: LSCV is known to undersmooth clustered and multimodal samples, which is exactly
what archaeological groups look like, so the default stays Scott's rule.
"""
from __future__ import annotations

import numpy as np
import pytest

from visualization.plotting.kde_bandwidth import lscv_bw_method, lscv_factor


def _sample(seed: int = 0, n: int = 40, scale: float = 1.0) -> np.ndarray:
    return np.random.default_rng(seed).normal(0.0, 1.0, (n, 2)) * scale


def test_the_factor_stays_in_the_configured_range() -> None:
    for scale in (0.05, 1.0, 20.0):
        factor = lscv_factor(_sample(scale=scale))

        assert 0.05 <= factor <= 3.0, f"factor out of range for scale {scale}: {factor}"


def test_the_factor_is_deterministic() -> None:
    data = _sample()

    assert lscv_factor(data) == lscv_factor(data), "a redraw must not change the bandwidth"


def test_too_few_points_fall_back_to_one() -> None:
    assert lscv_factor(np.zeros((1, 2))) == 1.0


def test_the_callable_form_is_accepted_by_scipy() -> None:
    from scipy.stats import gaussian_kde

    kde = gaussian_kde(_sample().T, bw_method=lscv_bw_method())

    assert kde.factor > 0.0


def test_large_samples_are_subsampled_for_speed() -> None:
    big = np.random.default_rng(1).normal(0.0, 1.0, (5000, 2))

    factor = lscv_factor(big, max_points=200)

    assert 0.05 <= factor <= 3.0
