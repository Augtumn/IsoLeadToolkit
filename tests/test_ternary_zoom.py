"""Ternary zoom geometry: the pure functions the Qt gesture relies on.

The interactive part is covered by tests/test_ternary_zoom_qt.py (real widgets, real
Qt events); this module only checks the maths: converting between mpltern's Cartesian
space and ternary components, and turning a drag into ternary limits.
"""
from __future__ import annotations

import matplotlib
import pytest

matplotlib.use("Agg")

import mpltern  # noqa: F401  (registers the "ternary" projection)
from matplotlib.figure import Figure  # noqa: E402

from visualization.plotting.ternary import (  # noqa: E402
    cartesian_to_ternary,
    similar_subtriangle_limits,
    ternary_limits_cover_full_view,
)

CENTROID = (0.0, 1.0 / 3.0)
APEX = (0.0, 1.0)
FULL_LIMITS = (0.0, 1.0, 0.0, 1.0, 0.0, 1.0)


def test_cartesian_to_ternary_matches_mpltern_geometry() -> None:
    """The mapping must invert mpltern's own vertex placement."""
    axes = Figure().add_subplot(projection="ternary")
    for components in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1 / 3, 1 / 3, 1 / 3)):
        axes.scatter([components[0]], [components[1]], [components[2]])
        offset = axes.collections[-1].get_offsets()[0]
        back = cartesian_to_ternary(float(offset[0]), float(offset[1]))
        assert max(abs(back[i] - components[i]) for i in range(3)) < 1e-9, components


def test_drag_from_centroid_makes_a_similar_subtriangle() -> None:
    """Halfway to the apex doubles the exit scale, so the ratio is 1/2."""
    midway = (0.0, (1.0 / 3.0 + 1.0) / 2.0)
    limits = similar_subtriangle_limits(CENTROID[0], CENTROID[1], *midway)
    assert limits == pytest.approx((1 / 6, 2 / 3, 1 / 6, 2 / 3, 1 / 6, 2 / 3))
    assert not ternary_limits_cover_full_view(limits)


def test_dragging_towards_a_vertex_zooms_that_corner() -> None:
    limits = similar_subtriangle_limits(-0.4, 0.1, -0.2, 0.1)
    tmin, tmax, lmin, lmax, rmin, rmax = limits
    assert lmin > 0.5, limits          # the left component dominates the zoom
    assert rmax < 0.5 and tmax < 0.5, limits
    assert not ternary_limits_cover_full_view(limits)


def test_outward_or_zero_drag_resets_the_zoom() -> None:
    assert ternary_limits_cover_full_view(
        similar_subtriangle_limits(CENTROID[0], CENTROID[1], *APEX)
    )
    assert similar_subtriangle_limits(CENTROID[0], CENTROID[1], *CENTROID) == pytest.approx(
        FULL_LIMITS
    )
    assert ternary_limits_cover_full_view(
        similar_subtriangle_limits(CENTROID[0], CENTROID[1], 5.0, 5.0)
    )
