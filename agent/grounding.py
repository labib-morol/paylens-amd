"""Deterministic Numeric Grounding Verification and Templating Engine for PayLens.

Architecture Rule 2: GROUNDING CHECK.
Every number in the LLM's English or multilingual output must be regex-extracted
and verified against tool results and allowed card numbers.
If a mismatch occurs, retry once with an explicit error prompt, then fall back
to a deterministic template to maintain mathematical integrity.
"""

import re
from typing import Dict, List, Tuple
from engine.schema import RecommendationCard, RecommendationType, LeakSubType

BENGALI_TO_ASCII = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def _normalize_text(text: str) -> str:
    """Translate Bengali digits and normalize thousands and lakh formatting."""
    translated = text.translate(BENGALI_TO_ASCII)
    # Remove commas between digits for Western (12,500) and South Asian / Lakh (1,25,000)
    cleaned = re.sub(r"(?<=\d),(?=\d)", "", translated)
    return cleaned


def extract_numbers_from_text(text: str) -> List[float]:
    """Extract financial and quantitative numbers from text while stripping incidental prose numbers.

    Strips before extraction:
    - Entity identifiers (e.g., ORD-1042, SKU-LUM-01, MERCH_02, PAY-123, SET-456, CONS-789, TXN-999)
    - Phone numbers (+1-415-..., +88017..., etc.)
    - ISO dates (e.g. 2026-10-17, 2026-10-15T12:00:00, 15/10/2026, 2026-10-15)
    - Timestamps (e.g. 14:30, 2:30pm, 09:15:00)
    - Standalone list bullets (e.g., '1.', '2.', '#1', '1)')
    - Prose timeframes (e.g., '24 hours', '48 hours', '7 days', '14 days', '30 days')
    - Currency symbols ($ and ৳, etc.) and currency words
    """
    if not text:
        return []

    normalized = _normalize_text(text)

    # 1. Mask out entity identifiers (e.g., ORD-1042, SKU-LUM-01, MERCH_02, PAY-123, SET-456, CONS-789)
    masked = re.sub(
        r"\b(ORD|SKU|CONS|CARD|MERCH|RP|TXN|SETTLE|SET|PAY|REF|WIRE|PAYPAL|STRIPE|INJ|INV|CUST)[A-Za-z0-9_-]*\b",
        " ",
        normalized,
        flags=re.IGNORECASE,
    )
    # Mask general alphanumeric codes with embedded dashes/underscores (e.g., ORD-1042, SKU-01)
    masked = re.sub(r"\b[A-Za-z]{2,}[-_][A-Za-z0-9_-]+\b", " ", masked)

    # 2. Mask out phone numbers (+1-415-..., +88017..., etc.)
    masked = re.sub(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", " ", masked)
    masked = re.sub(r"\b(?:\+?880)?1[3-9]\d{8}\b", " ", masked)

    # 3. Mask out ISO dates and common date formats (e.g. 2026-10-17, 2026-09-16T12:00:00, 15/10/2026)
    masked = re.sub(r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?)?\b", " ", masked)
    masked = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", " ", masked)

    # 4. Mask out timestamps and times of day (e.g. 14:30, 2:30pm, 09:15:00)
    masked = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:am|pm|AM|PM)?\b", " ", masked)

    # 5. Mask out prose timeframes (e.g. 24 hours, 7 days, 30 days, 48 hrs, 14 days)
    masked = re.sub(
        r"\b\d+\s*(?:hours?|hrs?|days?|weeks?|months?|minutes?|mins?|seconds?|secs?)\b",
        " ",
        masked,
        flags=re.IGNORECASE,
    )

    # 6. Mask out standalone list bullets (e.g., '1.', '2.', '#1', '1)')
    masked = re.sub(r"(?:^|\n|\s)#?\d+[\.\)]\s+", " ", masked)
    masked = re.sub(r"\b\d+\.\s+", " ", masked)

    # 7. Mask out currency symbols and currency words
    masked = re.sub(r"[\$\৳€£₹]", " ", masked)
    masked = re.sub(r"\b(usd|dollars|dollar|cents|taka|tk|bdt|inr|eur|gbp)\b", " ", masked, flags=re.IGNORECASE)

    # 8. Extract all remaining numbers (floats or integers)
    number_tokens = re.findall(r"\b\d+(?:\.\d+)?\b", masked)
    return [float(token) for token in number_tokens]


