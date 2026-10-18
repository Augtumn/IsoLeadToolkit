"""The ternary zoom filter: wheel zoom, middle-button pan and the drag, one filter per canvas.

One QObject installs itself on a canvas and handles the wheel, the pan and the zoom drag for the panel that canvas
belongs to. It lived at the bottom of the canvas mixin, which had grown to hold everything; the code is unchanged and
the mixin re-exports the names the tests import.
"""
from __future__ import annotations

import logging
from PyQt5.QtCore import QEvent, QObject, Qt
from PyQt5.QtGui import QWindow
from PyQt5.QtWidgets import QApplication, QWidget

from core import app_state, state_gateway
from visualization.plotting.panel_labels import refresh_panel_labels

logger = logging.getLogger(__name__)

#: Keys of app_state.ternary_manual_limits in component order.
_LIMIT_KEYS = ("tmin", "tmax", "lmin", "lmax", "rmin", "rmax")


class TernaryZoomEventFilter(QObject):
    #: The last wheel event already handled, so the second filter does not apply it again.
    _last_wheel_event = None
    """Turns a left-button drag over the canvas into ternary limits."""

    def __init__(self, canvas: QWidget, toolbar=None) -> None:
        super().__init__(canvas)
        self._canvas = canvas
        self._toolbar = toolbar
        self._press: tuple[float, float] | None = None
        self._axes = None
        #: Where a middle-button pan started, in data coordinates.
        self._pan_from: tuple[float, float] | None = None

    def _zoom_tool_active(self) -> bool:
        """True while the toolbar's magnifier is selected.

        Until then a drag stays a selection gesture, which is how the toolbar is
        meant to behave.
        """
        return str(getattr(self._toolbar, "mode", "") or "") == "zoom rect"

    # ── helpers ──────────────────────────────────────────────────────────
    def _ternary_axes(self):
        try:
            for axes in self._canvas.figure.axes:
                if hasattr(axes, "set_ternary_lim"):
                    return axes
        except Exception as err:
            logger.warning("_ternary_axes failed: %s", err)
        return None

    def _axes_now(self):
        """The ternary axes of the live canvas, falling back to the app state."""
        axes = self._ternary_axes()
        if axes is None:
            try:
                candidate = app_state.ax
                if candidate is not None and hasattr(candidate, "set_ternary_lim"):
                    axes = candidate
            except Exception:
                axes = None
        return axes


    def _zoom_tool_active_for(self, canvas) -> bool:
        """True while the panel shown in *canvas* holds the magnifier.

        Every panel has its own toolbar and the state mirrors one of them, so the tool must be read
        from the panel the event is over.
        """
        for record in list(getattr(app_state, "plot_panel_windows", []) or []):
            if record.canvas is not canvas:
                continue
            toolbar = record.toolbar
            mode = str(getattr(getattr(toolbar, "mode", None), "name", "") or "")
            return mode.upper() == "ZOOM"
        return self._zoom_tool_active()

    def _zoom_cartesian(self, axes, coords, event) -> None:
        """Zoom a 2D axes around the pointer, by one wheel step.

        Kept here rather than left to the toolbar's magnifier so that it works in every panel and
        cannot be lost when the toolbar is rebuilt for another one.
        """
        try:
            delta = int(event.angleDelta().y())
        except Exception as err:
            logger.warning("Could not read the wheel delta: %s", err)
            return
        if delta == 0:
            return
        factor = 0.85 if delta > 0 else 1.0 / 0.85
        try:
            x, y = float(coords[0]), float(coords[1])
        except Exception:
            return
        try:
            x0, x1 = axes.get_xlim()
            y0, y1 = axes.get_ylim()
            axes.set_xlim(x - (x - x0) * factor, x + (x1 - x) * factor)
            axes.set_ylim(y - (y - y0) * factor, y + (y1 - y) * factor)
            figure = getattr(axes, "figure", None)
            if figure is not None:
                figure.canvas.draw_idle()
            # The labels belong to the view that was just changed, so they are laid out again for
            # it; a zoom that moves the view but not the labels leaves them behind.
            refresh_panel_labels(axes)
        except Exception as err:
            logger.warning("Could not zoom the panel: %s", err)


    def _handle_wheel(self, axes, coords, event) -> None:
        """Wheel over the plot: zoom about the cursor (any plot type).

        A ternary wheel zoom magnifies the view the same way the 2D one does - the axes are handed
        the zoomed window, so the points grow on screen - and the tick labels move with the
        drawing. The window is recorded so a re-render keeps it (no checkbox needed).

        Only while the toolbar's magnifier is selected; otherwise the wheel belongs to
        whatever else is listening (scrolling the panel, matplotlib's own handlers).
        """
        if str(getattr(axes, "name", "")) != "ternary":
            # The wheel zooms here, per canvas, whatever the toolbar is doing: depending on the
            # magnifier being selected meant the zoom quietly stopped whenever the toolbar was
            # rebuilt for another panel.
            self._zoom_cartesian(axes, coords, event)
            return
        from visualization.plotting.ternary import cartesian_to_ternary
        from visualization.plotting.view_zoom import (
            is_ternary_axes,
            wheel_factor,
            zoom_cartesian,
            zoom_ternary,
        )

        factor = wheel_factor(event.angleDelta().y())
        if factor == 1.0:
            return
        try:
            if is_ternary_axes(axes):
                t, l, r = cartesian_to_ternary(coords[0], coords[1])
                limits = zoom_ternary(axes, factor, t, l, r)
                self._remember_ternary_limits(limits)
            else:
                zoom_cartesian(axes, factor, coords[0], coords[1])
            # The axes can belong to another panel than the canvas this filter was built with, so
            # the canvas to redraw is the axes' own - redrawing the filter's left a pan in any other
            # panel invisible, which is the reported "only the first window responds".
            figure = getattr(axes, "figure", None)
            own_canvas = getattr(figure, "canvas", None)
            if own_canvas is not None:
                own_canvas.draw_idle()
            refresh_panel_labels(axes)
        except Exception as err:
            logger.warning("Wheel zoom failed: %s", err)

    def _pan_view(self, current) -> None:
        """Middle-button drag: translate the view by the drag delta."""
        from visualization.plotting.view_zoom import (
            is_ternary_axes,
            pan_cartesian,
            pan_ternary,
        )

        if self._pan_from is None or current is None:
            return
        dx = current[0] - self._pan_from[0]
        dy = current[1] - self._pan_from[1]
        axes = self._current_axes()
        if axes is None:
            return
        try:
            if is_ternary_axes(axes):
                from visualization.plotting.ternary import cartesian_to_ternary

                t0, l0, _r0 = cartesian_to_ternary(*self._pan_from)
                t1, l1, _r1 = cartesian_to_ternary(*current)
                limits = pan_ternary(axes, (t1 - t0 + l1 - l0) / 2.0)
                self._remember_ternary_limits(limits)
            else:
                pan_cartesian(axes, -dx, -dy)
            # The axes can belong to another panel than the canvas this filter was built with, so
            # the canvas to redraw is the axes' own - redrawing the filter's left a pan in any other
            # panel invisible, which is the reported "only the first window responds".
            figure = getattr(axes, "figure", None)
            own_canvas = getattr(figure, "canvas", None)
            if own_canvas is not None:
                own_canvas.draw_idle()
            refresh_panel_labels(axes)
        except Exception as err:
            logger.warning("Pan failed: %s", err)
        self._pan_from = current

    def _remember_ternary_limits(self, limits) -> None:
        """Persist a ternary view window so every later render keeps it.

        The window is the region the gesture asked to see, so it is what the drawing shows and what
        the labels report. The zoom itself records it on the axes (``store_ternary_view_window`` in
        visualization/plotting/ternary.py), which is what makes the next render draw it again; this
        write is the copy the panel and the session keep. The manual-limits box keeps meaning "my
        window, not the inferred one", and this deliberately does not touch it.
        """
        keys = ("tmin", "tmax", "lmin", "lmax", "rmin", "rmax")
        try:
            manual = dict(app_state.ternary_manual_limits or {})
            manual.update(dict(zip(keys, limits)))
            state_gateway.set_ternary_manual_limits(manual)
            state_gateway.set_ternary_auto_zoom(True)
            # The manual-limits checkbox is left to the user: enabling it here made a zoom
            # flip it on, and it then came up ticked on the next launch.
        except Exception as err:
            logger.warning("Could not persist the ternary view: %s", err)

    def _current_axes(self):
        """The axes under the pointer: the ternary one when present, else the live axes.

        ``_axes_now()`` deliberately only returns ternary axes (the drag zoom needs them);
        wheel zoom and pan work on any plot type, so they use this wider accessor.
        """
        axes = self._ternary_axes()
        if axes is not None:
            return axes
        try:
            return app_state.ax
        except Exception:
            return None

    def _targets_canvas(self, obj) -> bool:
        """True when *obj* is (a child of) the canvas or its native window.

        Unrelated widgets (panels, menus, toolbar buttons) are excluded: the
        old global-position fallback once accepted a press on a QCheckBox as
        a gesture start.
        """
        if obj is self._canvas:
            return True
        if isinstance(obj, QWidget):
            try:
                return self._canvas.isAncestorOf(obj)
            except RuntimeError:
                return False
        if isinstance(obj, QWindow):
            return True
        return False

    def _data_coords(self, obj, event):
        """Widget position -> data coordinates, or None when outside the canvas."""
        try:
            if obj is self._canvas:
                point = event.pos()
            elif isinstance(obj, QWidget) and self._canvas.isAncestorOf(obj):
                point = self._canvas.mapFrom(obj, event.pos())
            elif isinstance(obj, QWindow):
                # Native-window copy of the event: its pos() is window-local,
                # so map through the global position instead.
                point = self._canvas.mapFromGlobal(event.globalPos())
            else:
                return None
            if not (0 <= point.x() <= self._canvas.width() and 0 <= point.y() <= self._canvas.height()):
                return None
            ratio = self._canvas.devicePixelRatioF()
            display = (point.x() * ratio, (self._canvas.height() - point.y()) * ratio)
            axes = self._axes if self._axes is not None else self._current_axes()
            if axes is None:
                return None
            data = axes.transData.inverted().transform(display)
            return float(data[0]), float(data[1])
        except Exception as err:
            logger.debug("Ternary zoom Qt: coordinate mapping failed: %s", err)
            return None

    # ── event filter ─────────────────────────────────────────────────────
    def eventFilter(self, obj, event) -> bool:
        # Qt-level tracing, because on a real machine matplotlib's own mouse callbacks do not
        # receive canvas events at all: without this, a click that does nothing gives no clue
        # whether Qt saw it, whether it was a canvas, or whether it arrived as a double click.
        try:
            kind = event.type()
            if kind in (
                QEvent.MouseButtonPress,
                QEvent.MouseButtonRelease,
                QEvent.MouseButtonDblClick,
            ):
                widget = obj if isinstance(obj, QWidget) else None
                is_canvas = bool(widget is not None and hasattr(widget, "figure"))
                if kind != QEvent.MouseMove or is_canvas:
                    logger.info(
                        "qt mouse: %s on %s (canvas=%s) button=%s",
                        kind,
                        type(obj).__name__,
                        is_canvas,
                        getattr(event, "button", lambda: None)(),
                    )
                if (
                    is_canvas
                    and kind == QEvent.MouseButtonDblClick
                    and event.button() == Qt.LeftButton
                    and not app_state.selection_mode
                ):
                    # Only when no selection tool is active: with the tool on, the tool already
                    # handles the click, and forwarding it as well toggled the sample twice -
                    # the conflict where a double click appeared to do nothing.
                    # Qt saw a double click on a canvas but matplotlib's callback may never be
                    # called, so the click handler is invoked here with an equivalent event.
                    from matplotlib.backend_bases import MouseEvent
                    from visualization.event_handlers import on_click

                    position = event.pos()
                    height = widget.figure.bbox.height if widget.figure is not None else 0.0
                    synthetic = MouseEvent(
                        "button_press_event",
                        widget,
                        float(position.x()),
                        float(height - position.y()),
                        button=1,
                    )
                    synthetic.dblclick = True
                    on_click(synthetic)
                    return True
        except Exception as err:
            logger.warning("qt mouse tracing failed: %s", err)

        try:
            kind = event.type()
            if kind == QEvent.Wheel:
                # One notch is one step. Qt hands the same event to every filter that watches it,
                # and this filter is installed on the application as well as on each canvas, so a
                # notch was applied twice - and a different number of times per window.
                # The event itself, not its id: an id is reused once the event is collected, and a
                # later notch then looked like the same one and was skipped.
                if event is self._last_wheel_event:
                    return False
                self._last_wheel_event = event
                # Bound to the magnifier, as asked, and to the magnifier of the panel the wheel is
                # over: a wheel that ignores the tool is what this used to be.
                canvas = obj if isinstance(obj, QWidget) and hasattr(obj, "figure") else self._canvas
                if not self._zoom_tool_active_for(canvas):
                    return False
                axes = None
                coords = None
                try:
                    point = canvas.mapFromGlobal(event.globalPos())
                    ratio = canvas.devicePixelRatioF()
                    display = (point.x() * ratio, (canvas.height() - point.y()) * ratio)
                    for candidate in list(canvas.figure.axes):
                        try:
                            if candidate.bbox.contains(*display):
                                axes = candidate
                                break
                        except Exception:
                            continue
                    if axes is not None:
                        data = axes.transData.inverted().transform(display)
                        coords = (float(data[0]), float(data[1]))
                except Exception as err:
                    logger.warning("Wheel: could not resolve the panel under the pointer: %s", err)
                if axes is not None and coords is not None:
                    # The wheel zooms the plot under the pointer only while this canvas's window is the one in
                    # use: with a dialog open, the wheel belongs to the dialog and zooming the chart behind it
                    # surprised the user. A window with no active window at all - offscreen, or before the
                    # first focus - is left alone, and a canvas that is not a widget has no window to compare.
                    # A dialog in front takes the wheel: without this, scrolling in a dialog that sits over the
                    # plot zoomed the chart behind it. The test is the modal widget rather than the active
                    # window, because the active window is the dialog only some of the time.
                    if QApplication.activeModalWidget() is not None:
                        return False
                    self._handle_wheel(axes, coords, event)
                    return False
            if kind == QEvent.MouseButtonPress and event.button() == Qt.MiddleButton:
                if not self._zoom_tool_active():
                    # A pan left over from a previous mode must not continue.
                    self._pan_from = None
                    return False
                if self._targets_canvas(obj):
                    self._pan_from = self._data_coords(obj, event)
                    return False
            if kind == QEvent.MouseMove and self._pan_from is not None:
                current = self._data_coords(obj, event)
                if current is not None:
                    self._pan_view(current)
                    return False
            if kind == QEvent.MouseButtonRelease and event.button() == Qt.MiddleButton:
                if self._pan_from is not None:
                    logger.debug("Pan finished.")
                self._pan_from = None
                return False
            if kind == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                if not self._zoom_tool_active():
                    return False
                if not self._targets_canvas(obj):
                    return False
                self._axes = self._axes_now()
                if self._axes is None:
                    self._press = None
                    return False
                coords = self._data_coords(obj, event)
                if coords is None:
                    # The native QWindow copy of a press outside the canvas
                    # (e.g. over the axes frame) arrives first; the widget
                    # copy below may still map inside. Keep state clean.
                    self._press = None
                    return False
                self._press = coords
                logger.info(
                    "Ternary zoom press accepted at (%.4f, %.4f)", *coords
                )
            elif kind == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                start = self._press
                if start is None:
                    return False
                coords = self._data_coords(obj, event)
                if coords is None:
                    # Never conclude on an unusable copy: the QWindow copy
                    # arrives first and cannot be mapped via pos(); the
                    # canvas copy (or the QWindow copy via globalPos) right
                    # after it carries usable coordinates. Only a release
                    # genuinely delivered to the canvas but outside it
                    # cancels the gesture.
                    if obj is self._canvas:
                        logger.info(
                            "Ternary zoom cancelled: release outside the canvas"
                        )
                        self._press = None
                        self._axes = None
                    return False
                axes = self._axes
                self._press = None
                self._axes = None
                self._apply(axes, start, coords)
        except Exception as err:
            logger.warning("eventFilter failed: %s", err)
        return False  # never swallow the event

    def _apply(self, axes, start, end) -> None:
        from visualization.plotting.ternary import (
            apply_ternary_zoom_window,
            drag_ternary_window,
            ternary_axes_limits,
            ternary_limits_cover_full_view,
        )

        # The drag is measured against what is drawn, not against the whole triangle, so a second
        # drag composes with the first and an outward drag stays a usable reset gesture.
        window = ternary_axes_limits(axes)
        if window is None:
            logger.info("Ternary zoom drag ignored: the drawn window could not be read.")
            return
        limits = drag_ternary_window(window, start, end)
        if limits is None:
            logger.info("Ternary zoom drag ignored: too short to be a gesture.")
            return
        logger.info(
            "Ternary zoom drag -> view window %s",
            tuple(round(float(value), 4) for value in limits),
        )
        full_view = ternary_limits_cover_full_view(limits)
        try:
            if full_view:
                # An outward drag is the reset gesture: it drops the stored window, so the drawing
                # goes back to the whole triangle and the labels to the range the data implies. The
                # manual-limits box is cleared with it, because its window is not what is being
                # asked for here.
                state_gateway.set_ternary_manual_limits_enabled(False)
                self._reset_ternary_view(axes)
                logger.info("Ternary zoom reset by an outward drag.")
            else:
                manual = dict(app_state.ternary_manual_limits or {})
                manual.update(dict(zip(_LIMIT_KEYS, limits)))
                state_gateway.set_ternary_manual_limits(manual)
                state_gateway.set_ternary_auto_zoom(True)
                # The manual-limits checkbox is left to the user: enabling it here made a zoom
                # flip it on, and it then came up ticked on the next launch.
                apply_ternary_zoom_window(axes, limits)
                logger.info(
                    "Ternary local zoom (Qt): t=[%.3f, %.3f] l=[%.3f, %.3f] r=[%.3f, %.3f]",
                    limits[0], limits[1], limits[2], limits[3], limits[4], limits[5],
                )
        except Exception as err:
            logger.warning("Failed to apply ternary zoom (Qt): %s", err)
            return
        # The canvas needs a repaint, not a fresh render: the zoom would survive a render now, but a
        # repaint is all this gesture asks for. The axes' own canvas, since the gesture can be on
        # any panel while this filter was built with one.
        own_canvas = getattr(getattr(axes, "figure", None), "canvas", None)
        if own_canvas is not None:
            own_canvas.draw_idle()

    def _reset_ternary_view(self, axes) -> None:
        """Undo the zoom: the whole triangle again, labelled with the range the data implies."""
        from visualization.plotting.ternary import reset_ternary_view

        window = reset_ternary_view(axes)
        logger.info(
            "Ternary view reset to t=[%.3f, %.3f] l=[%.3f, %.3f] r=[%.3f, %.3f]",
            window[0], window[1], window[2], window[3], window[4], window[5],
        )


def install_ternary_zoom_filter(canvas: QWidget, toolbar=None):
    """Install the filter on the application (once per canvas).

    An application-level filter sees both the native QWindow copy and the
    widget copy of each mouse event; installing on the canvas alone would
    miss the QWindow copy (and historically missed events entirely when the
    canvas was replaced during a redraw).
    """
    existing = getattr(canvas, "_ternary_zoom_filter", None)
    if existing is not None:
        return existing
    filt = TernaryZoomEventFilter(canvas, toolbar)
    application = QApplication.instance()
    if application is not None:
        application.installEventFilter(filt)
    else:  # pragma: no cover - no QApplication in headless use
        canvas.installEventFilter(filt)
    canvas._ternary_zoom_filter = filt
    logger.info(
        "Ternary zoom filter installed: canvas id=%s app_filter=%s",
        id(canvas),
        application is not None,
    )
    return filt
