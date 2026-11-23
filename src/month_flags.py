"""
month_flags.py

Responsible for:
- Parsing and normalizing service dates
- Filtering services to the reporting period
- Adding month-level keys for grouping
- Generating a month index for the reporting window
"""

from __future__ import annotations

from datetime import date
from typing import Tuple

import pandas as pd


def normalize_service_dates(
    df: pd.DataFrame,
    date_col: str = "Service Date",
    new_col: str = "service_date_dt",
) -> pd.DataFrame:
    """
    Parse the raw service date column into a datetime column.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame containing a raw date column.
    date_col : str, default "Service Date"
        Name of the column with raw date strings.
    new_col : str, default "service_date_dt"
        Name of the new datetime column to create.

    Returns
    -------
    pd.DataFrame
        DataFrame with a new datetime column added.
    """
    df = df.copy()

    df[new_col] = pd.to_datetime(
        df[date_col],
        errors="coerce",  # invalid dates become NaT
        infer_datetime_format=True,
    )

    return df


def filter_to_reporting_period(
    df: pd.DataFrame,
    report_start: date,
    report_end: date,
    date_col: str = "service_date_dt",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filter services to the reporting period.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with a datetime column for service dates.
    report_start : date
        Start of the reporting period (inclusive).
    report_end : date
        End of the reporting period (inclusive).
    date_col : str, default "service_date_dt"
        Name of the datetime column to use for filtering.

    Returns
    -------
    df_in_period : pd.DataFrame
        Rows with non-null dates in [report_start, report_end].
    df_out_of_period : pd.DataFrame
        Rows with null dates or dates outside the reporting window.
    """
    df = df.copy()

    # Ensure datetime type
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    start_ts = pd.to_datetime(report_start)
    end_ts = pd.to_datetime(report_end)

    mask_valid = df[date_col].notna()
    mask_range = (df[date_col] >= start_ts) & (df[date_col] <= end_ts)
    mask_in_period = mask_valid & mask_range

    df_in_period = df.loc[mask_in_period].copy()
    df_out_of_period = df.loc[~mask_in_period].copy()

    return df_in_period, df_out_of_period


def add_month_columns(
    df: pd.DataFrame,
    date_col: str = "service_date_dt",
    month_key_col: str = "month_key",
    month_label_col: str = "month_label",
) -> pd.DataFrame:
    """
    Add month-level keys based on a datetime column.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with a datetime column.
    date_col : str, default "service_date_dt"
        Name of the datetime column to derive months from.
    month_key_col : str, default "month_key"
        Name of the machine-friendly month key column (e.g. '2024-09').
    month_label_col : str, default "month_label"
        Name of the human-friendly month label column (e.g. 'Sep 2024').

    Returns
    -------
    pd.DataFrame
        DataFrame with month_key and month_label columns added.
    """
    df = df.copy()

    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    month_period = df[date_col].dt.to_period("M")

    df[month_key_col] = month_period.dt.strftime("%Y-%m")
    df[month_label_col] = month_period.dt.strftime("%b %Y")

    return df


def generate_month_index(
    report_start: date,
    report_end: date,
    freq: str = "MS",
) -> pd.DataFrame:
    """
    Generate an ordered month index for the reporting period.

    Parameters
    ----------
    report_start : date
        Start of the reporting period (inclusive).
    report_end : date
        End of the reporting period (inclusive).
    freq : str, default "MS"
        Pandas frequency string; "MS" = month start.

    Returns
    -------
    pd.DataFrame
        DataFrame with one row per month, including:
        - month_key (YYYY-MM)
        - month_label (e.g. 'Sep 2024')
        - month_start_date (date)
    """
    start_ts = pd.to_datetime(report_start)
    end_ts = pd.to_datetime(report_end)

    # Ensure we include a month if end date is not exactly on a month start
    month_starts = pd.date_range(start=start_ts, end=end_ts, freq=freq)

    month_index = pd.DataFrame(
        {
            "month_start_date": month_starts.normalize().date,
        }
    )
    month_index["month_key"] = month_starts.strftime("%Y-%m")
    month_index["month_label"] = month_starts.strftime("%b %Y")

    # Reorder columns for readability
    month_index = month_index[["month_key", "month_label", "month_start_date"]]

    return month_index
