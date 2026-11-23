"""
dev_run_month_flags.py

Quick standalone test of the month_flags module using the sample
ServicesComplete CSV. This ignores grants for now and just checks:

- date parsing
- reporting-period filtering
- month_key / month_label generation
- month index generation
"""

from datetime import date
from pathlib import Path

import pandas as pd

from month_flags import (
    normalize_service_dates,
    filter_to_reporting_period,
    add_month_columns,
    generate_month_index,
)


def main() -> None:
    # ----- Paths -----
    project_root = Path(__file__).resolve().parents[1]
    sample_data_dir = project_root / "data" / "sample"
    services_path = sample_data_dir / "ServicesComplete_sample.csv"

    print(f"Loading services from: {services_path}")

    df_services = pd.read_csv(services_path)

    print(f"Raw services rows: {len(df_services)}")

    # ----- Normalize dates -----
    df_services = normalize_service_dates(
        df_services,
        date_col="Service Date",
        new_col="service_date_dt",
    )

    # ----- Define reporting period (EDIT THESE DATES as needed) -----
    # Example: FY24 07/01/2024–06/30/2025
    report_start = date(2024, 7, 1)
    report_end = date(2025, 6, 30)

    # ----- Filter to reporting period -----
    df_in_period, df_out_of_period = filter_to_reporting_period(
        df_services,
        report_start=report_start,
        report_end=report_end,
        date_col="service_date_dt",
    )

    print(f"Rows in reporting period: {len(df_in_period)}")
    print(f"Rows OUT of reporting period (or bad dates): {len(df_out_of_period)}")

    # ----- Add month columns -----
    df_in_period = add_month_columns(
        df_in_period,
        date_col="service_date_dt",
        month_key_col="month_key",
        month_label_col="month_label",
    )

    # Show a small sample
    print("\nSample of services with month columns:")
    cols_to_show = [
        "Service Date",
        "service_date_dt",
        "month_key",
        "month_label",
        "Service Staff",
        "Clarity Client ID",
    ]
    existing_cols = [c for c in cols_to_show if c in df_in_period.columns]
    print(df_in_period[existing_cols].head(10))

    # ----- Generate month index -----
    month_index_df = generate_month_index(
        report_start=report_start,
        report_end=report_end,
    )

    print("\nMonth index for reporting period:")
    print(month_index_df)


if __name__ == "__main__":
    main()
