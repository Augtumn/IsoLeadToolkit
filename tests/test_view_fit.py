"""Fitting a panel to its points, tested without a window.

These rules lived in the canvas mixin, so testing them meant building one. They are pure functions in
visualization.plotting.view_fit now: an axes in, limits out. What the mixin keeps is its own business - which panels
to frame, and whether a view the user set may be touched.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import pytest  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

from visualization.plotting.view_fit import fit_axes, panel_targets, scatter_bounds  # noqa: E402


class _Collection:
    def __init__(self, points):
        self._points = list(points)

    def get_offsets(self):
        return list(self._points)


class _Axes:
    def __init__(self, name, points, z=False):
        self.name = name
        self.collections = [_Collection(points)]
        self.xlim = self.ylim = self.zlim = None

    def set_xlim(self, low, high):
        self.xlim = (low, high)

    def set_ylim(self, low, high):
        self.ylim = (low, high)

    def set_zlim(self, low, high):
        self.zlim = (low, high)

    def set_ternary_lim(self, *limits):
        self.ternary = limits


def test_bounds_keep_only_finite_points() -> None:
    axes = _Axes("2d", [(1.0, 2.0), (float("nan"), 3.0), (4.0, float("inf")), (5.0, 6.0)])
    xs, ys, zs = scatter_bounds(axes)
    assert xs == [1.0, 5.0]
    assert ys == [2.0, 6.0]
    assert zs == []


def test_a_2d_fit_adds_five_percent_padding() -> None:
    axes = _Axes("2d", [(0.0, 0.0), (100.0, 200.0)])
    assert fit_axes("2D", axes) is True
    assert axes.xlim == (-5.0, 105.0)
    assert axes.ylim == (-10.0, 210.0)


def test_a_flat_axis_gets_a_unit_of_room() -> None:
    axes = _Axes("2d", [(7.0, 7.0)])
    assert fit_axes("2D", axes) is True
    assert axes.xlim == (6.0, 8.0)
    assert axes.ylim == (6.0, 8.0)


def test_a_3d_fit_sets_the_z_limits_too() -> None:
    axes = _Axes("3d", [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)])
    assert fit_axes("3D", axes) is True
    assert axes.zlim == (3.0, 6.0)


def test_a_ternary_fit_frames_the_whole_triangle() -> None:
    axes = _Axes("ternary", [(0.2, 0.3)])
    assert fit_axes("Ternary", axes) is True
    assert axes.ternary == (0.0, 1.0, 0.0, 1.0, 0.0, 1.0)


def test_an_axes_with_no_points_is_not_framed() -> None:
    assert fit_axes("2D", _Axes("2d", [])) is False


def test_panel_targets_use_the_windows_and_fall_back_to_the_single_figure() -> None:
    from core.panel_record import PanelRecord

    windows = [PanelRecord({"mode": "2D", "axes": "a"}), PanelRecord({"mode": "3D", "axes": "b"})]
    assert panel_targets(windows, "single", "PCA") == [("2D", "a"), ("3D", "b")]
    assert panel_targets([], "single", "PCA") == [("PCA", "single")]
    assert panel_targets([], None, "PCA") == []

