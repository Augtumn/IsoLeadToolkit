"""Hover and click handlers for point interaction."""
from __future__ import annotations
import logging
import weakref

from typing import Any

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

from visualization.plotting.highlight import HoverHighlighter

#: Highlights the hovered point so it is visible under the cursor.
_hover_highlighter = HoverHighlighter()

logger = logging.getLogger(__name__)

#: One hover tooltip per figure, created on demand: a window showing several figures needs one in
#: each of them, or the tooltip appears in whichever figure happens to own the shared annotation.
#: Keyed by the figure itself, not by id(figure). An id is reused as soon as the old figure is collected, so a
#: panel built afterwards could inherit a tooltip belonging to a figure that no longer existed - the tooltip was
#: then written into a dead object and those panels showed none at all.
_figure_annotations: "weakref.WeakKeyDictionary[Any, Any]" = weakref.WeakKeyDictionary()


def _resolve_sample_index(event: object) -> int | None:
    """Attempt to map a Matplotlib event to a sample index, in the panel it happened in."""
    try:
        # The panel the event happened in owns the collections and the mapping to look in. Using
        # the single-figure ones resolved against the first panel, which is why a click or a
        # double click in another window found no sample at all.
        panel = _panel_for(getattr(event, "inaxes", None))
        collections = (
            list(panel.get("collections") or []) if panel is not None
            else list(app_state.scatter_collections)
        )
        mapping = (
            dict(panel.get("artist_to_sample") or {}) if panel is not None
            else dict(app_state.artist_to_sample)
        )

        for sc in collections:
            if sc is None:
                continue
            try:
                cont, ind = sc.contains(event)
            except Exception as err:
                logger.warning("Hit testing failed for a collection: %s", err)
                continue
            if not cont or 'ind' not in ind or not ind['ind']:
                continue
            idx_in_scatter = int(ind['ind'][0])
            sample_idx = mapping.get((id(sc), idx_in_scatter))
            if sample_idx is not None:
                return sample_idx

        # The coordinate fallback belongs to the active figure: the stored coordinates are the
        # ones that figure draws, and nearest-to-a-point means nothing in another projection.
        if panel is None and event is not None and event.xdata is not None and event.ydata is not None:
            return SELECTION_USE_CASE.nearest_sample_index(
                app_state.sample_coordinates,
                x=float(event.xdata),
                y=float(event.ydata),
            )
    except Exception as err:
        logger.warning("Could not resolve a sample index: %s", err)
        return None
    return None


def _panel_highlight_targets(sample_idx: int) -> list[tuple[Any, int]]:
    """Where *sample_idx* is drawn, one ``(collection, index)`` per panel that draws it.

    Built from the record each render leaves behind per panel, so a hover in one panel can
    enlarge the same sample in all of them. Empty for the ordinary single-figure window,
    where the caller's own collection is the only place the sample is drawn.
    """
    targets: list[tuple[Any, int]] = []
    for state in getattr(app_state, "plot_panel_states", []) or []:
        pair = (state.get("sample_to_artist") or {}).get(int(sample_idx))
        if not pair:
            continue
        artist_id, index = pair
        for collection in state.get("collections") or []:
            if id(collection) == artist_id:
                targets.append((collection, int(index)))
                break
    return targets


def _panel_for(axes: Any) -> dict | None:
    """The record of the panel drawn into *axes*, if any.

    The axes of a panel is not stable: switching its plot type clears the figure and builds a new one, and the
    record then points at axes that no longer exist. The figure lasts as long as the window does, so it is the
    second key - without it the panels whose axes had been rebuilt stopped resolving, and their tooltips and
    box selection did nothing.
    """
    states = list(getattr(app_state, "plot_panel_states", []) or [])
    for state in states:
        if state.get("ax") is axes:
            return state
    figure = getattr(axes, "figure", None)
    if figure is not None:
        for state in states:
            if state.get("figure") is figure:
                return state
    return None


