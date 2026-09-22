# 3-Minute Screen Recording Script

No slides. Screen capture of your terminal/editor/output files. Read
naturally, don't memorize word-for-word.

---

**0:00-0:20 -- Problem and objective**

"Vireo's Finance Controller had two conflicting refund numbers -- his own
export said over a crore a quarter, the helpdesk's own report said about
11 lakh. My job was to figure out why, and give him a monthly refund
breakdown by reason and agent he could actually trust."

*(Show: the client email thread on screen briefly)*

**0:20-0:50 -- Repository structure**

"Here's the project. `src/` has the pipeline -- data cleaning, policy
rules, an LLM classifier, and analysis. `data/` holds the client's CSVs,
which I've kept out of git since they contain customer PII. `validation/`
has the accuracy check, and `DECISIONS.md` documents every judgment call
I made."

*(Show: file tree, briefly open DECISIONS.md and scroll)*

**0:50-1:30 -- Run the tool**

"Let me run it." *(run `python -m src.main`)* "It loads the five CSVs,
corrects a currency bug I'll show you in a second, reclassifies about a
thousand tickets that got tagged with the dropdown's default 'goodwill'
option, and writes the output files."

*(Show: terminal output scrolling, then the final summary lines)*

**1:30-2:10 -- Show monthly/agent/reason output**

"Here's `refund_reasons.csv` -- after reclassification, goodwill drops
from being the largest bucket by a mile to a much smaller, more honest
number. Here's `agent_refunds.csv` -- Returns Desk shows the highest
refund rate, which is expected, they process most refunds by policy
design, so I excluded low-volume agents and flagged GW-OTHER overuse
instead, which is the fairer signal."

*(Show: open refund_reasons.csv and agent_refunds.csv, scroll through key
columns)*

**2:10-2:35 -- Show validation and error rate**

"I validated the reclassification against a manually-reviewed sample of
120 tickets, stratified across the possible labels. Accuracy came out to
77.5% -- here's where it gets things wrong: the LLM over-hedges to
'ambiguous' more than it should, and the keyword fallback's default
bucket -- for tickets no rule matches -- is the weakest part, only about
13% accurate on its own."

*(Show: validation_summary.md)*

**2:35-2:55 -- What changed between versions, what was discarded**

"Two things I'll be honest about: I first tried classifying with 8
parallel API calls, and got rate-limited into a fallback for most of the
tickets. I found the actual rate limit in the response headers, switched
to paced serial calls, and reprocessed just the ambiguous ones -- the
ones the keyword fallback couldn't confidently tag anyway. I also
discarded a first attempt at a small token budget that a reasoning model
burned entirely on its internal reasoning before it could answer."

*(Show: AI_USAGE.md "What was discarded" section)*

**2:55-3:00 -- Business outcome**

"Bottom line: refunds are really running about Rs 11.2 lakh a quarter, not
a crore, and about Rs 1.56 lakh a quarter of that is goodwill over the
approval cap with no sign-off on record -- that's the number I'd put in
front of the board."
