"""The hover tooltip stays on top of whatever is drawn after it.

Reported: the tooltip should always be on top. It was raised once, when it was made; a render that added artists
later - or an overlay, or the selection marks - painted over it. The show path raises it again on every hover, and the
annotation no longer clips itself at the axes edge.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from visualization.plotting.tooltip import TOOLTIP_MIN_ZORDER, raise_tooltip_above_data  # noqa: E402


def test_an_artist_added_later_is_passed_by_a_re_raise() -> None:
    figure, axes = plt.subplots()
    try:
        annotation = axes.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points")
        raise_tooltip_above_data(axes, annotation)
        late = axes.scatter([1, 2], [3, 4], zorder=5000)

        # What the show path now does every time the tooltip appears.
        raise_tooltip_above_data(axes, annotation)

        assert annotation.get_zorder() > late.get_zorder()
        assert annotation.get_zorder() >= TOOLTIP_MIN_ZORDER
    finally:
        plt.close(figure)


def test_the_tooltip_does_not_clip_itself() -> None:
    """A box drawn near an edge is still the whole box."""
    from visualization.event_handlers.pointer_events import _annotation_for

    figure = plt.figure()
    try:
        axes = figure.add_subplot(111)
        annotation = _annotation_for(figure)
        assert annotation is not None
        assert annotation.get_clip_on() is False
        assert annotation.get_annotation_clip() is False
    finally:
        plt.close(figure)

