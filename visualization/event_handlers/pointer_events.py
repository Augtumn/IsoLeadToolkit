"""Hover and click handlers for point interaction."""
from __future__ import annotations

import pandas as pd

from .overlay import refresh_selection_overlay
from .shared import (
    SELECTION_USE_CASE,
    TOOLTIP_CONTENT_USE_CASE,
    app_state,
    df_global,
    logger,
    state_gateway,
    translate,
)


def _resolve_sample_index(event: object) -> int | None:
    """Attempt to map a Matplotlib event to a sample index."""
    try:
        for sc in app_state.scatter_collections:
            if sc is None:
                continue
            try:
                cont, ind = sc.contains(event)
            except Exception:
                continue
            if not cont or 'ind' not in ind or not ind['ind']:
                continue
            idx_in_scatter = int(ind['ind'][0])
            sample_idx = app_state.artist_to_sample.get((id(sc), idx_in_scatter))
            if sample_idx is not None:
                return sample_idx

        if event is not None and event.xdata is not None and event.ydata is not None:
            return SELECTION_USE_CASE.nearest_sample_index(
                app_state.sample_coordinates,
                x=float(event.xdata),
                y=float(event.ydata),
            )
    except Exception:
        return None
    return None


def on_hover(event) -> None:
    """Handle mouse hover events."""
    try:
        if app_state.render_mode == '3D':
            return

        if event is None or not hasattr(event, 'inaxes'):
            return

        if event.inaxes != app_state.ax or app_state.annotation is None:
            return
        if not getattr(app_state, 'show_tooltip', True):
            try:
                app_state.annotation.set_visible(False)
            except Exception:
                pass
            return

        visible = False

        for sc in app_state.scatter_collections:
            if sc is None:
                continue

            try:
                cont, ind = sc.contains(event)
                if not cont or not ind or 'ind' not in ind or len(ind['ind']) == 0:
                    continue

                idx_in_scatter = int(ind['ind'][0])
                sample_idx = app_state.artist_to_sample.get((id(sc), idx_in_scatter))
                if sample_idx is None:
                    continue

                offsets = sc.get_offsets()
                if offsets is None or len(offsets) <= idx_in_scatter:
                    continue

                x, y = offsets[idx_in_scatter]
                x, y = float(x), float(y)

                try:
                    df = df_global()
                    if df is None:
                        continue
                    row = df.loc[sample_idx]
                    if isinstance(row, pd.DataFrame):
                        row = row.iloc[0]
                except KeyError:
                    continue

                txt = TOOLTIP_CONTENT_USE_CASE.build_text(
                    row=row,
                    df_columns=df.columns,
                    sample_idx=sample_idx,
                    tooltip_columns=getattr(app_state, 'tooltip_columns', None),
                    selected=sample_idx in app_state.selected_indices,
                    selected_status_label=translate('Status: Selected'),
                )

                app_state.annotation.xy = (x, y)
                app_state.annotation.set_text(txt)
                app_state.annotation.set_visible(True)
                visible = True
                break

            except Exception:
                continue

        if not visible:
            try:
                app_state.annotation.set_visible(False)
            except Exception:
                pass

    except Exception:
        pass


def on_click(event) -> None:
    """Handle mouse click events for interactive selection."""
    try:
        if app_state.render_mode == '3D':
            return

        if event is None or not hasattr(event, 'inaxes'):
            return

        if event.inaxes != app_state.ax:
            return

        if not hasattr(event, 'button') or event.button != 1:
            return

        if app_state.selection_mode:
            if getattr(event, 'dblclick', False):
                sample_idx = _resolve_sample_index(event)
                if sample_idx is None:
                    logger.warning('No point detected for selection.')
                    return

                try:
                    df = df_global()
                    if df is None:
                        lab_label = str(sample_idx)
                    else:
                        row = df.loc[sample_idx]
                        lab_value = row['Lab No.'] if 'Lab No.' in df.columns else sample_idx
                        if pd.notna(lab_value):
                            lab_label = str(lab_value)
                        else:
                            lab_label = str(sample_idx)
                except Exception:
                    lab_label = str(sample_idx)

                if sample_idx in app_state.selected_indices:
                    state_gateway.remove_selected_indices([sample_idx])
                    logger.info('Deselected sample %s.', lab_label)
                else:
                    state_gateway.add_selected_indices([sample_idx])
                    logger.info('Selected sample %s.', lab_label)

                refresh_selection_overlay()
            return

        logger.info(translate('Click export has been removed. Use the control panel export instead.'))
        return

    except Exception as err:
        logger.warning('Click handler error: %s', err)
