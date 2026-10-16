"""The embedding-family modes, on the shared render sequence.

Eleven modes - the four computed algorithms and the seven geochemistry and ternary ones - share one
render path and differ in what they compute, how they configure their axes, what they overlay and how
they are named. That path was one function branching on the algorithm; here the branching is a mode
attribute and each piece is delegated to the helper that already owns it, so the path exists once.
"""
from __future__ import annotations

import logging
from typing import Any

from ..context import RenderContext
from ..pipeline import Ink
from ..registry import Adapter, register

logger = logging.getLogger(__name__)

#: The modes this adapter family draws.
EMBEDDING_MODES: tuple[str, ...] = (
    "UMAP", "tSNE", "PCA", "RobustPCA", "Ternary", "V1V2",
    "PB_EVOL_76", "PB_EVOL_86", "PLUMBOTECTONICS_76", "PLUMBOTECTONICS_86",
    "PB_MU_AGE", "PB_KAPPA_AGE",
)


class EmbeddingAdapter(Adapter):
    """One embedding-family mode, drawn by the shared embedding helpers."""

    def __init__(self, mode: str) -> None:
        self.mode = str(mode)

    @property
    def algorithm(self) -> str:
        from ..embedding.algorithm import normalize_algorithm

        return normalize_algorithm(self.mode)

    def token(self, context: RenderContext) -> tuple[Any, ...]:
        return ("embedding", self.algorithm)

    def axes_dimensions(self, context: RenderContext) -> Any:
        from ..embedding.algorithm import resolve_target_dimensions

        return resolve_target_dimensions(self.algorithm)

    def validate(self, context: RenderContext) -> None:
        if context.figure is None:
            raise ValueError("the plot figure is not initialized")
        if self.algorithm == "TERNARY" and len(context.columns_ternary) != 3:
            raise ValueError("the ternary mode needs exactly three selected columns")

    def prepare(self, context: RenderContext) -> Any:
        from ..embedding.algorithm import compute_embedding, resolve_embedding_params
        from ..embedding.dataframe import prepare_plot_dataframe

        umap, tsne, pca, robust = resolve_embedding_params(
            context.umap_params, context.tsne_params, context.pca_params, context.robust_pca_params
        )
        embedding = compute_embedding(
            self.algorithm,
            precomputed_embedding=context.precomputed_embedding,
            precomputed_meta=context.precomputed_meta,
            umap_params=umap, tsne_params=tsne, pca_params=pca, robust_pca_params=robust,
        )
        if embedding is None:
            logger.error("Failed to compute %s embedding", self.mode)
            return False
        prepared = prepare_plot_dataframe(context.group_col, self.algorithm, embedding)
        if prepared is None:
            logger.error("Failed to prepare the plot dataframe for %s", self.mode)
            return False
        return prepared

    def configure_axes(self, context: RenderContext, prepared: Any) -> None:
        from core import app_state, state_gateway

        if self.algorithm != "TERNARY":
            try:
                context.axes.set_aspect("auto")
                context.axes.set_autoscale_on(True)
            except Exception as err:
                logger.warning("Could not configure the axes for %s: %s", self.mode, err)
            return

        from ...ternary import configure_ternary_axis, prepare_ternary_components

        df_plot, _unique_cats = prepared
        ts = df_plot["_emb_t"].to_numpy(dtype=float, copy=False)
        ls = df_plot["_emb_l"].to_numpy(dtype=float, copy=False)
        rs = df_plot["_emb_r"].to_numpy(dtype=float, copy=False)
        t_norm, l_norm, r_norm = prepare_ternary_components(ts, ls, rs)
        df_plot["_emb_tn"] = t_norm
        df_plot["_emb_ln"] = l_norm
        df_plot["_emb_rn"] = r_norm
        tmin, tmax, lmin, lmax, rmin, rmax = configure_ternary_axis(
            context.axes, t_norm, l_norm, r_norm,
            labels=list(context.columns_ternary),
            auto_zoom=bool(app_state.ternary_auto_zoom),
            raw_values=(ts, ls, rs),
        )
        state_gateway.set_ternary_ranges(
            {"t": (tmin, tmax), "l": (lmin, lmax), "r": (rmin, rmax)}
        )

    def groups(self, context: RenderContext, prepared: Any) -> list[Any]:
        _df_plot, unique_cats = prepared
        return list(unique_cats)

    def draw(self, context: RenderContext, prepared: Any) -> Ink:
        from core import app_state

        from ..common.scatter import _render_scatter_groups
        from ..kde import _render_kde_overlay

        df_plot, unique_cats = prepared
        palette = app_state.current_palette
        _render_kde_overlay(self.algorithm, df_plot, context.group_col, unique_cats, palette)
        scatters = _render_scatter_groups(
            self.algorithm, df_plot, context.group_col, unique_cats, context.point_size,
            palette=palette,
        )
        if scatters is None:
            if len(df_plot) == 0:
                logger.warning(
                    "No point belongs to a visible group; the plot stays empty until a group is "
                    "ticked in the legend."
                )
                return Ink.EMPTY
            logger.warning("No scatter groups rendered for %s", self.mode)
            return Ink.FAILED
        return Ink.DRAWN

    def legend(self, context: RenderContext, prepared: Any) -> None:
        from core import app_state

        from ..common.legend import _render_legend

        _df_plot, unique_cats = prepared
        _render_legend(
            self.algorithm, context.group_col, unique_cats, list(app_state.scatter_collections)
        )

    def decorate(self, context: RenderContext, prepared: Any) -> None:
        from ..common.title import _render_title_labels
        from ..embedding.algorithm import resolve_embedding_params

        umap, tsne, pca, robust = resolve_embedding_params(
            context.umap_params, context.tsne_params, context.pca_params, context.robust_pca_params
        )
        _render_title_labels(self.algorithm, context.group_col, umap, tsne, pca, robust)

    def finish(self, context: RenderContext, prepared: Any) -> None:
        from core import app_state, state_gateway

        from ...event_bridge import refresh_selection_overlay_safe
        from ...tooltip import raise_tooltip_above_data
        from ..common.legend import _notify_legend_panel
        from ..geo_layers import _render_geo_overlays

        df_plot, unique_cats = prepared
        if len(df_plot) == 0:
            _notify_legend_panel(context.group_col, [], [])

        if context.show_marginal_kde and self.algorithm != "TERNARY":
            import visualization.plotting.kde as kde_utils

            try:
                if getattr(context.axes, "name", "") != "3d":
                    kde_utils.clear_marginal_axes()
                    kde_utils.draw_marginal_kde(
                        context.axes, df_plot, context.group_col,
                        app_state.current_palette, unique_cats,
                    )
            except Exception as kde_err:
                logger.warning("Failed to render marginal KDE: %s", kde_err)

        # No previous-view argument: the sequence owns the view, so the layer must not touch it.
        _render_geo_overlays(self.algorithm, None, None, None, None)
        context.axes.tick_params()
        state_gateway.set_annotation(
            context.axes.annotate(
                "", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#cbd5e1", alpha=0.95),
                arrowprops=dict(arrowstyle="->", color="#475569"),
            ),
        )
        app_state.annotation.set_visible(False)
        raise_tooltip_above_data(context.axes, app_state.annotation)
        try:
            refresh_selection_overlay_safe()
        except Exception as err:
            logger.warning("Failed to restore the selection overlay: %s", err)


def register_embedding_modes() -> tuple[str, ...]:
    """Put an adapter for every embedding-family mode on the registry."""
    for mode in EMBEDDING_MODES:
        register(EmbeddingAdapter(mode))
    return EMBEDDING_MODES
