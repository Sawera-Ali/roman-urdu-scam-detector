"""
Dataset loading.

Reads the Excel file that contains the Roman Urdu SMS messages and checks
that the three columns we need are actually present.
"""

from pathlib import Path

import pandas as pd

from . import config


class DatasetError(Exception):
    """Raised when the dataset cannot be loaded or is missing columns."""


def load_dataset(file_path=None, sheet_name=None):
    """
    Load the SMS dataset from an Excel (.xlsx) file.

    file_path  : path to the .xlsx file (defaults to data/raw/...xlsx)
    sheet_name : worksheet to read (defaults to "Scam Messages")

    Returns a pandas DataFrame with the columns:
        msg, status, Authentic/Synthetic

    Raises DatasetError with a clear message if anything is wrong.
    """
    if file_path is None:
        file_path = config.DEFAULT_DATASET_PATH
    if sheet_name is None:
        sheet_name = config.SHEET_NAME

    file_path = Path(file_path)

    # --- 1. Does the file exist? -------------------------------------------
    if not file_path.exists():
        raise DatasetError(
            f"Error: Dataset file not found -> {file_path}\n"
            f"Place the Excel file inside: {config.RAW_DATA_DIR}"
        )

    if file_path.suffix.lower() not in (".xlsx", ".xlsm"):
        raise DatasetError(
            f"Error: Expected an Excel .xlsx file, got '{file_path.suffix}'."
        )

    # --- 2. Does the worksheet exist? --------------------------------------
    try:
        excel_file = pd.ExcelFile(file_path)
    except Exception as error:                      # unreadable / corrupt file
        raise DatasetError(f"Error: Could not open the Excel file -> {error}")

    if sheet_name not in excel_file.sheet_names:
        raise DatasetError(
            f"Error: Worksheet '{sheet_name}' not found. "
            f"Available worksheets: {excel_file.sheet_names}"
        )

    # --- 3. Read it --------------------------------------------------------
    try:
        dataframe = pd.read_excel(excel_file, sheet_name=sheet_name)
    except Exception as error:
        raise DatasetError(f"Error: Could not read the worksheet -> {error}")

    # --- 4. Are the required columns present? ------------------------------
    missing_columns = [
        column for column in config.REQUIRED_COLUMNS if column not in dataframe.columns
    ]
    if missing_columns:
        for column in missing_columns:
            print(f"[ERROR] Required column '{column}' not found.")
        raise DatasetError(
            "Dataset must contain the columns: "
            + ", ".join(config.REQUIRED_COLUMNS)
            + f"\nFound instead: {list(dataframe.columns)}"
        )

    # Keep only the columns we care about, in a predictable order.
    dataframe = dataframe[config.REQUIRED_COLUMNS].copy()

    return dataframe


def describe_dataset(dataframe):
    """
    Build a small dictionary of basic dataset statistics.

    Everything is computed from the DataFrame, nothing is hard-coded, so the
    numbers stay correct when the dataset grows.
    """
    label_counts = dataframe[config.LABEL_COLUMN].astype(str).str.strip().value_counts()
    source_counts = dataframe[config.SOURCE_COLUMN].astype(str).str.strip().value_counts()

    return {
        "total_records": int(len(dataframe)),
        "columns": list(dataframe.columns),
        "label_counts": {str(k): int(v) for k, v in label_counts.items()},
        "source_counts": {str(k): int(v) for k, v in source_counts.items()},
    }
