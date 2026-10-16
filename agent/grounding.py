"""Deterministic Numeric Grounding Verification and Templating Engine for PayLens Solo.

Architecture Rule 2: GROUNDING CHECK.
Every number in the LLM's English or Bangla output must be regex-extracted
(converting Bengali digits ০১২৩৪৫৬৭৮৯ to ASCII) and verified against tool results.
If a mismatch occurs, retry once, then fall back to a deterministic template.
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

    Translates Bengali digits, strips currency symbols and commas,
    ignores leading list numbering and entity IDs, and checks each number
    against allowed numbers (including percentages and unit multiples).
    """
    if not text:
        return True, []

    normalized = _normalize_text(text)

    # 1. Mask out entity identifiers (e.g., ORD-1042, SKU-CAH-01, CONS-SHORT-8001, MERCH_02, TXN-12345, CARD-123)
    masked = re.sub(r"\b(ORD|SKU|CONS|CARD|MERCH|RP|TXN|SETTLE|REF)[A-Za-z0-9_-]*\b", " ", normalized)

    # 2. Mask out Bangladeshi phone numbers (+88017..., 017...)
    masked = re.sub(r"\b(?:\+?880)?1[3-9]\d{8}\b", " ", masked)

    # 3. Mask out ISO dates and timestamps (e.g. 2026-10-15, 2026-09-16T12:00:00)
    masked = re.sub(r"\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2})?\b", " ", masked)

    # 4. Mask out list bullet numbers at line starts or standalone (e.g., "1. ", "2) ", "#1 ")
    masked = re.sub(r"(?:^|\n|\s)#?\d+[\.\)]\s+", " ", masked)

    # 5. Mask out currency symbols and words
    masked = re.sub(r"[৳\$]", " ", masked)
    masked = re.sub(r"\b(taka|tk|bdt|bdt\.)\b", " ", masked, flags=re.IGNORECASE)

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
            # Relative tolerance for large values
            if allowed != 0 and abs(val - allowed) / abs(allowed) <= 0.01:
                is_match = True
                break
            # Percentage match (e.g., 0.35 allowed -> 35 in text)
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


