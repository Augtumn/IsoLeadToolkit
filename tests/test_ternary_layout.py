"""Ternary figures run without constrained_layout; the 2D path restores it."""
from __future__ import annotations

import warnings

import matplotlib
import pytest

matplotlib.use("Agg")

import mpltern  # noqa: F401  (registers the "ternary" projection)
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.layout_engine import ConstrainedLayoutEngine, PlaceHolderLayoutEngine  # noqa: E402

from visualization.plotting.style import configure_constrained_layout  # noqa: E402
from visualization.plotting.ternary import use_ternary_layout  # noqa: E402


def test_a_ternary_figure_drops_the_layout_engine() -> None:
    figure = Figure(figsize=(6, 5), constrained_layout=True)
    assert isinstance(figure.get_layout_engine(), ConstrainedLayoutEngine)

    use_ternary_layout(figure)

    # matplotlib represents "no engine" with a placeholder, not None.
    assert isinstance(figure.get_layout_engine(), PlaceHolderLayoutEngine)


def test_it_is_idempotent_and_tolerates_missing_figures() -> None:
    figure = Figure(figsize=(6, 5), constrained_layout=True)
    use_ternary_layout(figure)

    use_ternary_layout(figure)
    use_ternary_layout(None)

    assert isinstance(figure.get_layout_engine(), PlaceHolderLayoutEngine)


def test_the_2d_path_restores_constrained_layout() -> None:
    """A 2D render over the same figure takes the engine back."""
    figure = Figure(figsize=(6, 5))
    use_ternary_layout(figure)

    configure_constrained_layout(figure)

    assert isinstance(figure.get_layout_engine(), ConstrainedLayoutEngine)


def test_drawing_without_the_engine_emits_no_collapse_warning() -> None:
    figure = Figure(figsize=(6, 5), constrained_layout=True)
    axes = figure.add_subplot(projection="ternary")
    axes.scatter([0.3, 0.5], [0.3, 0.2], [0.4, 0.3])
    use_ternary_layout(figure)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        figure.canvas.draw()

    assert not [
        w for w in caught if "collapsed to zero" in str(w.message)
    ], [str(w.message) for w in caught]
