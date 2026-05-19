"""Unified data import dialog mixin composition."""
from __future__ import annotations

from .build import DataImportBuildMixin
from .submit import DataImportSubmitMixin
from .workflow import DataImportWorkflowMixin


class Qt5DataImportDialogMixin(
    DataImportBuildMixin,
    DataImportWorkflowMixin,
    DataImportSubmitMixin,
):
    """Unified dialog mixin for data import and configuration."""
