"""One-off: fill any GW-OTHER ticket not yet in the classification cache
with the deterministic keyword fallback. Used when the LLM pass is cut
short by a rate limit -- see DECISIONS.md / AI_USAGE.md for why.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import classification, config, data_cleaning, data_loader  # noqa: E402


def main():
    cache_path = config.OUTPUT_DIR / "classification_cache.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8"))

    tickets = data_cleaning.clean_tickets(data_loader.load_tickets())
    gw = tickets[tickets["refund_reason_code"] == config.DEFAULT_DROPDOWN_CODE]

    missing = gw[~gw["ticket_id"].isin(cache.keys())]
    print(f"{len(missing)} GW-OTHER tickets have no cached classification -- "
          f"filling with keyword fallback")

    for _, row in missing.iterrows():
        result = classification._keyword_fallback(row["customer_message"], row["agent_notes"])
        result.update({"source": "keyword_fallback", "prompt_tokens": 0, "completion_tokens": 0,
                        "fallback_reason": "LLM pass stopped early (rate limit) -- see DECISIONS.md"})
        cache[row["ticket_id"]] = result

    cache_path.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    print(f"Cache now has {len(cache)} entries "
          f"({sum(1 for v in cache.values() if v['source']=='llm')} llm, "
          f"{sum(1 for v in cache.values() if v['source']=='keyword_fallback')} fallback)")


if __name__ == "__main__":
    main()
