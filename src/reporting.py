"""Writes the output/ CSVs and the executive summary."""
from pathlib import Path

import pandas as pd

from . import config


def write_outputs(monthly: pd.DataFrame, reasons: pd.DataFrame,
                   agents: pd.DataFrame, flagged: pd.DataFrame) -> None:
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    monthly.to_csv(config.OUTPUT_DIR / "monthly_refunds.csv", index=False)
    reasons.to_csv(config.OUTPUT_DIR / "refund_reasons.csv", index=False)
    agents.to_csv(config.OUTPUT_DIR / "agent_refunds.csv", index=False)
    flagged.to_csv(config.OUTPUT_DIR / "flagged_cases.csv", index=False)


def write_executive_summary(monthly: pd.DataFrame, reasons: pd.DataFrame,
                             agents: pd.DataFrame, flagged: pd.DataFrame,
                             total_tickets: int, classify_stats: dict) -> None:
    total_refund = monthly["refund_amount_inr"].sum()
    total_avoidable = monthly["potentially_avoidable_amount_inr"].sum()
    n_quarters = max(1, round(len(monthly) / 3))
    per_quarter = total_refund / n_quarters
    avoidable_per_quarter = total_avoidable / n_quarters
    conflict_count = (flagged["flag_type"] == "refund_and_replacement_both_issued").sum()
    conflict_amount = flagged.loc[
        flagged["flag_type"] == "refund_and_replacement_both_issued", "refund_amount_corrected"
    ].sum()

    top_reason = reasons.iloc[0]
    low_vol_excluded = agents["low_volume_excluded_from_ranking"].sum()
    ranked_agents = agents[~agents["low_volume_excluded_from_ranking"]].sort_values(
        "refund_rate", ascending=False
    )

    lines = []
    lines.append("# Executive Summary -- Vireo Audio Refund Analysis\n")
    lines.append(f"Period covered: {monthly['month'].min()} to {monthly['month'].max()} "
                 f"({len(monthly)} months, {total_tickets:,} unique tickets after dedup).\n")

    lines.append("## Headline numbers\n")
    lines.append(f"- Total refunds (currency-corrected, deduped): **Rs {total_refund:,.0f}** "
                 f"over the period -> **Rs {per_quarter:,.0f}/quarter** average.\n")
    lines.append(f"- Potentially avoidable leakage (goodwill >Rs {config.GOODWILL_CAP_INR} cap, "
                 f"no approval note): **Rs {total_avoidable:,.0f}** total -> "
                 f"**Rs {avoidable_per_quarter:,.0f}/quarter** "
                 f"({total_avoidable/total_refund:.1%} of all refund value).\n")
    lines.append(f"- Refund + replacement issued on the same ticket (policy conflict): "
                 f"{conflict_count} tickets, Rs {conflict_amount:,.0f}.\n")
    lines.append(f"- Largest reason bucket after reclassification: {top_reason['effective_reason_code']} "
                 f"({top_reason['ticket_count']} tickets, Rs {top_reason['refund_amount_inr']:,.0f}, "
                 f"{top_reason['pct_of_refund_amount']:.1%} of refund value).\n")

    lines.append("## Data-quality corrections applied\n")
    lines.append("- legacy_fd refund amounts were stored in paise, not rupees (confirmed via "
                 "125 tickets that appear under both source systems with an exact 100x ratio). "
                 "Corrected before any aggregation.\n")
    lines.append("- 638 tickets were re-imported and appeared under both source systems; "
                 "deduplicated to one row per ticket_id (helpdesk version kept).\n")

    lines.append("## AI classification\n")
    lines.append(f"- {classify_stats.get('total', 0)} GW-OTHER tickets reclassified from free text.\n")
    lines.append(f"- {classify_stats.get('llm', 0)} via Groq LLM, "
                 f"{classify_stats.get('fallback', 0)} via keyword fallback "
                 f"(no key / call failure / rate limit).\n")
    lines.append(f"- Estimated API cost for this run: ${classify_stats.get('cost_usd', 0):.4f}.\n")

    lines.append("## Agent view\n")
    lines.append(f"- {low_vol_excluded} of {len(agents)} agents excluded from refund-rate ranking "
                 f"(fewer than {agents.attrs.get('min_tickets', 30)} tickets in the window -- "
                 "too little volume for a fair comparison).\n")
    if len(ranked_agents):
        top = ranked_agents.iloc[0]
        lines.append(f"- Highest refund rate among comparable agents: {top['agent_id']} "
                     f"({top['team']}) at {top['refund_rate']:.1%} "
                     f"({top['tickets_handled']} tickets). Returns Desk agents are expected to "
                     "run highest by policy design (they process the large majority of refunds) "
                     "and should be read in that context, not as an anomaly.\n")

    lines.append("\n*See validation/validation_summary.md for accuracy of the AI classification, "
                 "and DECISIONS.md for every judgment call made in this analysis.*\n")

    (config.OUTPUT_DIR / "executive_summary.md").write_text("\n".join(lines), encoding="utf-8")
