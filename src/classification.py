"""Reclassifies GW-OTHER tickets using their free-text fields.

Tries the Groq API first (see prompts/classification_prompt.md for the
exact prompt); falls back to deterministic keyword rules if no API key is
set, the call fails, or the response is malformed. Results are cached to
disk by ticket_id so re-runs don't re-spend on already-classified tickets.
"""
import json
import re
import time

import requests

from . import config

_PHONE_RE = re.compile(r"\b\d[\d\-\s]{7,}\d\b")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


class RateLimitError(Exception):
    def __init__(self, retry_after: float):
        self.retry_after = retry_after
        super().__init__(f"rate limited, retry after {retry_after}s")

SYSTEM_PROMPT = """You are classifying a customer-support refund ticket for Vireo Audio, a
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
 "evidence": "<one short phrase from the text that supports this label>"}"""


def _redact(text: str) -> str:
    text = _EMAIL_RE.sub("[email]", str(text))
    text = _PHONE_RE.sub("[phone]", text)
    return text


def _keyword_fallback(customer_message: str, agent_notes: str) -> dict:
    text = f"{customer_message} {agent_notes}".lower()
    rules = [
        ("DUP-PAYMENT", ["duplicate", "charged twice", "paid once", "statement disagrees",
                          "deducted twice", "paid twice", "no order was created", "duplicate txn",
                          "duplicate payment"]),
        ("CANCEL", ["cancel", "ordered by mistake", "before dispatch"]),
        ("LOST-TRANSIT", ["lost", "tracking", "not delivered", "courier", "out for delivery",
                            "stuck in transit", "undelivered"]),
        ("DOA-REPL", ["dead on arrival", "doa", "not working out of box", "defective on arrival"]),
        ("WTY-BUYBACK", ["warranty", "buyback", "buy-back", "in-warranty"]),
        ("PRICE-ADJ", ["coupon", "discount", "price adjustment", "promo code"]),
        ("RETURN-QC-OK", ["pickup", "return pickup", "reverse pickup", "qc", "quality check"]),
    ]
    for label, keywords in rules:
        if any(k in text for k in keywords):
            return {"label": label, "confidence": 0.6, "evidence": f"keyword match ({label})"}
    if len(text.strip()) < 15:
        return {"label": "AMBIGUOUS", "confidence": 0.3, "evidence": "message too short to classify"}
    return {"label": "TRUE-GOODWILL", "confidence": 0.4, "evidence": "no specific policy reason detected"}


def _call_groq(customer_message: str, agent_notes: str, category: str, amount: float) -> dict:
    if not config.GROQ_API_KEY:
        raise RuntimeError("no GROQ_API_KEY set")

    user_prompt = (
        f'Category tag: {category}\n'
        f'Refund amount: Rs {amount}\n'
        f'Customer message: "{_redact(customer_message)}"\n'
        f'Agent closing note: "{_redact(agent_notes)}"'
    )
    payload = {
        "model": config.GROQ_MODEL,
        "temperature": 0,
        "max_tokens": 500,
        "reasoning_effort": "low",
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {config.GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    resp = requests.post(config.GROQ_API_URL, headers=headers, json=payload, timeout=20)
    if resp.status_code == 429:
        retry_after = float(resp.headers.get("Retry-After", 10))
        raise RateLimitError(retry_after)
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usage", {})
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)

    if parsed.get("label") not in config.CLASSIFICATION_LABELS:
        raise ValueError(f"model returned unknown label: {parsed.get('label')!r}")
    conf = float(parsed.get("confidence", 0))
    if not (0.0 <= conf <= 1.0):
        raise ValueError(f"model returned out-of-range confidence: {conf!r}")

    return {
        "label": parsed["label"],
        "confidence": conf,
        "evidence": str(parsed.get("evidence", ""))[:200],
        "source": "llm",
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
    }


def classify_ticket(ticket_id: str, customer_message: str, agent_notes: str,
                     category: str, amount: float, cache: dict, max_retries: int = 4) -> dict:
    """Classify one ticket, using the cache if present."""
    if ticket_id in cache:
        return cache[ticket_id]

    result = None
    last_err = None
    for attempt in range(max_retries):
        try:
            result = _call_groq(customer_message, agent_notes, category, amount)
            break
        except RateLimitError as e:
            last_err = e
            time.sleep(min(e.retry_after, 20) + 1)
        except Exception as e:  # noqa: BLE001 -- any other failure falls back to rules
            last_err = e
            time.sleep(0.5 * (attempt + 1))

    if result is None:
        fallback = _keyword_fallback(customer_message, agent_notes)
        fallback.update({"source": "keyword_fallback", "prompt_tokens": 0, "completion_tokens": 0,
                          "fallback_reason": str(last_err) if last_err else "no API key set"})
        result = fallback

    cache[ticket_id] = result
    return result