def _annotation_for(figure: Any) -> Any:
    """The hover tooltip belonging to *figure*, created on first use.

    A window showing several figures has several figures, and an annotation belongs to one of
    them: sharing a single annotation meant the tooltip was drawn in whichever figure happened to
    own it rather than in the window being pointed at.
    """
    if figure is None:
        return None
    found = _figure_annotations.get(figure)
    if found is not None:
        # The cached tooltip is only usable while it is still attached to an axes of this figure. A render that
        # clears the figure takes its axes away, and the annotation is then orphaned: it exists, its axes is None,
        # and set_visible() draws nothing. That is why some panels showed no tooltip - the cache kept handing back
        # the orphan made by the previous render.
        attached = getattr(found, "axes", None)
        if attached is not None and getattr(attached, "figure", None) is figure:
            return found
        logger.info("hover: the cached tooltip was orphaned; building a new one for this figure")
    axis = figure.axes[0] if getattr(figure, "axes", None) else None
    if axis is None:
        return None
    try:
        # The same tooltip the renderers build, so the one for a second figure looks and behaves
        # identically: placed at the point with an offset, boxed and arrowed - not a bare
        # top-left text, which is what an earlier version of this helper wrongly created.
        found = axis.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#cbd5e1", alpha=0.95),
            arrowprops=dict(arrowstyle="->", color="#475569"),
        )
        # A tooltip must not take part in the layout: as an ordinary artist it widened the figure's tight bbox,
        # and the axes were re-laid-out whenever the box appeared - the view moved because the tooltip existed.
        found.set_in_layout(False)
        found.set_visible(False)
        # Raising it is what keeps the box above the data and the labels. The call sat after the handler's
        # `return None`, so it never ran and the tooltip could be drawn under the points.
        try:
            from visualization.plotting.tooltip import raise_tooltip_above_data

            raise_tooltip_above_data(axis, found)
        except Exception as err:
            logger.warning("Could not raise the hover annotation: %s", err)
    except Exception as err:
        logger.warning("Could not create the hover annotation: %s", err)
        return None
    _figure_annotations[figure] = found
    return found


def clear_hover_highlight() -> bool:
    """Hide the tooltip of the readout; the marked sample is left alone.

    The mark belongs to the double click that set it, not to hovering, so switching the readout
    off must not silently drop the sample being studied.
    """
    changed = False
    try:
        if app_state.annotation is not None and app_state.annotation.get_visible():
            app_state.annotation.set_visible(False)
            changed = True
    except Exception as err:
        logger.warning("Could not hide the hover annotation: %s", err)
    if changed:
        # Every panel can carry the mark, while the state's figure mirrors one panel: clearing
        # through it left the others showing the old mark.
        from visualization.events import repaint_panels

        repaint_panels()
    return changed


