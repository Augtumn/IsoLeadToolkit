"""Embedding plotting routines extracted from render facade."""
from __future__ import annotations

import logging
import traceback

import numpy as np

from core import app_state, state_gateway
from .. import kde as kde_utils
from ..event_bridge import refresh_selection_overlay_safe
from ..style import _apply_current_style, _enforce_plot_style
from ..core import (
    _ensure_axes,
    _build_group_palette,
)
from .embedding_algorithm import (
    compute_embedding,
    normalize_algorithm,
    resolve_embedding_params,
    resolve_target_dimensions,
)
from .embedding_dataframe import prepare_plot_dataframe
from .helpers import (
    _render_geo_overlays,
    _render_kde_overlay,
    _render_legend,
    _render_scatter_groups,
    _render_title_labels,
)

logger = logging.getLogger(__name__)

def plot_embedding(
    group_col: str,
    algorithm: str,
    umap_params: dict | None = None,
    tsne_params: dict | None = None,
    pca_params: dict | None = None,
    robust_pca_params: dict | None = None,
    size: int = 60,
    precomputed_embedding: np.ndarray | None = None,
    precomputed_meta: dict | None = None,
) -> bool:
    """Update plot with specified algorithm and parameters"""
    try:
        logger.debug("plot_embedding called: algorithm=%s, group_col=%s, size=%s", algorithm, group_col, size)

        if app_state.fig is None:
            logger.error("Plot axes not initialized")
            return False

        actual_algorithm = normalize_algorithm(algorithm)
        target_dims = resolve_target_dimensions(actual_algorithm)

        prev_ax = app_state.ax
        prev_embedding_type = getattr(app_state, 'last_embedding_type', None)
        prev_xlim = None
        prev_ylim = None
        if prev_ax is not None and getattr(prev_ax, 'name', '') != '3d':
            try:
                prev_xlim = prev_ax.get_xlim()
                prev_ylim = prev_ax.get_ylim()
            except Exception:
                prev_xlim = None
                prev_ylim = None

        _ensure_axes(dimensions=target_dims)

        if app_state.ax is None:
            logger.error("Failed to configure axes")
            return False

        # Apply style before clearing
        _apply_current_style()

        app_state.ax.clear()
        try:
            # Reset any prior aspect/scale settings (e.g., ternary plots) for 2D
            app_state.ax.set_aspect('auto')
            app_state.ax.set_autoscale_on(True)
        except Exception:
            pass
        _enforce_plot_style(app_state.ax)
        app_state.clear_plot_state()

        umap_params, tsne_params, pca_params, robust_pca_params = resolve_embedding_params(
            umap_params,
            tsne_params,
            pca_params,
            robust_pca_params,
        )

        logger.debug(
            "Using params - UMAP: %s, tSNE: %s, PCA: %s, RobustPCA: %s",
            umap_params, tsne_params, pca_params, robust_pca_params,
        )

        logger.debug("Actual algorithm (normalized): %s", actual_algorithm)
        embedding = compute_embedding(
            actual_algorithm,
            precomputed_embedding=precomputed_embedding,
            precomputed_meta=precomputed_meta,
            umap_params=umap_params,
            tsne_params=tsne_params,
            pca_params=pca_params,
            robust_pca_params=robust_pca_params,
        )

        if embedding is None:
            logger.error("Failed to compute %s embedding", algorithm)
            return False

        prepared = prepare_plot_dataframe(group_col, actual_algorithm, embedding)
        if prepared is None:
            return False
        df_plot, unique_cats = prepared

        new_palette = _build_group_palette(unique_cats)

        if actual_algorithm == 'TERNARY':
            t_cols = getattr(app_state, 'selected_ternary_cols', ['Top', 'Left', 'Right'])

            h = np.sqrt(3) / 2

            app_state.ax.plot([0, 1, 0.5, 0], [0, 0, h, 0], 'k-', linewidth=1.5, zorder=0)

            if getattr(app_state, 'plot_style_grid', False):
                grid_color = '#e2e8f0'
                for i in range(1, 10):
                    val = i * 0.1
                    app_state.ax.plot([val * 0.5, 1 - val * 0.5], [val * h, val * h], '-', color=grid_color, lw=0.6, zorder=0)

                    x1, y1 = (1 - val), 0
                    x2, y2 = (0.5 * (1 - val)), h * (1 - val)
                    app_state.ax.plot([x1, x2], [y1, y2], '-', color=grid_color, lw=0.6, zorder=0)

                    x3, y3 = val, 0
                    x4, y4 = (0.5 + 0.5 * val), h * (1 - val)
                    app_state.ax.plot([x3, x4], [y3, y4], '-', color=grid_color, lw=0.6, zorder=0)

            app_state.ax.text(0.5, h + 0.05, t_cols[0], ha='center', va='bottom', fontsize=10, fontweight='bold')
            app_state.ax.text(-0.05, -0.05, t_cols[1], ha='right', va='top', fontsize=10, fontweight='bold')
            app_state.ax.text(1.05, -0.05, t_cols[2], ha='left', va='top', fontsize=10, fontweight='bold')

            app_state.ax.axis('off')
            app_state.ax.set_aspect('equal')

            app_state.ax.set_xlim(-0.1, 1.1)
            app_state.ax.set_ylim(-0.1, h + 0.1)

        _render_kde_overlay(actual_algorithm, df_plot, group_col, unique_cats, new_palette)

        scatters = _render_scatter_groups(actual_algorithm, df_plot, group_col, unique_cats, size)
        show_marginal_kde = getattr(app_state, 'show_marginal_kde', False)
        if scatters is None:
            return False

        kde_utils.clear_marginal_axes()
        if show_marginal_kde and actual_algorithm != 'TERNARY':
            try:
                if getattr(app_state.ax, 'name', '') != '3d':
                    kde_utils.draw_marginal_kde(app_state.ax, df_plot, group_col, app_state.current_palette, unique_cats)
            except Exception as kde_err:
                logger.warning("Failed to render marginal KDE: %s", kde_err)

        _render_legend(actual_algorithm, group_col, unique_cats, scatters)
        _render_title_labels(actual_algorithm, group_col, umap_params, tsne_params, pca_params, robust_pca_params)
        _render_geo_overlays(actual_algorithm, prev_ax, prev_embedding_type, prev_xlim, prev_ylim)

        app_state.ax.tick_params()

        state_gateway.set_attr(
            'annotation',
            app_state.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#cbd5e1", alpha=0.95),
            arrowprops=dict(arrowstyle="->", color="#475569"),
            zorder=15,
            ),
        )
        app_state.annotation.set_visible(False)
        try:
            if app_state.annotation.arrow_patch is not None:
                app_state.annotation.arrow_patch.set_zorder(14)
        except Exception:
            pass

        try:
            refresh_selection_overlay_safe()
        except Exception as err:
            logger.warning("Failed to restore selection overlay: %s", err)

        return True

    except Exception as err:
        logger.error("Plot update failed: %s", err)
        traceback.print_exc()
        return False

