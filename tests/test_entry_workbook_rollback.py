"""The A15 write rolls back the row it created, not only the values put in it.

Reported by review: when the write self-check found new errors it dropped the values but kept a row it had just
created, leaving an id and a group with no data behind in a workbook whose write was reported as rolled back.
"""
from __future__ import annotations

from types import SimpleNamespace

from application.use_cases import entry_workbook
from data.metadata_profile.layout import SheetKind


class _Column:
    def __init__(self, header_key: str) -> None:
        self.header_key = header_key


class _GroupSheet:
    """The little of a GROUP sheet that _store_age_model asks for."""

    name = "5_Analysis_Rows"
    kind = SheetKind.GROUP

    def column(self, oid: str):
        return _Column("col:" + oid) if oid.startswith("A15.") else None


def _issue(message: str):
    """The two fields validate.format_message reads."""
    return SimpleNamespace(message_key=message, params={})


def _errors(*counts):
    """A _row_errors stand-in whose successive answers have the given lengths."""
    answers = iter([[_issue("problem %d" % index) for index in range(count)] for count in counts])
    return lambda *args, **kwargs: next(answers)


def test_a_created_a15_row_is_removed_when_the_write_is_rolled_back(monkeypatch) -> None:
    sheet = _GroupSheet()
    rows: list[dict] = []
    records = {sheet.name: rows}
    # The creation check is clean, the empty row is clean, and the values introduce an error.
    monkeypatch.setattr(entry_workbook, "_row_errors", _errors(0, 1, 2))

    written = entry_workbook._store_age_model(sheet, None, records, "A-1", {"A15.2": 250.0})

    assert written is False, "the write is refused"
    assert rows == [], "and the row created for it is gone with the values"


def test_a_created_a15_row_stays_when_the_write_is_accepted(monkeypatch) -> None:
    sheet = _GroupSheet()
    rows: list[dict] = []
    records = {sheet.name: rows}
    monkeypatch.setattr(entry_workbook, "_row_errors", _errors(0, 0, 0))

    assert entry_workbook._store_age_model(sheet, None, records, "A-1", {"A15.2": 250.0}) is True
    assert len(rows) == 1, "the row that was accepted stays"
    assert rows[0]["col:A15.2"] == 250.0


def test_an_existing_a15_row_keeps_its_place_when_rolled_back(monkeypatch) -> None:
    """An existing row is not created by this write, so a rollback must not remove it."""
    sheet = _GroupSheet()
    rows: list[dict] = [{"id": "A-1-A15", "col:A15.2": 100.0}]
    records = {sheet.name: rows}
    monkeypatch.setattr(entry_workbook, "_row_errors", _errors(0, 1, 2))

    assert entry_workbook._store_age_model(sheet, None, records, "A-1", {"A15.2": 250.0}) is False
    assert len(rows) == 1, "the row was already there and stays"
    assert rows[0]["col:A15.2"] == 100.0, "with its own value restored"
