"""The hover tooltip moves itself, not the chart.

Reported: avoiding occlusion must not cost the chart. The box used to sit at a fixed (20, 20) points - up and to
the right - so near the top or right edge it was clipped, and elsewhere it covered the point it described. It now
opens away from the nearest edge, and the axes limits are never touched.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pytest  # noqa: E402

from visualization.plotting.tooltip import place_tooltip  # noqa: E402


@pytest.fixture()
def scene():
    fig, ax = plt.subplots()
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    annotation = ax.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points")
    yield ax, annotation
    plt.close(fig)


@pytest.mark.parametrize(
    ("x", "y", "expected"),
    [
        (2.0, 2.0, (20, 20)),
        (8.0, 2.0, (-20, 20)),
        (2.0, 8.0, (20, -28)),
        (8.0, 8.0, (-20, -28)),
    ],
)
def test_the_box_opens_away_from_the_nearest_edge(scene, x, y, expected) -> None:
    ax, annotation = scene
    place_tooltip(annotation, x, y)
    assert annotation.get_position() == expected, "right and upper halves open the other way"
    assert annotation.xy == (x, y)


def test_the_axes_limits_are_not_touched(scene) -> None:
    """The tooltip never costs the chart its view - which is what the review asked for."""
    ax, annotation = scene
    before = (ax.get_xlim(), ax.get_ylim())
    place_tooltip(annotation, 9.5, 9.5)
    assert (ax.get_xlim(), ax.get_ylim()) == before
