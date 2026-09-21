"""Deterministic checks straight from support-policy.pdf Section 5.

No NLP needed for these -- they're structured-field comparisons.
"""
import re

import pandas as pd

from . import config

_APPROVAL_RE = re.compile(config.APPROVAL_KEYWORDS_REGEX, re.IGNORECASE)


def flag_replacement_refund_conflict(tickets: pd.DataFrame) -> pd.Series:
    """Policy: 'In no case is a customer to receive both a refund and a
    replacement for the same order.' True when both happened on one ticket.
    """
    return (tickets["replacement_issued"] == "Y") & (
        tickets["refund_amount_corrected"].notna()
    )


def flag_over_goodwill_cap(tickets: pd.DataFrame) -> pd.Series:
    """Policy: goodwill credits >Rs 500 require Team Lead approval."""
    return tickets["refund_amount_corrected"] > config.GOODWILL_CAP_INR


def flag_approval_mentioned(tickets: pd.DataFrame) -> pd.Series:
    """Heuristic only: does the closing note mention TL/approval language?
    Absence does not prove absence of approval -- documented as a limitation.
    """
    return tickets["agent_notes"].astype(str).str.contains(_APPROVAL_RE)
