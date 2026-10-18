"""One panel record, described once.

The health check found four representations of the same panel state, kept consistent by hand, with two panel bugs
traced to them disagreeing. PanelRecord is the contract they converge on. It is a dict subclass so the migration can
happen call site by call site; the properties are what the call sites move to.
"""
from __future__ import annotations

import pathlib

from core.panel_record import PanelRecord

#: The keys the two kinds of record carry today, as measured before the class was written: a window record has nine
#: of them, a render-state record six, and mode is in both. A key added to a panel has to be added here deliberately.
EXPECTED_KEYS = (
    "window",
    "mode",
    "figure",
    "canvas",
    "axes",
    "toolbar",
    "needs_fit",
    "active",
    "legend",
    "ax",
    "collections",
    "artist_to_sample",
    "sample_to_artist",
    "group_to_scatter",
)


def test_the_declared_keys_are_the_measured_ones() -> None:
    assert sorted(PanelRecord.KEYS) == sorted(EXPECTED_KEYS)


def test_it_still_behaves_like_the_dict_call_sites_read() -> None:
    """Every existing record.get(...) keeps working while the call sites move."""
    record = PanelRecord({"mode": "2D", "needs_fit": True, "legend": {"legend_position": "upper left"}})

    assert isinstance(record, dict)
    assert record.get("mode") == "2D"
    assert record.get("missing") is None
    assert record["needs_fit"] is True


def test_the_properties_read_the_dict() -> None:
    record = PanelRecord({"mode": "PCA", "needs_fit": 1, "legend": {"a": 1}})
    assert record.mode == "PCA"
    assert record.needs_fit is True
    assert record.legend == {"a": 1}
    assert record.window is None, "an absent key reads as None, like the dict it wraps"


def test_both_producers_build_panel_records() -> None:
    """The window records and the render-state records are built through the one class."""
    root = pathlib.Path(__file__).resolve().parents[1]
    for relative in (
        "ui/main_window_parts/mdi_panels.py",
        "application/use_cases/render_plot.py",
    ):
        source = (root / relative).read_text(encoding="utf-8")
        assert "PanelRecord(" in source, relative + " does not build PanelRecords"

