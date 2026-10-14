"""A style change redraws every panel, not just the one the state points at.

Reported: changing a group's colour updated a single window. The panels are equals, so a change
goes through the palette and a redraw rather than through the artists of one panel.
"""
from __future__ import annotations

from ui.main_window_parts.legend_styles import MainWindowLegendStyleMixin


def test_a_colour_change_redraws_the_plots(monkeypatch) -> None:
    called = []

    class _Gateway:
        def set_palette_and_marker_map(self, palette, markers) -> None:
            called.append(("palette", dict(palette)))

    class _Host(MainWindowLegendStyleMixin):
        def _update_marker_swatch(self, group, swatch) -> None:
            called.append(("swatch", group))

    import ui.main_window_parts.legend_styles as module

    monkeypatch.setattr(module, "state_gateway", _Gateway(), raising=False)
    monkeypatch.setattr(module.QColorDialog, "getColor", staticmethod(lambda *a, **k: _Valid()), raising=False)
    monkeypatch.setattr("visualization.events.on_slider_change", lambda: called.append(("redraw", None)))

    from core import app_state

    monkeypatch.setattr(app_state, "current_palette", {"g": "#111111"}, raising=False)
    monkeypatch.setattr(app_state, "group_marker_map", {}, raising=False)
    host = _Host.__new__(_Host)
    host._pick_color("g", None)

    kinds = [kind for kind, _value in called]
    assert "palette" in kinds, "the palette is written to the state"
    assert "redraw" in kinds, "and the plots are redrawn, which redraws every panel"


class _Valid:
    def isValid(self) -> bool:
        return True

    def name(self) -> str:
        return "#ff0000"
