"""Constants pulled directly from support-policy.pdf and the client brief.

Every number here traces to a specific policy section or an explicit
assignment instruction -- nothing here is invented.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
VALIDATION_DIR = PROJECT_ROOT / "validation"

TICKETS_CSV = DATA_DIR / "tickets.csv"
ORDERS_CSV = DATA_DIR / "orders.csv"
CUSTOMERS_CSV = DATA_DIR / "customers.csv"
PRODUCTS_CSV = DATA_DIR / "products.csv"
AGENTS_CSV = DATA_DIR / "agents.csv"

# --- support-policy.pdf Section 5: Refunds, replacements and reason codes ---
GOODWILL_CAP_INR = 500  # goodwill credits >Rs 500 require Team Lead approval
REFUND_REASON_CODES = [
    "GW-OTHER", "DOA-REPL", "LOST-TRANSIT", "DUP-PAYMENT",
    "CANCEL", "PRICE-ADJ", "RETURN-QC-OK", "WTY-BUYBACK",
]
# GW-OTHER is the dropdown's first/default option (per Sameer's email) --
# the reason code most likely to be picked lazily rather than accurately.
DEFAULT_DROPDOWN_CODE = "GW-OTHER"

# Categories the classifier may re-code a GW-OTHER ticket into.
# The first 7 mirror the real dropdown; TRUE-GOODWILL and AMBIGUOUS are ours.
CLASSIFICATION_LABELS = [
    "DOA-REPL", "LOST-TRANSIT", "DUP-PAYMENT", "CANCEL",
    "PRICE-ADJ", "RETURN-QC-OK", "WTY-BUYBACK",
    "TRUE-GOODWILL",  # genuinely discretionary, no other code fits
    "AMBIGUOUS",       # not enough information in the text to tell
]

# --- support-policy.pdf Section 9: Systems and timestamps ---
# The legacy Freshdesk export stores refund_amount_inr in paise; the current
# helpdesk stores rupees. Confirmed empirically: every ticket_id that shows
# up under both source systems has legacy_fd amount == helpdesk amount x 100
# (n=125 exact matches, std dev 0). See DECISIONS.md.
LEGACY_SOURCE_SYSTEM = "legacy_fd"
LEGACY_CURRENCY_DIVISOR = 100.0
HELPDESK_GO_LIVE_DATE = "2025-09-14"

# --- Client volume assumption (client brief) ---
CLIENT_TICKETS_PER_WEEK = 650
CLIENT_TICKETS_PER_MONTH = CLIENT_TICKETS_PER_WEEK * 52 / 12  # ~2816.7

# --- Groq LLM classifier ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-20b"  # cheapest published self-serve production
# model on Groq as of Sep 2026: $0.075 / 1M input tokens, $0.30 / 1M output
# tokens (console.groq.com/docs/models). llama-3.1-8b-instant is now
# enterprise/contact-sales only and has no public per-token rate.
GROQ_PRICE_PER_1M_INPUT = 0.075
GROQ_PRICE_PER_1M_OUTPUT = 0.30

# Approval-language proxy used to flag GW-OTHER>cap tickets with no visible
# sign-off in the closing note. This is a heuristic, not proof either way --
# documented as a limitation.
APPROVAL_KEYWORDS_REGEX = r"\bTL\b|team lead|approv"
