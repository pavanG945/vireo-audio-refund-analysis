# Validation Summary

## Method

120 GW-OTHER tickets, stratified across the tool's 9 possible output
labels (13-15 per label) so rare labels aren't drowned out by common ones
(`validation/run_validation.py build`, seed 42). Each ticket's
`customer_message` and `agent_notes` were read manually and compared
against the tool's predicted label, blind to the tool's confidence score.
Reviewed by Claude (acting as the manual reviewer) rather than an
independent human -- see `AI_USAGE.md` for why, and treat this as an
AI-assisted sanity check rather than a fully independent audit.

## Headline

**Accuracy: 77.5% (93/120).**

**By classification source** (this matters more than the flat number):
- LLM-classified (33 tickets): **69.7%** (23/33)
- Keyword-fallback-classified (87 tickets): **80.5%** (70/87)

The keyword fallback outperforming the LLM here is specific to *this*
sample's composition, not a general claim that rules beat LLMs -- see
below.

## Where it gets things wrong

**1. The LLM over-hedges to AMBIGUOUS (10 of 13 AMBIGUOUS predictions were
wrong).** All 13 AMBIGUOUS-labeled tickets in the sample came from the
LLM. On manual review, 10 of them had a clear signal in the text the
model didn't act on -- e.g. two tickets with the identical phrase "the
parcel looked like it was kicked here from the warehouse, and the unit
has a crack" were labeled AMBIGUOUS, while three *other* tickets with
that exact same phrase elsewhere in the sample were correctly labeled
DOA-REPL. Similarly, three tickets containing the customer's own words
"for the return" were marked AMBIGUOUS instead of RETURN-QC-OK. This
looks like the model hedging under `reasoning_effort: low` rather than a
genuine information gap -- worth revisiting with a higher reasoning
effort or a lower AMBIGUOUS threshold if this classifier is used going
forward.

**2. The keyword fallback's default bucket (TRUE-GOODWILL, used when no
rule matches) is unreliable: 13 of 15 sampled were wrong.** This is the
single biggest error source in the whole sample, and it's a direct
consequence of the rate-limit shortfall documented in `AI_USAGE.md` --
these are exactly the "no confident keyword" tickets that were supposed
to go through the LLM and mostly didn't. Sub-patterns:
   - **Paraphrased DUP-PAYMENT** (5 tickets): "no order confirmation" /
     "upi shows success, app shows nothing" / "page failed after i paid"
     all mean the same thing as "no order was created," the literal
     phrase the keyword rule checks for, but weren't matched.
   - **Hardware/connectivity defects with no keyword category at all**
     (6 tickets): charging-case failures, connectivity dropouts, and
     wrong-item-delivered have no representation in the keyword rule
     list, so they fall straight to "no specific reason" even when the
     agent's own note says "escalated to warranty."
   - **PRICE-ADJ phrased without "coupon/discount/promo"** (1 ticket):
     "your ad said 20% off and the cart says full price" is a price
     complaint, just not in the three words the rule checks for.
   - **Genuinely closer to AMBIGUOUS than TRUE-GOODWILL** (1 ticket): a
     refund-delay ticket referencing a declined replacement offer implies
     a real prior issue, not "no reason."

**3. A keyword-ordering bug in LOST-TRANSIT vs RETURN-QC-OK** (4 of 13
LOST-TRANSIT predictions wrong, all from the same cause). The keyword
rules check LOST-TRANSIT's list (which includes "courier") before
RETURN-QC-OK's list (which includes "pickup"). Several tickets about a
missed *return* pickup happen to also mention "courier" ("re-raised
pickup with courier"), so they get caught by the earlier, wrong rule
before the correct one is ever checked.

**4. One false-positive keyword collision**: a ticket about a
microphone quality issue ("everyone on my calls says I sound like I'm
underwater... low mic pickup") got matched to RETURN-QC-OK because the
word "pickup" appears -- in "mic pickup," an audio term, not a parcel
pickup.

## What worked well

CANCEL, DUP-PAYMENT (when phrased with the exact expected words),
PRICE-ADJ (when phrased with "coupon/discount/promo"), DOA-REPL, and
WTY-BUYBACK were all 100% or near-100% accurate in this sample --
14/14, 13/13, 13/13, 13/13, and 13/13 respectively. These are cases where
either the agent's own note used unambiguous internal shorthand ("under
doa," "esc to wty") or the customer's phrasing matched the keyword list
closely.

## Practical takeaway

If this tool is used beyond a one-off analysis, the two highest-value
fixes are: (1) reorder the keyword rules so "pickup" is checked before
"courier," and expand the DUP-PAYMENT/PRICE-ADJ keyword lists with the
paraphrases found here, and (2) either raise the reasoning budget for the
LLM path or add a second-pass LLM call specifically for tickets the model
first calls AMBIGUOUS, since that label was wrong three times more often
than it was right.
