"""The ternary axes draw the full triangle, and an explicit zoom really magnifies it.

mpltern draws the *view region* for the current ternary limits.  With the full limits that region
is the triangle and it measures right; as soon as any component is narrowed - which is what a
per-component range means - the region becomes the view **hexagon**, whose natural bbox ratio is
0.5142.  mpltern scales that into a box expanded by 0.5*sqrt(3)*get_aspect() and the drawn region
then comes out 1690 x 538 px, i.e. height/width = 0.3178, where an equilateral triangle measures
0.8660 - the flat trapezoid that was reported (0.3340 at the export preset's 3.35x2.41in @300dpi).

It is not a rendering stretch (pixel anisotropy 0.07%), not dpi, figsize or savefig (all disproved
by measurement), and not a style reset.  21 configurations of aspect, adjustable, box_aspect,
xlim/ylim, position and mpltern's fit were measured: every one either leaves the outline flat or
distorts the data by 15-99%.  Making a narrowed region equilateral and keeping the data undistorted
are mutually exclusive.  The two halves of the agreed behaviour follow from that:

* **Default** - nothing selected and nothing zoomed - the axes draw the full equilateral triangle.
  The automatic range inferred from the data only *labels* the axes: it is what the tick labels
  report and what the callers store as ``app_state.ternary_ranges``, and it never clips the
  drawing.  A persisted or inferred range therefore cannot flatten the plot again.
* **Explicit zoom** - the wheel, the magnifier drag, a middle-drag pan - hands mpltern the zoomed
  window again, so the points really grow on screen and the labels move with the drawing.  The
  outline then has the window's shape, the hexagon above: flat, and visibly not a composition
  triangle.  That is the accepted trade-off of zooming - magnifying a box inside a triangle cannot
  stay equilateral - and it is no longer imposed on the default view.
* The manual-limits checkbox is the one setting that draws a stored window at render time; the
  automatic range never does.

These tests read pixels rather than transforms.  ``ax.transData`` on mpltern axes describes
mpltern's internal ternary transform, not the geometry on screen: it once reported three equal
1169.9 px edges on a figure only 400 px tall.
"""
from __future__ import annotations

import math

import matplotlib

matplotlib.use("Agg")

import mpltern  # noqa: F401,E402  (registers the "ternary" projection)
import numpy as np  # noqa: E402
import pytest  # noqa: E402
from matplotlib.backends.backend_agg import FigureCanvasAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from core import app_state, state_gateway  # noqa: E402
from visualization.plotting.ternary import (  # noqa: E402
    apply_ternary_label_window,
    apply_ternary_zoom_window,
    configure_ternary_axis,
    get_ternary_label_range,
    manual_ternary_label_range,
    reset_ternary_view,
    ternary_axes_limits,
)

#: An equilateral triangle's height / base.
EQUILATERAL_RATIO = math.sqrt(3.0) / 2.0
#: How far the measured ratio may sit from the ideal before it counts as stretched.
TOLERANCE = 0.03

#: The raw ratio scale the labels read in: the axes are handed ``component * RAW_SCALE`` as the
#: raw values, so one normalised unit prints as RAW_SCALE.
RAW_SCALE = 40.0

#: The range the app persisted for the real lead-isotope data (ui_state.json -> ternary_ranges).
#: It used to narrow the drawing on startup, which is the flattened trapezoid this file is about.
ZOOMED_RANGE = (
    0.17087023865971235, 0.23881614207058974,
    0.184689697216013, 0.413403997770168,
    0.41339721726071965, 0.6424400641242747,
)
#: The whole triangle: the reference case that already worked and must keep working.
FULL_LIMITS = (0.0, 1.0, 0.0, 1.0, 0.0, 1.0)
#: The keys ``app_state.ternary_manual_limits`` uses, in the order of a six-value window.
MANUAL_KEYS = ("tmin", "tmax", "lmin", "lmax", "rmin", "rmax")

#: Sizes to check: the shipping figure and the export preset's canvas.
FIGURE_CASES = (
    ((13.0, 9.0), 130),
    ((3.346456692913386, 2.409448818897638), 300),
)

#: Data gathered around one spot, so the inferred range is the app's auto-zoom window.
NARROW_COMPONENTS = (
    np.array([0.20, 0.22, 0.18]),
    np.array([0.30, 0.25, 0.35]),
    np.array([0.50, 0.53, 0.47]),
)
#: The three vertices, so the inferred range is the whole triangle.
FULL_COMPONENTS = (
    np.array([1.0, 0.0, 0.0]),
    np.array([0.0, 1.0, 0.0]),
    np.array([0.0, 0.0, 1.0]),
)

