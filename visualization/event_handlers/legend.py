"""Legend click interaction handlers."""
from __future__ import annotations
import logging

from typing import Any

from .shared import SELECTION_USE_CASE, app_state, logger, state_gateway

logger = logging.getLogger(__name__)


def on_legend_click(event: Any) -> None:
    """Handle legend click events and toggle group visibility."""
    try:
        if event is None or not hasattr(event, 'inaxes'):
            return

        if not hasattr(event, 'button') or event.button != 1:
            return

        legend = app_state.ax.get_legend()
        if legend is None or not app_state.scatter_collections:
            return

        try:
            contains, _ = legend.contains(event)
            if not contains:
                return
        except Exception:
            return

        leg_texts = legend.get_texts()
        scatter_labels = {sc.get_label(): sc for sc in app_state.scatter_collections if sc}

        for i, leg_text in enumerate(leg_texts):
            label = leg_text.get_text()
            if label not in scatter_labels:
                continue
            try:
                bbox = leg_text.get_window_extent()
                if event.x is None or event.y is None or not bbox.contains(event.x, event.y):
                    continue

                scatter = scatter_labels[label]
                new_visible = not scatter.get_visible()
                scatter.set_visible(new_visible)

                leg_text.set_alpha(1.0 if new_visible else 0.5)
                if i < len(legend.legendHandles):
                    legend.legendHandles[i].set_alpha(1.0 if new_visible else 0.5)

                visible_groups = SELECTION_USE_CASE.next_visible_groups(
                    current_visible_groups=(
                        list(app_state.visible_groups)
                        if app_state.visible_groups is not None
                        else None
                    ),
                    # app_state.current_groups is never populated; use the
                    # rendered group universe, otherwise a hide-click is a
                    # no-op and a show-click hides every other group.
                    all_groups=list(app_state.available_groups or app_state.current_palette.keys()),
                    target_group=label,
                    target_visible=new_visible,
                )
                state_gateway.set_visible_groups(visible_groups)

                logger.info('Toggled visibility for: %s to %s', label, new_visible)
                try:
                    app_state.fig.canvas.draw_idle()
                except Exception as err:
                    logger.warning("on_legend_click failed: %s", err)
                return
            except Exception as err:
                logger.warning("on_legend_click failed: %s", err)

    except Exception as err:
        logger.warning("on_legend_click failed: %s", err)
