**To:** Arjun Mehta, Finance Controller
**From:** Pavan Gembali, Vireo Audio Support Analytics Review
**Date:** 22 September 2026
**Subject:** Refund Review -- why the numbers disagreed, and what refunds actually look like

## Executive finding

Your export and the helpdesk's own report disagreed because of a unit
bug, not a reporting error on either side: the old support system
(retired mid-September 2025) recorded refund amounts in paise, the new
one records them in rupees, and 3,874 old tickets were carried into every
export still labeled in the old unit. Correcting that single bug, and
removing 638 tickets that got counted twice during the system migration,
brings the number in line with the helpdesk's own figure: refunds ran
**~Rs 11.2 lakh per quarter** (Rs 67.1 lakh over the 18 months of data we
had), not "well over a crore."

## Monthly trend

Refunds have risen gradually -- from about 19% of tickets in early 2025
to roughly 21-23% by mid-2026. This lines up with Priya's team's Q4 2025
decision to stop contesting refund requests at the frontline; we did not
see the CSAT improvement she cited clearly in the data, which is worth a
separate look but doesn't change the refund picture.

## Main refund reasons

The dropdown agents use to tag a refund's reason defaults to "Goodwill /
Other" -- and because it's the first option, it gets picked out of
convenience far more often than it reflects an actual goodwill decision.
We re-read the underlying customer messages and agent notes for every
such ticket and re-sorted them into what actually happened. After that
correction:

- **82%** of refund value is ordinary, policy-covered activity: duplicate
  payments, pre-dispatch cancellations, failed deliveries, dead-on-arrival
  units, warranty issues, and processed returns.
- **17%** is genuinely discretionary goodwill (Rs 11.3 lakh over the
  period), and of that, **83%** exceeds the Rs 500 threshold that's
  supposed to require a Team Lead's sign-off, with no note in the ticket
  confirming that sign-off happened.

## Agent-level pattern

Returns Desk agents show the highest refund rates (up to ~53%) --
expected and by design, since your policy has that team process the
large majority of refunds. The more useful signal is how often an agent
defaults to the lazy "Goodwill/Other" tag instead of the correct one:
company-wide it's about 42% of an agent's refunds, but ranges from under
15% to as high as 63% agent-to-agent, even within the same team. That
spread points to a training/UI issue (the dropdown itself) more than
individual judgment. `output/agent_refunds.csv` has the full per-agent
breakdown if a coaching conversation is useful -- flagged as a data-quality
opportunity, not a performance issue.

## Potential leakage

**Rs 1.56 lakh/quarter** (Rs 9.38 lakh over the period) in refunds is
goodwill, over the Rs 500 cap, with no approval note on file -- **14% of
all refund value**. This is not proof of unauthorized spending -- approval
may simply not be written down -- but it's the number worth checking
against whatever sign-off process actually exists today.

## Business goal

Reduce potentially-avoidable goodwill leakage from **14% of refund
value** to a materially lower level by (a) fixing the dropdown default so
GW-OTHER stops being the path of least resistance, and (b) requiring the
approval note itself to be a mandatory field above Rs 500, so the check
we're running today becomes automatic.

## Recommended next action

1. Reorder or require a selection in the reason-code dropdown so
   "Goodwill/Other" is no longer the default.
2. Make Team Lead approval a required, timestamped field above Rs 500,
   not a note left to an agent's discretion to write down.
3. Re-run this analysis monthly against the live export rather than a
   one-time snapshot -- happy to hand over the tool for that.

## Limitations and uncertainty

This analysis re-reads free text with an AI classifier, checked against a
manually-reviewed sample of 120 tickets (see `validation/validation_summary.md`):
**77.5% accuracy** overall. It most often gets things wrong on very short
or ambiguous messages, and on tickets phrased in ways our rule-based
fallback didn't anticipate -- both are documented in detail in the
validation summary, along with two specific, fixable causes we found.
"No approval note" means exactly that, not "no approval happened."