def on_hover(event: Any) -> None:
    """Handle mouse hover events."""
    try:
        if event is None or not hasattr(event, 'inaxes'):
            logger.info("click ignored: the event carries no inaxes (event=%s)", type(event).__name__)
            return

        panel = _panel_for(event.inaxes)
        if event.inaxes != app_state.ax and panel is None:
            return
        if panel is not None and str(panel.get("mode", "")).upper() == "3D":
            # A 3D panel has no hit testing; the others still do.
            return
        # Resolve and apply the highlight first, independently of the tooltip. Both checks that
        # used to stand here returned before the highlight ever ran: with several figures the
        # annotation belongs to another figure or does not exist yet, and the readout is off by
        # default - which is why the highlight never appeared.
        collections = (
            list(panel.get("collections") or []) if panel is not None
            else list(app_state.scatter_collections)
        )
        mapping = (
            dict(panel.get("artist_to_sample") or {}) if panel is not None
            else dict(app_state.artist_to_sample)
        )

        def _sample_under(event):
            for collection in collections:
                if collection is None:
                    continue
                try:
                    cont, ind = collection.contains(event)
                except Exception:
                    continue
                if not cont or not ind or 'ind' not in ind or len(ind['ind']) == 0:
                    continue
                found = mapping.get((id(collection), int(ind['ind'][0])))
                if found is not None:
                    return found, collection, int(ind['ind'][0])
            return None, None, None

        sample_under, under_collection, under_index = _sample_under(event)

        # The tooltip belongs to the figure being pointed at, not to a single shared annotation.
        hovered_figure = getattr(event.inaxes, "figure", None)
        annotation = app_state.annotation
        if hovered_figure is not None and getattr(annotation, "figure", None) is not hovered_figure:
            annotation = _annotation_for(hovered_figure)

        if not app_state.show_tooltip:
            if annotation is not None:
                try:
                    annotation.set_visible(False)
                except Exception as err:
                    logger.warning("on_hover failed: %s", err)
            if _hover_highlighter.clear():
                from visualization.events import repaint_panels

                repaint_panels()
            return

        redraw = False
        # The highlight is NOT a hover effect. It is set by a double click and stays until it is
        # cleared, so the same sample can be studied across every projection without keeping the
        # pointer on it - and hovering never disturbs it.

        if annotation is None:
            # Told here so a panel that shows no tooltip can be identified from the log instead of guessed at.
            logger.info(
                "hover: no tooltip for figure %s (inaxes=%s)",
                id(hovered_figure), event.inaxes,
            )
            # No tooltip to show - the highlight above still stands.
            if redraw and hovered_figure is not None:
                try:
                    hovered_figure.canvas.draw_idle()
                except Exception as err:
                    logger.warning("on_hover failed: %s", err)
            return

        visible = False

        for sc in collections:
            if sc is None:
                continue

            try:
                cont, ind = sc.contains(event)
                if not cont or not ind or 'ind' not in ind or len(ind['ind']) == 0:
                    continue

                idx_in_scatter = int(ind['ind'][0])
                sample_idx = mapping.get((id(sc), idx_in_scatter))
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
                    tooltip_columns=app_state.tooltip_columns,
                    selected=sample_idx in app_state.selected_indices,
                    selected_status_label=translate('Status: Selected'),
                )

                from visualization.plotting.tooltip import place_tooltip

                place_tooltip(annotation, x, y)
                annotation.set_text(txt)
                annotation.set_visible(True)
                logger.info(
                    "hover: tooltip shown on figure %s axes=%s (panel=%s)",
                    id(hovered_figure), getattr(annotation, "axes", None),
                    panel.get("mode") if panel is not None else None,
                )
                # Hovering shows the tooltip and nothing else: the mark belongs to the double
                # click, and a hover used to move it here, which is why the highlight wandered.
                redraw = True
                visible = True
                break

            except Exception:
                continue

        if not visible:
            try:
                annotation.set_visible(False)
                redraw = True
            except Exception as err:
                logger.warning("on_hover failed: %s", err)

        # Every figure involved is repainted: the one being pointed at, because the tooltip is
        # drawn there, and the active one, because the highlight is applied to all of them.
        for figure in (hovered_figure, app_state.fig):
            if figure is None:
                continue
            try:
                figure.canvas.draw_idle()
            except Exception as err:
                logger.warning("on_hover failed: %s", err)

    except Exception as err:
        logger.warning("on_hover failed: %s", err)


def _resolve_group_at(event: Any):
    """Group of the sample under the pointer.

    Reuses the selection resolver (which falls back to the nearest sample when
    ``contains()`` finds nothing) and maps the sample index through the group
    column, so the label matches the legend keys used by _bring_to_front().
    """
    sample_idx = _resolve_sample_index(event)
    if sample_idx is None:
        return None
    group_col = app_state.last_group_col
    df = df_global()
    if df is None or not group_col or group_col not in df.columns:
        return None
    if sample_idx not in df.index:
        return None
    value = df.loc[sample_idx, group_col]
    # Legend keys are the raw group values; keep the original type so
    # _bring_to_front() and the legend list find the entry (a numeric group
    # column would otherwise resolve to "42" and match nothing).
    for key in (app_state.group_to_scatter or {}):
        if key == value or str(key) == str(value):
            return key
    return value


