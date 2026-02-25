"""
Data Loading and Processing
Handles Excel file loading and data validation
"""
import logging
import os
import traceback

import numpy as np
import pandas as pd

from core.config import CONFIG
from core.state import app_state

logger = logging.getLogger(__name__)


def read_data_frame(excel_file, sheet_name=None):
    """Read data file into a cleaned DataFrame."""
    if sheet_name:
        try:
            df = pd.read_excel(excel_file, sheet_name=sheet_name, dtype=str, engine='calamine')
        except Exception:
            df = pd.read_excel(excel_file, sheet_name=sheet_name, dtype=str)
    else:
        df = pd.read_csv(excel_file, dtype=str)

    df.columns = df.columns.astype(str).str.strip()

    for col in df.columns:
        numeric_col = pd.to_numeric(df[col], errors='coerce')
        non_null_count = numeric_col.notna().sum()
        total_count = len(numeric_col)

        if non_null_count > 0 and (non_null_count / total_count) > 0.5:
            df[col] = numeric_col
        else:
            df[col] = df[col].fillna("empty").astype(str)
            df[col] = df[col].replace(['nan', 'NaN', 'None'], 'empty')

    return df


def load_data(show_file_dialog=True, show_config_dialog=True):
    """
    Load and validate Excel/CSV data
    
    Args:
        show_file_dialog: bool, whether to show file/sheet selection dialog
        show_config_dialog: bool, whether to show configuration dialog for column selection
    
    Returns:
        bool, success status
    """
    progress = None
    df_loaded = None
    config_from_dialog = False
    try:
        # Show unified import dialog when both steps are requested
        if show_file_dialog and show_config_dialog:
            logger.info("Showing unified data import dialog...")
            from ui.dialogs.data_import_dialog import get_data_import_configuration

            dialog_result = get_data_import_configuration(
                default_file=app_state.file_path,
                default_sheet=app_state.sheet_name,
                default_group_cols=app_state.group_cols,
                default_data_cols=app_state.data_cols
            )

            if dialog_result is None:
                logger.error("Data import cancelled by user")
                return False

            excel_file = dialog_result['file']
            sheet_name = dialog_result.get('sheet')
            df_loaded = dialog_result.get('df')
            app_state.group_cols = dialog_result.get('group_cols', [])
            app_state.data_cols = dialog_result.get('data_cols', [])
            config_from_dialog = True

        # Show file selection dialog if requested
        elif show_file_dialog:
            logger.info("Showing file selection dialog...")
            from ui.dialogs.file_dialog import get_file_sheet_selection
            
            file_result = get_file_sheet_selection(default_file=app_state.file_path)
            
            if file_result is None:
                logger.error("File selection cancelled by user")
                return False
            
            excel_file = file_result['file']
            sheet_name = None  # Will be set in next step if needed
            
            # Check if file is Excel
            is_excel = excel_file.lower().endswith(('.xlsx', '.xls'))
            
            if is_excel:
                logger.info("Excel file detected, showing sheet selection...")
                from ui.dialogs.sheet_dialog import get_sheet_selection
                
                selected_sheet = get_sheet_selection(excel_file, default_sheet=app_state.sheet_name)
                
                if selected_sheet is None:
                    logger.error("Sheet selection cancelled by user")
                    return False
                
                sheet_name = selected_sheet
                logger.info("Selected sheet: %s", sheet_name)
        else:
            excel_file = CONFIG['excel_file']
            sheet_name = CONFIG.get('sheet_name', 'Sheet1')
        
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
        
        # Show configuration dialog if requested
        if show_config_dialog and not config_from_dialog:
            if progress:
                progress.close()
                progress = None
            logger.info("Showing data configuration dialog...")
            from ui.dialogs.data_config import get_data_configuration
            
            config_result = get_data_configuration(
                df,
                default_group_cols=app_state.group_cols,
                default_data_cols=app_state.data_cols
            )
            
            if config_result is None:
                logger.error("Configuration cancelled by user")
                return False
            
            # Update app state with selected columns
            selected_groups = config_result['group_cols']
            missing_groups = [col for col in selected_groups if col not in df.columns]
            if missing_groups:
                logger.warning("Dropping missing group columns: %s", missing_groups)
            app_state.group_cols = [col for col in selected_groups if col in df.columns]
            app_state.data_cols = config_result['data_cols']
            
            logger.info("Selected group columns: %s", app_state.group_cols)
            logger.info("Selected data columns: %s", app_state.data_cols)
        elif not config_from_dialog:
            # If no dialog, use first columns as groups, rest as data
            logger.warning("No configuration dialog shown, using empty defaults")
            app_state.group_cols = []
            app_state.data_cols = []

        if app_state.last_group_col and app_state.last_group_col not in app_state.group_cols:
            app_state.last_group_col = app_state.group_cols[0] if app_state.group_cols else None
        app_state.selected_2d_cols = []
        app_state.selected_3d_cols = []
        app_state.selected_2d_confirmed = False
        app_state.selected_3d_confirmed = False
        app_state.available_groups = []
        app_state.visible_groups = None
        
        # Validate data columns are numeric
        for col in app_state.data_cols:
            if col not in df.columns:
                logger.error("Missing data column: %s", col)
                return False
            if not pd.api.types.is_numeric_dtype(df[col]):
                logger.error("Data column '%s' is not numeric", col)
                return False
            logger.debug("Data column '%s' is numeric: OK", col)
        
        # Validate grouping columns exist, skip missing ones
        valid_group_cols = []
        for col in app_state.group_cols:
            if col not in df.columns:
                logger.warning("Skipping missing group column: %s", col)
            else:
                valid_group_cols.append(col)
        app_state.group_cols = valid_group_cols
        
        if progress:
            progress.update_message("Cleaning data...")
        logger.info("Before cleanup: %s rows", len(df))
        df = df.dropna(subset=app_state.data_cols).copy()
        
        # Clean up grouping columns (replace empty/null values with 'Unknown')
        for col in app_state.group_cols:
            if col in df.columns:
                df[col] = df[col].replace(['——', '', '—', 'null', 'nan'], 'Unknown')
                df[col] = df[col].fillna('Unknown')
        
        app_state.df_global = df.reset_index(drop=True)
        try:
            app_state.data_version += 1
            app_state.embedding_cache.clear()
            logger.info("Data version updated: %s", app_state.data_version)
        except Exception:
            pass
        app_state.file_path = excel_file
        app_state.sheet_name = sheet_name if sheet_name else None
        app_state.selected_indices.clear()
        app_state.selection_mode = False
        logger.info("Loaded %s valid samples", len(app_state.df_global))
        if progress:
            progress.close()
        return True
        
    except Exception as e:
        try:
            if progress:
                progress.close()
        except Exception:
            pass
        logger.error("Data loading failed: %s", e)
        traceback.print_exc()
        return False
