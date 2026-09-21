# Decisions

## 1. Client request

Arjun Mehta (Finance Controller) asked for a monthly refund summary by
reason code and by agent, reconciled against his own export which sums to
"well over a crore a quarter" -- a number he doesn't trust.

## 2. What we built

A single Python CLI (`python -m src.main`) that: loads the five supplied
CSVs, fixes two concrete data-quality bugs, reclassifies the dropdown's
default reason code from free text (LLM + keyword fallback), applies three
deterministic policy checks, and writes board-ready CSVs plus an executive
summary. No UI, no database, no ML training.

## 3. What we narrowed or pushed back on

- **The ask was "refunds by reason code and agent." We didn't stop there.**
  Reading the data showed the reason codes themselves are unreliable
  (GW-OTHER is the dropdown default and catches ~43% of refund value), so
  a straight pivot table on the raw `refund_reason_code` column would have
  handed Arjun a technically-correct but substantively misleading report.
  We added a reclassification step before the pivot. This is scope we
  added, not scope the client asked for -- justified because it directly
  serves the stated goal ("who is giving away money and for what").
- **We did not try to resolve Arjun-vs-Sameer by picking a side.** Instead
  we found the actual mechanism (paise vs rupees) that produces both
  numbers, so the report is self-explanatory rather than another
  disputable export.
- **We did not investigate handle-time, SLA breach, or CSAT metrics**,
  even though the policy PDF defines them in detail and Priya's email
  invited a CSAT discussion. The brief asked for a refund summary; scope
  creep into support-ops KPIs would have used the 5-hour budget on
  something nobody asked for. (We did check Priya's CSAT claim in passing
  since it bears on refund trend interpretation -- see memo.)
- **We did not name or accuse any agent of misconduct.** The tool flags
  "goodwill over cap, no approval note" and "refund + replacement both
  issued" as *review candidates* with the underlying evidence attached,
  not verdicts. Section 5 of the policy explicitly requires escalation to
  a Team Lead for that second case -- we treat that as the client's
  process to run, not ours.

## 4. What we deliberately left out, and why

- **Streamlit/web UI.** The deliverable is a set of CSVs a Finance
  Controller drops into a board pack; a dashboard adds build time without
  adding analytical value here.
- **SQLite or any database.** Five CSVs, largest ~12k rows, fit in memory.
  A database would be pure ceremony.
- **Training a classifier.** A prompt against an LLM, with keyword rules
  as a zero-cost fallback, is more reliable in a 5-hour budget than
  labeling training data and fitting a model, and is transparent
  (evidence string per decision) in a way a trained classifier isn't.
- **Reconciling legacy resolved_at timestamps (UTC vs IST, Section 9).**
  This affects handle-time metrics, not refund amounts, which is what
  Arjun asked about. Flagged as a limitation, not fixed.
- **A from-scratch fraud/anomaly-detection model on agent behavior.** The
  data supports rate and amount comparisons, not intent. Policy Section 6
  already tells us Returns Desk *should* have the highest refund rate --
  building a model that flagged them anyway would have been actively
  wrong, not just unnecessary.

## 5. The two data bugs, and how we know

**Currency**: `legacy_fd` (pre-14-Sep-2025 tickets, migrated from
Freshdesk) stores `refund_amount_inr` in paise; the current helpdesk
stores rupees. Evidence: ticket `TK-240429` appears once under each
source system (a re-imported duplicate) with amounts Rs 2,124 (helpdesk)
and Rs 212,400 (legacy_fd) for the same ticket -- exactly 100x. Checked
across all 125 duplicate tickets that have a refund amount on both rows:
the ratio is exactly 100.0 in every case, std dev 0. Fix: divide
`legacy_fd` amounts by 100 (`src/data_cleaning.py:correct_currency`).

**Duplication**: 638 of 12,238 ticket rows are re-imported duplicates,
100% of them appearing under both `helpdesk` and `legacy_fd` for the same
`ticket_id` (never duplicated within one source system). Fix: keep the
`helpdesk` row when both exist, since Section 9 names it the live,
reconciled system (`src/data_cleaning.py:deduplicate_tickets`).

After both fixes: total refund value is ~Rs 11.18 lakh/quarter, which
matches Sameer's cited "helpdesk report says ~Rs 11 lakh a quarter" almost
exactly. This is strong evidence the correction is right, not just
plausible.

## 6. Choices with no clearly "correct" answer

- **On a duplicate ticket, we keep the helpdesk row entirely** (all
  fields, not just the amount) rather than merging fields from both. Risk:
  if the legacy and helpdesk rows ever disagree on a non-money field
  (e.g. `agent_id`), we silently take the helpdesk version. We did not
  find a case where this happened, but didn't exhaustively check every
  column.
- **Minimum ticket volume for agent comparison: 30 tickets** over the
  18-month window (~1.7/week). Below this, refund-rate swings are mostly
  noise. This threshold is a judgment call, not derived from the data.
- **"Potentially avoidable" = reclassified as TRUE-GOODWILL AND >Rs 500
  cap AND no TL/approval keyword in the closing note.** The last condition
  is a text-matching heuristic, not proof of an approval workflow gap --
  agents may get sign-off verbally or in a system we don't see. We
  disclose this explicitly rather than presenting the bucket as certain.
- **Client-data privacy over full reproducibility in the public repo.**
  `data/` and `output/` are gitignored because they carry customer PII
  (names, cities, phone numbers customers typed into messages) and Vireo's
  confidential refund figures. The code is fully public and reproducible;
  the client's data is not, and is instead shared via the private Google
  Drive link this submission also requires.

## 7. Risks created by these decisions

- If Vireo's dropdown behavior or reason-code list changes, the keyword
  rules and LLM prompt (`prompts/classification_prompt.md`) will need
  updating -- they're tuned to the current 8 codes and this data's tone.
- The 30-ticket agent-volume threshold could hide a real problem in a
  newer or part-time agent with <30 tickets. Worth a manual look if
  headcount changes significantly.
- The "no approval keyword" heuristic will under-count leakage if TL
  approval happens outside the ticket notes, and over-count it if agents
  get approval but don't write it down. Section 5 requiring TL approval
  for >Rs 500 goodwill, with no system field to record it, is itself a
  process gap worth flagging to Priya/Neha independent of this tool.

## 8. What could be built next

- A lightweight approval-tracking field in the helpdesk so "no approval
  keyword in the notes" becomes "no approval record" -- removing that
  heuristic's biggest weakness.
- Extending the reclassification approach to categorize `category` (the
  intake-bot tag) the same way GW-OTHER is reclassified here, since
  Section 2 notes it's also bot-assigned and agent-corrected inconsistently.
- A monthly-refresh version of this script wired to the live helpdesk
  export, rather than a one-off run against a CSV snapshot.
