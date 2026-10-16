"""The marginal KDE belongs to the panel that draws it.

Reported: with more than one panel open, only one of them could show the marginal KDE. The axes were kept
in a single list on the application, and every panel cleared that list before drawing its own, so the
panel that rendered second removed the first panel's axes. The layout used to make room for them was
tracked with a single module flag for the same reason.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from core import state_gateway  # noqa: E402
from visualization.plotting import kde as kde_utils  # noqa: E402


@pytest.fixture
def two_panels():
    """Two figures, as two panel windows are."""
    first = plt.subplots(figsize=(4, 3))
    second = plt.subplots(figsize=(4, 3))
    yield first, second
    plt.close(first[0])
    plt.close(second[0])


def _draw(fig, ax, frame, palette, cats) -> None:
    state_gateway.set_axis(ax)
    kde_utils.draw_marginal_kde(ax, frame, "Site", palette, cats)


@pytest.fixture
def sample():
    frame = pd.DataFrame(
        {
            "_emb_x": [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
            "_emb_y": [0.0, 1.0, 0.5, 1.5, 0.2, 1.2, 0.8, 1.8],
            "Site": ["A", "A", "B", "B", "A", "B", "A", "B"],
        }
    )
    return frame, {"A": "#1f77b4", "B": "#d62728"}, ["A", "B"]


def _marginal_count(fig) -> int:
    """Axes beyond the one data axes: the top and right marginals."""
    return len(fig.axes)


def test_two_panels_show_a_marginal_kde_at_the_same_time(two_panels, sample) -> None:
    (fig1, ax1), (fig2, ax2) = two_panels
    frame, palette, cats = sample

    _draw(fig1, ax1, frame, palette, cats)
    _draw(fig2, ax2, frame, palette, cats)

    assert _marginal_count(fig1) == 3, "the first panel kept its marginal axes"
    assert _marginal_count(fig2) == 3, "the second panel drew its own as well"


def test_clearing_one_panel_leaves_the_other_alone(two_panels, sample) -> None:
    (fig1, ax1), (fig2, ax2) = two_panels
    frame, palette, cats = sample

    _draw(fig1, ax1, frame, palette, cats)
    _draw(fig2, ax2, frame, palette, cats)

    state_gateway.set_axis(ax2)
    kde_utils.clear_marginal_axes(ax2)
    assert _marginal_count(fig2) == 1, "the panel that cleared lost its own marginals"
    assert _marginal_count(fig1) == 3, "the other panel is untouched"

    _draw(fig2, ax2, frame, palette, cats)
    assert _marginal_count(fig1) == 3 and _marginal_count(fig2) == 3

    state_gateway.set_axis(ax1)
    kde_utils.clear_marginal_axes(ax1)
    assert _marginal_count(fig1) == 1
    assert _marginal_count(fig2) == 3, "clearing the first panel did not touch the second"


def test_the_layout_of_each_panel_is_restored_on_its_own(two_panels, sample) -> None:
    """Divider axes cannot coexist with constrained layout, so drawing disables it per figure."""
    (fig1, ax1), (fig2, ax2) = two_panels
    frame, palette, cats = sample
    fig1.set_layout_engine("constrained")
    fig2.set_layout_engine("constrained")

    _draw(fig1, ax1, frame, palette, cats)
    _draw(fig2, ax2, frame, palette, cats)

    state_gateway.set_axis(ax1)
    kde_utils.clear_marginal_axes(ax1)
    assert fig1.get_layout_engine() is not None and fig1.get_layout_engine().__class__.__name__ == "ConstrainedLayoutEngine"
    assert fig2.get_layout_engine().__class__.__name__ == "PlaceHolderLayoutEngine", (
        "the second panel is still holding its marginals, so its layout stays disabled"
    )
