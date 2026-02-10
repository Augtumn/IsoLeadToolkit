"""
Data Loading and Processing
Handles Excel file loading and data validation
"""
import pandas as pd
import numpy as np
import os
import traceback
from core.config import CONFIG
from core.state import app_state


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

    column_mapping = {
        '省': 'Province', '省份': 'Province',
        '市/县': 'City/County',
        '遗址': 'Discovery site', '出土地': 'Discovery site',
        '年代': 'Period'
    }
    df = df.rename(columns=column_mapping)

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
            print("[INFO] Showing unified data import dialog...", flush=True)
            from ui.dialogs.data_import_dialog import get_data_import_configuration

            dialog_result = get_data_import_configuration(
                default_file=app_state.file_path,
                default_sheet=app_state.sheet_name,
                default_group_cols=app_state.group_cols,
                default_data_cols=app_state.data_cols
            )

            if dialog_result is None:
                print("[ERROR] Data import cancelled by user", flush=True)
                return False

            excel_file = dialog_result['file']
            sheet_name = dialog_result.get('sheet')
            df_loaded = dialog_result.get('df')
            app_state.group_cols = dialog_result.get('group_cols', [])
            app_state.data_cols = dialog_result.get('data_cols', [])
            config_from_dialog = True

        # Show file selection dialog if requested
        elif show_file_dialog:
            print("[INFO] Showing file selection dialog...", flush=True)
            from ui.dialogs.file_dialog import get_file_sheet_selection
            
            file_result = get_file_sheet_selection(default_file=app_state.file_path)
            
            if file_result is None:
                print("[ERROR] File selection cancelled by user", flush=True)
                return False
            
            excel_file = file_result['file']
            sheet_name = None  # Will be set in next step if needed
            
            # Check if file is Excel
            is_excel = excel_file.lower().endswith(('.xlsx', '.xls'))
            
            if is_excel:
                print("[INFO] Excel file detected, showing sheet selection...", flush=True)
                from ui.dialogs.sheet_dialog import get_sheet_selection
                
                selected_sheet = get_sheet_selection(excel_file, default_sheet=app_state.sheet_name)
                
                if selected_sheet is None:
                    print("[ERROR] Sheet selection cancelled by user", flush=True)
                    return False
                
                sheet_name = selected_sheet
                print(f"[INFO] Selected sheet: {sheet_name}", flush=True)
        else:
            excel_file = CONFIG['excel_file']
            sheet_name = CONFIG.get('sheet_name', 'Sheet1')
        
        if not os.path.exists(excel_file):
            print(f"[ERROR] Data file not found: {excel_file}", flush=True)
            return False
            
        print(f"[INFO] Loading file: {excel_file}", flush=True)
        try:
            from ui.dialogs.progress_dialog import ProgressDialog
            progress = ProgressDialog("Loading Data", "Reading file...")
        except Exception:
            progress = None
        if df_loaded is None:
            if sheet_name:
                print(f"[INFO] Using sheet: {sheet_name}", flush=True)
            df = read_data_frame(excel_file, sheet_name)
        else:
            df = df_loaded

        if progress:
            progress.update_message("Parsing columns...")

        print(f"[OK] Columns: {df.columns.tolist()}", flush=True)
        
        # Show configuration dialog if requested
        if show_config_dialog and not config_from_dialog:
            if progress:
                progress.close()
                progress = None
            print("[INFO] Showing data configuration dialog...", flush=True)
            from ui.dialogs.data_config import get_data_configuration
            
            config_result = get_data_configuration(
                df,
                default_group_cols=app_state.group_cols,
                default_data_cols=app_state.data_cols
            )
            
            if config_result is None:
                print("[ERROR] Configuration cancelled by user", flush=True)
                return False
            
            # Update app state with selected columns
            selected_groups = config_result['group_cols']
            missing_groups = [col for col in selected_groups if col not in df.columns]
            if missing_groups:
                print(f"[WARN] Dropping missing group columns: {missing_groups}", flush=True)
            app_state.group_cols = [col for col in selected_groups if col in df.columns]
            app_state.data_cols = config_result['data_cols']
            
            print(f"[OK] Selected group columns: {app_state.group_cols}", flush=True)
            print(f"[OK] Selected data columns: {app_state.data_cols}", flush=True)
        elif not config_from_dialog:
            # If no dialog, use first columns as groups, rest as data
            print("[WARN] No configuration dialog shown, using empty defaults", flush=True)
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
                print(f"[ERROR] Missing data column: {col}", flush=True)
                return False
            if not pd.api.types.is_numeric_dtype(df[col]):
                print(f"[ERROR] Data column '{col}' is not numeric", flush=True)
                return False
            print(f"[DEBUG] Data column '{col}' is numeric: OK", flush=True)
        
        # Validate grouping columns exist
        for col in app_state.group_cols:
            if col not in df.columns:
                print(f"[ERROR] Missing group column: {col}", flush=True)
                return False
        
        if progress:
            progress.update_message("Cleaning data...")
        print(f"[INFO] Before cleanup: {len(df)} rows", flush=True)
        df = df.dropna(subset=app_state.data_cols).copy()
        
        # Clean up grouping columns (replace empty/null values with 'Unknown')
        for col in app_state.group_cols:
            if col in df.columns:
                df[col] = df[col].replace(['——', '', '—', 'null', 'nan'], 'Unknown')
                df[col] = df[col].fillna('Unknown')
        
        app_state.df_global = df.reset_index(drop=True)
        app_state.file_path = excel_file
        app_state.sheet_name = sheet_name if sheet_name else None
        app_state.selected_indices.clear()
        app_state.selection_mode = False
        print(f"[OK] Loaded {len(app_state.df_global)} valid samples.", flush=True)
        if progress:
            progress.close()
        return True
        
    except Exception as e:
        try:
            if progress:
                progress.close()
        except Exception:
            pass
        print(f"[ERROR] Data loading failed: {e}", flush=True)
        traceback.print_exc()
        return False
