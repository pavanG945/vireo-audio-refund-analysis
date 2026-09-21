# AI Usage Log

## What was used

- **Claude (Anthropic), via Claude Code** -- pair-programmed the entire
  project interactively: data inspection, currency-bug discovery, all
  source code in `src/`, tests, this documentation, and the memo.
- **Groq API (`openai/gpt-oss-20b`)** -- the production classification
  step: reclassifying `GW-OTHER` tickets from free text. See
  `prompts/classification_prompt.md`.

## Where Claude helped

- **Data inspection**: wrote and ran pandas scripts against all five CSVs
  before any code was built, surfacing the row-count mismatch (line count
  vs. actual records, due to embedded newlines in quoted CSV fields), the
  100x currency ratio, and the 638 re-imported duplicate tickets. These
  were found by cross-tabulating source_system against duplicate
  ticket_ids and checking exact ratios -- not assumed from the client
  emails, though the emails (Sameer's warning) told us where to look.
- **Architecture and scope**: proposed the minimum-viable design (single
  CLI, no DB/UI) given the 5-hour target, and flagged the GW-OTHER
  dropdown-default problem as the real "AI-assisted" opportunity rather
  than defaulting to "run an LLM over everything."
- **Debugging a real production issue**: the first full pipeline run used
  8 parallel threads and got 913 of 991 classifications rate-limited
  (HTTP 429) into the keyword fallback. Claude diagnosed this by reading
  the `x-ratelimit-limit-tokens` response header (8,000 tokens/min on this
  key), rewrote the classifier to run serially with ~6.5s pacing, and
  triaged which of the 913 fallback results were worth re-processing
  (the 420 that hit no keyword rule at all and defaulted to
  TRUE-GOODWILL/AMBIGUOUS) versus which already had a confident keyword
  match and weren't worth spending quota on.
- **Test-driven bug catch**: writing `tests/test_core.py` surfaced a real
  `ZeroDivisionError` in the rate calculations (a month/agent/reason with
  zero refunds divided 0/0 as an object-dtype array instead of producing
  NaN). Fixed in `src/data_cleaning.py` and `src/analysis.py` before it
  could have hit production data.

## What was discarded

- **8-way parallel classification.** Worked in a single-ticket smoke test,
  failed at scale against this API key's real rate limit. Replaced with
  paced serial calls once the actual limit was visible in response
  headers.
- **`max_tokens: 150` on the classification call.** `gpt-oss-20b` is a
  reasoning model that spends tokens on a hidden chain-of-thought before
  the JSON answer; 150 tokens was consumed entirely by reasoning, leaving
  none for the actual output, and Groq returned `json_validate_failed`.
  Fixed with `reasoning_effort: "low"` and `max_tokens: 500`.
- **Sending all GW-OTHER tickets through the LLM regardless of keyword
  confidence.** Once the token-budget ceiling was known, we prioritized
  the 420 tickets where keyword rules had no signal at all, rather than
  spending the same limited budget re-confirming tickets the rules
  already matched with a clear phrase.
- **A from-scratch anomaly-detection model for agent behavior.** Considered
  and rejected -- see `DECISIONS.md` Section 4.

## Cost

See `submission-form.md` for the full per-ticket/per-month arithmetic.
Actual spend for this project's classification runs: well under $0.01
(991 tickets, 78 through the LLM in the first run at $0.0056; the retried
batch of 420 low-confidence tickets adds a comparable small amount -- see
`output/executive_summary.md` for the final run's logged cost).

## What was NOT AI-generated

The underlying business numbers (refund totals, the paise-vs-rupee
finding, the duplicate-ticket count) come from running the code against
the real data, not from an LLM's narrative -- Claude wrote the analysis
code, but the pandas/Groq output is what's reported, not a generated
summary of it.