#: A colour per marker, so each known data point can be found again in the rendered pixels.
POINT_COLOURS = ((1.0, 0.0, 0.0), (0.0, 0.6, 0.0), (0.0, 0.0, 1.0))
#: How far a pixel may sit from a marker colour and still count as that marker (anti-aliasing).
COLOUR_TOLERANCE = 60.0


@pytest.fixture(autouse=True)
def _restore_ternary_state():
    """Put the ternary app state back after each test.

    The ink these measurements look for is deliberately *not* pinned here.  It used to be: another
    test module called ``plt.style.use`` and left matplotlib's global rcParams with a white
    ``axes.edgecolor``, so a white outline on a white figure rendered no dark pixel at all and a
    full-suite run read "nothing was drawn" where this file alone passed.  That leak is fixed at
    its source now (``tests/test_display_panel_themes.py`` restores rcParams), and pinning the
    style here would hide it again - the pixel measurements only stay honest while the ambient
    rcParams are the app's own.
    """
    snapshot = {
        "manual": dict(getattr(app_state, "ternary_manual_limits", {}) or {}),
        "manual_enabled": bool(app_state.ternary_manual_limits_enabled),
        "auto_zoom": bool(getattr(app_state, "ternary_auto_zoom", True)),
        "mode": getattr(app_state, "ternary_limit_mode", None),
        "ranges": dict(getattr(app_state, "ternary_ranges", {}) or {}),
    }
    yield
    state_gateway.set_ternary_manual_limits(snapshot["manual"])
    state_gateway.set_ternary_manual_limits_enabled(snapshot["manual_enabled"])
    state_gateway.set_ternary_auto_zoom(snapshot["auto_zoom"])
    if snapshot["mode"] is not None:
        state_gateway.set_ternary_limit_mode(snapshot["mode"])
    state_gateway.set_ternary_ranges(snapshot["ranges"])


def visible_region_corners(limits) -> np.ndarray:
    """The corners of the region mpltern draws for *limits*, in ternary coordinates.

    mpltern shows the intersection of the triangle with the box
    ``[tmin,tmax] x [lmin,lmax] x [rmin,rmax]``.  With the full limits that is the triangle; as
    soon as a component is narrowed it is the view hexagon - the shape an explicit zoom draws, and
    the shape the default view avoids.
    """
    tmin, tmax, lmin, lmax, rmin, rmax = (float(v) for v in limits)
    return np.array([
        (tmax, lmin, 1.0 - tmax - lmin),
        (tmax, 1.0 - tmax - rmin, rmin),
        (1.0 - lmax - rmin, lmax, rmin),
        (tmin, lmax, 1.0 - lmax - tmin),
        (tmin, 1.0 - rmax - tmin, rmax),
        (1.0 - rmax - lmin, lmin, rmax),
    ])


def configured_axes(
    figsize=(13.0, 9.0),
    dpi=130,
    components=NARROW_COMPONENTS,
    points: bool = False,
    manual_enabled: bool = False,
):
    """The axes exactly as the app configures them, with a known raw scale for the labels."""
    state_gateway.set_ternary_limit_mode("both")
    state_gateway.set_ternary_manual_limits_enabled(manual_enabled)
    state_gateway.set_ternary_auto_zoom(True)

    t_vals, l_vals, r_vals = components
    figure = Figure(figsize=figsize, dpi=dpi)
    FigureCanvasAgg(figure)
    axes = figure.add_subplot(111, projection="ternary")
    configure_ternary_axis(
        axes,
        t_vals,
        l_vals,
        r_vals,
        labels=("T", "L", "R"),
        raw_values=(t_vals * RAW_SCALE, l_vals * RAW_SCALE, r_vals * RAW_SCALE),
    )
    if points:
        axes.scatter(t_vals, l_vals, r_vals, c=list(POINT_COLOURS), s=90, edgecolors="none")
    return figure, axes


