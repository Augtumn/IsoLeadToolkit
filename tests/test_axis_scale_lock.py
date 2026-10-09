"""The axis-scale lock: a re-render draws the ranges the lock recorded, or nothing changes.

These tests measure behaviour, not intent. The 2-D half asserts on the axes' own
``get_xlim``/``get_ylim`` after the real render path (``plot_2d_data``) has run twice with data
of deliberately different extent; the ternary half asserts on the window mpltern really drew and,
where it matters, on the pixels of the rendered region - ``ax.transData`` on mpltern axes
describes mpltern's internal transform rather than the geometry on screen (see
tests/test_ternary_rendered_geometry.py). The unlocked halves of both compare against a control
render that never saw a lock, so "restores the old behaviour" is measured against the old
behaviour rather than against a number written down here.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import mpltern  # noqa: F401,E402  (registers the "ternary" projection)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from core import app_state, state_gateway, translate  # noqa: E402
from core.localization import set_language  # noqa: E402
from core.state._normalizers import sync_state_store_to_app  # noqa: E402
from visualization.plotting.axis_lock import (  # noqa: E402
    CARTESIAN,
    TERNARY,
    disable_axis_scale_lock,
    enable_axis_scale_lock,
    read_axis_limits,
)
from visualization.plotting.ternary import (  # noqa: E402
    apply_ternary_zoom_window,
    configure_ternary_axis,
    ternary_axes_limits,
)
from visualization.plotting.rendering.raw.plot2d import plot_2d_data  # noqa: E402

#: The copy the toolbar carries; the locale keys are the English texts.
LOCK_TEXT_KEY = "Lock Axis Scale"
LOCK_TOOLTIP_KEY = (
    "Lock the axis scale so new data is drawn on the same ranges. "
    "While it is on, the lock wins over a ternary zoom."
)

#: Column pairs whose extents have nothing in common, so an autoscaled view of one is never
#: mistaken for another's: the ranges a lock must hold are far outside the next data's.
COLUMN_CASES = (("A_x", "A_y"), ("B_x", "B_y"), ("C_x", "C_y"))

#: The whole triangle: the ternary default the tests start from.
FULL_LIMITS = (0.0, 1.0, 0.0, 1.0, 0.0, 1.0)
#: A window an explicit zoom asked for; no component range past what the triangle allows, so
#: mpltern draws it back unchanged (a clipped window is a different test).
ZOOMED_WINDOW = (
    0.17087023865971235, 0.23881614207058974,
    0.184689697216013, 0.413403997770168,
    0.41339721726071965, 0.6424400641242747,
)
#: An equilateral triangle's height / base; a window draws a flatter hexagon instead.
EQUILATERAL_RATIO = math.sqrt(3.0) / 2.0

#: Ternary components gathered in one place, and the same data moved.
COMPONENTS_A = (
    np.array([0.20, 0.22, 0.18]),
    np.array([0.30, 0.25, 0.35]),
    np.array([0.50, 0.53, 0.47]),
)
COMPONENTS_B = (
    np.array([0.60, 0.55, 0.62]),
    np.array([0.10, 0.14, 0.12]),
    np.array([0.30, 0.31, 0.26]),
)
RAW_SCALE = 40.0


def _make_df() -> pd.DataFrame:
    """Three column pairs with deliberately different extents, and a grouping column."""
    rng = np.random.default_rng(7)
    count = 12
    return pd.DataFrame(
        {
            "A_x": rng.uniform(18.0, 19.5, count),
            "A_y": rng.uniform(15.5, 15.8, count),
            "B_x": rng.uniform(380.0, 420.0, count),
            "B_y": rng.uniform(-40.0, -30.0, count),
            "C_x": rng.uniform(0.0, 1.0, count),
            "C_y": rng.uniform(2000.0, 2500.0, count),
            "Group": [chr(65 + index % 3) for index in range(count)],
        }
    )


@pytest.fixture(autouse=True)
def _restore_shared_state():
    """Put the live figure, axes, canvas, data and lock back after each test.

    The lock's record is persisted state and the render path reads the live figure, so a test
    that leaves either behind would decide what the next one measures.
    """
    saved = {
        "fig": getattr(app_state, "fig", None),
        "ax": getattr(app_state, "ax", None),
        "canvas": getattr(app_state, "canvas", None),
        "df": getattr(app_state, "df_global", None),
        "group_cols": list(getattr(app_state, "group_cols", []) or []),
        "data_cols": list(getattr(app_state, "data_cols", []) or []),
        "locked": bool(getattr(app_state, "axis_scale_locked", False)),
        "limits": dict(getattr(app_state, "locked_axis_limits", {}) or {}),
        "manual_enabled": bool(getattr(app_state, "ternary_manual_limits_enabled", False)),
        "manual": dict(getattr(app_state, "ternary_manual_limits", {}) or {}),
        "auto_zoom": bool(getattr(app_state, "ternary_auto_zoom", True)),
        "ranges": dict(getattr(app_state, "ternary_ranges", {}) or {}),
        "mode": getattr(app_state, "ternary_limit_mode", None),
        "language": getattr(app_state, "language", None),
        "show_marginal_kde": bool(getattr(app_state, "show_marginal_kde", True)),
    }
    yield
    state_gateway.set_axis_scale_locked(saved["locked"])
    state_gateway.set_locked_axis_limits(saved["limits"])
    state_gateway.set_figure_axes(saved["fig"], saved["ax"])
    state_gateway.set_canvas(saved["canvas"])
    state_gateway.set_dataframe_and_source(
        saved["df"], file_path="", sheet_name=None
    )
    state_gateway.set_group_data_columns(saved["group_cols"], saved["data_cols"])
    state_gateway.set_ternary_manual_limits_enabled(saved["manual_enabled"])
    state_gateway.set_ternary_manual_limits(saved["manual"])
    state_gateway.set_ternary_auto_zoom(saved["auto_zoom"])
    state_gateway.set_ternary_ranges(saved["ranges"])
    if saved["mode"] is not None:
        state_gateway.set_ternary_limit_mode(saved["mode"])
    state_gateway.set_show_marginal_kde(saved["show_marginal_kde"])
    if saved["language"] and str(getattr(app_state, "language", "")) != str(saved["language"]):
        set_language(str(saved["language"]))


# ── 2-D: the render path, measured on the axes ──────────────────────────


def _start_2d_session(df: pd.DataFrame):
    """The live 2-D figure, canvas and axes the render path will draw on."""
    state_gateway.set_show_marginal_kde(False)
    figure = Figure(figsize=(6.0, 4.5), dpi=100)
    canvas = FigureCanvasAgg(figure)
    axes = figure.add_subplot(111)
    state_gateway.set_figure_axes(figure, axes)
    state_gateway.set_canvas(canvas)
    state_gateway.set_dataframe_and_source(df, file_path=None, sheet_name=None)
    state_gateway.set_group_data_columns(["Group"], list(df.columns))
    return figure, canvas, axes


def _render_2d(canvas, columns, show_kde: bool = False) -> None:
    """Run the app's 2-D render and finish with the draw the lock has to survive."""
    rendered = plot_2d_data("Group", list(columns), size=30, show_kde=show_kde)
    assert rendered is True, f"the 2-D render of {columns} failed"
    canvas.draw()