def _figures_for_panels() -> list[Any]:
    """The figures the panels draw into, so a change can be repainted in all of them."""
    figures: list[Any] = []
    for record in getattr(app_state, "plot_panel_windows", []) or []:
        figure = record.get("figure")
        if figure is not None and figure not in figures:
            figures.append(figure)
    if not figures and app_state.fig is not None:
        figures.append(app_state.fig)
    return figures


def _log_click(event: Any) -> None:
    """Say what a click looks like before anything decides what to do with it.

    Detailed on purpose: a click that does nothing has several possible reasons - it never
    arrived, it arrived in a panel that was not recognised, the sample was not resolved, or the
    selection did not refresh - and guessing between them wastes the user's time.
    """
    inaxes = getattr(event, "inaxes", None)
    panel = _panel_for(inaxes) if inaxes is not None else None
    logger.info(
        "click: button=%s dblclick=%s inaxes=%s panel=%s selection_mode=%s state_ax_is_it=%s",
        getattr(event, "button", None),
        getattr(event, "dblclick", False),
        "none" if inaxes is None else getattr(inaxes, "name", "axes"),
        "none" if panel is None else panel.get("mode"),
        app_state.selection_mode,
        inaxes is app_state.ax,
    )


def on_click(event: Any) -> None:
    """Handle mouse click events for interactive selection."""
    try:
        if app_state.render_mode == '3D':
            logger.info("click ignored: the single render mode says 3D")
            return

        if event is None or not hasattr(event, 'inaxes'):
            return
        _log_click(event)
        logger.debug(
            "click detail: has_inaxes=%s inaxes=%s button=%s dblclick=%s xdata=%s ydata=%s",
            hasattr(event, "inaxes"),
            getattr(event, "inaxes", None),
            getattr(event, "button", None),
            getattr(event, "dblclick", False),
            getattr(event, "xdata", None),
            getattr(event, "ydata", None),
        )

        # A click counts in any panel, not only in the one the state mirrors: the panels are
        # equals, and requiring the active one is why a click sometimes did nothing.
        if event.inaxes != app_state.ax and _panel_for(event.inaxes) is None:
            logger.info("click ignored: the axes belongs to no known panel")
            return

        if not hasattr(event, 'button') or event.button != 1:
            logger.info(
                "click ignored: button=%s (only the left button acts) dblclick=%s",
                getattr(event, "button", None),
                getattr(event, "dblclick", False),
            )
            return

        double_click = bool(getattr(event, 'dblclick', False))
        # A double click reveals a group and marks a sample; it used to do that whatever the user had switched
        # on. It belongs to the two features it serves - the tooltip and the selection - so with both off the
        # click is not this handler's business.
        if double_click and not (app_state.selection_mode or app_state.show_tooltip):
            logger.info("double click ignored: neither the tooltip nor the selection is on")
            return
        if not app_state.selection_mode and not double_click:
            return

        if not app_state.selection_mode:
            if getattr(event, 'dblclick', False):
                # Without the selection mode, a double click reveals the clicked point's group in
                # the legend - and then selects that point, further down, with the same selection
                # the selection tool makes. There is one way to mark a sample, not two: the
                # separate highlight kept failing, and the selection already draws in every panel.
                group = _resolve_group_at(event)
                callback = getattr(app_state, 'group_reveal_callback', None)
                if group is not None and callback is not None:
                    callback(group)
                    logger.info('Revealed group %s in the legend.', group)
            if getattr(event, 'dblclick', False):
                sample_idx = _resolve_sample_index(event)
                logger.info("double click: resolved sample=%s", sample_idx)
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
                    logger.info(
                        'Selected sample %s; the selection now holds %d.',
                        lab_label,
                        len(app_state.selected_indices or ()),
                    )

                refresh_selection_overlay()
                logger.info(
                    'Selection overlay refreshed for %d panel(s): %s',
                    len(app_state.plot_panel_states or []),
                    [str(state.get('mode')) for state in (app_state.plot_panel_states or [])],
                )
            return

    except Exception as err:
        logger.warning('Click handler error: %s', err)
