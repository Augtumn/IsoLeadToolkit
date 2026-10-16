"""The mode list, its capabilities, and the renderer's own sets agree - and the guard says so."""
from __future__ import annotations

import pathlib
import sys

from core.render_modes import (
    LABEL_FOR_MODE,
    MODE_CAPABILITIES,
    RENDER_MODE_CHOICES,
    RENDER_MODE_VALUES,
    asynchronous_modes,
    capabilities_for,
)

_SCRIPTS = pathlib.Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import check_render_modes as guard  # noqa: E402


def test_every_mode_has_its_capabilities_recorded() -> None:
    listed = set(RENDER_MODE_VALUES)
    assert set(MODE_CAPABILITIES) == listed, "one record per mode, and no records for anything else"
    assert len(RENDER_MODE_VALUES) == len(RENDER_MODE_CHOICES), "no mode is listed twice"
    assert set(LABEL_FOR_MODE) == listed, "every mode has a label"


def test_the_modes_that_need_selected_columns_ask_for_them() -> None:
    assert capabilities_for("2D").needs_columns == 2
    assert capabilities_for("3D").needs_columns == 3
    assert capabilities_for("Ternary").needs_columns == 3
    assert capabilities_for("3D").projection == "3d"
    assert capabilities_for("Ternary").projection == "ternary"
    assert capabilities_for("2D").projection == "2d"
    # The geochemistry modes are the ones the panels must show their sections for.
    assert capabilities_for("PLUMBOTECTONICS_76").shows_plumbotectonics_model is True
    assert capabilities_for("PB_EVOL_76").shows_isochron_controls is True
    assert capabilities_for("PB_EVOL_86").shows_isochron_controls is False, "only 206-207 fits one"
    assert capabilities_for("PB_MU_AGE").shows_plumbotectonics_model is False
    assert capabilities_for("2D").shows_geochem_controls is False


def test_the_guard_agrees_with_the_tables() -> None:
    assert guard._problems() == [], "the guard is the check that keeps this file honest"


def test_the_guard_reports_a_mode_without_capabilities(monkeypatch) -> None:
    monkeypatch.delitem(guard.MODE_CAPABILITIES, "PB_KAPPA_AGE")
    problems = guard._problems()
    assert any("PB_KAPPA_AGE" in problem for problem in problems), f"got {problems}"


def test_the_guard_reports_a_capability_without_a_mode(monkeypatch) -> None:
    monkeypatch.setitem(guard.MODE_CAPABILITIES, "GHOST", capabilities_for("2D"))
    problems = guard._problems()
    assert any("GHOST" in problem for problem in problems), f"got {problems}"


def test_the_guard_reports_an_asynchronous_set_that_disagrees(monkeypatch) -> None:
    monkeypatch.setattr(guard, "_ASYNC_EMBEDDING_ALGORITHMS", {"UMAP"})
    problems = guard._problems()
    assert any("_ASYNC_EMBEDDING_ALGORITHMS" in problem for problem in problems), f"got {problems}"


def test_the_recorded_asynchronous_modes_are_the_four_algorithms() -> None:
    assert set(asynchronous_modes()) == {"UMAP", "tSNE", "PCA", "RobustPCA"}
