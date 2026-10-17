"""One hover tooltip per figure, keyed by the figure itself.

Reported: with four windows open only two showed a tooltip and a double-click highlight. The cache holding the
tooltips was keyed by id(figure); an id is reused once the old figure is collected, so a panel built later could be
handed the tooltip of a figure that no longer existed. The tooltip was then written into a dead object, and that
panel showed nothing at all.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import pytest  # noqa: E402
from types import SimpleNamespace  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from visualization.event_handlers import pointer_events  # noqa: E402


@pytest.fixture(autouse=True)
def empty_cache():
    pointer_events._figure_annotations.clear()
    yield
    pointer_events._figure_annotations.clear()


def test_the_same_figure_keeps_one_tooltip() -> None:
    figure = Figure()
    figure.add_subplot(111)
    assert pointer_events._annotation_for(figure) is pointer_events._annotation_for(figure)


def test_two_figures_do_not_share_a_tooltip() -> None:
    first = Figure()
    first.add_subplot(111)
    second = Figure()
    second.add_subplot(111)

    assert pointer_events._annotation_for(first) is not pointer_events._annotation_for(second)
    assert len(pointer_events._figure_annotations) == 2


def test_the_cache_is_keyed_by_the_figure() -> None:
    """Not by id(figure): that number is reused, which is what made some panels go dead."""
    figure = Figure()
    figure.add_subplot(111)
    pointer_events._annotation_for(figure)
    assert figure in pointer_events._figure_annotations

def test_an_orphaned_tooltip_is_replaced() -> None:
    """Reported from the log: "tooltip shown ... axes=None" on the panels that showed no tooltip.

    A render that clears the figure takes the axes away, and the annotation made against it is orphaned: it exists,
    its axes is None, and set_visible() draws nothing. The cache used to keep handing that orphan back. An
    annotation's axes cannot be changed, so the orphan is represented by a stub with axes=None.
    """
    figure = Figure()
    figure.add_subplot(111)

    orphan = SimpleNamespace(axes=None)
    pointer_events._figure_annotations[figure] = orphan

    replacement = pointer_events._annotation_for(figure)
    assert replacement is not orphan, "the orphan is not reused"
    assert replacement.axes is not None, "the replacement hangs on an axes"
    assert replacement.axes.figure is figure
    assert pointer_events._figure_annotations[figure] is replacement
