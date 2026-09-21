"""Fixes the two data-quality bugs Sameer's email warned about:

1. legacy_fd rows store refund_amount_inr in paise, not rupees (confirmed
   empirically -- see DECISIONS.md for the evidence).
2. A subset of legacy tickets was re-imported and appears under both
   source systems with the same ticket_id.

Nothing else about the raw data is altered.
"""
import pandas as pd

from . import config


def correct_currency(tickets: pd.DataFrame) -> pd.DataFrame:
    """Divide legacy_fd refund amounts by 100 to express them in rupees."""
    df = tickets.copy()
    df["refund_amount_corrected"] = pd.to_numeric(df["refund_amount_inr"], errors="coerce")
    is_legacy = df["source_system"] == config.LEGACY_SOURCE_SYSTEM
    df.loc[is_legacy, "refund_amount_corrected"] = (
        df.loc[is_legacy, "refund_amount_inr"] / config.LEGACY_CURRENCY_DIVISOR
    )
    return df


def deduplicate_tickets(tickets: pd.DataFrame) -> pd.DataFrame:
    """Collapse re-imported tickets to one row per ticket_id.

    When a ticket_id appears under both source systems, the helpdesk row is
    kept (it is the live, currently-reconciled system per policy Section 9).
    """
    df = tickets.copy()
    df["_prefer_helpdesk"] = (df["source_system"] == "helpdesk").astype(int)
    df = df.sort_values(
        ["ticket_id", "_prefer_helpdesk"], ascending=[True, False]
    )
    df = df.drop_duplicates(subset="ticket_id", keep="first")
    df = df.drop(columns="_prefer_helpdesk")
    return df.reset_index(drop=True)


def clean_tickets(tickets: pd.DataFrame) -> pd.DataFrame:
    df = correct_currency(tickets)
    df = deduplicate_tickets(df)
    df["month"] = df["created_at"].dt.to_period("M").astype(str)
    df["quarter"] = df["created_at"].dt.to_period("Q").astype(str)
    return df
