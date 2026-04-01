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
from ..ternary import configure_ternary_axis, prepare_ternary_components
from .embedding.algorithm import (
    compute_embedding,
    normalize_algorithm,
    resolve_embedding_params,
    resolve_target_dimensions,
)
from .embedding.dataframe import prepare_plot_dataframe
from .common.legend import _render_legend
from .common.scatter import _render_scatter_groups
from .common.title import _render_title_labels
from .geo_layers import _render_geo_overlays
from .kde import _render_kde_overlay

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
            if actual_algorithm != 'TERNARY':
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

            ts = df_plot['_emb_t'].to_numpy(dtype=float, copy=False)
            ls = df_plot['_emb_l'].to_numpy(dtype=float, copy=False)
            rs = df_plot['_emb_r'].to_numpy(dtype=float, copy=False)

            t_norm, l_norm, r_norm = prepare_ternary_components(ts, ls, rs)
            df_plot['_emb_tn'] = t_norm
            df_plot['_emb_ln'] = l_norm
            df_plot['_emb_rn'] = r_norm

            auto_zoom = bool(getattr(app_state, 'ternary_auto_zoom', True))
            tmin, tmax, lmin, lmax, rmin, rmax = configure_ternary_axis(
                app_state.ax,
                t_norm,
                l_norm,
                r_norm,
                labels=t_cols,
                auto_zoom=auto_zoom,
            )
            app_state.ternary_ranges = {
                't': (tmin, tmax),
                'l': (lmin, lmax),
                'r': (rmin, rmax),
            }

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
