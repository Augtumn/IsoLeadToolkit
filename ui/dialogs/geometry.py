"""Remember a dialog's size and position between sessions.

Dialogs used to open at their default size every time, so the user re-adjusted them on
every single visit. ``remember_geometry()`` restores the stored geometry and saves it when
the dialog closes; the key is the dialog's identity (its class name by default).
"""
from __future__ import annotations

from typing import Any

import logging

from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QDialog, QWidget

logger = logging.getLogger(__name__)


def _settings() -> QSettings:
    return QSettings("IsotopesAnalyse", "Dialogs")


def remember_geometry(dialog: QWidget, key: str | None = None) -> None:
    """Restore *dialog*'s stored geometry and save it again when it closes."""
    if dialog is None:
        return
    name = key or type(dialog).__name__
    settings = _settings()
    stored = settings.value(f"geometry/{name}")
    if stored is not None:
        try:
            dialog.restoreGeometry(stored)
        except Exception as err:  # pragma: no cover - a corrupt setting must not break the dialog
            logger.warning("Could not restore dialog geometry for %s: %s", name, err)

    original_close = dialog.closeEvent

    def closeEvent(event):  # noqa: N802 - Qt naming
        try:
            settings.setValue(f"geometry/{name}", dialog.saveGeometry())
        except Exception as err:
            logger.warning("Could not save dialog geometry for %s: %s", name, err)
        original_close(event)

    dialog.closeEvent = closeEvent  # type: ignore[method-assign]


def forget_geometry(key: str) -> None:
    """Drop the stored geometry (used by tests and by a future "reset layout")."""
    settings = _settings()
    settings.remove(f"geometry/{key}")
    settings.sync()