def build_fallback_template(card: RecommendationCard, tone: str = "Polite Reminder") -> Dict[str, str]:
    """Generate 100% grounded deterministic explanation and action drafts strictly from card fields."""
    impact = card.impact_taka
    entity = card.entity_id
    m_name = card.merchant_name

    if card.rec_type == RecommendationType.PAYMENT_LEAKAGE:
        if card.leak_sub_type == LeakSubType.DISPATCHED_UNPAID:
            if tone == "VIP 5% Instant-Pay Discount":
                explanation_en = (
                    f"Audit for {m_name}: Order #{entity} was dispatched on digital rails without verified settlement. "
                    f"Total uncollected leakage amount is ৳{impact:,.2f}."
                )
                explanation_bn = (
                    f"{m_name} এর অডিট: ডিজিটাল মাধ্যমে প্রেরিত অর্ডার #{entity} এর কোনো পেমেন্ট রেকর্ড পাওয়া যায়নি। "
                    f"মোট অপরিশোধিত ক্ষতির পরিমাণ ৳{impact:,.2f} টাকা।"
                )
                action_en = (
                    f"Urgent Payment Request: Order #{entity} is marked dispatched with an uncollected balance of ৳{impact:,.2f}. "
                    f"Please settle immediately to verify delivery."
                )
                action_bn = (
                    f"জরুরি পেমেন্ট নোটিশ: অর্ডার #{entity} সরবরাহ করা হলেও ৳{impact:,.2f} টাকা বকেয়া রয়েছে। "
                    f"দয়া করে অবিলম্বে বকেয়া পরিশোধ করুন।"
                )
            else:
                explanation_en = (
                    f"Reconciliation Alert for {m_name}: Dispatched order #{entity} has no corresponding "
                    f"successful rail payment. Uncollected balance is ৳{impact:,.2f}."
                )
                explanation_bn = (
                    f"{m_name} এর জন্য রিকনসিলিয়েশন সতর্কতা: অর্ডার #{entity} ডেলিভারি হলেও কোনো পেমেন্ট পাওয়া যায়নি। "
                    f"বকেয়া পরিমাণ ৳{impact:,.2f} টাকা।"
                )
                action_en = (
                    f"Payment Follow-up: Order #{entity} shows an uncollected payment of ৳{impact:,.2f}. "
                    f"Kindly verify your payment status."
                )
                action_bn = (
                    f"পেমেন্ট অনুস্মারক: অর্ডার #{entity} এর অপরিশোধিত ৳{impact:,.2f} টাকা পরিশোধ নিশ্চিত করার জন্য অনুরোধ করা হচ্ছে।"
                )

        else:  # SETTLEMENT_SHORTFALL
            explanation_en = (
                f"Courier Shortfall Alert for {m_name}: Consignment #{entity} received undersettled payout. "
                f"Discrepancy shortfall is ৳{impact:,.2f}."
            )
            explanation_bn = (
                f"{m_name} এর কুরিয়ার হিসাব অমিল: কনসাইনমেন্ট #{entity} এ প্রত্যাশিত টাকার চেয়ে কম পরিশোধ করা হয়েছে। "
                f"ঘাটতি পরিমাণ ৳{impact:,.2f} টাকা।"
            )
            action_en = (
                f"Formal Courier Dispute: Consignment #{entity} has an underpaid shortfall of ৳{impact:,.2f}. "
                f"Immediate reimbursement is requested."
            )
            action_bn = (
                f"কুরিয়ার দাবি নোটিশ: কনসাইনমেন্ট #{entity} এর জন্য ৳{impact:,.2f} টাকা কম দেওয়া হয়েছে। "
                f"অবিলম্বে ঘাটতি অর্থ সমন্বয়ের দাবি জানানো হচ্ছে।"
            )

    elif card.rec_type == RecommendationType.FAILED_PAYMENT_RECOVERY:
        explanation_en = (
            f"Checkout Abandonment Alert for {m_name}: Order #{entity} failed during payment checkout. "
            f"Estimated recoverable revenue at current recovery rate is ৳{impact:,.2f}."
        )
        explanation_bn = (
            f"{m_name} এর ব্যর্থ চেকআউট সতর্কতা: অর্ডার #{entity} পেমেন্টের সময় ব্যর্থ হয়েছে। "
            f"বর্তমান হারে সম্ভাব্য পুনরুদ্ধারযোগ্য রাজস্ব ৳{impact:,.2f} টাকা।"
        )
        action_en = (
            f"Recovery Prompt: We noticed your payment for order #{entity} was interrupted. "
            f"Expected basket recovery value is ৳{impact:,.2f}. Complete your order today."
        )
        action_bn = (
            f"পেমেন্ট সহায়তা: অর্ডার #{entity} এর পেমেন্ট সম্পন্ন হয়নি। "
            f"আপনার ৳{impact:,.2f} টাকার অর্ডারটি সম্পন্ন করতে সহায়তা প্রয়োজন হলে জানান।"
        )

    else:  # STOCKOUT_RISK
        explanation_en = (
            f"Stockout Surge Warning for {m_name}: High demand surge on SKU {entity}. "
            f"Holt-Winters forecasting estimates lost profit margin of ৳{impact:,.2f} without replenishment."
        )
        explanation_bn = (
            f"{m_name} এর স্টক ঘাটতি সতর্কতা: পণ্য {entity} এর বিক্রি বৃদ্ধি পাওয়ায় ঘাটতির ঝুঁকি তৈরি হয়েছে। "
            f"হোল্ট-উইন্টার্স পূর্বাভাস অনুযায়ী সম্ভাব্য মুনাফা ক্ষতি ৳{impact:,.2f} টাকা।"
        )
        action_en = (
            f"Purchase Order Notice: High demand on SKU {entity} threatens stockout with ৳{impact:,.2f} "
            f"margin at risk. Expedite supplier reorder immediately."
        )
        action_bn = (
            f"ক্রয়াদেশ রিকুইজিশন: পণ্য {entity} এর তীব্র চাহিদায় ৳{impact:,.2f} টাকার মুনাফা ঝুঁকির মুখে। "
            f"অবিলম্বে নতুন স্টক সরবরাহের নির্দেশ দিন।"
        )

    return {
        "explanation_en": explanation_en,
        "explanation_bn": explanation_bn,
        "action_draft_en": action_en,
        "action_draft_bn": action_bn,
    }
