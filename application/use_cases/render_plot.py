"""Application use case for plot rendering orchestration."""

from __future__ import annotations

from core.render_modes import algorithm_modes

import logging
from typing import Any, Callable

from core import state_gateway

logger = logging.getLogger(__name__)

_ASYNC_EMBEDDING_ALGORITHMS = set(algorithm_modes())


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
        start_async_embedding_render: Callable[[str, str], tuple[bool, bool]],
        plot_embedding: Callable[..., bool],
        plot_2d_data: Callable[..., bool],
        plot_3d_data: Callable[..., bool],
        refresh_selection_overlay: Callable[[], None],
        sync_selection_tools: Callable[[], None],
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
        selected_columns_3d = list(self._state.selected_3d_cols)
        selected_columns_2d = list(self._state.selected_2d_cols)

        self._sync_visible_groups(group_col)

        render_mode, selected_columns_2d, selected_columns_3d = self._validate_render_columns(
            render_mode,
            selected_columns_2d,
            selected_columns_3d,
        )
        self._sync_render_mode(render_mode)

        panels = [str(panel) for panel in list(getattr(self._state, "plot_panels", []) or [])]
        if len(panels) <= 1:
            rendered_ok, pending_async = self._dispatch_render(
                group_col,
                selected_columns_2d,
                selected_columns_3d,
            )
        else:
            # The columns are validated for every mode a panel actually uses. Doing it once for the
            # mirrored mode meant a panel set to Ternary never had its columns defaulted, and the
            # compute reported "Ternary columns not selected" while that panel drew nothing.
            for panel_mode in dict.fromkeys(panels):
                self._validate_render_columns(
                    panel_mode, selected_columns_2d, selected_columns_3d
                )
            rendered_ok, pending_async = self._render_panels(
                panels,
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
            try:
                self._state.fig.canvas.draw_idle()
                self._state.fig.canvas.flush_events()
            except Exception as err:
                logger.warning("Draw error: %s", err)
        else:
            logger.warning("Plot rendering failed")
            self._handle_render_fallback(group_col)

        self._state_write.set_initial_render_done(True)

    def _render_panels(
        self,
        panels: list[str],
        group_col: str,
        selected_columns_2d: list[str],
        selected_columns_3d: list[str],
    ) -> tuple[bool, bool]:
        """Draw one figure per panel, each in its own mode, into its own axes.

        Each panel keeps the artists that belong to it and both directions of the sample map,
        which is what lets a hover in any panel find the same sample in the others. The first
        panel stays the active axes afterwards, so everything that reads ``app_state.ax`` keeps
        addressing the figure the user works in.
        """
        from core import state_gateway

        # One figure and one canvas per panel, built by the window; this layer only draws into
        # them, so the figures arrive through a runtime list rather than an import.
        windows = list(getattr(self._state, "plot_panel_windows", []) or [])
        if not windows:
            logger.warning("No panel windows to draw %d panel(s) into", len(panels))
            return False, False
        if len(windows) != len(panels):
            # The two lists must agree: the renderer is handed the panel list and looks the windows
            # up by it. Drawing a subset was rejected before as a half-drawn state, and the caller
            # that let them drift - switching one panel's mode - keeps them in step now.
            logger.warning(
                "No window for %d of %d panel(s); cannot draw them",
                len(panels) - len(windows),
                len(panels),
            )
            return False, False

        states: list[dict] = []
        rendered_ok = False
        pending_async = False
        for mode, record in zip(panels, windows):
            figure = record.get("figure")
            ax = record.get("axes")
            if figure is not None:
                # The plotters draw into the active figure; this window's figure is the panel's.
                state_gateway.set_figure(figure)
            state_gateway.set_axis(ax)
            # The legend frame belongs to this panel: the control panel keeps it with the panel in
            # use, and each panel draws with its own rather than with the last one set.
            legend = record.get("legend")
            if legend:
                try:
                    frames = {
                        key: value for key, value in legend.items() if key.startswith("legend_frame_")
                    }
                    if frames:
                        state_gateway.set_panel_style_updates(frames)
                    # The position keys are policy, not style: they go through their own setters.
                    if "legend_location" in legend:
                        state_gateway.set_legend_location(legend["legend_location"])
                    if "legend_position" in legend:
                        state_gateway.set_legend_position(legend["legend_position"])
                    # The nudge is that panel's own too, so a panel keeps the placement it was given.
                    if "legend_offset" in legend:
                        state_gateway.set_legend_offset(legend["legend_offset"])
                except Exception as err:
                    logger.warning("Could not apply a panel's legend style: %s", err)
            self._state.scatter_collections.clear()
            self._state.artist_to_sample.clear()
            ok, pending = self._dispatch_render(
                group_col, selected_columns_2d, selected_columns_3d, mode=mode
            )
            rendered_ok = rendered_ok or ok
            pending_async = pending_async or pending
            sample_to_artist: dict[int, tuple[int, int]] = {}
            for (artist_id, index), sample in self._state.artist_to_sample.items():
                sample_to_artist.setdefault(int(sample), (int(artist_id), int(index)))
            states.append(
                {
                    "mode": mode,
                    "ax": ax,
                    "collections": list(self._state.scatter_collections),
                    "artist_to_sample": dict(self._state.artist_to_sample),
                    "sample_to_artist": sample_to_artist,
                    # Per panel, like everything else in the record: the single-figure map is
                    # overwritten by every panel's render, so anything that edits a group's artist
                    # - colour, stacking - must use this panel's own map, or it edits the last
                    # panel's artist and the other panels keep the old look.
                    "group_to_scatter": dict(getattr(self._state, "group_to_scatter", None) or {}),
                }
            )

        self._state.plot_panel_states = states
        # The panels are equals, so none of them owns the state: the active one is mirrored into
        # the single-figure references for the code that still reads them, and a tool acts on that
        # panel. Mirroring the first panel instead is what made every tool act on the first one.
        active = next((record for record in windows if record.get("active")), windows[0])
        if active.get("figure") is not None:
            state_gateway.set_figure(active["figure"])
        state_gateway.set_axis(active["axes"])
        # What each panel ended up showing: a panel that renders blank can then be told from one
        # whose view was set to something empty.
        for record in windows:
            axis = record.get("axes")
            drawn = next(
                (len(state.get("collections") or []) for state in states if state.get("ax") is axis),
                0,
            )
            try:
                xlim = axis.get_xlim()
                ylim = axis.get_ylim()
                logger.info(
                    "Panel %s: xlim=(%.4g, %.4g) ylim=(%.4g, %.4g) artists=%d",
                    record.get("mode"),
                    xlim[0],
                    xlim[1],
                    ylim[0],
                    ylim[1],
                    drawn,
                )
            except Exception as err:
                logger.warning("Could not read a panel's view after the render: %s", err)
        self._state.scatter_collections[:] = list(states[0]["collections"])
        self._state.artist_to_sample.clear()
        self._state.artist_to_sample.update(states[0]["artist_to_sample"])
        return rendered_ok, pending_async

    def _resolve_group_col(self) -> str | None:
        group_col = self._state.last_group_col
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
        except KeyError:
            # The column is not in this dataset. Passing an empty list on would clear the groups the user
            # chose, because the handler drops visible groups that are no longer available.
            logger.warning("Cannot list the groups of %r: the column is not in the data.", group_col)
            return

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
                preselected = self._state.selected_ternary_cols
                valid_preselected = [c for c in preselected if c in available_cols_ternary]
                if len(valid_preselected) == 3:
                    if not self._state.selected_ternary_confirmed:
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
        mode: str | None = None,
    ) -> tuple[bool, bool]:
        # The mode is a parameter so one render cycle can draw several panels, each in its own
        # mode. Without it the active mode is used, which is the ordinary single-figure window.
        mode = str(mode or self._state.render_mode)
        if mode == "3D":
            if self._state.selection_mode:
                self._state_write.disable_selection_mode()
                self._disable_rectangle_selector()
                self._refresh_selection_overlay()
                logger.info("Selection mode automatically disabled for 3D view.")
            if len(selected_columns_3d) != 3:
                logger.warning("Invalid 3D column selection; skipping plot")
                return False, False
            self._cancel_embedding_task("switch_to_3d")
            logger.debug("Rendering 3D plot with columns=%s", selected_columns_3d)
            return self._plot_3d_data(group_col, selected_columns_3d, size=self._state.point_size), False

        if mode == "2D":
            if len(selected_columns_2d) != 2:
                logger.warning("Invalid 2D column selection; skipping plot")
                return False, False
            self._cancel_embedding_task("switch_to_2d")
            logger.debug("Rendering 2D plot with columns=%s", selected_columns_2d)
            is_kde = bool(self._state.show_kde or getattr(self._state, "show_2d_kde", False))
            return self._plot_2d_data(
                group_col,
                selected_columns_2d,
                size=self._state.point_size,
                show_kde=is_kde,
            ), False

        algorithm = mode
        if algorithm in _ASYNC_EMBEDDING_ALGORITHMS:
            # Returns (rendered_ok, pending_async): a cache hit renders
            # synchronously (pending=False); otherwise a worker is started. The mode travels with the
            # request: with several panels the one being drawn is not the one the state calls current,
            # and reading the state here rendered another panel's algorithm.
            return self._start_async_embedding_render(group_col, algorithm)

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
            try:
                self._state.fig.canvas.draw_idle()
                self._state.fig.canvas.flush_events()
            except Exception as err:
                logger.warning("_handle_render_fallback failed: %s", err)
        else:
            logger.warning("Fallback UMAP plot also failed")