"""Shared state helpers and singletons for event handlers."""
from __future__ import annotations

import logging

from application import (
    SelectedIsochronUseCase,
    SelectionInteractionUseCase,
    TooltipContentUseCase,
)
from core import app_state, state_gateway, translate
from ..plotting.rendering.common.state_access import (
    _data_state as data_state,
    _df_global as df_global,
)

logger = logging.getLogger(__name__)

# Minimum box size to register a rectangle selection (data units)
SELECTION_MIN_SPAN = 1e-9
# Maximum distance (data units) for hover nearest-neighbor lookup
HOVER_DISTANCE_THRESHOLD = 0.15

SELECTION_USE_CASE = SelectionInteractionUseCase(
    hover_distance_threshold=HOVER_DISTANCE_THRESHOLD,
)
SELECTED_ISOCHRON_USE_CASE = SelectedIsochronUseCase()
TOOLTIP_CONTENT_USE_CASE = TooltipContentUseCase()


def notify_selection_ui() -> None:
    """Ask the control panel to refresh selection-related widgets."""
    panel = getattr(app_state, 'control_panel_ref', None)
    if panel is None:
        return

    update_fn = getattr(panel, 'update_selection_controls', None)
    if not callable(update_fn):
        return

    try:
        update_fn()
    except Exception as err:
        logger.warning('Unable to update selection controls: %s', err)