def _ranges(axes) -> tuple:
    """The x/y ranges the axes draws, as plain tuples."""
    return tuple(axes.get_xlim()), tuple(axes.get_ylim())


def test_a_locked_view_keeps_its_ranges_when_other_data_is_rendered() -> None:
    """Lock on: the first render defines the ranges, and two later data sets cannot move them."""
    df = _make_df()
    _figure, canvas, axes = _start_2d_session(df)
    _render_2d(canvas, COLUMN_CASES[0])
    locked = _ranges(axes)

    enable_axis_scale_lock(canvas)
    assert app_state.axis_scale_locked is True
    assert app_state.locked_axis_limits[CARTESIAN]["xlim"] == [float(locked[0][0]), float(locked[0][1])]

    for columns in COLUMN_CASES[1:]:
        _render_2d(canvas, columns)
        drawn = _ranges(axes)
        assert drawn[0] == locked[0], f"{columns} moved the locked x range"
        assert drawn[1] == locked[1], f"{columns} moved the locked y range"


def test_a_locked_view_survives_a_kde_render_and_a_style_change() -> None:
    """The other half of "a re-render must not move the ranges": KDE on, and a new marker size."""
    df = _make_df()
    _figure, canvas, axes = _start_2d_session(df)
    _render_2d(canvas, COLUMN_CASES[0])
    locked = _ranges(axes)

    enable_axis_scale_lock(canvas)

    _render_2d(canvas, COLUMN_CASES[0], show_kde=True)
    assert _ranges(axes) == locked, "the KDE render moved the locked ranges"

    state_gateway.set_plot_marker_size(140)
    _render_2d(canvas, COLUMN_CASES[0])
    assert _ranges(axes) == locked, "the style change moved the locked ranges"


