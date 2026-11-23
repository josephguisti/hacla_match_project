"""
main.py

Entry point for the HACLA staff match tool.

Current focus:
- Prompt user for reporting period
- Prompt user to choose which grant(s) to include
- Load GrantClients and Services files from Prep Outputs
- Flag services as grant vs non-grant
- Apply month flags
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import List, Tuple

import pandas as pd

from grant_flags import (
    get_unique_grants,
    filter_grants_by_names,
    build_grant_client_table,
    flag_services_with_grant,
)
from month_flags import (
    normalize_service_dates,
    filter_to_reporting_period,
    add_month_columns,
    generate_month_index,
)

from staff_match import (
    compute_staff_month_detail,
    compute_staff_year_summary,
)

from output_tables import write_outputs

# ---------- Date prompting ----------


def prompt_for_date(prompt_text: str) -> date:
    """
    Prompt the user for a date in YYYY-MM-DD format and return a date object.
    Re-prompts until a valid date is entered.
    """
    while True:
        raw = input(prompt_text).strip()
        try:
            return date.fromisoformat(raw)
        except ValueError:
            print("Invalid date. Please use YYYY-MM-DD (e.g. 2024-07-01).")


def prompt_for_reporting_period() -> Tuple[date, date]:
    """
    Interactively ask the user for a reporting period (start and end dates).
    Ensures start <= end.
    """
    while True:
        print("Enter reporting period for HACLA APR.")
        start = prompt_for_date("  Start date (YYYY-MM-DD): ")
        end = prompt_for_date("  End date   (YYYY-MM-DD): ")

        if start > end:
            print("Start date is after end date. Please try again.\n")
            continue

        print(f"\nYou entered: {start} to {end}")
        confirm = input("Is this correct? [y/n]: ").strip().lower()
        if confirm == "y":
            return start, end
        print("Let's try again.\n")


# ---------- Grant selection ----------


def prompt_for_grant_selection(df_grants: pd.DataFrame) -> List[str]:
    """
    Show the user all unique grants, numbered, and ask them to choose
    one or more by number (comma-separated). Returns the selected grant names.
    """
    all_grants = get_unique_grants(df_grants)

    if not all_grants:
        print("No grants found in GrantClients file.")
        return []

    print("\nAvailable grants found in GrantClients data:")
    for idx, grant_name in enumerate(all_grants, start=1):
        print(f"  {idx}. {grant_name}")

    while True:
        raw = input(
            "\nEnter one or more grant numbers separated by commas "
            "(e.g. 1,3,4), or 'all' to include all grants: "
        ).strip().lower()

        if raw == "all":
            selected = all_grants
            break

        if not raw:
            print("No input detected. Please enter one or more numbers, or 'all'.")
            continue

        parts = [part.strip() for part in raw.split(",") if part.strip()]
        indices: List[int] = []
        valid = True

        for part in parts:
            if not part.isdigit():
                print(f"'{part}' is not a valid number.")
                valid = False
                break
            idx = int(part)
            if idx < 1 or idx > len(all_grants):
                print(f"{idx} is out of range. Valid range is 1 to {len(all_grants)}.")
                valid = False
                break
            indices.append(idx)

        if not valid:
            continue

        # Deduplicate while preserving order
        seen = set()
        selected = []
        for idx in indices:
            name = all_grants[idx - 1]
            if name not in seen:
                seen.add(name)
                selected.append(name)

        if not selected:
            print("No valid grant numbers selected. Please try again.")
            continue

        print("\nYou selected the following grants:")
        for name in selected:
            print(f"  - {name}")

        confirm = input("Is this correct? [y/n]: ").strip().lower()
        if confirm == "y":
            break

    return selected


# ---------- Main pipeline (sample data for now) ----------


def main() -> None:
    # --- 1. Prompt for reporting period ---
    report_start, report_end = prompt_for_reporting_period()

    # main.py -> src -> Python script -> HACLA Cash Match Workflow
    project_root = Path(__file__).resolve().parents[1]
    workflow_root = project_root.parent
    prep_outputs_dir = workflow_root / "Prep Outputs"

    grant_clients_path = prep_outputs_dir / "GrantClients.csv"
    services_path = prep_outputs_dir / "ServicesComplete.csv"


    # --- 2. Load GrantClients and prompt for grants ---
    print(f"\nLoading grant clients from: {grant_clients_path}")
    df_grants = pd.read_csv(grant_clients_path)
    print(f"Rows in GrantClients sample: {len(df_grants)}")

    selected_grants = prompt_for_grant_selection(df_grants)

    df_grants_filtered = filter_grants_by_names(
        df_grants,
        selected_grants,
        grant_col="Programs Name",
    )
    print(f"\nRows in GrantClients after filtering to selected grants: {len(df_grants_filtered)}")

    # Build unique grant client table
    grant_client_table = build_grant_client_table(
        df_grants_filtered,
        client_id_col="Clarity Client ID",
        flag_col="is_grant_client",
    )
    print(f"Unique grant clients (after selection): {len(grant_client_table)}")

    # --- 3. Load services ---
    print(f"\nLoading services from: {services_path}")
    df_services = pd.read_csv(services_path)
    print(f"Raw services rows: {len(df_services)}")

    # --- 4. Flag services with grant membership ---
    df_services_flagged = flag_services_with_grant(
        df_services,
        grant_client_table,
        client_id_col="Clarity Client ID",
        flag_col="is_grant_client",
    )

    print(
        "Example grant flag counts in services:\n"
        f"  Grant services (is_grant_client=True): "
        f"{df_services_flagged['is_grant_client'].sum()}\n"
        f"  Non-grant services: "
        f"{(~df_services_flagged['is_grant_client']).sum()}"
    )

    # --- 5. Month flags pipeline (using user-entered dates) ---
    df_services_flagged = normalize_service_dates(
        df_services_flagged,
        date_col="Service Date",
        new_col="service_date_dt",
    )

    df_in_period, df_out_of_period = filter_to_reporting_period(
        df_services_flagged,
        report_start=report_start,
        report_end=report_end,
        date_col="service_date_dt",
    )
    print(f"\nRows in reporting period: {len(df_in_period)}")
    print(f"Rows OUT of reporting period (or bad dates): {len(df_out_of_period)}")

    df_in_period = add_month_columns(df_in_period)

    month_index_df = generate_month_index(
        report_start=report_start,
        report_end=report_end,
    )

    print("\nSample of in-period services with month + grant flag:")
    cols_to_show = [
        "Service Date",
        "service_date_dt",
        "month_key",
        "month_label",
        "Service Staff",
        "Clarity Client ID",
        "is_grant_client",
    ]
    existing_cols = [c for c in cols_to_show if c in df_in_period.columns]
    print(df_in_period[existing_cols].head(10))

    print("\nMonth index:")
    print(month_index_df)

    # --- 6. Staff match calculations ---

    # Staff-month detail (granular)
    staff_month_detail = compute_staff_month_detail(
        df_in_period,
        staff_col="Service Staff",
        client_id_col="Clarity Client ID",
        grant_flag_col="is_grant_client",
        month_key_col="month_key",
    )

    print("\nSample staff × month detail:")
    print(staff_month_detail.head(10))


    # Staff-year summary (final APR logic)
    staff_year_summary = compute_staff_year_summary(
        df_in_period,
        month_index_df,
        staff_col="Service Staff",
        client_id_col="Clarity Client ID",
        grant_flag_col="is_grant_client",
        month_key_col="month_key",
    )

    print("\nSample staff yearly summary:")
    print(staff_year_summary.head(10))

    # --- 7. Write CSV outputs ---

    output_dir = project_root / "output"

    df_included_services = df_in_period[df_in_period["is_grant_client"] == True].copy()

    write_outputs(
        output_dir=output_dir,
        df_included_services=df_included_services,
        df_excluded_services=df_out_of_period,
        staff_month_detail=staff_month_detail,
        staff_year_summary=staff_year_summary,
        month_index_df=month_index_df,
    )


if __name__ == "__main__":
    main()