def verify_numeric_grounding(
    text: str,
    allowed_numbers: List[float],
    tolerance: float = 0.05,
) -> Tuple[bool, List[float]]:
    """Extract and verify all numbers in text against allowed_numbers.

    Strips currency symbols ($ and ৳), commas, ignores leading list numbering,
    entity IDs, dates, times, phone numbers, and validates every extracted number
    against allowed numbers (including percentages e.g. 0.35 -> 35% and unit multiples).
    """
    if not text:
        return True, []

    number_tokens = extract_numbers_from_text(text)
    ungrounded: List[float] = []

    for val in number_tokens:
        # Check if val matches any allowed number
        is_match = False
        for allowed in allowed_numbers:
            # Direct match within absolute tolerance
            if abs(val - allowed) <= tolerance:
                is_match = True
                break
            # Relative tolerance for large values (0.5%)
            if allowed != 0 and abs(val - allowed) / abs(allowed) <= 0.005:
                is_match = True
                break
            # Percentage match (e.g., 0.35 allowed -> 35 in text or vice-versa)
            if abs(val - (allowed * 100.0)) <= tolerance:
                is_match = True
                break
            if abs((val / 100.0) - allowed) <= tolerance:
                is_match = True
                break

        if not is_match:
            ungrounded.append(val)

    is_grounded = len(ungrounded) == 0
    return is_grounded, ungrounded


def build_fallback_template(card: RecommendationCard, tone: str = "Polite Payment Reminder") -> Dict[str, str]:
    """Generate grounded deterministic explanation and action drafts strictly from card fields."""
    impact = card.impact_usd
    entity = card.entity_id
    m_name = card.merchant_name

    # If tone is VIP 5% discount, pre-compute values in code and whitelist them
    if tone == "VIP 5% Instant-Pay Discount":
        discount_amount = round(impact * 0.95, 2)
        savings_amount = round(impact * 0.05, 2)
        for num in [discount_amount, savings_amount, 5.0, 0.05]:
            if num not in card.allowed_numbers:
                card.allowed_numbers.append(num)

    if card.rec_type == RecommendationType.PAYMENT_LEAKAGE:
        if card.leak_sub_type == LeakSubType.DISPATCHED_UNPAID:
            if tone == "VIP 5% Instant-Pay Discount":
                discount_amount = round(impact * 0.95, 2)
                explanation_en = (
                    f"Audit for {m_name}: Order #{entity} was fulfilled and marked dispatched without verified gateway settlement. "
                    f"Total uncollected capital at risk is ${impact:,.2f}."
                )
                action_en = (
                    f"Priority VIP Settlement Offer: Order #{entity} was dispatched with an uncollected balance of ${impact:,.2f}. "
                    f"Pay ${discount_amount:,.2f} today (5% instant discount applied) via your secure checkout link to verify fulfillment."
                )
            else:
                explanation_en = (
                    f"Reconciliation Alert for {m_name}: Dispatched order #{entity} has no matching "
                    f"settlement record in payment logs. Outstanding uncollected balance is ${impact:,.2f}."
                )
                action_en = (
                    f"Payment Follow-up: Order #{entity} shows an outstanding uncollected balance of ${impact:,.2f}. "
                    f"Please confirm your payment method or update checkout details."
                )

        else:  # SETTLEMENT_SHORTFALL
            explanation_en = (
                f"Carrier Remittance Discrepancy for {m_name}: Carrier consignment #{entity} payout was undersettled. "
                f"Recoverable carrier dispute shortfall is ${impact:,.2f}."
            )
            action_en = (
                f"Carrier Claim Notice: Consignment #{entity} settlement statement reflects an underpaid discrepancy of ${impact:,.2f}. "
                f"Prompt remittance credit adjustment is requested under standard merchant service agreement."
            )

    elif card.rec_type == RecommendationType.FAILED_PAYMENT_RECOVERY:
        explanation_en = (
            f"Checkout Drop-Off Alert for {m_name}: Order #{entity} was abandoned at gateway checkout. "
            f"Modeled recoverable revenue at current recovery rate is ${impact:,.2f}."
        )
        action_en = (
            f"Cart Recovery Prompt: We noticed your checkout for order #{entity} was interrupted. "
            f"Your saved items valued at ${impact:,.2f} are reserved. Click to resume payment."
        )

    else:  # STOCKOUT_RISK
        explanation_en = (
            f"Inventory Run-Out Surge Alert for {m_name}: Demand acceleration detected for SKU {entity}. "
            f"Holt-Winters statistical forecasting projects ${impact:,.2f} in lost gross margin before supplier restock."
        )
        action_en = (
            f"Expedited Purchase Order: Accelerated demand on SKU {entity} risks stockout with ${impact:,.2f} "
            f"in gross margin exposed. Issue expedited supplier purchase order immediately."
        )

    return {
        "explanation_en": explanation_en,
        "action_draft_en": action_en,
        "explanation_bn": explanation_en,
        "action_draft_bn": action_en,
    }