def drawn_pixels(axes, figure) -> tuple[float, float] | None:
    """The pixel bbox of the region the axes itself draws, as ``(width, height)``.

    Every tick, tick label, axis label and gridline is switched off first, so the only ink left is
    the region's own outline - the three spines mpltern places at the axes' limits - and the
    measurement is the geometry alone.  The values are read from the rendered pixels, never from
    ``ax.transData`` (see the module docstring for what that transform actually describes).  The
    tick labels are put back on the current window afterwards, so a pixel measurement can sit
    between two label readings.
    """
    window = get_ternary_label_range(axes)
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
    measured = None
    if columns.size:
        width = float(columns.max() - columns.min()) + 1.0
        height = float(rows.max() - rows.min()) + 1.0
        if width > 0.0 and height > 0.0:
            measured = width, height

    if window is not None:
        apply_ternary_label_window(axes, window)
    return measured


def shape_ratio(measured) -> float | None:
    """The height/width of a measured pixel bbox."""
    if measured is None:
        return None
    return measured[1] / measured[0]


def point_centroids(figure, axes) -> list[tuple[float, float]]:
    """Where each coloured data point landed, in pixels, read from the rendered buffer.

    The magnification has to be measured on the points themselves: zooming into the middle of the
    triangle makes the drawn region *wider and shorter* than the triangle (measured 1043 x 904 ->
    1690 x 538 px at 13x9in @130dpi), so the outline's bounding box is no proxy for it.  Each point
    ist drawn in its own colour and found again by the centroid of that colour's pixels.
    """
    figure.canvas.draw()
    buffer = np.asarray(figure.canvas.buffer_rgba())[:, :, :3].astype(float)
    centroids: list[tuple[float, float]] = []
    for colour in POINT_COLOURS:
        mask = np.linalg.norm(buffer - np.asarray(colour) * 255.0, axis=2) < COLOUR_TOLERANCE
        rows, columns = np.nonzero(mask)
        assert columns.size > 0, f"the marker drawn in {colour} was not found in the pixels"
        centroids.append((float(columns.mean()), float(rows.mean())))
    return centroids


def pairwise_distances(centroids) -> list[float]:
    """The three pixel distances between the three measured markers."""
    distances: list[float] = []
    for first, second in ((0, 1), (0, 2), (1, 2)):
        delta = np.asarray(centroids[first]) - np.asarray(centroids[second])
        distances.append(float(np.hypot(delta[0], delta[1])))
    return distances


def tick_values(axes, name: str = "t") -> list[float]:
    """The raw values the *name* axis labels carry, parsed from the rendered texts."""
    axis = getattr(axes, f"{name}axis", None)
    if axis is None:
        return []
    values: list[float] = []
    for text in axis.get_ticklabels():
        try:
            values.append(float(text.get_text()))
        except ValueError:
            continue
    return values


def test_the_full_triangle_measures_equilateral() -> None:
    """Sanity: the reference case really does render as an equilateral triangle."""
    for figsize, dpi in FIGURE_CASES:
        figure, axes = configured_axes(figsize, dpi, FULL_COMPONENTS)
        measured = shape_ratio(drawn_pixels(axes, figure))
        assert measured is not None, f"the ternary figure drew nothing at {figsize}@{dpi}"
        assert abs(measured - EQUILATERAL_RATIO) <= TOLERANCE * EQUILATERAL_RATIO, (
            f"the full triangle measured h/w={measured:.4f} at {figsize}@{dpi}, "
            f"equilateral is {EQUILATERAL_RATIO:.4f}"
        )
        assert get_ternary_label_range(axes) == pytest.approx(FULL_LIMITS)


