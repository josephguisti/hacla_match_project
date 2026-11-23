"""
staff_match.py

Compute:
- Staff x month detail (unique grant vs non-grant clients per month)
- Staff-level yearly summary with:
  - total unique grant clients
  - total unique non-grant clients
  - total unique clients
  - match_pct_overall
  - months_worked_on_grant (compressed ranges, e.g. 'Aug24–Oct24; Jan25–Apr25')
"""

from __future__ import annotations

from typing import Dict, List, Tuple

import pandas as pd


CLIENT_ID_COL = "Clarity Client ID"
STAFF_COL = "Service Staff"
GRANT_FLAG_COL = "is_grant_client"
MONTH_KEY_COL = "month_key"


# ---------- Detail: staff x month ----------


def compute_staff_month_detail(
    df_in_period: pd.DataFrame,
    staff_col: str = STAFF_COL,
    client_id_col: str = CLIENT_ID_COL,
    grant_flag_col: str = GRANT_FLAG_COL,
    month_key_col: str = MONTH_KEY_COL,
) -> pd.DataFrame:
    """
    For each staff x month, compute:
    - unique grant clients
    - unique non-grant clients
    - total unique clients

    Parameters
    ----------
    df_in_period : pd.DataFrame
        Services filtered to the reporting period, with columns:
        - staff_col
        - client_id_col
        - grant_flag_col (bool)
        - month_key_col

    Returns
    -------
    pd.DataFrame
        One row per (staff, month_key) with columns:
        - staff_col
        - month_key_col
        - grant_unique_clients
        - non_grant_unique_clients
        - total_unique_clients
    """
    required_cols = {staff_col, client_id_col, grant_flag_col, month_key_col}
    missing = required_cols - set(df_in_period.columns)
    if missing:
        raise KeyError(f"Missing required columns in df_in_period: {missing}")

    df = df_in_period.copy()

    # group by staff, month, grant_flag -> unique clients
    grp = df.groupby([staff_col, month_key_col, grant_flag_col])[client_id_col].nunique()

    # pivot grant_flag dimension to two columns
    detail = grp.unstack(grant_flag_col, fill_value=0).reset_index()

    # Ensure both True/False columns exist even if one is missing in the sample
    if True not in detail.columns:
        detail[True] = 0
    if False not in detail.columns:
        detail[False] = 0

    detail = detail.rename(
        columns={
            True: "grant_unique_clients",
            False: "non_grant_unique_clients",
        }
    )

    detail["total_unique_clients"] = (
        detail["grant_unique_clients"] + detail["non_grant_unique_clients"]
    )

    return detail[[staff_col, month_key_col, "grant_unique_clients",
                   "non_grant_unique_clients", "total_unique_clients"]]


# ---------- Helper: build months_worked_on_grant string ----------


def _build_months_string_for_staff(
    staff_months: List[str],
    month_index_df: pd.DataFrame,
    month_key_col: str = MONTH_KEY_COL,
) -> str:
    """
    Given a sorted list of month_keys for a staff member where they had
    at least one grant client, compress into ranges like 'Aug24–Oct24; Jan25–Apr25'.
    """
    if not staff_months:
        return ""

    # Ensure month_index_df is in chronological order and enrich with short labels
    month_idx = month_index_df.reset_index(drop=True).copy()
    if "month_label_short" not in month_idx.columns:
        # e.g. 'Aug24'
        month_idx["month_label_short"] = pd.to_datetime(
            month_idx["month_start_date"]
        ).dt.strftime("%b%y")

    # Map month_key -> position index
    month_order: Dict[str, int] = {
        row[month_key_col]: idx for idx, row in month_idx.iterrows()
    }

    # Filter out any unknown month_keys (defensive)
    filtered = [m for m in staff_months if m in month_order]
    if not filtered:
        return ""

    # Sort by chronological order
    sorted_keys = sorted(filtered, key=lambda m: month_order[m])
    indices = [month_order[m] for m in sorted_keys]

    # Build contiguous ranges
    ranges: List[Tuple[int, int]] = []
    start = prev = indices[0]

    for idx in indices[1:]:
        if idx == prev + 1:
            # still in same run
            prev = idx
        else:
            # close previous run
            ranges.append((start, prev))
            start = prev = idx
    # close final run
    ranges.append((start, prev))

    # Convert ranges to strings
    parts: List[str] = []
    for start_idx, end_idx in ranges:
        start_label = month_idx.loc[start_idx, "month_label_short"]
        end_label = month_idx.loc[end_idx, "month_label_short"]
        if start_idx == end_idx:
            parts.append(start_label)
        else:
            # Use a simple ASCII hyphen for maximum compatibility with Excel
            parts.append(f"{start_label}-{end_label}")

    return "; ".join(parts)


