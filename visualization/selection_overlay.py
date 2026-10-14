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


def _overlay_axes(state: Any) -> list[Any]:
    """Every axes the selection is drawn on: the panels, or the single active one.

    With several panels the selection has to be visible in all of them, or a point selected in
    one figure would look unselected in the next. An ordinary window has no panel records and
    gets exactly the one axes it always had.
    """
    axes: list[Any] = []
    for panel in getattr(state, "plot_panel_states", []) or []:
        axis = panel.get("ax")
        if axis is not None and not any(axis is seen for seen in axes):
            axes.append(axis)
    if not axes and state.ax is not None:
        axes.append(state.ax)
    return axes


def _panel_points(state, axis, indices, fallback_xs, fallback_ys):
    """Where *indices* really are in *axis*'s panel, from that panel's own artists.

    Using one panel's data coordinates on another panel drew a point that does not exist there:
    a different projection places the same sample elsewhere, or nowhere at all. The position comes
    from the artist that panel drew for the sample, and the caller's coordinates are only the
    fallback for a single-figure window with no panel record.
    """
    for panel in getattr(state, "plot_panel_states", []) or []:
        if panel.get("ax") is not axis:
            continue
        mapping = panel.get("sample_to_artist") or {}
        collections = list(panel.get("collections") or [])
        xs: list[float] = []
        ys: list[float] = []
        for idx in indices:
            pair = mapping.get(int(idx))
            if not pair:
                continue
            artist_id, position = pair
            for collection in collections:
                if id(collection) != artist_id:
                    continue
                try:
                    offsets = collection.get_offsets()
                    point = offsets[int(position)]
                    xs.append(float(point[0]))
                    ys.append(float(point[1]))
                except Exception as err:
                    logger.warning("Could not read a panel point: %s", err)
                break
        return xs, ys
    return list(fallback_xs), list(fallback_ys)


def _repaint_every_figure(state) -> None:
    """Repaint every panel, not only the one the single-figure reference points at.

    The overlay is built on each panel's axes, but only the active figure was repainted, so a
    selection appeared in one window while the others kept the previous picture - the reported
    "the panels do not synchronise".
    """
    figures: list[Any] = []
    for panel in getattr(state, "plot_panel_states", []) or []:
        axis = panel.get("ax") if isinstance(panel, dict) else None
        figure = getattr(axis, "figure", None)
        if figure is not None and figure not in figures:
            figures.append(figure)
    active = getattr(state, "fig", None)
    if active is not None and active not in figures:
        figures.append(active)
    for figure in figures:
        try:
            figure.canvas.draw_idle()
        except Exception as err:
            logger.warning("Could not repaint a panel after the selection changed: %s", err)


def refresh_selection_overlay_state(
    *,
    state: Any,
    state_write: Any,
) -> None:
    """Refresh selection overlay artists for current state."""
    try:
        # The overlay in the panels beyond the first is a runtime extra, not a registered field,
        # so it has to be cleared here whatever happens next - including the early returns.
        for extra in list(getattr(state, "selection_overlay_extras", []) or []):
            try:
                extra.remove()
            except Exception as err:
                logger.warning("refresh_selection_overlay_state failed: %s", err)
        state.selection_overlay_extras = []

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
        logger.info(
            "overlay coords: selected=%d drawable=%d coordinates_known=%d",
            len(state.selected_indices or ()),
            len(valid_indices),
            len(state.sample_coordinates or {}),
        )
        if not valid_indices:
            _repaint_every_figure(state)
            return

        xs = [state.sample_coordinates[idx][0] for idx in valid_indices]
        ys = [state.sample_coordinates[idx][1] for idx in valid_indices]
        should_draw_ellipse = state.show_ellipses or getattr(state, "draw_selection_ellipse", False)
        confidence = float(
            getattr(state, "confidence_level", None)
            or getattr(state, "ellipse_confidence", 0.95)
        )
        base_marker_size = getattr(state, "plot_marker_size", state.point_size)
        highlight_size = max(int(base_marker_size * 1.8), 20)
        axes = _overlay_axes(state)
        extras: list[Any] = []
        first_overlay = None
        first_ellipse = None

        for position, axis in enumerate(axes):
            current_xlim = axis.get_xlim()
            current_ylim = axis.get_ylim()
            # Each panel marks the sample where that panel drew it.
            panel_xs, panel_ys = _panel_points(state, axis, valid_indices, xs, ys)

            # Drawn whenever there is something selected: gating this on the selection tool meant a
            # double click marked nothing while no tool was active - the reported
            # "without the tool the point is not highlighted".
            if panel_xs:
                overlay = axis.scatter(
                    panel_xs,
                    panel_ys,
                    s=[highlight_size] * len(xs),
                    facecolors="none",
                    edgecolors="#f97316",
                    linewidths=1.6,
                    zorder=6,
                )
                if position == 0:
                    first_overlay = overlay
                else:
                    extras.append(overlay)

            if should_draw_ellipse and len(panel_xs) >= 3:
                try:
                    # Read the tracked confidence level (the 68/95/99% radios
                    # write it); state.ellipse_confidence is config-only and was
                    # never updated by the UI, making those radios inert.
                    ellipse = draw_confidence_ellipse(
                        np.array(panel_xs),
                        np.array(panel_ys),
                        axis,
                        confidence=confidence,
                        edgecolor="#f97316",
                        linestyle="--",
                        linewidth=2,
                        zorder=5,
                        alpha=0.8,
                    )
                    if position == 0:
                        first_ellipse = ellipse
                    elif ellipse is not None:
                        extras.append(ellipse)
                except Exception as err:
                    logger.warning("Failed to draw selection ellipse: %s", err)

            axis.set_xlim(current_xlim)
            axis.set_ylim(current_ylim)

        # The registered field keeps the first panel's artist, so everything that reads it is
        # unaffected; the rest live in a runtime list that is never persisted.
        state_write.set_selection_overlay(first_overlay)
        if first_ellipse is not None:
            state_write.set_selection_ellipse(first_ellipse)
        if should_draw_ellipse and len(xs) >= 3 and first_ellipse is not None:
            logger.info(
                "Drawn %.0f%% confidence ellipse for %d selected points.",
                confidence * 100,
                len(xs),
            )
        logger.info(
            "selection overlay built: selected=%d panel(s)=%d artists=%d "
            "first_panel_artists=%s",
            len(getattr(state, "selected_indices", ()) or ()),
            len(getattr(state, "plot_panel_states", []) or []),
            len(extras),
            [type(a).__name__ for a in extras[:4]],
        )
        state.selection_overlay_extras = extras

        _repaint_every_figure(state)
    except Exception as err:
        logger.warning("Unable to refresh selection overlay: %s", err)
