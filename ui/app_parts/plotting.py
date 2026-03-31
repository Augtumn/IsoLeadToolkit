"""Plot figure and event wiring helpers for Qt startup flow."""

import logging

from core import CONFIG, app_state, state_gateway

logger = logging.getLogger(__name__)


class Qt5AppPlottingMixin:
    """Plot construction and runtime event setup methods for Qt5Application."""

    def _create_plot_figure(self):
        """Create the main matplotlib figure and connect redraw hooks."""
        import matplotlib.pyplot as plt

        logger.info("Creating plot figure...")

        fig, ax = plt.subplots(figsize=CONFIG["figure_size"], constrained_layout=True)
        state_gateway.set_figure_axes(fig, ax)
        try:
            app_state.fig.set_constrained_layout_pads(w_pad=0.02, h_pad=0.02, wspace=0.02, hspace=0.02)
        except Exception:
            pass

        def _on_resize(event):
            try:
                if app_state.fig is None:
                    return
                app_state.fig.set_constrained_layout(True)
                try:
                    app_state.fig.set_constrained_layout_pads(
                        w_pad=0.02,
                        h_pad=0.02,
                        wspace=0.02,
                        hspace=0.02,
                    )
                except Exception:
                    pass
                app_state.fig.canvas.draw_idle()
            except Exception:
                pass

        try:
            app_state.fig.canvas.mpl_connect("resize_event", _on_resize)

            def _on_draw(event):
                try:
                    if getattr(app_state, "paleo_label_refreshing", False):
                        state_gateway.set_attr("paleo_label_refreshing", False)
                        return
                    from visualization.plotting import refresh_paleoisochron_labels

                    refresh_paleoisochron_labels()
                    if app_state.fig is not None and app_state.fig.canvas is not None:
                        state_gateway.set_attr("paleo_label_refreshing", True)
                        app_state.fig.canvas.draw_idle()
                except Exception:
                    state_gateway.set_attr("paleo_label_refreshing", False)

            app_state.fig.canvas.mpl_connect("draw_event", _on_draw)

            def _on_view_change(event):
                try:
                    from visualization.plotting import refresh_paleoisochron_labels

                    refresh_paleoisochron_labels()
                    if app_state.fig is not None and app_state.fig.canvas is not None:
                        app_state.fig.canvas.draw_idle()
                except Exception:
                    pass

            app_state.fig.canvas.mpl_connect("button_release_event", _on_view_change)
            app_state.fig.canvas.mpl_connect("scroll_event", _on_view_change)
        except Exception:
            pass

        logger.info("Plot figure created.")
        plt.ion()

    def _setup_control_panel(self):
        """Disable legacy control panel in menu-driven UI mode."""
        logger.info("Control panel disabled; using top menu dialogs.")
        self.control_panel = None
        import core.state as state

        state.control_panel = None
        state_gateway.set_attr("control_panel_ref", None)

    def _connect_event_handlers(self):
        """Connect interactive matplotlib handlers."""
        from visualization.events import on_click, on_hover, on_legend_click

        logger.info("Connecting event handlers...")
        app_state.fig.canvas.mpl_connect("motion_notify_event", on_hover)
        app_state.fig.canvas.mpl_connect("button_press_event", on_click)
        app_state.fig.canvas.mpl_connect("button_press_event", on_legend_click)
        logger.info("Event handlers connected.")

    def _render_initial_plot(self):
        """Render the initial plot after data and UI are ready."""
        from visualization.events import on_slider_change

        logger.info("Rendering initial plot...")
        on_slider_change()
        logger.info("Plot ready.")

    def _print_instructions(self):
        """Print startup interaction hints to log."""
        logger.info("Application Controls:")
        logger.info("  * Use the Control Panel window to adjust parameters")
        logger.info("  * Algorithm selector -> Choose UMAP or t-SNE")
        logger.info("  * Point size -> Adjust marker size")
        logger.info("  * Hover over points -> View Lab No. / Site / Period")
        logger.info("  * Left click point -> Export sample to CSV")
        logger.info("  * Click legend item -> Bring group to front")
        logger.info("Application started. Close the windows to exit.")
