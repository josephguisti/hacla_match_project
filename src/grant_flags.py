"""
grant_flags.py

Responsible for:
- Taking a GrantClients table and building a lookup of grant clients
- Listing available grants
- Filtering to selected grants
- Flagging service rows as grant vs non-grant based on client ID
"""

from __future__ import annotations

from typing import Iterable, Sequence

import pandas as pd


# Column name defaults based on your actual CSVs
DEFAULT_CLIENT_ID_COL = "Clarity Client ID"
DEFAULT_GRANT_COL = "Programs Name"
DEFAULT_FLAG_COL = "is_grant_client"


def get_unique_grants(
    df_grants: pd.DataFrame,
    grant_col: str = DEFAULT_GRANT_COL,
) -> list[str]:
    """
    Return a sorted list of unique grant names found in the GrantClients table.

    Parameters
    ----------
    df_grants : pd.DataFrame
        GrantClients table.
    grant_col : str, default DEFAULT_GRANT_COL
        Column containing the grant / program name.

    Returns
    -------
    list of str
        Sorted list of unique grant names (non-null).
    """
    if grant_col not in df_grants.columns:
        raise KeyError(f"Grant column '{grant_col}' not found in GrantClients DataFrame.")

    grants_series = (
        df_grants[grant_col]
        .dropna()
        .drop_duplicates()
        .astype(str)
        .sort_values()
    )
    return grants_series.tolist()


def filter_grants_by_names(
    df_grants: pd.DataFrame,
    selected_grants: Sequence[str],
    grant_col: str = DEFAULT_GRANT_COL,
) -> pd.DataFrame:
    """
    Filter the GrantClients table to only the selected grants.

    Parameters
    ----------
    df_grants : pd.DataFrame
        GrantClients table.
    selected_grants : sequence of str
        Grant names to keep.
    grant_col : str, default DEFAULT_GRANT_COL
        Column containing the grant / program name.

    Returns
    -------
    pd.DataFrame
        Filtered GrantClients DataFrame.
    """
    if grant_col not in df_grants.columns:
        raise KeyError(f"Grant column '{grant_col}' not found in GrantClients DataFrame.")

    if not selected_grants:
        # No selection -> return empty frame explicitly
        return df_grants.iloc[0:0].copy()

    mask = df_grants[grant_col].isin(selected_grants)
    return df_grants.loc[mask].copy()


def build_grant_client_table(
    df_grants: pd.DataFrame,
    client_id_col: str = DEFAULT_CLIENT_ID_COL,
    flag_col: str = DEFAULT_FLAG_COL,
) -> pd.DataFrame:
    """
    Build a unique list of grant clients.

    Parameters
    ----------
    df_grants : pd.DataFrame
        GrantClients table, potentially with multiple rows per client
        (e.g., one per grant).
    client_id_col : str, default DEFAULT_CLIENT_ID_COL
        Column name containing the client ID.
    flag_col : str, default DEFAULT_FLAG_COL
        Name of the boolean flag column to create.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - client_id_col
        - flag_col (bool, always True)
    """
    if client_id_col not in df_grants.columns:
        raise KeyError(f"Client ID column '{client_id_col}' not found in GrantClients DataFrame.")

    df = df_grants.copy()

    # Drop rows with missing client IDs
    df = df[df[client_id_col].notna()]

    unique_ids = df[client_id_col].drop_duplicates().reset_index(drop=True)

    result = pd.DataFrame({client_id_col: unique_ids})
    result[flag_col] = True

    return result


def flag_services_with_grant(
    df_services: pd.DataFrame,
    grant_clients: pd.DataFrame,
    client_id_col: str = DEFAULT_CLIENT_ID_COL,
    flag_col: str = DEFAULT_FLAG_COL,
) -> pd.DataFrame:
    """
    Flag each service row as belonging to a grant client or not.

    Parameters
    ----------
    df_services : pd.DataFrame
        Services table with one row per service event.
    grant_clients : pd.DataFrame
        Output of build_grant_client_table, or any DataFrame that has:
        - client_id_col
        - flag_col (bool)
    client_id_col : str, default DEFAULT_CLIENT_ID_COL
        Column name containing the client ID in both tables.
    flag_col : str, default DEFAULT_FLAG_COL
        Name of the boolean flag column indicating grant membership.

    Returns
    -------
    pd.DataFrame
        Copy of df_services with an added boolean column flag_col.
        Rows whose client IDs are not in grant_clients get False.
    """
    if client_id_col not in df_services.columns:
        raise KeyError(f"Client ID column '{client_id_col}' not found in services DataFrame.")
    if client_id_col not in grant_clients.columns:
        raise KeyError(f"Client ID column '{client_id_col}' not found in grant_clients DataFrame.")
    if flag_col not in grant_clients.columns:
        raise KeyError(f"Flag column '{flag_col}' not found in grant_clients DataFrame.")

    services = df_services.copy()

    # Ensure we only keep the ID + flag from grant_clients for merge
    lookup_cols: Iterable[str] = [client_id_col, flag_col]
    lookup = grant_clients.loc[:, lookup_cols].drop_duplicates()

    merged = services.merge(
        lookup,
        how="left",
        on=client_id_col,
    )

    # Clients not present in grant_clients get NaN -> treat as False
    merged[flag_col] = merged[flag_col].fillna(False).astype(bool)

    return merged
