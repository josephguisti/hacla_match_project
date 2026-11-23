"""
output_tables.py

Functions to write CSV outputs for:
- included services (in reporting period)
- excluded services (out of period / bad dates)
- staff x month detail
- staff-year summary
- month index
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def ensure_dir(path: Path) -> None:
    """
    Ensure the given directory exists.
    """
    path.mkdir(parents=True, exist_ok=True)


def write_outputs(
    output_dir: Path,
    df_included_services: pd.DataFrame,
    df_excluded_services: pd.DataFrame,
    staff_month_detail: pd.DataFrame,
    staff_year_summary: pd.DataFrame,
    month_index_df: pd.DataFrame,
) -> None:
    """
    Write all core CSV outputs to the output directory.

    Parameters
    ----------
    output_dir : Path
        Base directory where CSV files will be written.
    df_included_services : pd.DataFrame
        Services used for match calculations (in reporting period).
    df_excluded_services : pd.DataFrame
        Services excluded due to dates / bad dates.
    staff_month_detail : pd.DataFrame
        Staff x month detail table.
    staff_year_summary : pd.DataFrame
        Staff-level full-year summary table.
    month_index_df : pd.DataFrame
        Month index for the reporting period.
    """
    ensure_dir(output_dir)

    included_path = output_dir / "included_services.csv"
    excluded_path = output_dir / "excluded_services.csv"
    staff_month_path = output_dir / "staff_month_detail.csv"
    staff_year_path = output_dir / "staff_year_summary.csv"
    month_index_path = output_dir / "month_index.csv"

    df_included_services.to_csv(included_path, index=False)
    df_excluded_services.to_csv(excluded_path, index=False)
    staff_month_detail.to_csv(staff_month_path, index=False)
    staff_year_summary.to_csv(staff_year_path, index=False)
    month_index_df.to_csv(month_index_path, index=False)

    print("\nCSV outputs written to:")
    print(f"  - {included_path}")
    print(f"  - {excluded_path}")
    print(f"  - {staff_month_path}")
    print(f"  - {staff_year_path}")
    print(f"  - {month_index_path}")
