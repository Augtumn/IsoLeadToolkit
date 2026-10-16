"""Dialog-driven dataset loading: the UI half of the import use case.

`application/use_cases/load_dataset.py` is Qt-free by contract; this module owns the dialogs
that collect its input and the progress feedback, then hands a
:class:`~application.use_cases.load_dataset.DatasetImport` over.  A failure is shown to the
user (and logged with its stack) instead of being swallowed into a bare ``False``
(docs/dev_conventions.md §11.1: the UI layer is where an error becomes a message).
"""
from __future__ import annotations

import logging

from PyQt5.QtWidgets import QMessageBox

from application.use_cases.load_dataset import DatasetImport, load_dataset
from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)

__all__ = ["load_dataset_via_dialogs"]


def _collect_import() -> DatasetImport | None:
    """Run the import wizard; ``None`` when the user cancels."""
    from ui.panels.data.dialogs.data_import_dialog import get_data_import_configuration

    result = get_data_import_configuration(
        default_file=app_state.file_path,
        default_sheet=app_state.sheet_name,
        default_group_cols=app_state.group_cols,
        default_data_cols=app_state.data_cols,
        default_render_mode=app_state.render_mode,
    )
    if result is None:
        logger.info("Data import cancelled by the user")
        return None
    return DatasetImport(
        file_path=result["file"],
        sheet_name=result.get("sheet"),
        frame=result["df"],
        group_cols=tuple(result["group_cols"]),
        data_cols=tuple(result["data_cols"]),
        render_mode=result.get("render_mode"),
    )


def load_dataset_via_dialogs() -> bool:
    """Ask for a dataset, load it, and report the outcome.

    Returns:
        True when the dataset was loaded and the state hydrated; False when the user
        cancelled or the load failed (the failure is shown and logged).
    """
    request = _collect_import()
    if request is None:
        return False

    from ui.dialogs.progress_dialog import ProgressDialog

    progress = ProgressDialog(translate("Loading Data"), translate("Reading file…"))
    try:
        load_dataset(request)
    except Exception as error:
        progress.close()
        logger.exception("Data loading failed: %s", error)
        QMessageBox.critical(
            None,
            translate("Error"),
            translate("Failed to load Excel file: {error}").format(error=str(error)),
        )
        return False
    progress.close()
    logger.info("Dataset loaded: %s", request.file_path)
    # A newly imported dataset starts as one figure drawn the way it was chosen in the wizard. The
    # panel list describes the previous layout, and leaving it in place made the window open several
    # panels - the reported "I picked one algorithm and got two windows". A session restore keeps
    # the list; importing data does not.
    state_gateway.set_plot_panels([])
    return True
