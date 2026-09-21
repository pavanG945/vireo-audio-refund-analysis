"""Tests for the calculations that matter most: currency correction, dedup,
policy flags, and the three aggregation views. Run with: pytest tests/
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import analysis, data_cleaning, policy_rules  # noqa: E402


def make_tickets(rows):
    """Build a minimal tickets DataFrame with sane defaults for columns
    the functions under test don't care about.
    """
    defaults = {
        "status": "resolved", "channel": "chat", "product_sku": "VA-EB-PL1",
        "category": "Other", "priority": "Normal", "assigned_team": "Chat Frontline",
        "transfers": 0, "csat_score": 4.0, "customer_message": "msg",
        "agent_notes": "note", "replacement_issued": "N", "order_id": "VR000001",
    }
    out = []
    for r in rows:
        row = {**defaults, **r}
        out.append(row)
    df = pd.DataFrame(out)
    df["created_at"] = pd.to_datetime(df["created_at"])
    return df


# ---------- currency correction ----------

def test_legacy_amount_divided_by_100():
    df = make_tickets([
        {"ticket_id": "T1", "created_at": "2025-01-01", "customer_id": "C1",
         "agent_id": "A1", "source_system": "legacy_fd", "refund_amount_inr": 212400.0,
         "refund_reason_code": "GW-OTHER"},
    ])
    out = data_cleaning.correct_currency(df)
    assert out.loc[0, "refund_amount_corrected"] == 2124.0


def test_helpdesk_amount_unchanged():
    df = make_tickets([
        {"ticket_id": "T1", "created_at": "2025-01-01", "customer_id": "C1",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": 2124.0,
         "refund_reason_code": "GW-OTHER"},
    ])
    out = data_cleaning.correct_currency(df)
    assert out.loc[0, "refund_amount_corrected"] == 2124.0


def test_null_refund_amount_stays_null():
    df = make_tickets([
        {"ticket_id": "T1", "created_at": "2025-01-01", "customer_id": "C1",
         "agent_id": "A1", "source_system": "legacy_fd", "refund_amount_inr": None,
         "refund_reason_code": None},
    ])
    out = data_cleaning.correct_currency(df)
    assert pd.isna(out.loc[0, "refund_amount_corrected"])


# ---------- dedup ----------

def test_dedup_prefers_helpdesk_row():
    df = make_tickets([
        {"ticket_id": "T1", "created_at": "2025-01-01", "customer_id": "C1",
         "agent_id": "A1", "source_system": "legacy_fd", "refund_amount_inr": 212400.0,
         "refund_reason_code": "GW-OTHER"},
        {"ticket_id": "T1", "created_at": "2025-01-01", "customer_id": "C1",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": 2124.0,
         "refund_reason_code": "GW-OTHER"},
    ])
    out = data_cleaning.deduplicate_tickets(df)
    assert len(out) == 1
    assert out.iloc[0]["source_system"] == "helpdesk"


def test_dedup_leaves_unique_tickets_alone():
    df = make_tickets([
        {"ticket_id": "T1", "created_at": "2025-01-01", "customer_id": "C1",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": 100.0,
         "refund_reason_code": "CANCEL"},
        {"ticket_id": "T2", "created_at": "2025-01-02", "customer_id": "C2",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": 200.0,
         "refund_reason_code": "CANCEL"},
    ])
    out = data_cleaning.deduplicate_tickets(df)
    assert len(out) == 2


# ---------- policy rules ----------

def test_flags_replacement_and_refund_together():
    df = make_tickets([
        {"ticket_id": "T1", "created_at": "2025-01-01", "customer_id": "C1",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": 1000.0,
         "refund_reason_code": "GW-OTHER", "replacement_issued": "Y"},
    ])
    df = data_cleaning.correct_currency(df)
    flags = policy_rules.flag_replacement_refund_conflict(df)
    assert flags.iloc[0]


def test_no_flag_when_only_refund_issued():
    df = make_tickets([
        {"ticket_id": "T1", "created_at": "2025-01-01", "customer_id": "C1",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": 1000.0,
         "refund_reason_code": "GW-OTHER", "replacement_issued": "N"},
    ])
    df = data_cleaning.correct_currency(df)
    flags = policy_rules.flag_replacement_refund_conflict(df)
    assert not flags.iloc[0]


def test_goodwill_cap_flag():
    df = make_tickets([
        {"ticket_id": "T1", "created_at": "2025-01-01", "customer_id": "C1",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": 501.0,
         "refund_reason_code": "GW-OTHER"},
        {"ticket_id": "T2", "created_at": "2025-01-01", "customer_id": "C2",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": 500.0,
         "refund_reason_code": "GW-OTHER"},
    ])
    df = data_cleaning.correct_currency(df)
    flags = policy_rules.flag_over_goodwill_cap(df)
    assert flags.iloc[0] and not flags.iloc[1]


def test_approval_keyword_detected_case_insensitively():
    df = make_tickets([
        {"ticket_id": "T1", "created_at": "2025-01-01", "customer_id": "C1",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": 1000.0,
         "refund_reason_code": "GW-OTHER", "agent_notes": "approved by TL"},
        {"ticket_id": "T2", "created_at": "2025-01-01", "customer_id": "C2",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": 1000.0,
         "refund_reason_code": "GW-OTHER", "agent_notes": "cx satisfied"},
    ])
    flags = policy_rules.flag_approval_mentioned(df)
    assert flags.iloc[0] and not flags.iloc[1]


# ---------- aggregation ----------

def _prepared(df):
    df = data_cleaning.correct_currency(df)
    df["month"] = df["created_at"].dt.to_period("M").astype(str)
    df["effective_reason_code"] = df["refund_reason_code"]
    df["classification_confidence"] = pd.NA
    df = analysis.add_policy_flags(df)
    return df


def test_monthly_summary_totals_reconcile_to_source():
    df = make_tickets([
        {"ticket_id": "T1", "created_at": "2025-01-01", "customer_id": "C1",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": 1000.0,
         "refund_reason_code": "CANCEL"},
        {"ticket_id": "T2", "created_at": "2025-01-15", "customer_id": "C2",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": None,
         "refund_reason_code": None},
        {"ticket_id": "T3", "created_at": "2025-02-01", "customer_id": "C3",
         "agent_id": "A1", "source_system": "legacy_fd", "refund_amount_inr": 200000.0,
         "refund_reason_code": "DOA-REPL"},
    ])
    df = _prepared(df)
    out = analysis.monthly_summary(df)
    assert out.set_index("month").loc["2025-01", "refund_amount_inr"] == 1000.0
    assert out.set_index("month").loc["2025-01", "total_tickets"] == 2
    assert out.set_index("month").loc["2025-02", "refund_amount_inr"] == 2000.0  # 200000/100


def test_reason_summary_amounts_reconcile():
    df = make_tickets([
        {"ticket_id": "T1", "created_at": "2025-01-01", "customer_id": "C1",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": 1000.0,
         "refund_reason_code": "CANCEL"},
        {"ticket_id": "T2", "created_at": "2025-01-02", "customer_id": "C2",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": 500.0,
         "refund_reason_code": "CANCEL"},
    ])
    df = _prepared(df)
    out = analysis.reason_summary(df)
    row = out.set_index("effective_reason_code").loc["CANCEL"]
    assert row["refund_amount_inr"] == 1500.0
    assert row["ticket_count"] == 2
    assert row["pct_of_refund_amount"] == pytest.approx(1.0)


def test_agent_summary_flags_low_volume():
    df = make_tickets([
        {"ticket_id": f"T{i}", "created_at": "2025-01-01", "customer_id": f"C{i}",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": 100.0,
         "refund_reason_code": "CANCEL"}
        for i in range(5)
    ])
    df = _prepared(df)
    agents = pd.DataFrame([{"agent_id": "A1", "name": "Test Agent", "site": "Bengaluru",
                             "team": "Billing", "tier": 1}])
    out = analysis.agent_summary(df, agents)
    assert out.iloc[0]["low_volume_excluded_from_ranking"]  # 5 < MIN_TICKETS_FOR_AGENT_COMPARISON


def test_missing_values_do_not_crash_pipeline():
    df = make_tickets([
        {"ticket_id": "T1", "created_at": "2025-01-01", "customer_id": "C1",
         "agent_id": "A1", "source_system": "helpdesk", "refund_amount_inr": None,
         "refund_reason_code": None, "order_id": None},
    ])
    df = _prepared(df)
    monthly = analysis.monthly_summary(df)
    reasons = analysis.reason_summary(df)
    assert monthly.iloc[0]["refund_tickets"] == 0
    assert len(reasons) == 0
