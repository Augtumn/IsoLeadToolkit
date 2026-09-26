"""Selection overlay rendering helpers."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import scipy.stats
from matplotlib.patches import Ellipse

logger = logging.getLogger(__name__)


_DEFAULT_ELLIPSE_CONFIDENCE = 0.95


def draw_confidence_ellipse(
    x: np.ndarray,
    y: np.ndarray,
    ax: Any,
    confidence: float = _DEFAULT_ELLIPSE_CONFIDENCE,
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

    # Eigen-decomposition of the covariance gives the true chi-square
    # ellipse: semi-axes are sqrt(eigenvalue) * n_std along the principal
    # directions. The old 2*sqrt(1 +/- rho) recipe is only correct when
    # var_x == var_y; otherwise the axes are badly mis-sized.
    try:
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
    except np.linalg.LinAlgError:
        return None
    if not np.all(np.isfinite(eigenvalues)):
        return None
    # Clip tiny negative eigenvalues from numerical error; perfectly
    # collinear data legitimately degenerates to a zero minor axis.
    eigenvalues = np.clip(eigenvalues, 0.0, None)
    if float(np.max(eigenvalues)) <= 0.0:
        return None

    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    major_axis = eigenvectors[:, 0]
    theta_deg = float(np.degrees(np.arctan2(major_axis[1], major_axis[0])))

    width = 2.0 * float(np.sqrt(eigenvalues[0])) * float(n_std)
    height = 2.0 * float(np.sqrt(eigenvalues[1])) * float(n_std)
    mean_x = float(np.mean(x_valid))
    mean_y = float(np.mean(y_valid))

    ellipse = Ellipse(
        (mean_x, mean_y),
        width=width,
        height=height,
        angle=theta_deg,
        facecolor=facecolor,
        **kwargs,
    )
    return ax.add_patch(ellipse)


def refresh_selection_overlay_state(
    *,
    state: Any,
    state_write: Any,
) -> None:
    """Refresh selection overlay artists for current state."""
    try:
        if state.fig is None or state.ax is None or state.render_mode == "3D":
            if state.selection_overlay is not None:
                try:
                    state.selection_overlay.remove()
                except Exception as err:
                    logger.warning("refresh_selection_overlay_state failed: %s", err)
                state_write.set_selection_overlay(None)
            return

        if state.selection_overlay is not None:
            try:
                state.selection_overlay.remove()
            except Exception as err:
                logger.warning("refresh_selection_overlay_state failed: %s", err)
            state_write.set_selection_overlay(None)

        if state.selection_ellipse is not None:
            try:
                state.selection_ellipse.remove()
            except Exception as err:
                logger.warning("refresh_selection_overlay_state failed: %s", err)
            state_write.set_selection_ellipse(None)

        valid_indices = [idx for idx in state.selected_indices if idx in state.sample_coordinates]
        if not valid_indices:
            state.fig.canvas.draw_idle()
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
                # Read the tracked confidence level (the 68/95/99% radios
                # write it); state.ellipse_confidence is config-only and was
                # never updated by the UI, making those radios inert.
                confidence = float(
                    getattr(state, "confidence_level", None)
                    or getattr(state, "ellipse_confidence", 0.95)
                )
                x_arr = np.array(xs)
                y_arr = np.array(ys)
                ellipse = draw_confidence_ellipse(
                    x_arr,
                    y_arr,
                    state.ax,
                    confidence=confidence,
                    edgecolor="#f97316",
                    linestyle="--",
                    linewidth=2,
                    zorder=5,
                    alpha=0.8,
                )
                state_write.set_selection_ellipse(ellipse)
                logger.info(
                    "Drawn %.0f%% confidence ellipse for %d selected points.",
                    confidence * 100,
                    len(xs),
                )
            except Exception as err:
                logger.warning("Failed to draw selection ellipse: %s", err)

        state.ax.set_xlim(current_xlim)
        state.ax.set_ylim(current_ylim)

        state.fig.canvas.draw_idle()
    except Exception as err:
        logger.warning("Unable to refresh selection overlay: %s", err)
