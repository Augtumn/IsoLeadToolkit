"""Selection overlay rendering helpers."""

from __future__ import annotations

import logging
from typing import Any

import matplotlib
import numpy as np
import scipy.stats
from matplotlib.patches import Ellipse

logger = logging.getLogger(__name__)


def draw_confidence_ellipse(
    x: np.ndarray,
    y: np.ndarray,
    ax: Any,
    confidence: float = 0.95,
    facecolor: str = "none",
    **kwargs,
) -> Ellipse | None:
    """Create covariance confidence ellipse patch for x/y points."""
    x_arr = np.asarray(x, dtype=float).ravel()
    y_arr = np.asarray(y, dtype=float).ravel()
    if x_arr.size != y_arr.size:
        return None

    finite_mask = np.isfinite(x_arr) & np.isfinite(y_arr)
    if np.count_nonzero(finite_mask) < 2:
        return None

    x_valid = x_arr[finite_mask]
    y_valid = y_arr[finite_mask]

    chi2_val = scipy.stats.chi2.ppf(confidence, df=2)
    n_std = np.sqrt(chi2_val)

    cov = np.cov(x_valid, y_valid)
    if not np.all(np.isfinite(cov)):
        return None

    var_x = cov[0, 0]
    var_y = cov[1, 1]
    if var_x <= 0 or var_y <= 0:
        return None

    denom = np.sqrt(var_x * var_y)
    if not np.isfinite(denom) or denom <= np.finfo(float).tiny:
        return None

    pearson = cov[0, 1] / denom
    pearson = float(np.clip(pearson, -1.0, 1.0))

    ell_radius_x = np.sqrt(1 + pearson)
    ell_radius_y = np.sqrt(1 - pearson)

    ellipse = Ellipse(
        (0, 0),
        width=ell_radius_x * 2,
        height=ell_radius_y * 2,
        facecolor=facecolor,
        **kwargs,
    )

    scale_x = np.sqrt(var_x) * n_std
    mean_x = np.mean(x_valid)
    scale_y = np.sqrt(var_y) * n_std
    mean_y = np.mean(y_valid)

    theta = 0.5 * np.arctan2(2 * cov[0, 1], var_x - var_y)
    transf = (
        matplotlib.transforms.Affine2D()
        .rotate(theta)
        .scale(scale_x, scale_y)
        .translate(mean_x, mean_y)
    )

    ellipse.set_transform(transf + ax.transData)
    return ax.add_patch(ellipse)


def refresh_selection_overlay_state(
    *,
    state: Any,
    state_write: Any,
    notify_selection_ui: Any,
) -> None:
    """Refresh selection overlay artists for current state."""
    try:
        if state.fig is None or state.ax is None or state.render_mode == "3D":
            if state.selection_overlay is not None:
                try:
                    state.selection_overlay.remove()
                except Exception:
                    pass
                state_write.set_selection_overlay(None)
            notify_selection_ui()
            return

        if state.selection_overlay is not None:
            try:
                state.selection_overlay.remove()
            except Exception:
                pass
            state_write.set_selection_overlay(None)

        if state.selection_ellipse is not None:
            try:
                state.selection_ellipse.remove()
            except Exception:
                pass
            state_write.set_selection_ellipse(None)

        valid_indices = [idx for idx in state.selected_indices if idx in state.sample_coordinates]
        if not valid_indices:
            state.fig.canvas.draw_idle()
            notify_selection_ui()
            return

        current_xlim = state.ax.get_xlim()
        current_ylim = state.ax.get_ylim()

        xs = [state.sample_coordinates[idx][0] for idx in valid_indices]
        ys = [state.sample_coordinates[idx][1] for idx in valid_indices]

        if state.selection_tool:
            base_marker_size = getattr(state, "plot_marker_size", state.point_size)
            highlight_size = max(int(base_marker_size * 1.8), 20)
            overlay = state.ax.scatter(
                xs,
                ys,
                s=[highlight_size] * len(xs),
                facecolors="none",
                edgecolors="#f97316",
                linewidths=1.6,
                zorder=6,
            )
            state_write.set_selection_overlay(overlay)

        should_draw_ellipse = state.show_ellipses or getattr(state, "draw_selection_ellipse", False)
        if should_draw_ellipse and len(xs) >= 3:
            try:
                x_arr = np.array(xs)
                y_arr = np.array(ys)
                ellipse = draw_confidence_ellipse(
                    x_arr,
                    y_arr,
                    state.ax,
                    confidence=state.ellipse_confidence,
                    edgecolor="#f97316",
                    linestyle="--",
                    linewidth=2,
                    zorder=5,
                    alpha=0.8,
                )
                state_write.set_selection_ellipse(ellipse)
                logger.info(
                    "Drawn %.0f%% confidence ellipse for %d selected points.",
                    state.ellipse_confidence * 100,
                    len(xs),
                )
            except Exception as err:
                logger.warning("Failed to draw selection ellipse: %s", err)

        state.ax.set_xlim(current_xlim)
        state.ax.set_ylim(current_ylim)

        state.fig.canvas.draw_idle()
        notify_selection_ui()
    except Exception as err:
        logger.warning("Unable to refresh selection overlay: %s", err)
