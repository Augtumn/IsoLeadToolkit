"""What the application shares about panels: the limit and the projection of a mode."""
from __future__ import annotations

import pytest

from visualization.plotting.panels import MAX_PANELS, projection_for


def test_a_window_shows_a_bounded_number_of_panels() -> None:
    assert isinstance(MAX_PANELS, int)
    assert MAX_PANELS >= 2, "at least two, or there would be no panels to compare"


@pytest.mark.parametrize(
    ("mode", "projection"),
    [("3D", "3d"), ("3d", "3d"), ("Ternary", "ternary"), ("TERNARY", "ternary")],
)
def test_modes_that_need_a_projection_get_one(mode, projection) -> None:
    assert projection_for(mode) == projection


@pytest.mark.parametrize("mode", ["2D", "UMAP", "tSNE", "PB_EVOL_76", "", None])
def test_ordinary_modes_use_a_plain_axes(mode) -> None:
    assert projection_for(mode) is None
