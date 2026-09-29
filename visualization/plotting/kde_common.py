"""Shared KDE primitives: the bandwidth vocabulary, the option ranges, the estimator input.

Both density paths grew their own copy of these - the rule names in four places, the option
clamps in three, the bandwidth arithmetic and the finite-value cleaning in two each. That is how
seaborn once received the literal "lscv", how the state layer once dropped it, and how the
marginal once stopped following the joint density's rule. The vocabulary now lives in
core.state.coercers (core may not import visualization), and everything else lives here.

The estimators themselves stay separate on purpose: the 2-D overlay goes through seaborn's
kdeplot, which hard-codes the Gaussian kernel and offers no cut, while the ternary density is a
Gaussian KDE drawn by hand in the axes' Cartesian frame. Unifying those two means replacing
seaborn; this module unifies what is genuinely the same, so the paths can no longer disagree
about *parameters*.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from core.state.coercers import KDE_BANDWIDTH_RULES, KDE_BANDWIDTH_RULE_DEFAULT
from visualization.plotting.kde_bandwidth import lscv_factor

KDE_BW_ADJUST_MIN = 0.05
KDE_BW_ADJUST_MAX = 5.0
KDE_GRIDSIZE_MIN = 32
KDE_GRIDSIZE_MAX = 1024
KDE_THRESH_MIN = 0.05
KDE_THRESH_MAX = 0.9
KDE_BW_MIN = 1e-12


def resolve_rule(value: Any) -> str:
    """The one place that decides which bandwidth rule a name means."""
    name = str(value or KDE_BANDWIDTH_RULE_DEFAULT).strip().lower()
    return name if name in KDE_BANDWIDTH_RULES else KDE_BANDWIDTH_RULE_DEFAULT


def clamp_bw_adjust(value: Any) -> float:
    return max(KDE_BW_ADJUST_MIN, min(float(value), KDE_BW_ADJUST_MAX))


def clamp_gridsize(value: Any) -> int:
    return max(KDE_GRIDSIZE_MIN, min(int(value), KDE_GRIDSIZE_MAX))


def clamp_thresh(value: Any) -> float:
    return max(KDE_THRESH_MIN, min(float(value), KDE_THRESH_MAX))


def finite_float_array(values) -> np.ndarray:
    """Finite values of *values* as a float array - the input every estimator expects."""
    arr = np.asarray(values, dtype=float)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    return arr[np.isfinite(arr)]


def bandwidth_for(
    rule: str,
    values,
    *,
    bw_adjust: float = 1.0,
    absolute: float = 0.0,
    dim: int = 1,
) -> float:
    """The bandwidth a rule (or an absolute value) gives for *values*.

    Scott and Silverman are the textbook factors for the given dimension; LSCV comes from
    kde_bandwidth. An absolute bandwidth wins, and bw_adjust scales whichever result applies.
    """
    adjust = clamp_bw_adjust(bw_adjust)
    if absolute and float(absolute) > 0.0:
        return max(KDE_BW_MIN, float(absolute) * adjust)

    data = finite_float_array(values)
    if data.size < 2:
        return KDE_BW_MIN
    if dim == 1:
        std = float(np.nanstd(data))
    else:
        flat = np.asarray(values, dtype=float)
        flat = flat[np.isfinite(flat).all(axis=-1)] if flat.ndim > 1 else flat[np.isfinite(flat)]
        std = float(np.mean(np.std(flat, axis=0))) if flat.size else 0.0
        data = flat
    if not np.isfinite(std) or std <= 1e-12:
        std = 1.0

    name = resolve_rule(rule)
    if name == "lscv":
        shaped = data[:, None] if np.ndim(data) == 1 else data
        factor = float(lscv_factor(shaped))
    else:
        n = max(int(np.size(data, 0)), 2)
        exponent = -1.0 / (dim + 4.0)
        if name == "silverman":
            factor = float((n * (dim + 2.0) / 4.0) ** exponent)
        else:
            factor = float(n ** exponent)
    return max(KDE_BW_MIN, std * factor * adjust)


def scipy_bw_method(rule: str):
    """The rule in a form scipy's gaussian_kde and seaborn accept.

    They take 'scott', 'silverman', a scalar or a callable - never the literal 'lscv'. Handing
    them the name raised "bw_method should be 'scott', 'silverman', a scalar or a callable",
    which was caught and turned into a missing curve: that is why the marginal KDE vanished when
    LSCV was selected, and why the 2-D overlay failed to render at all.
    """
    name = resolve_rule(rule)
    if name == "lscv":
        from visualization.plotting.kde_bandwidth import lscv_bw_method

        return lscv_bw_method()
    return name
