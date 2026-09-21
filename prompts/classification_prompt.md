# GW-OTHER reclassification prompt

## Why this exists

`GW-OTHER` ("Goodwill / Other") is the first option in the refund-reason
dropdown (per Sameer's email) and accounts for 43% of refund value in the
data -- far more than a real goodwill program would suggest. Reading the
free text shows most of these are legitimate refunds (duplicate payments,
cancellations, DOA, connectivity/warranty issues) that got tagged with the
default option instead of the correct one. This prompt re-reads the two
free-text fields on every `GW-OTHER` ticket and assigns the reason code the
agent should have picked.

## Privacy minimization

Before sending to the API, `customer_message` and `agent_notes` are passed
through a light redaction pass (`classification.py:_redact`) that masks
phone-number-like digit sequences and email addresses. No customer_id,
name, or order_id is ever included in the prompt -- the model only sees the
two free-text fields plus the ticket's category tag and refund amount.

## System prompt

```
You are classifying a customer-support refund ticket for Vireo Audio, a
consumer-audio company. The agent tagged this refund with the dropdown's
default/first option, "GW-OTHER" (Goodwill / Other), which is often picked
out of convenience rather than accuracy. Read the customer's message and
the agent's closing note, and decide which of the following categories the
ticket actually belongs to:

- DOA-REPL: product was dead/faulty on arrival (within ~7 days of delivery)
- LOST-TRANSIT: item lost, undelivered, or stuck in transit
- DUP-PAYMENT: duplicate charge, failed payment still charged, billing error
- CANCEL: order cancelled before dispatch
- PRICE-ADJ: coupon/discount/price adjustment
- RETURN-QC-OK: a return was picked up and passed quality check
- WTY-BUYBACK: in-warranty hardware fault leading to a buy-back/replacement
- TRUE-GOODWILL: no specific policy reason applies; a discretionary goodwill
  gesture (e.g. an apology credit, a delay with no product/payment fault)
- AMBIGUOUS: the text does not contain enough information to tell

Respond with ONLY a JSON object, no other text:
{"label": "<one of the 9 categories above, exact spelling>",
 "confidence": <float 0.0-1.0>,
 "evidence": "<one short phrase from the text that supports this label>"}
```

## User prompt template

```
Category tag: {category}
Refund amount: Rs {amount}
Customer message: "{customer_message}"
Agent closing note: "{agent_notes}"
```

## Model and parameters

- Provider: Groq (`https://api.groq.com/openai/v1/chat/completions`)
- Model: `openai/gpt-oss-20b` (cheapest published self-serve production
  model on Groq as of Sep 2026 -- `llama-3.1-8b-instant` moved to
  enterprise/contact-sales pricing and no longer has a public rate)
- `temperature`: 0 (deterministic, reproducible classification)
- `reasoning_effort`: `low` -- gpt-oss-20b is a reasoning model and emits a
  hidden chain-of-thought before the JSON; without this it sometimes burns
  the whole token budget on reasoning and returns no content, which the
  code treats as a failure and falls back to keyword rules.
- `response_format`: `{"type": "json_object"}`
- `max_tokens`: 500 (reasoning + JSON both count against this)

## Validation and fallback

Every response is checked against the allowed label list and confidence
range; a malformed or missing response falls back to the deterministic
keyword rules in `classification.py:_keyword_fallback`. Results are cached
to `output/classification_cache.json` by `ticket_id` so re-running the
pipeline doesn't re-spend on tickets already classified.