def test_an_unlocked_view_autoscales_again() -> None:
    """Lock off: the next render fits its own data - exactly as a render with no lock at all."""
    df = _make_df()
    _figure, canvas, axes = _start_2d_session(df)
    _render_2d(canvas, COLUMN_CASES[0])
    locked = _ranges(axes)

    enable_axis_scale_lock(canvas)
    _render_2d(canvas, COLUMN_CASES[1])
    assert _ranges(axes) == locked, "the lock did not hold while it was on"

    disable_axis_scale_lock(canvas)
    assert app_state.axis_scale_locked is False
    assert app_state.locked_axis_limits == {}

    _render_2d(canvas, COLUMN_CASES[2])
    after_unlock = _ranges(axes)
    assert after_unlock != locked, "the unlocked render kept the locked ranges"

    # The control: the same data rendered on axes that never saw a lock. "The old behaviour is
    # back" is only measured if that is what it is compared against.
    _control_figure, control_canvas, control_axes = _start_2d_session(df)
    _render_2d(control_canvas, COLUMN_CASES[2])
    assert after_unlock == _ranges(control_axes)


# ── ternary: the window that is really drawn ────────────────────────────


def _start_ternary(components):
    """A ternary figure, its canvas, and the axes the renderer configures."""
    state_gateway.set_ternary_limit_mode("both")
    state_gateway.set_ternary_manual_limits_enabled(False)
    state_gateway.set_ternary_auto_zoom(True)
    figure = Figure(figsize=(6.0, 5.0), dpi=100)
    canvas = FigureCanvasAgg(figure)
    axes = _configure_ternary(figure, components)
    state_gateway.set_figure_axes(figure, axes)
    state_gateway.set_canvas(canvas)
    canvas.draw()
    return figure, canvas, axes


def _configure_ternary(figure, components):
    """The render path for the triangle: a fresh axes, configured from the data."""
    axes = figure.add_subplot(111, projection="ternary")
    t_vals, l_vals, r_vals = components
    configure_ternary_axis(
        axes,
        t_vals,
        l_vals,
        r_vals,
        labels=("T", "L", "R"),
        raw_values=(t_vals * RAW_SCALE, l_vals * RAW_SCALE, r_vals * RAW_SCALE),
    )
    return axes


def _drawn_bbox(figure, axes):
    """The pixel bbox of the region the axes draws, as ``(width, height)``.

    Every tick, tick label, axis label and gridline is switched off first, so the only ink left
    is the region's own outline and the measurement is the geometry alone.
    """
    for name in ("t", "l", "r"):
        axis = getattr(axes, f"{name}axis", None)
        if axis is None:
            continue
        axis.set_ticks([])
        axis.set_ticklabels([])
    axes.set_tlabel("")
    axes.set_llabel("")
    axes.set_rlabel("")
    axes.grid(False)

    figure.canvas.draw()
    buffer = np.asarray(figure.canvas.buffer_rgba())
    rows, columns = np.nonzero(buffer[:, :, :3].mean(axis=2) < 200)
    if not columns.size:
        return None
    return float(columns.max() - columns.min()) + 1.0, float(rows.max() - rows.min()) + 1.0


def test_a_locked_ternary_window_is_drawn_again_on_axes_that_never_saw_it() -> None:
    """Lock on: the recorded window is what the next render draws, on a freshly built triangle."""
    figure, canvas, axes = _start_ternary(COMPONENTS_A)
    assert ternary_axes_limits(axes) == pytest.approx(FULL_LIMITS), "the default view is the triangle"

    apply_ternary_zoom_window(axes, ZOOMED_WINDOW)
    canvas.draw()
    locked_window = ternary_axes_limits(axes)
    assert locked_window == pytest.approx(ZOOMED_WINDOW)
    locked_bbox = _drawn_bbox(figure, axes)

    enable_axis_scale_lock(canvas)
    assert app_state.locked_axis_limits[TERNARY] == [float(value) for value in locked_window]

    # What the app does when the plot type changes: the figure loses its axes and a new ternary
    # one is configured from other data. Without the lock this draws the whole triangle again.
    figure.clf()
    fresh_axes = _configure_ternary(figure, COMPONENTS_B)
    state_gateway.set_figure_axes(figure, fresh_axes)
    canvas.draw()

    drawn = ternary_axes_limits(fresh_axes)
    assert drawn == pytest.approx(locked_window), "the locked window was not drawn again"
    assert drawn != pytest.approx(FULL_LIMITS), "the whole triangle was drawn instead"

    measured = _drawn_bbox(figure, fresh_axes)
    assert measured is not None, "the ternary figure drew nothing"
    assert measured == pytest.approx(locked_bbox, abs=1.0), (
        f"the locked window was drawn at {measured}, not at {locked_bbox}"
    )
    ratio = measured[1] / measured[0]
    assert abs(ratio - EQUILATERAL_RATIO) > 0.03, (
        "a zoomed window draws the view hexagon, not an equilateral triangle"
    )


