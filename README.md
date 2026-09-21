# Vireo Audio Refund Intelligence

## Problem

Vireo Audio's Finance Controller asked for a monthly refund summary by
reason code and by agent for the board pack. His own export sums to "well
over a crore a quarter"; the helpdesk's own report says "~Rs 11 lakh a
quarter." Both can't be right, and the raw reason codes are unreliable
(the dropdown's default option catches ~43% of refund value).

## Business objective

Give Finance a refund number they can trust, broken down in a way that
answers "who is giving away money and for what" -- and quantify the
portion of refund spend that's *potentially avoidable* (goodwill issued
over the policy cap with no visible approval), in rupees per quarter.

## Solution

A single Python pipeline that:
1. Fixes two concrete data bugs (currency unit mismatch, re-imported
   duplicates) -- see `DECISIONS.md` Section 5 for the evidence.
2. Reclassifies the dropdown-default reason code (`GW-OTHER`) from the
   ticket's free text, using an LLM with a deterministic keyword fallback.
3. Applies three policy checks straight from `support-policy.pdf`
   (goodwill cap, refund+replacement conflict, approval-language proxy).
4. Produces monthly / reason-code / agent-level CSVs and an executive
   summary, team-normalized so Returns Desk isn't flagged for doing its
   job.

## Architecture

```
src/
  config.py          constants traced to specific policy sections
  data_loader.py      load the 5 CSVs
  data_cleaning.py    currency fix + dedup
  policy_rules.py     deterministic policy checks
  classification.py   GW-OTHER reclassification (LLM + keyword fallback)
  analysis.py         monthly / reason / agent aggregation
  reporting.py        writes output/ CSVs + executive summary
  main.py             orchestrates the above
validation/
  run_validation.py   builds a stratified sample, scores tool vs manual labels
prompts/
  classification_prompt.md   the exact prompt, documented
tests/
  test_core.py        unit tests for every calculation above
```

No database, no web server, no ML training -- five CSVs fit in memory,
and a prompt-based classifier with a rules fallback is more transparent
and reliable in a short build than a trained model.

## Data

Not included in this repository -- see `data/README.md`. Place Vireo's
five CSVs in `data/` before running.

## How it works

```
python -m src.main
```

Loads data -> corrects currency -> dedupes -> classifies GW-OTHER tickets
(cached in `output/classification_cache.json`, safe to re-run) -> applies
policy flags -> writes `output/*.csv` and `output/executive_summary.md`.

## AI component

`GW-OTHER` ("Goodwill / Other") is the refund-reason dropdown's first/
default option and is heavily overused relative to what a real goodwill
program would look like. For every GW-OTHER ticket, the tool reads
`customer_message` + `agent_notes` and asks an LLM (Groq, `openai/gpt-oss-20b`)
to decide which of the policy's actual reason codes fits, or whether it's
genuinely discretionary goodwill, or too ambiguous to tell. If no API key
is set, a call fails, or the response is malformed, it falls back to
deterministic keyword rules -- see `prompts/classification_prompt.md` for
the exact prompt and `src/classification.py` for the fallback rules.

**Rate limit note**: the Groq key used here is capped at 8,000 tokens/min.
Classification calls are paced (`PACING_SECONDS` in `src/main.py`) to stay
under that; a higher-tier key could safely parallelize instead.

## Running locally

### Prerequisites
- Python 3.8+
- Vireo's 5 CSVs placed in `data/` (see `data/README.md`)
- (Optional) a Groq API key for LLM classification -- without one, the
  tool still runs end-to-end using keyword rules only, at $0 cost.

### Installation
```bash
pip install -r requirements.txt
```

### Configuration
```bash
cp .env.example .env
# edit .env and set GROQ_API_KEY=... (optional)
```

### Run
```bash
python -m src.main
```

### Expected output
`output/monthly_refunds.csv`, `output/refund_reasons.csv`,
`output/agent_refunds.csv`, `output/flagged_cases.csv`,
`output/executive_summary.md`. Console prints the same headline numbers.

### Tests
```bash
pip install -r requirements-dev.txt
pytest tests/
```

## Validation

See `validation/README.md` for the full procedure and
`validation/validation_summary.md` for results (accuracy, sample size,
error types) once a validation pass has been run.

## Business findings

See `output/executive_summary.md` (generated) and `memo/arjun_mehta_memo.md`
for the numbers. Headline: currency-correcting and deduping alone resolves
the Arjun-vs-Sameer discrepancy; the residual analytical question is how
much of the remaining refund spend is policy-driven vs. potentially
avoidable goodwill.

## Limitations

- The "approval mentioned" check is a keyword proxy on free text, not
  proof of an approval workflow -- see `DECISIONS.md` Section 6.
- Legacy ticket `resolved_at` timestamps mix IST/UTC per policy Section 9;
  unaffected metrics (refund amount) are unaffected, but handle-time
  metrics were not attempted here.
- LLM classification accuracy is bounded by ambiguous free text (typos,
  Hinglish, terse messages); see `validation/validation_summary.md` for
  the measured error rate and error types.
- One-time snapshot analysis, not a live/scheduled pipeline.

## AI usage

See `AI_USAGE.md`.

## Project structure

See the tree under Architecture above; `memo/`, `submission-form.md`,
`AI_USAGE.md`, and `DECISIONS.md` sit at the repo root.

## Reproducibility

`output/classification_cache.json` records every GW-OTHER ticket's
classification (label, confidence, evidence, and whether it came from the
LLM or the keyword fallback), so re-running the pipeline is deterministic
for cached tickets and doesn't re-spend API budget.

## Assumptions and decisions

See `DECISIONS.md` for the full log of what we changed, narrowed, left
out, and why.
