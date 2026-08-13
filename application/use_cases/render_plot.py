"""Application use case for plot rendering orchestration."""

from __future__ import annotations

import logging
from typing import Any, Callable

from core import state_gateway

logger = logging.getLogger(__name__)

_ASYNC_EMBEDDING_ALGORITHMS = {"UMAP", "tSNE", "PCA", "RobustPCA"}


class RenderPlotUseCase:
    """Coordinate render-mode validation and plot dispatch."""

    def __init__(
        self,
        *,
        state: Any,
        get_df_global: Callable[[], Any],
        get_data_cols: Callable[[], list[str]],
        get_group_cols: Callable[[], list[str]],
        sync_render_mode: Callable[[str], None],
        cancel_embedding_task: Callable[[str], None],
        start_async_embedding_render: Callable[[str], bool],
        plot_embedding: Callable[..., bool],
        plot_2d_data: Callable[..., bool],
        plot_3d_data: Callable[..., bool],
        refresh_selection_overlay: Callable[[], None],
        sync_selection_tools: Callable[[], None],
        notify_selection_ui: Callable[[], None],
        disable_rectangle_selector: Callable[[], None],
        state_write: Any = state_gateway,
    ) -> None:
        self._state = state
        self._state_write = state_write
        self._df_global = get_df_global
        self._data_cols = get_data_cols
        self._group_cols = get_group_cols
        self._sync_render_mode = sync_render_mode
        self._cancel_embedding_task = cancel_embedding_task
        self._start_async_embedding_render = start_async_embedding_render
        self._plot_embedding = plot_embedding
        self._plot_2d_data = plot_2d_data
        self._plot_3d_data = plot_3d_data
        self._refresh_selection_overlay = refresh_selection_overlay
        self._sync_selection_tools = sync_selection_tools
        self._notify_selection_ui = notify_selection_ui
        self._disable_rectangle_selector = disable_rectangle_selector

    def execute(self) -> None:
        """Run a full render cycle for current app state."""
        df = self._df_global()
        if df is None or len(df) == 0:
            logger.warning("No data available")
            return

        group_col = self._resolve_group_col()
        if group_col is None:
            logger.warning("No group columns available")
            return

        render_mode = self._state.render_mode
        selected_columns_3d = list(getattr(self._state, "selected_3d_cols", []))
        selected_columns_2d = list(getattr(self._state, "selected_2d_cols", []))

        self._sync_visible_groups(group_col)

        render_mode, selected_columns_2d, selected_columns_3d = self._validate_render_columns(
            render_mode,
            selected_columns_2d,
            selected_columns_3d,
        )
        self._sync_render_mode(render_mode)

        rendered_ok, pending_async = self._dispatch_render(
            group_col,
            selected_columns_2d,
            selected_columns_3d,
        )

        if pending_async:
            logger.debug("Render deferred to async embedding task")
            return

        if rendered_ok:
            logger.debug("Plot rendered successfully, calling draw_idle")
            self._refresh_selection_overlay()
            self._sync_selection_tools()
            self._notify_selection_ui()
            try:
                self._state.fig.canvas.draw_idle()
                self._state.fig.canvas.flush_events()
            except Exception as err:
                logger.warning("Draw error: %s", err)
        else:
            logger.warning("Plot rendering failed")
            self._handle_render_fallback(group_col)

        self._state_write.set_initial_render_done(True)

    def _resolve_group_col(self) -> str | None:
        group_col = getattr(self._state, "last_group_col", None)
        group_cols = self._group_cols()
        if not group_col or group_col not in group_cols:
            if group_cols:
                group_col = group_cols[0]
                logger.debug("Using default group_col: %s", group_col)
            else:
                return None
        return group_col

    def _sync_visible_groups(self, group_col: str) -> None:
        try:
            df = self._df_global()
            if df is None:
                all_groups = []
            else:
                df_groups_source = df[group_col].fillna("Unknown").astype(str)
                all_groups = sorted(df_groups_source.unique())
        except Exception:
            all_groups = []

        self._state_write.sync_available_and_visible_groups(all_groups)

    def _validate_render_columns(
        self,
        render_mode: str,
        selected_columns_2d: list[str],
        selected_columns_3d: list[str],
    ) -> tuple[str, list[str], list[str]]:
        df = self._df_global()
        data_cols = self._data_cols()

        if render_mode == "3D":
            available_cols = [c for c in data_cols if df is not None and c in df.columns]
            logger.debug("Available numeric columns for 3D: %s", available_cols)
            if len(available_cols) < 3:
                logger.warning("Not enough numeric columns for 3D view; reverting to 2D")
                render_mode = "2D"
            else:
                preselected = [c for c in selected_columns_3d if c in available_cols]
                if len(preselected) == 3:
                    selected_columns_3d = preselected
                elif len(available_cols) >= 3:
                    selected_columns_3d = available_cols[:3]
                    self._state_write.set_selected_3d_columns(selected_columns_3d, confirmed=False)
                    logger.info("Using default 3D columns: %s", selected_columns_3d)

        if render_mode == "2D":
            available_cols_2d = [c for c in data_cols if df is not None and c in df.columns]
            logger.debug("Available numeric columns for 2D: %s", available_cols_2d)
            if len(available_cols_2d) < 2:
                logger.warning("Not enough numeric columns for 2D view; falling back to UMAP")
                render_mode = "UMAP"
            else:
                preselected_2d = [c for c in selected_columns_2d if c in available_cols_2d][:2]
                if len(preselected_2d) == 2:
                    selected_columns_2d = preselected_2d
                elif len(available_cols_2d) >= 2:
                    selected_columns_2d = available_cols_2d[:2]
                    self._state_write.set_selected_2d_columns(selected_columns_2d, confirmed=False)
                    logger.info("Using default 2D columns: %s", selected_columns_2d)

        if render_mode == "Ternary":
            available_cols_ternary = [c for c in data_cols if df is not None and c in df.columns]
            if len(available_cols_ternary) < 3:
                logger.warning("Not enough numeric columns for Ternary view; falling back to UMAP")
                render_mode = "UMAP"
            else:
                preselected = getattr(self._state, "selected_ternary_cols", [])
                valid_preselected = [c for c in preselected if c in available_cols_ternary]
                if len(valid_preselected) == 3:
                    if not getattr(self._state, "selected_ternary_confirmed", False):
                        self._state_write.set_selected_ternary_columns(
                            valid_preselected,
                            confirmed=False,
                        )
                elif len(available_cols_ternary) >= 3:
                    self._state_write.set_selected_ternary_columns(
                        available_cols_ternary[:3],
                        confirmed=False,
                    )

        return render_mode, selected_columns_2d, selected_columns_3d

    def _dispatch_render(
        self,
        group_col: str,
        selected_columns_2d: list[str],
        selected_columns_3d: list[str],
    ) -> tuple[bool, bool]:
        if self._state.render_mode == "3D":
            if getattr(self._state, "selection_mode", False):
                self._state_write.disable_selection_mode()
                self._disable_rectangle_selector()
                self._refresh_selection_overlay()
                self._notify_selection_ui()
                logger.info("Selection mode automatically disabled for 3D view.")
            if len(selected_columns_3d) != 3:
                logger.warning("Invalid 3D column selection; skipping plot")
                return False, False
            self._cancel_embedding_task("switch_to_3d")
            logger.debug("Rendering 3D plot with columns=%s", selected_columns_3d)
            return self._plot_3d_data(group_col, selected_columns_3d, size=self._state.point_size), False

        if self._state.render_mode == "2D":
            if len(selected_columns_2d) != 2:
                logger.warning("Invalid 2D column selection; skipping plot")
                return False, False
            self._cancel_embedding_task("switch_to_2d")
            logger.debug("Rendering 2D plot with columns=%s", selected_columns_2d)
            is_kde = bool(getattr(self._state, "show_kde", False) or getattr(self._state, "show_2d_kde", False))
            return self._plot_2d_data(
                group_col,
                selected_columns_2d,
                size=self._state.point_size,
                show_kde=is_kde,
            ), False

        algorithm = self._state.render_mode
        if algorithm in _ASYNC_EMBEDDING_ALGORITHMS:
            # Returns (rendered_ok, pending_async): a cache hit renders
            # synchronously (pending=False); otherwise a worker is started.
            return self._start_async_embedding_render(group_col)

        self._cancel_embedding_task("switch_to_sync_embedding")
        logger.debug("Calling plot_embedding with algorithm=%s, group_col=%s", algorithm, group_col)
        return (
            self._plot_embedding(
                group_col,
                algorithm,
                umap_params=self._state.umap_params,
                tsne_params=self._state.tsne_params,
                pca_params=self._state.pca_params,
                robust_pca_params=self._state.robust_pca_params,
                size=self._state.point_size,
            ),
            False,
        )

    def _handle_render_fallback(self, group_col: str) -> None:
        if self._state.render_mode not in ("2D", "3D"):
            return

        logger.info("Falling back to UMAP embedding for display")
        self._sync_render_mode("UMAP")
        fallback_ok = self._plot_embedding(
            group_col,
            "UMAP",
            umap_params=self._state.umap_params,
            tsne_params=self._state.tsne_params,
            size=self._state.point_size,
        )
        if fallback_ok:
            self._refresh_selection_overlay()
            self._sync_selection_tools()
            self._notify_selection_ui()
            try:
                self._state.fig.canvas.draw_idle()
                self._state.fig.canvas.flush_events()
            except Exception:
                pass
        else:
            logger.warning("Fallback UMAP plot also failed")