def test_an_unlocked_ternary_view_draws_the_triangle_again() -> None:
    """Lock off: the same fresh axes draws the default view, so nothing is being re-applied."""
    figure, canvas, _axes = _start_ternary(COMPONENTS_A)
    apply_ternary_zoom_window(_axes, ZOOMED_WINDOW)
    canvas.draw()

    enable_axis_scale_lock(canvas)
    figure.clf()
    locked_axes = _configure_ternary(figure, COMPONENTS_B)
    state_gateway.set_figure_axes(figure, locked_axes)
    canvas.draw()
    assert ternary_axes_limits(locked_axes) == pytest.approx(ZOOMED_WINDOW)

    disable_axis_scale_lock(canvas)
    assert app_state.axis_scale_locked is False
    assert app_state.locked_axis_limits == {}

    figure.clf()
    free_axes = _configure_ternary(figure, COMPONENTS_B)
    state_gateway.set_figure_axes(figure, free_axes)
    canvas.draw()
    assert ternary_axes_limits(free_axes) == pytest.approx(FULL_LIMITS), (
        "an unlocked render must draw the triangle again"
    )


def test_the_lock_wins_over_a_ternary_zoom_while_it_is_on() -> None:
    """The two must not fight: while the lock is on the locked window is what is drawn."""
    _figure, canvas, axes = _start_ternary(COMPONENTS_A)
    enable_axis_scale_lock(canvas)
    locked_window = ternary_axes_limits(axes)
    assert locked_window == pytest.approx(FULL_LIMITS)

    apply_ternary_zoom_window(axes, ZOOMED_WINDOW)
    canvas.draw()
    assert ternary_axes_limits(axes) == pytest.approx(locked_window), (
        "the zoom moved the view while the lock was on"
    )

    # Switching off gives the zoom back, and a re-render keeps drawing it: the ternary rule that
    # a zoom survives a render is the renderer's and was never the lock's to change.
    disable_axis_scale_lock(canvas)
    canvas.draw()
    assert ternary_axes_limits(axes) == pytest.approx(ZOOMED_WINDOW), (
        "the zoom the lock had overridden did not come back"
    )

    configure_ternary_axis(
        axes,
        *COMPONENTS_A,
        labels=("T", "L", "R"),
        raw_values=tuple(values * RAW_SCALE for values in COMPONENTS_A),
    )
    canvas.draw()
    assert ternary_axes_limits(axes) == pytest.approx(ZOOMED_WINDOW), (
        "the re-render dropped the zoom once the lock was off"
    )


def test_reading_the_axes_is_what_the_lock_records() -> None:
    """The record is the drawn view itself, not a conversion of it."""
    _figure, _canvas, axes = _start_ternary(COMPONENTS_A)
    apply_ternary_zoom_window(axes, ZOOMED_WINDOW)
    recorded = read_axis_limits(axes)
    assert recorded[TERNARY] == pytest.approx(list(ZOOMED_WINDOW))


# ── state round trip ────────────────────────────────────────────────────


def test_the_lock_round_trips_through_the_state_store() -> None:
    """A gateway write reaches the snapshot and the live state, and the sync carries it back."""
    limits = {CARTESIAN: {"xlim": [1.0, 2.0], "ylim": [3.0, 4.0]}}

    state_gateway.set_axis_scale_locked(True)
    state_gateway.set_locked_axis_limits(limits)

    store_snapshot = app_state.state_store.snapshot()
    assert store_snapshot["axis_scale_locked"] is True
    assert store_snapshot["locked_axis_limits"] == limits
    assert app_state.axis_scale_locked is True
    assert app_state.locked_axis_limits == limits

    # A state written behind the store's back only follows again after the sync - the snapshot is
    # what the store owns, and the write-back is what puts it back on app_state.
    app_state.axis_scale_locked = False
    app_state.locked_axis_limits = {}
    sync_state_store_to_app(app_state, store_snapshot)
    assert app_state.axis_scale_locked is True
    assert app_state.locked_axis_limits == limits

    # And the coercer refuses a shape the render path could not draw with.
    state_gateway.set_locked_axis_limits({"2d": {"xlim": ["nonsense", 1]}, "ternary": [1, 2, 3]})
    assert app_state.locked_axis_limits == {}


