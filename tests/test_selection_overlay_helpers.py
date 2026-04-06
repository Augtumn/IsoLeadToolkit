"""Tests for selection overlay helper functions."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from visualization.selection_overlay import draw_confidence_ellipse


def test_draw_confidence_ellipse_filters_nonfinite_points() -> None:
    fig, ax = plt.subplots()
    try:
        ellipse = draw_confidence_ellipse(
            np.array([0.0, 1.0, np.nan, 2.0, 3.0], dtype=float),
            np.array([1.0, 2.0, 3.0, np.inf, 4.0], dtype=float),
            ax,
            edgecolor="#f97316",
        )

        assert ellipse is not None
        assert ellipse in ax.patches
    finally:
        plt.close(fig)


def test_draw_confidence_ellipse_returns_none_for_mismatched_sizes() -> None:
    fig, ax = plt.subplots()
    try:
        ellipse = draw_confidence_ellipse(
            np.array([0.0, 1.0, 2.0], dtype=float),
            np.array([1.0, 2.0], dtype=float),
            ax,
        )

        assert ellipse is None
    finally:
        plt.close(fig)


def test_draw_confidence_ellipse_returns_none_for_zero_variance() -> None:
    fig, ax = plt.subplots()
    try:
        ellipse = draw_confidence_ellipse(
            np.array([1.0, 1.0, 1.0], dtype=float),
            np.array([2.0, 3.0, 4.0], dtype=float),
            ax,
        )

        assert ellipse is None
    finally:
        plt.close(fig)
