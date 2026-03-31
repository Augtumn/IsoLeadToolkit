"""Session loading and render-mode validation helpers for Qt startup."""

import logging

from core import CONFIG, app_state, load_session_params, set_language, state_gateway, validate_language

logger = logging.getLogger(__name__)


class Qt5AppSessionMixin:
    """Session restoration methods for Qt5Application."""

    def _load_session(self):
        """Load persisted session parameters and normalize language."""
        logger.info("Loading session parameters...")
        session_data = load_session_params()

        requested_language = None
        if session_data:
            requested_language = session_data.get("language")
        if not requested_language:
            requested_language = app_state.language or CONFIG.get("default_language")
        if not validate_language(requested_language):
            requested_language = CONFIG.get("default_language", "en")
        set_language(requested_language)

        return session_data

    def _restore_session_state(self, session_data):
        """Restore plotting and UI state from persisted session data."""
        if not session_data:
            state_gateway.set_attrs({"algorithm": "UMAP", "render_mode": "UMAP"})
            logger.info("No session data, using default algorithm: UMAP")
            return

        state_gateway.set_attr("algorithm", session_data.get("algorithm", "UMAP"))
        logger.info("Algorithm from session: %s", app_state.algorithm)

        app_state.umap_params.update(session_data.get("umap_params", {}))
        app_state.tsne_params.update(session_data.get("tsne_params", {}))
        state_gateway.set_attr("point_size", session_data.get("point_size", app_state.point_size))

        preserve_import_mode = bool(getattr(app_state, "preserve_import_render_mode", False))
        render_mode = session_data.get("render_mode")
        if not render_mode:
            legacy_mode = session_data.get("plot_mode")
            if legacy_mode == "3D":
                render_mode = "3D"
            elif legacy_mode == "2D":
                render_mode = "2D"
            else:
                render_mode = app_state.algorithm

        if not preserve_import_mode:
            state_gateway.set_attr("render_mode", render_mode or "UMAP")
        else:
            logger.info("Preserving render mode selected during import: %s", app_state.render_mode)

        state_gateway.set_selected_2d_columns(session_data.get("selected_2d_cols", []))
        state_gateway.set_selected_3d_columns(session_data.get("selected_3d_cols", []))

        saved_cols = session_data.get("tooltip_columns")
        if saved_cols is not None:
            state_gateway.set_attr("tooltip_columns", saved_cols)
            logger.debug("Restored tooltip columns from session: %s", saved_cols)
        else:
            logger.debug("No tooltip columns in session, using default: %s", app_state.tooltip_columns)

        state_gateway.set_attr("ui_theme", session_data.get("ui_theme") or "Modern Light")
        logger.info("Restored UI theme: %s", app_state.ui_theme)

        session_group_col = session_data.get("group_col")
        if session_group_col and session_group_col in app_state.group_cols:
            state_gateway.set_last_group_col(session_group_col)
            logger.info("Group column restored from session: %s", app_state.last_group_col)

    def _validate_render_mode(self):
        """Validate render mode against currently loaded numeric columns."""
        num_numeric_cols = len(app_state.data_cols)

        if app_state.render_mode == "3D" and num_numeric_cols < 3:
            if num_numeric_cols >= 2:
                logger.info("Not enough numeric columns for 3D; switching to 2D scatter.")
                state_gateway.set_render_mode("2D")
            else:
                logger.info("Not enough numeric columns for 3D; switching to UMAP.")
                state_gateway.set_render_mode("UMAP")

        if app_state.render_mode == "2D" and num_numeric_cols < 2:
            logger.info("Not enough numeric columns for 2D; switching to UMAP.")
            state_gateway.set_render_mode("UMAP")

        if app_state.render_mode == "3D":
            if num_numeric_cols == 3:
                state_gateway.set_selected_3d_columns(app_state.data_cols[:3])
            else:
                valid_cols = [col for col in app_state.selected_3d_cols if col in app_state.data_cols][:3]
                if len(valid_cols) == 3:
                    state_gateway.set_selected_3d_columns(valid_cols)
                else:
                    state_gateway.set_selected_3d_columns([])
                    logger.info(
                        "Stored 3D column selection invalid or incomplete; will prompt user on demand."
                    )

        if app_state.render_mode == "2D":
            if num_numeric_cols == 2:
                state_gateway.set_selected_2d_columns(app_state.data_cols[:2])
            else:
                valid_2d = [col for col in app_state.selected_2d_cols if col in app_state.data_cols][:2]
                if len(valid_2d) == 2:
                    state_gateway.set_selected_2d_columns(valid_2d)
                else:
                    state_gateway.set_selected_2d_columns([])
                    logger.info(
                        "Stored 2D column selection invalid or incomplete; will prompt user on demand."
                    )

        if app_state.render_mode in ("UMAP", "tSNE"):
            state_gateway.set_attr("algorithm", "UMAP" if app_state.render_mode == "UMAP" else "tSNE")