def test_the_automatic_range_labels_the_axes_without_narrowing_the_drawing() -> None:
    """A range that is not asked for labels the axes; it never flattens the drawing.

    This is the defect the default half of the behaviour fixes: a narrowed range used to be handed
    to mpltern, and the region it draws for one is the view hexagon (h/w 0.3178 against 0.8660).
    The range still exists - as the label window - so the drawing has to measure equilateral at
    every size while the labels carry the range.
    """
    for figsize, dpi in FIGURE_CASES:
        figure, axes = configured_axes(figsize, dpi, NARROW_COMPONENTS)
        inferred_labels = tick_values(axes)

        measured = shape_ratio(drawn_pixels(axes, figure))
        assert measured is not None, f"the ternary figure drew nothing at {figsize}@{dpi}"
        deviation = measured / EQUILATERAL_RATIO - 1.0
        assert abs(deviation) <= TOLERANCE, (
            f"the drawn ternary region is stretched at {figsize}@{dpi}: "
            f"h/w={measured:.4f}, equilateral is {EQUILATERAL_RATIO:.4f} "
            f"({deviation:+.1%})"
        )
        assert ternary_axes_limits(axes) == pytest.approx(FULL_LIMITS), (
            "an automatic range must not narrow the drawing"
        )

        window = get_ternary_label_range(axes)
        assert window is not None, "a fresh plot records no label window"
        assert window != pytest.approx(FULL_LIMITS), (
            "the automatic range is what the labels report"
        )
        low, high = window[0] * RAW_SCALE, window[1] * RAW_SCALE
        assert len(inferred_labels) >= 3, inferred_labels
        assert low - 1e-9 <= min(inferred_labels), (inferred_labels, low, high)
        assert max(inferred_labels) <= high + 1e-9, (inferred_labels, low, high)
        # The ladder covers the window up to one step at each end: the ticks are inside the range
        # they report and sit on round numbers, so they cannot start or stop exactly on it.
        steps = np.diff(np.asarray(inferred_labels, dtype=float))
        assert min(inferred_labels) - low <= steps[0] + 1e-9, (inferred_labels, low, high)
        assert high - max(inferred_labels) <= steps[0] + 1e-9, (inferred_labels, low, high)
        # Constant density: whatever window is current, the values are an even ladder of nice
        # numbers and the count stays bounded - a fixed number of ticks per span, not a fixed step.
        assert 3 <= len(inferred_labels) <= 7, inferred_labels
        assert np.allclose(steps, steps[0], rtol=0.0, atol=1e-9), inferred_labels


def test_a_persisted_range_cannot_flatten_a_fresh_plot() -> None:
    """The rangethe real session persisted is not enough to clip the drawing any more.

    ui_state.json carries ``ternary_ranges`` for the lead-isotope data; loaded as the manual window
    with the checkbox clear it must leave the whole triangle alone, because drawing it is what
    produced the flat trapezoid.
    """
    state_gateway.set_ternary_manual_limits(dict(zip(MANUAL_KEYS, ZOOMED_RANGE)))
    figure, axes = configured_axes(manual_enabled=False)

    assert ternary_axes_limits(axes) == pytest.approx(FULL_LIMITS), (
        "a stored range must not narrow the drawing while the manual box is clear"
    )
    measured = shape_ratio(drawn_pixels(axes, figure))
    assert measured is not None, "the ternary figure drew nothing"
    assert abs(measured - EQUILATERAL_RATIO) <= TOLERANCE * EQUILATERAL_RATIO, (
        f"the persisted range flattened the drawing: h/w={measured:.4f}"
    )


def test_a_manual_window_is_drawn_at_render_time() -> None:
    """With the checkbox ticked the stored window is what is drawn - and what the labels report.

    That is what the checkbox means, and it is what makes a manual view survive a re-render.
    """
    state_gateway.set_ternary_manual_limits(dict(zip(MANUAL_KEYS, ZOOMED_RANGE)))
    figure, axes = configured_axes(manual_enabled=True)

    expected = manual_ternary_label_range("both")
    assert ternary_axes_limits(axes) == pytest.approx(expected), (
        "the manual window was not applied to the drawing"
    )
    assert get_ternary_label_range(axes) == pytest.approx(expected), (
        "the labels must describe the window that is drawn"
    )
    measured = shape_ratio(drawn_pixels(axes, figure))
    assert measured is not None, "the ternary figure drew nothing"
    assert abs(measured - EQUILATERAL_RATIO) > TOLERANCE * EQUILATERAL_RATIO, (
        "the manual window was expected to draw the window's own shape, not the whole triangle"
    )

    # mpltern clips a window that reaches past the triangle; the labels must describe what is left.
    state_gateway.set_ternary_manual_limits(
        dict(zip(MANUAL_KEYS, (0.5, 1.0, 0.5, 1.0, 0.0, 1.0)))
    )
    clipped_figure, clipped_axes = configured_axes(manual_enabled=True)
    drawn = ternary_axes_limits(clipped_axes)
    assert drawn is not None
    assert drawn != pytest.approx(manual_ternary_label_range("both")), (
        "this window was expected to be clipped by the triangle"
    )
    assert get_ternary_label_range(clipped_axes) == pytest.approx(drawn), (
        "the labels must describe the window mpltern really drew"
    )
    assert shape_ratio(drawn_pixels(clipped_axes, clipped_figure)) is not None


