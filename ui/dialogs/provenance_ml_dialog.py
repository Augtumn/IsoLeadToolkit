"""Provenance ML dialog compatibility wrapper."""
from __future__ import annotations

from PyQt5.QtWidgets import QDialog

from .provenance_ml import ProvenanceMLDialogMixin


class ProvenanceMLDialog(ProvenanceMLDialogMixin, QDialog):
    """Provenance ML dialog."""


def show_provenance_ml(parent: object | None = None) -> None:
    """Open Provenance ML dialog."""
    dialog = ProvenanceMLDialog(parent)
    dialog.exec_()
