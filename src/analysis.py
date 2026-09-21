"""Monthly, reason-code, and agent-level refund analysis.

All monetary figures use refund_amount_corrected (currency-fixed, deduped).
"""
import pandas as pd

from . import config, policy_rules

MIN_TICKETS_FOR_AGENT_COMPARISON = 30  # ~1.7 tickets/week over 18 months;
# below this, refund-rate swings are noise, not signal -- see DECISIONS.md.


def add_effective_reason_code(tickets: pd.DataFrame, classifications: dict) -> pd.DataFrame:
    """Recodes GW-OTHER tickets to what the classifier decided they really
    are. Non-GW-OTHER tickets, and refund-less tickets, are untouched.
    """
    df = tickets.copy()
    df["effective_reason_code"] = df["refund_reason_code"]
    df["classification_confidence"] = pd.NA
    df["classification_evidence"] = pd.NA
    df["classification_source"] = pd.NA

    is_gw = df["refund_reason_code"] == config.DEFAULT_DROPDOWN_CODE
    for idx in df.index[is_gw]:
        tid = df.at[idx, "ticket_id"]
        result = classifications.get(tid)
        if result is None:
            continue
        df.at[idx, "effective_reason_code"] = result["label"]
        df.at[idx, "classification_confidence"] = result["confidence"]
        df.at[idx, "classification_evidence"] = result["evidence"]
        df.at[idx, "classification_source"] = result["source"]
    return df


def add_policy_flags(tickets: pd.DataFrame) -> pd.DataFrame:
    df = tickets.copy()
    df["flag_replacement_refund_conflict"] = policy_rules.flag_replacement_refund_conflict(df)
    df["approval_mentioned"] = policy_rules.flag_approval_mentioned(df)
    df["flag_potentially_avoidable"] = (
        (df["effective_reason_code"] == "TRUE-GOODWILL")
        & (df["refund_amount_corrected"] > config.GOODWILL_CAP_INR)
        & (~df["approval_mentioned"])
    )
    return df


def monthly_summary(tickets: pd.DataFrame) -> pd.DataFrame:
    g = tickets.groupby("month")
    out = g.agg(
        total_tickets=("ticket_id", "count"),
        refund_tickets=("refund_amount_corrected", lambda s: s.notna().sum()),
        refund_amount_inr=("refund_amount_corrected", "sum"),
        potentially_avoidable_amount_inr=(
            "flag_potentially_avoidable",
            lambda s: tickets.loc[s.index, "refund_amount_corrected"].where(s).sum(),
        ),
    )
    out["refund_rate"] = out["refund_tickets"] / out["total_tickets"].replace(0, pd.NA)
    out["potentially_avoidable_rate"] = out["potentially_avoidable_amount_inr"] / out[
        "refund_amount_inr"
    ].replace(0, pd.NA)
    return out.reset_index().sort_values("month")


def reason_summary(tickets: pd.DataFrame) -> pd.DataFrame:
    refunded = tickets[tickets["refund_amount_corrected"].notna()]
    g = refunded.groupby("effective_reason_code")
    out = g.agg(
        ticket_count=("ticket_id", "count"),
        refund_amount_inr=("refund_amount_corrected", "sum"),
        potentially_avoidable_amount_inr=(
            "flag_potentially_avoidable",
            lambda s: refunded.loc[s.index, "refund_amount_corrected"].where(s).sum(),
        ),
    )
    total = out["refund_amount_inr"].sum()
    out["pct_of_refund_amount"] = out["refund_amount_inr"] / (total if total else pd.NA)
    return out.reset_index().sort_values("refund_amount_inr", ascending=False)


def agent_summary(tickets: pd.DataFrame, agents: pd.DataFrame) -> pd.DataFrame:
    agent_meta = agents[["agent_id", "name", "site", "team", "tier"]].drop_duplicates("agent_id")
    merged = tickets.merge(agent_meta, on="agent_id", how="left")

    g = merged.groupby(["agent_id", "name", "team", "site", "tier"])
    out = g.agg(
        tickets_handled=("ticket_id", "count"),
        refund_tickets=("refund_amount_corrected", lambda s: s.notna().sum()),
        refund_amount_inr=("refund_amount_corrected", "sum"),
        potentially_avoidable_amount_inr=(
            "flag_potentially_avoidable",
            lambda s: merged.loc[s.index, "refund_amount_corrected"].where(s).sum(),
        ),
        gw_other_original_count=("refund_reason_code", lambda s: (s == "GW-OTHER").sum()),
    )
    out["refund_rate"] = out["refund_tickets"] / out["tickets_handled"].replace(0, pd.NA)
    out["potentially_avoidable_rate"] = (
        out["potentially_avoidable_amount_inr"] / out["refund_amount_inr"].replace(0, pd.NA)
    ).fillna(0)
    out["gw_other_share_of_refunds"] = (
        out["gw_other_original_count"] / out["refund_tickets"].replace(0, pd.NA)
    ).fillna(0)
    out["low_volume_excluded_from_ranking"] = (
        out["tickets_handled"] < MIN_TICKETS_FOR_AGENT_COMPARISON
    )
    return out.reset_index().sort_values("refund_amount_inr", ascending=False)


def flagged_cases(tickets: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "ticket_id", "created_at", "agent_id", "customer_id", "order_id",
        "category", "refund_amount_corrected", "refund_reason_code",
        "effective_reason_code", "replacement_issued",
        "flag_replacement_refund_conflict", "flag_potentially_avoidable",
        "classification_confidence", "classification_evidence",
    ]
    conflict = tickets[tickets["flag_replacement_refund_conflict"]].copy()
    conflict["flag_type"] = "refund_and_replacement_both_issued"

    avoidable = tickets[tickets["flag_potentially_avoidable"]].copy()
    avoidable["flag_type"] = "goodwill_over_cap_no_approval_note"

    low_conf = tickets[
        (tickets["effective_reason_code"] == "AMBIGUOUS")
        & tickets["refund_amount_corrected"].notna()
    ].copy()
    low_conf["flag_type"] = "ambiguous_classification_needs_human_review"

    out = pd.concat([conflict, avoidable, low_conf], ignore_index=True)
    return out[cols + ["flag_type"]].sort_values("refund_amount_corrected", ascending=False)
