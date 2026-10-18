"""The hover highlighter remembers a collection without keeping it alive.

Reported by the same sweep that found the tooltip cache: the highlighter keyed its size and width caches by
id(collection) and kept a strong reference beside each id so the number could not be reused. That reference kept
every collection a re-render detached - and its data arrays - alive for the life of the application: fifty renders,
fifty kept collections, proven. Weak keys let the caches go with the collections and keep id reuse impossible.
"""
from __future__ import annotations

import gc

import matplotlib

matplotlib.use("Agg")

from matplotlib.figure import Figure  # noqa: E402

from visualization.plotting.highlight import HoverHighlighter  # noqa: E402


def test_the_highlight_is_restored_when_it_is_cleared() -> None:
    highlighter = HoverHighlighter()
    figure = Figure()
    axes = figure.add_subplot(111)
    scatter = axes.scatter([1, 2], [3, 4], s=20)
    base = list(scatter.get_sizes())

    assert highlighter.highlight_sample(0, [(scatter, 0)]) is True
    assert list(scatter.get_sizes()) != base, "the point under the cursor is drawn larger"

    assert highlighter.clear() is True
    assert list(scatter.get_sizes()) == base, "and the sizes come back"


def test_a_repeated_target_does_not_redraw() -> None:
    highlighter = HoverHighlighter()
    figure = Figure()
    axes = figure.add_subplot(111)
    scatter = axes.scatter([1, 2], [3, 4], s=20)

    assert highlighter.highlight_sample(0, [(scatter, 0)]) is True
    assert highlighter.highlight_sample(0, [(scatter, 0)]) is False


def test_a_detached_collection_is_not_kept() -> None:
    highlighter = HoverHighlighter()
    figure = Figure()
    axes = figure.add_subplot(111)
    scatter = axes.scatter([1, 2], [3, 4], s=20)
    highlighter.highlight_sample(0, [(scatter, 0)])
    assert len(highlighter._base_sizes) == 1

    # The highlighted list holds the collection strongly while the highlight is on - it has to, to put the sizes
    # back - so the cursor leaving comes first, which is what the application does on the same event.
    assert highlighter.clear() is True
    figure.clf()
    del scatter, axes, figure
    gc.collect()

    assert len(highlighter._base_sizes) == 0, "the cache went with the collection it described"
    assert len(highlighter._base_widths) == 0

