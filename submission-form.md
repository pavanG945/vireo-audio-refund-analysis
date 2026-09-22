# Submission Form -- Vireo Audio Support Tickets (Set C)

## What did you build, and what business outcome does it move?

A Python CLI that fixes two real data bugs (a currency-unit mismatch
inflating legacy refund amounts 100x, and 638 duplicate tickets from a
system migration), reclassifies the refund-reason dropdown's overused
default option using an LLM, and produces monthly/reason/agent refund
views plus a "potentially avoidable" leakage figure.

Business outcome: currency-correcting and deduping alone resolves the
Arjun-vs-Sameer dispute (helpdesk's ~Rs 11 lakh/quarter figure was right;
Arjun's export was reading legacy paise values as rupees -- corrected
total is Rs 11.18 lakh/quarter, matching Sameer's figure almost exactly).
Beyond that, the tool identifies **Rs 1.56 lakh/quarter (14.0% of refund
value)** in goodwill refunds over the policy's Rs 500 cap with no approval
note on file -- a concrete, actionable number for the board pack.

## What does one run cost, and what would a month cost at Vireo's volume?

One run classifies every `GW-OTHER`-tagged ticket (the reason code that
needed reclassification) using Groq's `openai/gpt-oss-20b`
($0.075/1M input tokens, $0.30/1M output tokens as of Sep 2026 --
`llama-3.1-8b-instant` moved to enterprise/contact-sales pricing and has
no public rate anymore).

**This run**: 118 tickets classified via LLM, 873 via the zero-cost
keyword fallback (used when no key is set, a call fails, or -- as
happened here -- the API key's rate limit is hit partway through; see
`AI_USAGE.md`). Logged cost: **$0.0088** (see `output/executive_summary.md`).

**Per-ticket cost** (LLM path): $0.0088 / 118 = **$0.0000746/ticket**
(~450-500 prompt tokens + ~100-400 completion tokens -- this is a
reasoning model, so its hidden chain-of-thought counts as completion
tokens).

**Monthly volume**: 650 tickets/week x 52/12 = **2,816.7 tickets/month**.
GW-OTHER made up 991 of 11,600 tickets in our 18-month sample = **8.5% of
all tickets**. Applying that rate: 2,816.7 x 0.0854 ~= **241 GW-OTHER
tickets/month** needing classification.

**Estimated monthly cost**: 241 x $0.0000746 ~= **$0.018/month**
(~Rs 1.51/month at ~Rs 84/$1) if every GW-OTHER ticket goes through the
LLM with no rate-limit interruption. Effectively free at this volume
either way. If Vireo's dropdown default were fixed (see `DECISIONS.md`
recommendation), this ongoing cost would shrink further as fewer tickets
need reclassification at all.

## How do you know it works?

- **Sample**: 120 GW-OTHER tickets, stratified across the classifier's 9
  possible output labels (13-15 each) so rare categories aren't drowned
  out by common ones (see `validation/run_validation.py:build_sample`).
- **Method**: manually read each ticket's `customer_message` and
  `agent_notes` and judged whether the tool's label matched what actually
  happened, blind to the tool's confidence score.
- **Accuracy**: **77.5%** (93/120) -- see `validation/validation_summary.md`.
  Broken down by source: LLM-classified tickets 69.7% (23/33),
  keyword-fallback tickets 80.5% (70/87).
- **Where it gets it wrong** (full detail in `validation/validation_summary.md`):
  (1) the LLM over-hedges to "AMBIGUOUS" -- 10 of 13 AMBIGUOUS predictions
  were actually wrong, on tickets with a clear signal in the text; (2) the
  keyword fallback's default bucket (used when no rule matches) is
  unreliable -- 13 of 15 sampled TRUE-GOODWILL predictions were wrong,
  mostly paraphrased versions of other categories (e.g. "no order
  confirmation" instead of the literal phrase "no order was created") or
  hardware/connectivity defects with no keyword category at all; (3) a
  keyword-rule ordering bug misclassifies some return-pickup tickets as
  LOST-TRANSIT because "courier" is checked before "pickup."

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
- LLM classification was rate-limited mid-project (see `AI_USAGE.md`); 873
  of 991 GW-OTHER tickets are classified by keyword fallback rather than
  the LLM. Validation shows this concretely costs accuracy: the fallback's
  default "no keyword matched" bucket was only 13% accurate in our sample
  (2/15) -- see `validation/validation_summary.md`. This is the single
  biggest known accuracy gap in what we're handing over.
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
