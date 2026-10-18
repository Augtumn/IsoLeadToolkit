"""Every analysis dialog clears the wait cursor when it closes.

Reported by the same sweep that found the SilverQuest case: a dialog sets the wait cursor when it starts a worker and
clears it when the result arrives. Closing the dialog during a run stops the worker, so that result never arrives,
and the whole application kept showing the busy cursor - which looks exactly like a freeze.
"""
from __future__ import annotations

import pathlib

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from ui.panels.analysis.dialogs.analysis_worker import restore_wait_cursor

DIALOGS = [
    "ui/panels/analysis/dialogs/clustering_dialog.py",
    "ui/panels/analysis/dialogs/endmember_dialog.py",
    "ui/panels/analysis/dialogs/mixing_dialog.py",
    "ui/panels/analysis/dialogs/provenance_ml/workflow.py",
    "ui/panels/analysis/dialogs/silverquest_dialog.py",
]


def _drain() -> None:
    while QApplication.overrideCursor() is not None:
        QApplication.restoreOverrideCursor()


def test_restore_wait_cursor_drains_the_stack(qapp) -> None:
    """A run started while another override was on must not leave one behind."""
    QApplication.setOverrideCursor(Qt.WaitCursor)
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        restore_wait_cursor()
        assert QApplication.overrideCursor() is None
    finally:
        _drain()


def test_restoring_an_empty_stack_does_nothing(qapp) -> None:
    """That is what makes it safe to call on every close."""
    _drain()
    restore_wait_cursor()
    assert QApplication.overrideCursor() is None


@pytest.mark.parametrize("relative", DIALOGS)
def test_every_dialog_clears_the_cursor_on_close(relative: str) -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    # The files are checked out with CRLF on this platform; the slice below is written for LF.
    source = (root / relative).read_text(encoding="utf-8").replace("\r\n", "\n")
    start = source.index("def closeEvent")
    end = source.index("\n    def ", start + 1)
    close_event = source[start:end]
    assert "restore_wait_cursor" in close_event, relative + " does not clear the cursor when it closes"
