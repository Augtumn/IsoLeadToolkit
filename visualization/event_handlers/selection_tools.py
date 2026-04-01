"""Rectangle/lasso tool lifecycle and mode switching handlers."""
from __future__ import annotations

from matplotlib.widgets import LassoSelector, RectangleSelector

from .isochron import refresh_isochron_after_selection
from .overlay import refresh_selection_overlay
from .shared import (
    SELECTION_MIN_SPAN,
    SELECTION_USE_CASE,
    app_state,
    logger,
    notify_selection_ui,
    state_gateway,
)


def _disable_rectangle_selector() -> None:
    selector = getattr(app_state, 'rectangle_selector', None)
    if selector is None:
        return
    try:
        selector.set_active(False)
    except Exception:
        pass


def _disable_lasso_selector() -> None:
    selector = getattr(app_state, 'lasso_selector', None)
    if selector is None:
        return
    try:
        selector.set_active(False)
    except Exception:
        pass


def _ensure_rectangle_selector() -> None:
    if not app_state.selection_mode or app_state.render_mode == '3D':
        _disable_rectangle_selector()
        return

    if app_state.selection_tool == 'lasso':
        _disable_rectangle_selector()
        return

    if app_state.ax is None:
        return

    selector = getattr(app_state, 'rectangle_selector', None)

    if selector is not None:
        try:
            # If the selector is bound to a different axes, rebuild it.
            if getattr(selector, 'ax', None) is not app_state.ax:
                try:
                    selector.disconnect_events()
                except Exception:
                    pass
                state_gateway.set_rectangle_selector(None)
                selector = None
            else:
                selector.set_active(True)
        except Exception:
            state_gateway.set_rectangle_selector(None)
            selector = None

    if selector is None:
        try:
            selector = RectangleSelector(
                app_state.ax,
                _handle_rectangle_select,
                useblit=True,
                button=[1],
                spancoords='data',
                interactive=False,
            )
            state_gateway.set_rectangle_selector(selector)
        except Exception as err:
            logger.warning('Unable to initialize rectangle selector: %s', err)
            state_gateway.set_rectangle_selector(None)


def _ensure_lasso_selector() -> None:
    if not app_state.selection_mode or app_state.render_mode == '3D':
        _disable_lasso_selector()
        return

    if app_state.selection_tool != 'lasso':
        _disable_lasso_selector()
        return

    if app_state.ax is None:
        return

    selector = getattr(app_state, 'lasso_selector', None)

    if selector is not None:
        try:
            if getattr(selector, 'ax', None) is not app_state.ax:
                try:
                    selector.disconnect_events()
                except Exception:
                    pass
                state_gateway.set_lasso_selector(None)
                selector = None
            else:
                selector.set_active(True)
        except Exception:
            state_gateway.set_lasso_selector(None)
            selector = None

    if selector is None:
        try:
            selector = LassoSelector(
                app_state.ax,
                _handle_lasso_select,
                button=[1],
            )
            state_gateway.set_lasso_selector(selector)
        except Exception as err:
            logger.warning('Unable to initialize lasso selector: %s', err)
            state_gateway.set_lasso_selector(None)


def _handle_rectangle_select(eclick, erelease) -> None:
    try:
        if not app_state.selection_mode or app_state.render_mode == '3D':
            return

        if any(val is None for val in (eclick.xdata, erelease.xdata, eclick.ydata, erelease.ydata)):
            return

        x_min, x_max = sorted([float(eclick.xdata), float(erelease.xdata)])
        y_min, y_max = sorted([float(eclick.ydata), float(erelease.ydata)])

        if abs(x_max - x_min) < SELECTION_MIN_SPAN or abs(y_max - y_min) < SELECTION_MIN_SPAN:
            return

        indices_in_box = SELECTION_USE_CASE.rectangle_indices(
            app_state.sample_coordinates,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
        )

        if not indices_in_box:
            return

        plan = SELECTION_USE_CASE.plan_toggle(app_state.selected_indices, indices_in_box)
        if plan.action == 'remove':
            state_gateway.remove_selected_indices(plan.indices)
            logger.info('Deselected %d samples via box selection.', len(indices_in_box))
        elif plan.action == 'add':
            state_gateway.add_selected_indices(plan.indices)
            logger.info('Selected %d samples via box selection.', len(indices_in_box))

        refresh_selection_overlay()
        notify_selection_ui()
        refresh_isochron_after_selection()
    except Exception as err:
        logger.warning('Rectangle selection failed: %s', err)


def _handle_lasso_select(vertices) -> None:
    try:
        if not app_state.selection_mode or app_state.render_mode == '3D':
            return

        if not vertices:
            return

        indices_in_shape = SELECTION_USE_CASE.lasso_indices(
            app_state.sample_coordinates,
            vertices,
        )

        if not indices_in_shape:
            return

        plan = SELECTION_USE_CASE.plan_toggle(app_state.selected_indices, indices_in_shape)
        if plan.action == 'remove':
            state_gateway.remove_selected_indices(plan.indices)
            logger.info('Deselected %d samples via custom shape.', len(indices_in_shape))
        elif plan.action == 'add':
            state_gateway.add_selected_indices(plan.indices)
            logger.info('Selected %d samples via custom shape.', len(indices_in_shape))

        refresh_selection_overlay()
        notify_selection_ui()
        refresh_isochron_after_selection()
    except Exception as err:
        logger.warning('Custom shape selection failed: %s', err)


def toggle_selection_mode(tool_type: str = 'export') -> None:
    """Toggle interactive selection mode (export/lasso/isochron)."""
    try:
        try:
            new_tool = SELECTION_USE_CASE.resolve_next_tool(
                app_state.selection_tool,
                tool_type,
                app_state.render_mode,
            )
        except ValueError:
            logger.warning('Selection mode is only available for 2D projections.')
            return

        if app_state.selection_tool:
            _disable_rectangle_selector()
            _disable_lasso_selector()
            if app_state.selected_indices and not getattr(app_state, 'draw_selection_ellipse', False):
                state_gateway.clear_selected_indices()
            if app_state.selection_tool == 'isochron':
                state_gateway.set_selected_isochron_data(None)

        state_gateway.set_selection_tool(new_tool)

        if app_state.selection_tool:
            logger.info("Selection tool '%s' enabled.", new_tool)
            if new_tool == 'lasso':
                _ensure_lasso_selector()
            else:
                _ensure_rectangle_selector()

            try:
                if app_state.fig.canvas.toolbar.mode == 'zoom rect':
                    app_state.fig.canvas.toolbar.zoom()
                elif app_state.fig.canvas.toolbar.mode == 'pan/zoom':
                    app_state.fig.canvas.toolbar.pan()
            except Exception:
                pass
        else:
            logger.info('Selection tool disabled.')
            _disable_rectangle_selector()
            _disable_lasso_selector()

        notify_selection_ui()
        refresh_selection_overlay()

        if new_tool is None and app_state.selection_tool is None:
            try:
                from visualization.events import on_slider_change

                on_slider_change()
            except Exception as err:
                logger.warning('Failed to refresh plot after disabling selection tool: %s', err)
    except Exception as err:
        logger.warning('Failed to toggle selection mode: %s', err)


def sync_selection_tools() -> None:
    """Ensure selection helpers stay in sync with current axes."""
    if app_state.selection_tool == 'lasso':
        _ensure_lasso_selector()
        _disable_rectangle_selector()
    elif app_state.selection_tool:
        _ensure_rectangle_selector()
        _disable_lasso_selector()
    else:
        _disable_rectangle_selector()
        _disable_lasso_selector()