def test_a_zoomed_window_survives_a_re_render_only_with_the_manual_box() -> None:
    """The gesture stores its window; the checkbox is what makes the next render draw it again.

    ``_remember_ternary_limits`` writes the window but deliberately leaves the box alone, so a
    re-render is the default view until the user ticks it - and the stored window from then on.
    """
    state_gateway.set_ternary_manual_limits(dict(zip(MANUAL_KEYS, ZOOMED_RANGE)))

    # Box clear: the next render is the default view again - whole triangle, inferred labels.
    _, plain = configured_axes(manual_enabled=False)
    assert ternary_axes_limits(plain) == pytest.approx(FULL_LIMITS)
    assert get_ternary_label_range(plain) != pytest.approx(FULL_LIMITS)

    # Box ticked: the stored window is drawn and labelled, so the zoom survives the re-render.
    _, kept = configured_axes(manual_enabled=True)
    expected = manual_ternary_label_range("both")
    assert ternary_axes_limits(kept) == pytest.approx(expected)
    assert get_ternary_label_range(kept) == pytest.approx(expected)


def test_an_explicit_zoom_magnifies_the_points_and_moves_the_labels() -> None:
    """The other half of the behaviour, measured: the same points, further apart, new numbers.

    The user asked for the magnification, so ``set_ternary_lim`` has to receive the zoomed window
    again; the labels then describe exactly the window that is drawn.  The pixels are the evidence:
    every pair of known markers must end up further apart than it started.
    """
    for figsize, dpi in FIGURE_CASES:
        figure, axes = configured_axes(figsize, dpi, NARROW_COMPONENTS, points=True)
        before_points = point_centroids(figure, axes)
        before_labels = tick_values(axes)
        assert len(before_labels) >= 3, before_labels

        window = apply_ternary_zoom_window(axes, ZOOMED_RANGE)
        assert window == pytest.approx(ZOOMED_RANGE), window

        after_points = point_centroids(figure, axes)
        for index, (before, after) in enumerate(
            zip(pairwise_distances(before_points), pairwise_distances(after_points))
        ):
            assert after > 1.5 * before, (
                f"marker pair {index} did not grow at {figsize}@{dpi}: {before:.1f} -> {after:.1f} px"
            )

        assert ternary_axes_limits(axes) == pytest.approx(ZOOMED_RANGE), (
            "the zoom must narrow the drawing, not only the labels"
        )
        assert len(after_points) == len(before_points)

        after_labels = tick_values(axes)
        assert after_labels != before_labels, "the zoom did not change the tick labels"
        low, high = window[0] * RAW_SCALE, window[1] * RAW_SCALE
        assert len(after_labels) >= 3, after_labels
        assert low - 1e-9 <= min(after_labels), (after_labels, low, high)
        assert max(after_labels) <= high + 1e-9, (after_labels, low, high)
        steps = np.diff(np.asarray(after_labels, dtype=float))
        assert min(after_labels) - low <= steps[0] + 1e-9, (after_labels, low, high)
        assert high - max(after_labels) <= steps[0] + 1e-9, (after_labels, low, high)
        assert np.allclose(steps, steps[0], rtol=0.0, atol=1e-9), after_labels
        assert get_ternary_label_range(axes) == pytest.approx(window), (
            "the labels must describe the window that is drawn"
        )

        # The accepted trade-off of zooming, measured rather than assumed: the outline is the
        # window's own shape, which is flatter than the triangle the default view draws.
        zoomed_ratio = shape_ratio(drawn_pixels(axes, figure))
        assert zoomed_ratio is not None, "the zoomed figure drew nothing"
        assert zoomed_ratio < EQUILATERAL_RATIO - TOLERANCE, (
            f"a zoomed outline measured h/w={zoomed_ratio:.4f}; the window's hexagon is flatter "
            f"than the equilateral {EQUILATERAL_RATIO:.4f}"
        )


