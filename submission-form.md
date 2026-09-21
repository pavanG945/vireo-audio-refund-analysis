# Submission Form -- Vireo Audio Support Tickets (Set C)

## What did you build, and what business outcome does it move?

A Python CLI that fixes two real data bugs (a currency-unit mismatch
inflating legacy refund amounts 100x, and 638 duplicate tickets from a
system migration), reclassifies the refund-reason dropdown's overused
default option using an LLM, and produces monthly/reason/agent refund
views plus a "potentially avoidable" leakage figure.

Business outcome: currency-correcting and deduping alone resolves the
Arjun-vs-Sameer dispute (helpdesk's ~Rs 11 lakh/quarter figure was right;
Arjun's export was reading legacy paise values as rupees). Beyond that,
the tool identifies **Rs [Z-amount]/quarter (~[Z]% of refund value)** in
goodwill refunds over the policy's Rs 500 cap with no approval note on
file -- a concrete, actionable number for the board pack.

## What does one run cost, and what would a month cost at Vireo's volume?

One run classifies every `GW-OTHER`-tagged ticket (the reason code that
needed reclassification) using Groq's `openai/gpt-oss-20b`
($0.075/1M input tokens, $0.30/1M output tokens as of Sep 2026 --
`llama-3.1-8b-instant` moved to enterprise/contact-sales pricing and has
no public rate anymore).

**This run**: [N_LLM] tickets classified via LLM, [N_FALLBACK] via the
zero-cost keyword fallback (used when no key is set, a call fails, or --
as happened here -- the API key's rate limit is hit; see `AI_USAGE.md`).
Logged cost: **$[COST]** (see `output/executive_summary.md`).

**Per-ticket cost** (LLM path): ~450-500 prompt tokens + ~100-400
completion tokens (this is a reasoning model; its hidden chain-of-thought
counts as completion tokens) ~= **$0.00006-0.00013/ticket**.

**Monthly volume**: 650 tickets/week x 52/12 = **2,816.7 tickets/month**.
GW-OTHER made up 991 of 11,600 tickets in our 18-month sample = **8.5% of
all tickets**. Applying that rate: 2,816.7 x 0.085 ~= **240 GW-OTHER
tickets/month** needing classification.

**Estimated monthly cost**: 240 x $0.0001 ~= **$0.024/month** (~Rs 2/month
at ~Rs 84/$1). Effectively free at this volume. If Vireo's dropdown
default were fixed (see `DECISIONS.md` recommendation), this ongoing cost
would shrink further as fewer tickets need reclassification.

## How do you know it works?

- **Sample**: [N] GW-OTHER tickets, stratified across the classifier's 9
  possible output labels so rare categories aren't drowned out by common
  ones (see `validation/run_validation.py:build_sample`).
- **Method**: manually read each ticket's `customer_message` and
  `agent_notes` and judged whether the tool's label matched what actually
  happened, blind to the tool's confidence score.
- **Accuracy**: **[ACCURACY]%** ([correct]/[N]) -- see
  `validation/validation_summary.md`.
- **Where it gets it wrong**: [ERROR_TYPES -- fill from validation_summary.md,
  e.g. terse/ambiguous messages defaulting to TRUE-GOODWILL, Hinglish
  phrasing not matched by keyword rules, messages referencing an issue
  resolved in a prior ticket not visible in this one].

## Did you change, narrow, or push back on the client's ask?

Yes -- see `DECISIONS.md` Section 3 for the full list. Briefly: we added
a reclassification step the brief didn't explicitly ask for, because a
straight pivot on the raw (unreliable) reason code would have technically
answered the question while substantively misleading the board. We did
not investigate handle-time/SLA/CSAT metrics even though the policy doc
covers them, since the brief was specifically about refunds.

## What is wrong with what you are handing us?

- The "no approval note" signal is a keyword match on free text
  (`\bTL\b|team lead|approv`), not proof an approval process was or
  wasn't followed -- see `DECISIONS.md` Section 6.
- LLM classification was rate-limited mid-project (see `AI_USAGE.md`); a
  portion of GW-OTHER tickets are classified by keyword fallback rather
  than the LLM. Fallback rules are simpler and more likely to default to
  TRUE-GOODWILL on ambiguous text than the LLM would.
- Dedup logic keeps the entire helpdesk row when a ticket is duplicated
  across systems, without cross-checking that non-money fields (agent_id,
  category) agree between the two versions.
- This is a one-time snapshot analysis, not a live pipeline.
- No handling for the legacy IST/UTC timestamp mismatch (Section 9) --
  doesn't affect refund amounts, but would affect any handle-time metric
  built on this code later.

## What did you deliberately leave out, and why that rather than something else?

See `DECISIONS.md` Section 4. Short version: no UI, no database, no
trained ML model, no handle-time/CSAT analysis, no agent-misconduct
inference -- all either out of scope for a refund ask or not justified by
a 5-hour budget relative to the CSV-and-CLI approach.

## Anything you built or found that nobody asked for?

Found: the exact mechanism behind the Arjun/Sameer numbers disagreement
(nobody asked us to explain *why* the two numbers differed, just to
reconcile them) and the dropdown-default bias explaining ~43% of "refund
reasons" being uninformative. Built: a reusable validation harness
(`validation/run_validation.py`) that isn't part of the core ask but makes
"how do you know it works" answerable for any future reclassification
change, not just this one.

## What did you use AI for?

See `AI_USAGE.md` for the full log -- tools/models, what helped, what got
discarded (8-way parallel API calls that turned out to violate this key's
rate limit; an initial `max_tokens` setting too low for a reasoning
model), and the recording linked below.

**Screen recording**: [DRIVE/YOUTUBE LINK]

## Your Public Google Drive Link

[LINK]

## Someone picks this up on Monday and you are unreachable. The three things they need to know.

1. **The currency bug is the whole story for the totals mismatch.**
   `legacy_fd` rows (pre-14-Sep-2025) store refund amounts in paise; the
   fix is one line (`src/data_cleaning.py:correct_currency`), already
   applied and tested. Don't re-litigate whose export was "right" --
   both were reading real data, just one unit was wrong.
2. **The classification cache (`output/classification_cache.json`) is
   safe to keep re-using.** Re-running `python -m src.main` will only
   call the API for tickets not already in the cache. If you need to
   force a re-classification of specific tickets, delete their entries
   from that file first.
3. **This Groq key is rate-limited to 8,000 tokens/minute.** If you add
   concurrency back or switch keys, check the `x-ratelimit-*` response
   headers before assuming a higher throughput is safe -- see
   `AI_USAGE.md` for exactly how this bit us once already.

## Honest hours spent

[HOURS]

## Github Repo Link

[LINK]
