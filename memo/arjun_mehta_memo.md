**To:** Arjun Mehta, Finance Controller
**From:** [Your name], Vireo Audio Support Analytics Review
**Date:** [DATE]
**Subject:** Refund Review -- why the numbers disagreed, and what refunds actually look like

## Executive finding

Your export and the helpdesk's own report disagreed because of a unit
bug, not a reporting error on either side: the old support system
(retired mid-September 2025) recorded refund amounts in paise, the new
one records them in rupees, and 3,874 old tickets were carried into every
export still labeled in the old unit. Correcting that single bug, and
removing 638 tickets that got counted twice during the system migration,
brings the number in line with the helpdesk's own figure: refunds ran
**~Rs [X] lakh per quarter**, not "well over a crore."

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

- **[Y]%** of refund value is ordinary, policy-covered activity: duplicate
  payments, pre-dispatch cancellations, failed deliveries, dead-on-arrival
  units, and processed returns.
- **[Z]%** is genuinely discretionary goodwill, and of that, most exceeds
  the Rs 500 threshold that's supposed to require a Team Lead's sign-off,
  with no note in the ticket confirming that sign-off happened.

## Agent-level pattern

Returns Desk agents show the highest refund rates -- expected and by
design, since your policy has that team process the large majority of
refunds. The more useful signal is how often an agent defaults to the
lazy "Goodwill/Other" tag instead of the correct one: that varies
agent-to-agent even within the same team, which points to a training/UI
issue (the dropdown itself) more than individual judgment. We've listed
specific agents worth a coaching conversation in the attached detail, not
because they're doing anything wrong, but because they're an easy fix for
data quality.

## Potential leakage

**Rs [Z-amount]/quarter** in refunds is goodwill, over the Rs 500 cap,
with no approval note on file. This is not proof of unauthorized
spending -- approval may simply not be written down -- but it's the
number worth checking against whatever sign-off process actually exists
today.

## Business goal

Reduce potentially-avoidable goodwill leakage from **[Z]%** of refund
value to a materially lower level by (a) fixing the dropdown default so
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
manually-reviewed sample (see attached validation summary: **[N]%
accuracy on [n] tickets**). It will occasionally miscategorize an
ambiguous or very short message -- those cases are flagged for human
review rather than reported as fact. "No approval note" means exactly
that, not "no approval happened."
