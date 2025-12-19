"""
Data Loading and Processing
Handles Excel file loading and data validation
"""
import pandas as pd
import numpy as np
import os
import traceback
from config import CONFIG
from state import app_state


def load_data(show_file_dialog=True, show_config_dialog=True):
    """
    Load and validate Excel/CSV data
    
    Args:
        show_file_dialog: bool, whether to show file/sheet selection dialog
        show_config_dialog: bool, whether to show configuration dialog for column selection
    
    Returns:
        bool, success status
    """
    try:
        # Show file selection dialog if requested
        if show_file_dialog:
            print("[INFO] Showing file selection dialog...", flush=True)
            from file_dialog import get_file_sheet_selection
            
            file_result = get_file_sheet_selection()
            
            if file_result is None:
                print("[ERROR] File selection cancelled by user", flush=True)
                return False
            
            excel_file = file_result['file']
            sheet_name = None  # Will be set in next step if needed
            
            # Check if file is Excel
            is_excel = excel_file.lower().endswith(('.xlsx', '.xls'))
            
            if is_excel:
                print("[INFO] Excel file detected, showing sheet selection...", flush=True)
                from sheet_dialog import get_sheet_selection
                
                selected_sheet = get_sheet_selection(excel_file)
                
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
        if sheet_name:
            print(f"[INFO] Using sheet: {sheet_name}", flush=True)
            # Try to use calamine engine for faster Excel reading if available
            # Requires: pip install python-calamine pandas>=2.2.0
            try:
                print("[INFO] Attempting to read with calamine engine...", flush=True)
                df = pd.read_excel(excel_file, sheet_name=sheet_name, dtype=str, engine='calamine')
            except Exception:
                # Fallback to default (openpyxl)
                print("[INFO] Calamine engine not available or failed, falling back to default (openpyxl).", flush=True)
                print("[TIP] For faster Excel loading, install python-calamine: pip install python-calamine", flush=True)
                df = pd.read_excel(excel_file, sheet_name=sheet_name, dtype=str)
        else:
            # For CSV files
            print("[INFO] Loading CSV file", flush=True)
            df = pd.read_csv(excel_file, dtype=str)
        
        df.columns = df.columns.astype(str).str.strip()
        
        # Column name mapping (for known datasets)
        column_mapping = {
            '省': 'Province', '省份': 'Province',
            '市/县': 'City/County',
            '遗址': 'Discovery site', '出土地': 'Discovery site',
            '年代': 'Period'
        }
        df = df.rename(columns=column_mapping)
        
        print(f"[OK] Columns: {df.columns.tolist()}", flush=True)
        
        # Convert data types: try to convert each column to numeric
        # Columns that can be converted will be treated as numeric
        for col in df.columns:
            # Try converting to numeric
            numeric_col = pd.to_numeric(df[col], errors='coerce')
            # If more than 50% of values are numeric, convert the column
            non_null_count = numeric_col.notna().sum()
            total_count = len(numeric_col)
            
            if non_null_count > 0 and (non_null_count / total_count) > 0.5:
                print(f"[DEBUG] Column '{col}': {non_null_count}/{total_count} values are numeric, converting", flush=True)
                df[col] = numeric_col
            else:
                # Keep as string (for grouping columns)
                print(f"[DEBUG] Column '{col}': keeping as string/object type", flush=True)
                # Fill missing values with "empty"
                df[col] = df[col].fillna("empty").astype(str)
                # Also replace string "nan" or "NaN" if they exist
                df[col] = df[col].replace(['nan', 'NaN', 'None'], 'empty')
        
        # Show configuration dialog if requested
        if show_config_dialog:
            print("[INFO] Showing data configuration dialog...", flush=True)
            from data_config import get_data_configuration
            
            config_result = get_data_configuration(df)
            
            if config_result is None:
                print("[ERROR] Configuration cancelled by user", flush=True)
                return False
            
            # Update app state with selected columns
            app_state.group_cols = config_result['group_cols']
            app_state.data_cols = config_result['data_cols']
            app_state.selected_2d_cols = []
            app_state.selected_3d_cols = []
            app_state.selected_2d_confirmed = False
            app_state.selected_3d_confirmed = False
            app_state.available_groups = []
            app_state.visible_groups = None
            
            print(f"[OK] Selected group columns: {app_state.group_cols}", flush=True)
            print(f"[OK] Selected data columns: {app_state.data_cols}", flush=True)
        else:
            # If no dialog, use first columns as groups, rest as data
            print("[WARN] No configuration dialog shown, using empty defaults", flush=True)
            app_state.group_cols = []
            app_state.data_cols = []
        
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
        return True
        
    except Exception as e:
        print(f"[ERROR] Data loading failed: {e}", flush=True)
        traceback.print_exc()
        return False
