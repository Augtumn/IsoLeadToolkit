"""The SilverQuest search leaves no wait cursor behind, whatever way it ends.

Both result paths restore the cursor (there is a comment explaining the bug that used to leave it on for the whole
application). Closing the dialog during a search is a third way to end it, and it restores the cursor now too.
"""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from ui.panels.analysis.dialogs import silverquest_dialog


def test_restore_wait_cursor_drains_the_whole_stack(qapp) -> None:
    """A search started while another override was already on must not leave one behind."""
    QApplication.setOverrideCursor(Qt.WaitCursor)
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        silverquest_dialog._restore_wait_cursor()
        assert QApplication.overrideCursor() is None
    finally:
        while QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()


def test_closing_the_dialog_restores_the_cursor(qapp, monkeypatch) -> None:
    """The close event calls the restore; a search stopped here never reaches a result path."""
    from PyQt5.QtGui import QCloseEvent

    restored = []
    monkeypatch.setattr(silverquest_dialog, "_restore_wait_cursor", lambda: restored.append(True))

    dialog = silverquest_dialog.SilverQuestDialog(None)
    dialog._search_worker = None
    dialog.closeEvent(QCloseEvent())

    assert restored, "closing the dialog restores the wait cursor"
