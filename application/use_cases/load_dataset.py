"""Application use case for dataset loading and state hydration."""

from __future__ import annotations

import logging
import os
import traceback
from typing import Any

import pandas as pd

from core import CONFIG, app_state, state_gateway
from data.loader import read_data_frame

logger = logging.getLogger(__name__)


def hydrate_state_from_dataframe(
    df: pd.DataFrame,
    file_path: str,
    sheet_name: str | None = None,
) -> bool:
    """Validate, clean, and hydrate global state from a DataFrame.

    Pure data processing — no UI dependencies. Can be called from any context
    (UI dialog, CLI, test, API) once a DataFrame is available.

    Args:
        df: The loaded DataFrame.
        file_path: Path to the source file.
        sheet_name: Optional sheet name for Excel files.

    Returns:
        True when state is hydrated successfully, False on validation failure.
    """
    try:
        if app_state.last_group_col and app_state.last_group_col not in app_state.group_cols:
            state_gateway.set_last_group_col(app_state.group_cols[0] if app_state.group_cols else None)

        state_gateway.reset_column_selection()

        for col in app_state.data_cols:
            if col not in df.columns:
                logger.error("Missing data column: %s", col)
                return False
            if not pd.api.types.is_numeric_dtype(df[col]):
                logger.error("Data column '%s' is not numeric", col)
                return False
            logger.debug("Data column '%s' is numeric: OK", col)

        valid_group_cols: list[str] = []
        for col in app_state.group_cols:
            if col not in df.columns:
                logger.warning("Skipping missing group column: %s", col)
            else:
                valid_group_cols.append(col)
        state_gateway.set_group_data_columns(valid_group_cols, app_state.data_cols)

        logger.info("Before cleanup: %s rows", len(df))
        df = df.dropna(subset=app_state.data_cols).copy()

        for col in app_state.group_cols:
            if col in df.columns:
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

        return True

    except Exception as exc:
        logger.error("State hydration from DataFrame failed: %s", exc)
        traceback.print_exc()
        return False


def load_dataset(
    *,
    show_file_dialog: bool = True,
    show_config_dialog: bool = True,
) -> bool:
    """Load dataset and hydrate global state for plotting workflow.

    Args:
        show_file_dialog: Whether to show file/sheet selection dialogs.
        show_config_dialog: Whether to show column configuration dialog.

    Returns:
        True when dataset is loaded successfully, otherwise False.
    """
    progress = None
    df_loaded = None
    config_from_dialog = False

    try:
        if show_file_dialog and show_config_dialog:
            logger.info("Showing unified data import dialog...")
            from ui.dialogs.data_import_dialog import get_data_import_configuration

            dialog_result = get_data_import_configuration(
                default_file=app_state.file_path,
                default_sheet=app_state.sheet_name,
                default_group_cols=app_state.group_cols,
                default_data_cols=app_state.data_cols,
                default_render_mode=getattr(app_state, "render_mode", "2D"),
            )

            if dialog_result is None:
                logger.error("Data import cancelled by user")
                return False

            excel_file = dialog_result["file"]
            sheet_name = dialog_result.get("sheet")
            df_loaded = dialog_result.get("df")
            state_gateway.set_group_data_columns(
                dialog_result.get("group_cols", []),
                dialog_result.get("data_cols", []),
            )

            selected_render_mode = dialog_result.get("render_mode")
            if selected_render_mode:
                state_gateway.set_render_mode(selected_render_mode)
                state_gateway.set_preserve_import_render_mode(True)
            else:
                state_gateway.set_preserve_import_render_mode(False)
            config_from_dialog = True

        elif show_file_dialog:
            logger.info("Showing file selection dialog...")
            from ui.dialogs.file_dialog import get_file_sheet_selection

            file_result = get_file_sheet_selection(default_file=app_state.file_path)
            if file_result is None:
                logger.error("File selection cancelled by user")
                return False

            excel_file = file_result["file"]
            sheet_name = None

            if excel_file.lower().endswith((".xlsx", ".xls")):
                logger.info("Excel file detected, showing sheet selection...")
                from ui.dialogs.sheet_dialog import get_sheet_selection

                selected_sheet = get_sheet_selection(excel_file, default_sheet=app_state.sheet_name)
                if selected_sheet is None:
                    logger.error("Sheet selection cancelled by user")
                    return False

                sheet_name = selected_sheet
                logger.info("Selected sheet: %s", sheet_name)
        else:
            excel_file = CONFIG["excel_file"]
            sheet_name = CONFIG.get("sheet_name", "Sheet1")

        if not os.path.exists(excel_file):
            logger.error("Data file not found: %s", excel_file)
            return False

        logger.info("Loading file: %s", excel_file)
        try:
            from ui.dialogs.progress_dialog import ProgressDialog

            progress = ProgressDialog("Loading Data", "Reading file...")
        except Exception:
            progress = None

        if df_loaded is None:
            if sheet_name:
                logger.info("Using sheet: %s", sheet_name)
            df = read_data_frame(excel_file, sheet_name)
        else:
            df = df_loaded

        if progress:
            progress.update_message("Parsing columns...")

        logger.info("Columns: %s", df.columns.tolist())

        if show_config_dialog and not config_from_dialog:
            if progress:
                progress.close()
                progress = None

            logger.info("Showing data configuration dialog...")
            from ui.dialogs.data_config import get_data_configuration

            config_result = get_data_configuration(
                df,
                default_group_cols=app_state.group_cols,
                default_data_cols=app_state.data_cols,
            )
            if config_result is None:
                logger.error("Configuration cancelled by user")
                return False

            selected_groups = config_result["group_cols"]
            missing_groups = [col for col in selected_groups if col not in df.columns]
            if missing_groups:
                logger.warning("Dropping missing group columns: %s", missing_groups)

            state_gateway.set_group_data_columns(
                [col for col in selected_groups if col in df.columns],
                config_result["data_cols"],
            )

            logger.info("Selected group columns: %s", app_state.group_cols)
            logger.info("Selected data columns: %s", app_state.data_cols)
        elif not config_from_dialog:
            logger.warning("No configuration dialog shown, using empty defaults")
            state_gateway.set_group_data_columns([], [])
            state_gateway.set_preserve_import_render_mode(False)

        if progress:
            progress.update_message("Cleaning data...")

        if not hydrate_state_from_dataframe(df, excel_file, sheet_name if sheet_name else None):
            if progress:
                progress.close()
            return False

        if progress:
            progress.close()

        return True

    except Exception as exc:
        try:
            if progress:
                progress.close()
        except Exception:
            pass

        logger.error("Data loading failed: %s", exc)
        traceback.print_exc()
        return False
