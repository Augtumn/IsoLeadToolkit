"""Data Loading and Processing
Handles Excel file loading and data validation
"""
from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def read_data_frame(excel_file: str, sheet_name: str | None = None) -> pd.DataFrame:
    """Read data file into a cleaned DataFrame."""
    if sheet_name:
        try:
            df = pd.read_excel(excel_file, sheet_name=sheet_name, dtype=str, engine='calamine')
        except Exception as calamine_err:
            # Fall back to openpyxl, but never silently: calamine problems
            # (missing wheel, unsupported file) are worth seeing in the log.
            logger.warning(
                "calamine engine failed (%s); falling back to openpyxl", calamine_err
            )
            df = pd.read_excel(excel_file, sheet_name=sheet_name, dtype=str)
    else:
        df = pd.read_csv(excel_file, dtype=str)

    df.columns = df.columns.astype(str).str.strip()

    for col in df.columns:
        numeric_col = pd.to_numeric(df[col], errors='coerce')
        non_null_count = numeric_col.notna().sum()
        total_count = len(numeric_col)

        if non_null_count > 0 and (non_null_count / total_count) > 0.5:
            # Count non-empty cells that are not numeric: they are silently
            # coerced to NaN and the rows are later dropped, so warn about
            # how much data that costs.
            original_non_empty = int(df[col].notna().sum())
            coerced = original_non_empty - int(non_null_count)
            if coerced > 0:
                logger.warning(
                    "Column '%s' treated as numeric; %s non-numeric cell(s) "
                    "will be dropped",
                    col,
                    coerced,
                )
            df[col] = numeric_col
        else:
            df[col] = df[col].fillna("empty").astype(str)
            df[col] = df[col].replace(['nan', 'NaN', 'None'], 'empty')

    return df
