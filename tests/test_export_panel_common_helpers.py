"""Tests for export panel common mixin helpers."""

from __future__ import annotations

from types import SimpleNamespace

from ui.panels.export.common import ExportPanelCommonMixin


class _FakeText:
    def __init__(self, text: str) -> None:
        self._text = text

    def get_text(self) -> str:
        return self._text


class _FakeBbox:
    def __init__(self, points):
        self._points = points

    def get_points(self):
        return self._points


class _IdentityTransform:
    def inverted(self):
        return self

    def transform(self, points):
        return points


class _FakeTitle:
    def set_visible(self, _visible: bool) -> None:
        return None

    def set_fontsize(self, _size: float) -> None:
        return None


class _FakeRebuiltLegend:
    def set_title(self, _title: str) -> None:
        return None

    def get_title(self) -> _FakeTitle:
        return _FakeTitle()


class _FakeLegend:
    def __init__(self, points) -> None:
        self._bbox = _FakeBbox(points)
        self._loc = "best"
        self._ncols = 1
        self.legend_handles = [object()]

    def get_texts(self):
        return [_FakeText("Group A")]

    def get_frame_on(self) -> bool:
        return True

    def get_bbox_to_anchor(self):
        return self._bbox

    def remove(self) -> None:
        return None


class _FakeAxis:
    def __init__(self, points) -> None:
        self._legend = _FakeLegend(points)
        self.transAxes = _IdentityTransform()
        self.legend_kwargs = None

    def get_legend(self):
        return self._legend

    def get_legend_handles_labels(self):
        return [object()], ["Group A"]

    def legend(self, **kwargs):
        self.legend_kwargs = kwargs
        return _FakeRebuiltLegend()


class _FakePanel(ExportPanelCommonMixin):
    @staticmethod
    def _apply_legend_marker_size_from_point(_legend, _point_size: float) -> None:
        return None


def test_normalize_export_legends_collapses_near_point_bbox_anchor() -> None:
    panel = _FakePanel()
    axis = _FakeAxis(points=((0.2, 0.3), (0.2 + 1e-12, 0.3 + 1e-12)))
    fig = SimpleNamespace(axes=[axis])

    panel._normalize_export_legends(fig, profile={"legend": {}}, legend_size_override=8, point_size_override=50)

    assert axis.legend_kwargs is not None
    assert axis.legend_kwargs["bbox_to_anchor"] == (0.2, 0.3)


def test_normalize_export_legends_keeps_bbox_extent_for_area_anchor() -> None:
    panel = _FakePanel()
    axis = _FakeAxis(points=((0.2, 0.3), (0.5, 0.6)))
    fig = SimpleNamespace(axes=[axis])

    panel._normalize_export_legends(fig, profile={"legend": {}}, legend_size_override=8, point_size_override=50)

    assert axis.legend_kwargs is not None
    assert axis.legend_kwargs["bbox_to_anchor"] == (0.2, 0.3, 0.3, 0.3)