# ---------- Summary: per staff, full-year match ----------


def compute_staff_year_summary(
    df_in_period: pd.DataFrame,
    month_index_df: pd.DataFrame,
    staff_col: str = STAFF_COL,
    client_id_col: str = CLIENT_ID_COL,
    grant_flag_col: str = GRANT_FLAG_COL,
    month_key_col: str = MONTH_KEY_COL,
) -> pd.DataFrame:
    """
    Compute per-staff summary over the entire reporting period:

    - total_grant_clients: unique grant clients over the year
    - total_non_grant_clients: unique non-grant clients over the year
    - total_clients: total unique clients over the year
    - match_pct_overall: total_grant_clients / total_clients
    - months_worked_on_grant: compressed ranges of months with >=1 grant client

    Parameters
    ----------
    df_in_period : pd.DataFrame
        Services filtered to the reporting period, with:
        - staff_col
        - client_id_col
        - grant_flag_col (bool)
        - month_key_col
    month_index_df : pd.DataFrame
        Output of month_flags.generate_month_index, with at least:
        - month_key
        - month_start_date

    Returns
    -------
    pd.DataFrame
        One row per staff with summary columns.
    """
    required_cols = {staff_col, client_id_col, grant_flag_col, month_key_col}
    missing = required_cols - set(df_in_period.columns)
    if missing:
        raise KeyError(f"Missing required columns in df_in_period: {missing}")

    df = df_in_period.copy()

    # --- 1. Year-level unique client counts per staff ---
    # group by staff + grant_flag to get unique clients
    grp = (
        df.groupby([staff_col, grant_flag_col])[client_id_col]
        .nunique()
        .unstack(grant_flag_col, fill_value=0)
    )

    # Ensure both True/False columns exist
    if True not in grp.columns:
        grp[True] = 0
    if False not in grp.columns:
        grp[False] = 0

    summary = grp.rename(
        columns={
            True: "total_grant_clients",
            False: "total_non_grant_clients",
        }
    ).reset_index()

    summary["total_clients"] = (
        summary["total_grant_clients"] + summary["total_non_grant_clients"]
    )

    # Avoid division by zero
    summary["match_pct_overall"] = summary.apply(
        lambda row: (
            row["total_grant_clients"] / row["total_clients"]
            if row["total_clients"] > 0
            else 0.0
        ),
        axis=1,
    )

    # --- 2. Months worked on grant (>=1 grant client in that month) ---
    # First compute staff-month detail so we know which months had grant clients
    detail = compute_staff_month_detail(
        df,
        staff_col=staff_col,
        client_id_col=client_id_col,
        grant_flag_col=grant_flag_col,
        month_key_col=month_key_col,
    )

    # months with >=1 grant client
    grant_months_df = detail[detail["grant_unique_clients"] > 0]

    months_by_staff: Dict[str, List[str]] = (
        grant_months_df.groupby(staff_col)[month_key_col].apply(list).to_dict()
    )

    # Now build the compressed string per staff
    months_strings: List[str] = []
    for _, row in summary.iterrows():
        staff_val = row[staff_col]
        staff_month_keys = months_by_staff.get(staff_val, [])
        months_str = _build_months_string_for_staff(
            staff_month_keys,
            month_index_df=month_index_df,
            month_key_col=month_key_col,
        )
        months_strings.append(months_str)

    summary["months_worked_on_grant"] = months_strings

    # Reorder columns for readability
    summary = summary[
        [
            staff_col,
            "months_worked_on_grant",
            "total_grant_clients",
            "total_non_grant_clients",
            "total_clients",
            "match_pct_overall",
        ]
    ]

     # Keep only staff who have at least one selected-grant client
    summary = summary[summary["total_grant_clients"] > 0].reset_index(drop=True)
    return summary
