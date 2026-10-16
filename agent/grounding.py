"""Deterministic Numeric Grounding Verification and Templating Engine for PayLens Solo.

Architecture Rule 2: GROUNDING CHECK.
Every number in the LLM's English or multilingual output must be regex-extracted
and verified against tool results and allowed card numbers.
If a mismatch occurs, retry once with an explicit error prompt, then fall back
to a 100% deterministic template to guarantee zero hallucinations.
"""

import re
from typing import Dict, List, Tuple
from engine.schema import RecommendationCard, RecommendationType, LeakSubType

BENGALI_TO_ASCII = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def _normalize_text(text: str) -> str:
    """Translate Bengali digits and clean formatting."""
    translated = text.translate(BENGALI_TO_ASCII)
    # Remove commas between digits (e.g. 12,500 -> 12500)
    cleaned = re.sub(r"(?<=\d),(?=\d)", "", translated)
    return cleaned


def verify_numeric_grounding(
    text: str,
    allowed_numbers: List[float],
    tolerance: float = 0.05,
) -> Tuple[bool, List[float]]:
    """Extract and verify all numbers in text against allowed_numbers.

    Strips currency symbols ($ and ৳), commas, ignores leading list numbering
    and entity IDs, and checks each number against allowed numbers
    (including percentages e.g. 0.35 -> 35% and unit multiples).
    """
    if not text:
        return True, []

    normalized = _normalize_text(text)

    # 1. Mask out entity identifiers (e.g., ORD-1042, SKU-LUM-01, CONS-SHORT-9001, MERCH_02, TXN-12345, CARD-123)
    masked = re.sub(r"\b(ORD|SKU|CONS|CARD|MERCH|RP|TXN|SETTLE|REF|WIRE|PAYPAL|STRIPE)[A-Za-z0-9_-]*\b", " ", normalized, flags=re.IGNORECASE)

    # 2. Mask out phone numbers (+1-415-..., +88017..., etc.)
    masked = re.sub(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", " ", masked)
    masked = re.sub(r"\b(?:\+?880)?1[3-9]\d{8}\b", " ", masked)

    # 3. Mask out ISO dates and timestamps (e.g. 2026-10-15, 2026-09-16T12:00:00)
    masked = re.sub(r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2})?\b", " ", masked)

    # 4. Mask out list bullet numbers at line starts or standalone (e.g., "1. ", "2) ", "#1 ")
    masked = re.sub(r"(?:^|\n|\s)#?\d+[\.\)]\s+", " ", masked)

    # 5. Mask out currency symbols and words
    masked = re.sub(r"[\$\৳€£]", " ", masked)
    masked = re.sub(r"\b(usd|dollars|dollar|cents|taka|tk|bdt)\b", " ", masked, flags=re.IGNORECASE)

    # 6. Extract all remaining numbers (floats or integers)
    number_tokens = re.findall(r"\b\d+(?:\.\d+)?\b", masked)

    ungrounded: List[float] = []

    for token in number_tokens:
        val = float(token)

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
    """Generate 100% grounded deterministic explanation and action drafts strictly from card fields."""
    impact = card.impact_usd
    entity = card.entity_id
    m_name = card.merchant_name

    if card.rec_type == RecommendationType.PAYMENT_LEAKAGE:
        if card.leak_sub_type == LeakSubType.DISPATCHED_UNPAID:
            if tone == "VIP 5% Instant-Pay Discount":
                explanation_en = (
                    f"Audit for {m_name}: Order #{entity} was fulfilled and marked dispatched without verified gateway settlement. "
                    f"Total uncollected capital at risk is ${impact:,.2f}."
                )
                action_en = (
                    f"Priority Settlement Notice: Order #{entity} was dispatched with an uncollected balance of ${impact:,.2f}. "
                    f"Complete settlement today via your secure checkout link to verify fulfillment."
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