def test_the_reset_returns_to_the_full_triangle_and_the_data_labels() -> None:
    """An explicit zoom is undone both ways: the drawing goes back and so do the numbers.

    ``app_state.ternary_ranges`` holds the range the last render reported, which is what a fresh
    plot labels the axes with - the data range, not the zoom.
    """
    figure, axes = configured_axes(points=True)
    data_window = get_ternary_label_range(axes)
    assert data_window is not None, "a fresh plot records no label window"
    state_gateway.set_ternary_ranges(
        {
            "t": tuple(data_window[0:2]),
            "l": tuple(data_window[2:4]),
            "r": tuple(data_window[4:6]),
        }
    )
    before_pixels = drawn_pixels(axes, figure)
    before_labels = tick_values(axes)
    before_points = point_centroids(figure, axes)
    assert before_pixels is not None, "the reference render drew nothing"

    apply_ternary_zoom_window(axes, ZOOMED_RANGE)
    assert drawn_pixels(axes, figure) != before_pixels, "the zoom did not move the drawing"

    reset_ternary_view(axes)

    assert ternary_axes_limits(axes) == pytest.approx(FULL_LIMITS), (
        "the reset must draw the whole triangle again"
    )
    assert get_ternary_label_range(axes) == pytest.approx(data_window)
    assert tick_values(axes) == before_labels, "the reset did not restore the data-range labels"
    assert drawn_pixels(axes, figure) == before_pixels, "the reset did not restore the drawing"
    assert pairwise_distances(point_centroids(figure, axes)) == pytest.approx(
        pairwise_distances(before_points)
    ), "the reset did not put the points back where they were"


def test_a_zoom_leaves_the_manual_limits_checkbox_alone() -> None:
    """An earlier fix removed the write that flipped the box on; zooming must not bring it back."""
    for enabled in (False, True):
        state_gateway.set_ternary_manual_limits(dict(zip(MANUAL_KEYS, ZOOMED_RANGE)))
        _, axes = configured_axes(manual_enabled=enabled)
        assert app_state.ternary_manual_limits_enabled is enabled

        window = apply_ternary_zoom_window(axes, ZOOMED_RANGE)

        assert app_state.ternary_manual_limits_enabled is enabled, (
            f"zooming changed the manual-limits checkbox (was {enabled})"
        )
        assert window == pytest.approx(ZOOMED_RANGE), window
        assert ternary_axes_limits(axes) == pytest.approx(window)
        assert get_ternary_label_range(axes) == pytest.approx(window)


def test_a_zoomed_region_cannot_be_both_equilateral_and_undistorted() -> None:
    """Documents the root cause, so the next reader does not re-derive it.

    The drawn region for narrowed limits *is* the view hexagon: its six corners sit on the window's
    bounds and its bounding box is far wider than ``sqrt(3)/2``, so putting it in an equilateral
    frame requires stretching the data - and mpltern forces exactly that choice, because
    ``get_aspect()`` is both the data aspect and the expansion multiplier.  That incompatibility is
    why the default view always draws the full triangle, and why a zoom's outline is the window's
    shape instead; this asserts it so that a future change which removes it fails here loudly
    rather than silently changing how every ternary plot is scaled.
    """
    from matplotlib import transforms as mtransforms

    #: The corners of mpltern's default triangle in its "original data" space (measured).
    default_boxin = (-1.0 / math.sqrt(3.0), 0.0, 1.0 / math.sqrt(3.0), 1.0)
    unit_triangle = np.array([[-0.5 / math.sqrt(3.0), 0.0], [0.5 / math.sqrt(3.0), 1.0]])

    corners = visible_region_corners(ZOOMED_RANGE)
    assert len({tuple(np.round(row, 9)) for row in corners}) == 6, (
        "a narrowed window is the view hexagon, not a triangle"
    )
    for row in corners:
        assert np.isclose(float(row.sum()), 1.0), row

    for figsize, dpi in FIGURE_CASES:
        figure = Figure(figsize=figsize, dpi=dpi)
        FigureCanvasAgg(figure)
        axes = figure.add_subplot(111, projection="ternary")
        figure.set_layout_engine("none")
        axes.set_aspect("equal", adjustable="box")
        axes.set_ternary_lim(*ZOOMED_RANGE)

        box_out = axes._create_bbox_from_ternary_lim("rectangle")
        transform = mtransforms.BboxTransform(
            mtransforms.Bbox.from_extents(*default_boxin), box_out,
        )
        region = mtransforms.Bbox.unit()
        region.update_from_data_xy(transform.transform(unit_triangle))
        natural = region.height / region.width

        # The hexagon's own aspect is nowhere near equilateral, so a distortion-free equilateral
        # rendering of it does not exist.
        assert abs(natural - EQUILATERAL_RATIO) > TOLERANCE * EQUILATERAL_RATIO, (
            "the view region's own aspect matched the equilateral one; the incompatibility this "
            "test documents no longer holds, so the draw-time correction can be revisited"
        )
