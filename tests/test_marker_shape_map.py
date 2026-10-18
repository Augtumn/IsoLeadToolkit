"""The two places that name a marker shape share one table.

Reported by review: the legend list and the shape editor each held a verbatim copy of the same twenty-five marker
translations, and identical tables drift. Both ask ui.icons for the one table now.
"""
from __future__ import annotations

from ui.icons import marker_shape_map
from ui.main_window_parts.legend_core import MainWindowLegendCoreMixin
from ui.panels.legend.editors import LegendEditorsMixin


class _ListSide(MainWindowLegendCoreMixin):
    pass


class _EditorSide(LegendEditorsMixin):
    pass


def test_the_legend_and_the_editor_use_the_same_marker_map(qapp) -> None:
    left = _ListSide()
    right = _EditorSide()
    left._ensure_marker_shape_map()
    right._ensure_marker_shape_map()

    assert left._marker_shape_map == right._marker_shape_map, "one table, not two"
    assert left._marker_shape_map == marker_shape_map()
    assert len(left._marker_shape_map) == 25
    assert all(character for character in left._marker_shape_map.values()), "every name maps to a marker"


def test_the_map_is_built_when_it_is_asked_for(qapp) -> None:
    """The names are translated, so the table must be built per call - a table made at import would be frozen.

    The test is identity, not content: two calls return different dicts. That is what a table captured at import
    could not do, and it is the difference between this and the translation bug the snapshot had.
    """
    first = marker_shape_map()
    second = marker_shape_map()

    assert isinstance(first, dict) and first
    assert first is not second, "a fresh table each time, not one captured at import"
    assert first == second, "and the same content"