# ── the toolbar switch ──────────────────────────────────────────────────


def test_the_lock_action_is_on_the_toolbar_and_checkable(main_window, qapp) -> None:
    """The switch exists where the select tools are, is checkable, and carries translated copy."""
    figure = Figure(figsize=(4.0, 3.0), dpi=100)
    FigureCanvasAgg(figure)

    main_window.set_matplotlib_figure(figure)
    qapp.processEvents()

    action = main_window._axis_lock_action
    assert action is not None, "the lock action was not built with the toolbar"
    assert action in main_window.toolbar.actions(), "the lock action is not on the main toolbar"
    assert action.isCheckable() is True
    assert action.text() == translate(LOCK_TEXT_KEY)
    assert action.toolTip() == translate(LOCK_TOOLTIP_KEY)
    assert action.isChecked() is False, "the lock is off by default"


def test_the_toolbar_switch_drives_the_lock_state(main_window, qapp) -> None:
    """Clicking the switch is what turns the lock on: state, record and draw hook all follow."""
    from visualization.plotting.axis_lock import axis_scale_lock_handler

    figure = Figure(figsize=(4.0, 3.0), dpi=100)
    FigureCanvasAgg(figure)
    main_window.set_matplotlib_figure(figure)
    qapp.processEvents()

    action = main_window._axis_lock_action
    canvas = getattr(app_state, "canvas", None)
    assert action is not None and canvas is not None
    assert axis_scale_lock_handler(canvas) is None, "a hook was installed before the lock was on"

    action.trigger()
    qapp.processEvents()
    assert action.isChecked() is True
    assert app_state.axis_scale_locked is True
    assert axis_scale_lock_handler(canvas) is not None, "the draw hook was not installed"

    action.trigger()
    qapp.processEvents()
    assert action.isChecked() is False
    assert app_state.axis_scale_locked is False
    assert app_state.locked_axis_limits == {}
    assert axis_scale_lock_handler(canvas) is None, "the draw hook stayed installed"


def test_the_lock_copy_is_translated_in_both_locales() -> None:
    """Both locale files carry the switch's copy: English is the key, Chinese a real translation."""
    root = Path(__file__).resolve().parents[1]

    def _table(name: str) -> dict:
        return json.loads((root / "locales" / f"{name}.json").read_text(encoding="utf-8-sig"))

    english = _table("en")
    chinese = _table("zh")

    for key in (LOCK_TEXT_KEY, LOCK_TOOLTIP_KEY):
        assert english.get(key), f"en.json is missing {key!r}"
        assert chinese.get(key), f"zh.json is missing {key!r}"
        assert chinese[key] != key, f"zh.json carries {key!r} untranslated"
        assert chinese[key] != english[key], f"zh.json repeats the English {key!r}"


def test_the_lock_action_is_retranslated_when_the_language_changes(main_window, qapp) -> None:
    """_refresh_language rewrites the switch's text: panels are refreshed by type, actions are not."""
    figure = Figure(figsize=(4.0, 3.0), dpi=100)
    FigureCanvasAgg(figure)
    main_window.set_matplotlib_figure(figure)
    qapp.processEvents()
    action = main_window._axis_lock_action
    assert action is not None

    original = str(getattr(app_state, "language", None) or "en")
    try:
        assert set_language("zh") is True
        main_window._refresh_language()
        chinese = translate(LOCK_TEXT_KEY, language="zh")
        assert action.text() == chinese
        assert action.text() != LOCK_TEXT_KEY, "the lock action kept its English text"
        assert action.toolTip() == translate(LOCK_TOOLTIP_KEY, language="zh")
    finally:
        set_language(original)
        main_window._refresh_language()

    # Back in whatever language the app was in, not necessarily English: the app ships Chinese.
    assert action.text() == translate(LOCK_TEXT_KEY)
    assert action.text() == translate(LOCK_TEXT_KEY, language=original)
