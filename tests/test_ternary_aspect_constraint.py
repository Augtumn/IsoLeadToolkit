"""The ternary triangle is equilateral, whatever the styles do to the aspect.

mpltern fills its axes box with the triangle, so the equal aspect is the physical constraint that
keeps the three edges the same length - and anything global can take it away: plt.style.use resets
rcParams while a window is being assembled, a theme can carry a different image.aspect, and a future
geometry control in the style panel would do the same. A stretched ternary triangle is meaningless
as a composition diagram, so the constraint is re-asserted after every draw.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib as mpl  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import mpltern  # noqa: E402,F401
import numpy as np  # noqa: E402

from visualization.plotting.ternary import configure_ternary_axis, enforce_ternary_aspect  # noqa: E402


def _edges(ax) -> list[float]:
    corners = [
        ax.transData.transform((0.0, 1.0)),
        ax.transData.transform((-1 / np.sqrt(3), 0.0)),
        ax.transData.transform((1 / np.sqrt(3), 0.0)),
    ]
    first, second, third = corners
    return [
        float(np.linalg.norm(first - second)),
        float(np.linalg.norm(second - third)),
        float(np.linalg.norm(third - first)),
    ]


def _figure():
    t = np.array([0.5, 0.2])
    l = np.array([0.3, 0.5])
    r = 1.0 - t - l
    figure = plt.figure(figsize=(14, 4))
    axes = figure.add_subplot(projection="ternary")
    axes.scatter(t, l, r)
    configure_ternary_axis(axes, t, l, r, labels=("A", "B", "C"), raw_values=(t * 40, l * 40, r * 40))
    return figure, axes


def test_a_fresh_ternary_triangle_is_equilateral() -> None:
    figure, axes = _figure()
    try:
        figure.canvas.draw()
        edges = _edges(axes)
        assert max(edges) / min(edges) < 1.01, edges
    finally:
        plt.close(figure)


def test_a_hostile_aspect_cannot_keep_the_triangle_stretched(caplog) -> None:
    """The invariant must survive a style that sets an incompatible aspect."""
    figure, axes = _figure()
    original = mpl.rcParams["image.aspect"]
    try:
        mpl.rcParams["image.aspect"] = "auto"
        axes.set_aspect("auto")

        with caplog.at_level("WARNING"):
            figure.canvas.draw()
            figure.canvas.draw()

        edges = _edges(axes)
        assert max(edges) / min(edges) < 1.01, f"the constraint was broken: {edges}"
        assert float(axes.get_aspect()) == 1.0
        assert any("restoring equal" in record.getMessage() for record in caplog.records), (
            "a drift must be reported, not corrected in silence"
        )
    finally:
        mpl.rcParams["image.aspect"] = original
        plt.close(figure)


def test_enforce_ternary_aspect_reports_whether_it_corrected() -> None:
    figure, axes = _figure()
    try:
        axes.set_aspect("equal", adjustable="box")
        assert enforce_ternary_aspect(axes) is False, "no drift, no correction"

        axes.set_aspect("auto")
        assert enforce_ternary_aspect(axes) is True, "a drift must be corrected"
    finally:
        plt.close(figure)
