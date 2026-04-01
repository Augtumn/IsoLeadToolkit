"""Isochron calculation and selection follow-up handlers."""
from __future__ import annotations

from visualization.plotting.isochron import resolve_isochron_errors as _resolve_isochron_errors

from .shared import (
    SELECTED_ISOCHRON_USE_CASE,
    app_state,
    df_global,
    logger,
    state_gateway,
)


def calculate_selected_isochron() -> None:
    """Calculate isochron age for selected data points."""
    try:
        from data.geochemistry import york_regression, calculate_pbpb_age_from_ratio, engine

        payload = SELECTED_ISOCHRON_USE_CASE.execute(
            df=df_global(),
            selected_indices=list(app_state.selected_indices),
            render_mode=app_state.render_mode,
            resolve_errors=_resolve_isochron_errors,
            york_regression=york_regression,
            calculate_age=calculate_pbpb_age_from_ratio,
            get_engine_parameters=engine.get_parameters,
        )

        if payload is None:
            logger.warning('Isochron calculation did not produce a valid result.')
            state_gateway.set_selected_isochron_data(None)
            return

        state_gateway.set_selected_isochron_data(payload)
        logger.info(
            'Isochron calculated: Age = %.1f Ma, n = %d, R² = %.4f',
            payload.get('age', 0.0),
            payload.get('n_points', 0),
            payload.get('r_squared', 0.0),
        )
        logger.info(
            'Slope = %.6f, Intercept = %.6f',
            payload.get('slope', 0.0),
            payload.get('intercept', 0.0),
        )

    except Exception as err:
        logger.warning('Isochron calculation failed: %s', err)
        state_gateway.set_selected_isochron_data(None)


def refresh_isochron_after_selection() -> None:
    """Recalculate isochron if selection changes in Pb evolution mode."""
    if app_state.render_mode != 'PB_EVOL_76':
        return

    is_active = bool(
        getattr(app_state, 'show_isochrons', False)
        or getattr(app_state, 'selected_isochron_data', None)
        or app_state.selection_tool == 'isochron'
    )
    if not is_active:
        return

    had_selected = app_state.selected_isochron_data is not None
    selected = app_state.selected_indices
    if selected and len(selected) >= 2:
        calculate_selected_isochron()
    else:
        state_gateway.set_selected_isochron_data(None)
        if had_selected:
            state_gateway.set_show_isochrons(True)

    if getattr(app_state, 'show_isochrons', False) or app_state.selected_isochron_data is not None or had_selected:
        try:
            from visualization.events import on_slider_change
            on_slider_change()
        except Exception as err:
            logger.warning('Failed to refresh plot after isochron update: %s', err)
