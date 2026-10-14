"""Application use case for dataset loading and state hydration.

Qt-free by contract (docs/dev_conventions.md §18.1): the UI collects the file, the sheet and
the column choices in its dialogs and hands them over as a :class:`DatasetImport`; this module
validates, cleans and hydrates the session state.  Failures raise - the caller decides what to
tell the user, so nothing is silently reported as loaded when it is not.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import pandas as pd

from core import app_state, state_gateway
from adapters.loader import read_data_frame

logger = logging.getLogger(__name__)

__all__ = [
    "DatasetImport",
    "hydrate_state_from_dataframe",
    "load_dataset",
    "read_dataset_frame",
]


@dataclass(frozen=True)
class DatasetImport:
    """The dataset the user chose, ready to be loaded.

    Attributes:
        file_path: source file, recorded in the session.
        sheet_name: Excel sheet, when the source is a workbook.
        frame: the parsed frame when the import wizard already read it; ``None`` makes
            :func:`load_dataset` read the file itself.
        group_cols: the grouping columns the user selected.
        data_cols: the numeric columns the user selected.
        render_mode: render mode picked in the wizard; ``None`` keeps the current one.
    """

    file_path: str
    sheet_name: str | None = None
    frame: pd.DataFrame | None = None
    group_cols: tuple[str, ...] = ()
    data_cols: tuple[str, ...] = ()
    render_mode: str | None = None


def read_dataset_frame(file_path: str, sheet_name: str | None = None) -> pd.DataFrame:
    """Read a dataset file; the import wizard's preview and the import flow share this reader."""
    return read_data_frame(file_path, sheet_name)


def hydrate_state_from_dataframe(
    df: pd.DataFrame,
    file_path: str,
    sheet_name: str | None = None,
) -> None:
    """Validate, clean and hydrate global state from a DataFrame.

    Args:
        df: the loaded DataFrame.
        file_path: path to the source file.
        sheet_name: optional sheet name for Excel files.

    Raises:
        ValueError: a selected data column is missing from *df* or is not numeric, or a
            selected grouping column is missing from *df*.  The selection is validated
            before any state is mutated, so a rejected frame leaves the session untouched.
    """
    for col in app_state.data_cols:
        if col not in df.columns:
            raise ValueError(f"Data column {col!r} is not in the loaded data")
        if not pd.api.types.is_numeric_dtype(df[col]):
            raise ValueError(f"Data column {col!r} is not numeric")

    missing_groups = [col for col in app_state.group_cols if col not in df.columns]
    if missing_groups:
        raise ValueError(
            "Grouping column(s) not in the loaded data: " + ", ".join(missing_groups)
        )

    if app_state.last_group_col and app_state.last_group_col not in app_state.group_cols:
        state_gateway.set_last_group_col(app_state.group_cols[0] if app_state.group_cols else None)

    state_gateway.reset_column_selection()
    state_gateway.set_group_data_columns(list(app_state.group_cols), app_state.data_cols)

    logger.info("Before cleanup: %s rows", len(df))
    df = df.dropna(subset=app_state.data_cols).copy()

    for col in app_state.group_cols:
        df[col] = df[col].replace(["——", "", "—", "null", "nan"], "Unknown")
        df[col] = df[col].fillna("Unknown")

    state_gateway.set_dataframe_and_source(
        df.reset_index(drop=True),
        file_path=file_path,
        sheet_name=sheet_name,
    )
    state_gateway.bump_data_version()
    state_gateway.clear_selection()
    logger.info("Loaded %s valid samples", len(app_state.df_global))


def load_dataset(request: DatasetImport) -> None:
    """Validate, clean and hydrate the session state from *request*.

    Args:
        request: everything the UI collected, including the chosen columns.

    Raises:
        FileNotFoundError: the file is not there.
        ValueError: a selected column cannot be used with the loaded frame.
        Exception: whatever the reader raises for an unreadable workbook.
    """
    if not os.path.exists(request.file_path):
        raise FileNotFoundError(f"Data file not found: {request.file_path}")

    state_gateway.set_group_data_columns(list(request.group_cols), list(request.data_cols))
    if request.render_mode:
        state_gateway.set_render_mode(request.render_mode)
        state_gateway.set_preserve_import_render_mode(True)
    else:
        state_gateway.set_preserve_import_render_mode(False)

    frame = (
        request.frame
        if request.frame is not None
        else read_dataset_frame(request.file_path, request.sheet_name)
    )
    logger.info("Loading dataset %s", request.file_path)
    hydrate_state_from_dataframe(frame, request.file_path, request.sheet_name)
