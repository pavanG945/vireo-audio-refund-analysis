"""Entry point: python -m src.main

Loads the client's CSVs, fixes the two known data bugs, reclassifies
GW-OTHER tickets from free text, applies the policy checks, and writes
the board-ready CSVs + executive summary to output/.
"""
import json
import sys
import time

from tqdm import tqdm

from . import analysis, classification, config, data_cleaning, data_loader, reporting

MAX_WORKERS = 1  # This Groq key is capped at 8,000 tokens/minute (see
# x-ratelimit-limit-tokens on any response) -- each classification call
# uses ~600-900 tokens, so concurrency just causes 429s. Paced serial
# calls (see PACING_SECONDS) stay under the cap; see DECISIONS.md.
PACING_SECONDS = 6.5  # ~9 requests/min x ~850 tokens/req < 8000 TPM


def load_cache() -> dict:
    path = config.OUTPUT_DIR / "classification_cache.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    path = config.OUTPUT_DIR / "classification_cache.json"
    path.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def run_classification(tickets, cache: dict, save_every: int = 20) -> dict:
    gw = tickets[tickets["refund_reason_code"] == config.DEFAULT_DROPDOWN_CODE]
    stats = {"total": len(gw), "llm": 0, "fallback": 0, "cost_usd": 0.0}
    already_cached = sum(1 for tid in gw["ticket_id"] if tid in cache)
    print(f"  {already_cached} of {len(gw)} already cached from a previous run")

    todo = gw[~gw["ticket_id"].isin(cache.keys())]
    processed_since_save = 0

    for _, row in tqdm(todo.iterrows(), total=len(todo), desc="Classifying GW-OTHER tickets"):
        result = classification.classify_ticket(
            ticket_id=row["ticket_id"],
            customer_message=row["customer_message"],
            agent_notes=row["agent_notes"],
            category=row["category"],
            amount=row["refund_amount_corrected"],
            cache=cache,
        )
        processed_since_save += 1
        if processed_since_save >= save_every:
            save_cache(cache)
            processed_since_save = 0
        if result["source"] == "llm":
            time.sleep(PACING_SECONDS)  # only pace real API calls, not fallbacks

    for tid in gw["ticket_id"]:
        result = cache.get(tid)
        if result is None:
            continue
        if result["source"] == "llm":
            stats["llm"] += 1
            stats["cost_usd"] += (
                result.get("prompt_tokens", 0) / 1_000_000 * config.GROQ_PRICE_PER_1M_INPUT
                + result.get("completion_tokens", 0) / 1_000_000 * config.GROQ_PRICE_PER_1M_OUTPUT
            )
        else:
            stats["fallback"] += 1

    save_cache(cache)
    return stats


def main():
    print("Loading data...")
    raw = data_loader.load_all()

    print("Cleaning: correcting legacy currency, deduplicating re-imports...")
    tickets = data_cleaning.clean_tickets(raw["tickets"])
    print(f"  {len(raw['tickets'])} raw rows -> {len(tickets)} unique tickets")

    print("Classifying GW-OTHER tickets from free text (cached across runs)...")
    cache = load_cache()
    stats = run_classification(tickets, cache)
    save_cache(cache)
    print(f"  {stats['total']} classified ({stats['llm']} via LLM, "
          f"{stats['fallback']} via keyword fallback), "
          f"est. cost ${stats['cost_usd']:.4f}")

    tickets = analysis.add_effective_reason_code(tickets, cache)
    tickets = analysis.add_policy_flags(tickets)

    print("Building monthly / reason / agent views...")
    monthly = analysis.monthly_summary(tickets)
    reasons = analysis.reason_summary(tickets)
    agents_summary = analysis.agent_summary(tickets, raw["agents"])
    agents_summary.attrs["min_tickets"] = analysis.MIN_TICKETS_FOR_AGENT_COMPARISON
    flagged = analysis.flagged_cases(tickets)

    print("Writing output/...")
    reporting.write_outputs(monthly, reasons, agents_summary, flagged)
    reporting.write_executive_summary(
        monthly, reasons, agents_summary, flagged, len(tickets), stats
    )

    total_refund = monthly["refund_amount_inr"].sum()
    total_avoidable = monthly["potentially_avoidable_amount_inr"].sum()
    print("\nDone.")
    print(f"Total refunds (corrected): Rs {total_refund:,.0f}")
    print(f"Potentially avoidable leakage: Rs {total_avoidable:,.0f} "
          f"({total_avoidable/total_refund:.1%} of refund value)")
    print(f"See {config.OUTPUT_DIR}/executive_summary.md for the full readout.")


if __name__ == "__main__":
    sys.exit(main())
