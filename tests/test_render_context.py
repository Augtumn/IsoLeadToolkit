"""The read-only context a render is given."""
from __future__ import annotations

import pytest

from core.render_modes import capabilities_for
from visualization.plotting.rendering.context import RenderContext, build_context


def _context(**overrides):
    fields = {
        "mode": "2D",
        "group_col": "Site",
        "figure": object(),
        "axes": object(),
        "columns_2d": ("x1", "x2"),
    }
    fields.update(overrides)
    return build_context(**fields)


def test_it_carries_what_the_mode_needs() -> None:
    context = _context()
    assert context.projection == "2d"
    assert context.capabilities == capabilities_for("2D")
    assert context.columns_2d == ("x1", "x2")
    assert context.is_subset is False


def test_the_capabilities_come_from_the_mode_not_the_caller() -> None:
    """A caller cannot hand a context capabilities that belong to another mode."""
    context = RenderContext(
        mode="3D",
        group_col="Site",
        figure=object(),
        axes=object(),
        capabilities=capabilities_for("2D"),
    )
    assert context.capabilities == capabilities_for("3D")
    assert context.projection == "3d"


def test_the_token_changes_with_what_the_picture_is_made_of() -> None:
    same = _context()
    assert same.token("x1", "x2") == _context().token("x1", "x2")

    assert same.token("x1", "x3") != same.token("x1", "x2"), "other columns are another picture"
    assert _context(mode="3D").token() != same.token(), "another mode is another picture"

    subset = _context(subset_indices=[0, 1, 2])
    assert subset.token("x1", "x2") != same.token("x1", "x2"), "a subset is another picture"
    assert subset.is_subset is True


def test_an_unknown_mode_has_no_capabilities_of_its_own() -> None:
    context = _context(mode="GHOST")
    assert context.capabilities == capabilities_for("GHOST")
    assert context.projection == "2d"
    assert context.token() != _context().token()


@pytest.mark.parametrize("mode", ["2D", "3D", "Ternary"])
def test_every_mode_that_asks_for_columns_reports_them(mode: str) -> None:
    context = _context(mode=mode, columns_2d=("a", "b"), columns_3d=("a", "b", "c"))
    assert context.columns_2d == ("a", "b")
    assert context.columns_3d == ("a", "b", "c")
    assert context.projection == capabilities_for(mode).projection
