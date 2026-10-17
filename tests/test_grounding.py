"""Tests for numeric regex grounding and text normalization."""
import pytest
from agent.grounding import verify_numeric_grounding, _normalize_text, build_fallback_template
from engine.schema import RecommendationCard, RecommendationType, LeakSubType


def test_bengali_digit_normalization():
    raw = "মূল্য ১২,৫০০ টাকা"
    normalized = _normalize_text(raw)
    assert "12500" in normalized


def test_lakh_formatting_normalization():
    raw = "Total balance is 1,25,000 dollars"
    normalized = _normalize_text(raw)
    assert "125000" in normalized


def test_grounding_verifier_valid_numbers():
    text = "We audited order ORD-1042 on 2026-10-15 at 14:30 and found $1,250.00 uncollected."
    allowed = [1250.0]
    is_grounded, ungrounded = verify_numeric_grounding(text, allowed)
    assert is_grounded is True
    assert ungrounded == []


def test_grounding_verifier_flags_hallucination():
    text = "We audited order ORD-1042 and fabricated $9,450.00 in missing funds."
    allowed = [1250.0]
    is_grounded, ungrounded = verify_numeric_grounding(text, allowed)
    assert is_grounded is False
    assert 9450.0 in ungrounded


def test_grounding_verifier_ignores_ids_dates_times_phones():
    text = "Order INJ-ORD-9021 called +1-415-555-0199 on 2026-10-15 at 09:30:00 with 1. bullet item: $500.00"
    allowed = [500.0]
    is_grounded, ungrounded = verify_numeric_grounding(text, allowed)
    assert is_grounded is True
    assert ungrounded == []


def test_vip_discount_precomputed_in_code():
    card = RecommendationCard(
        card_id="CARD-TEST-01",
        merchant_id="MERCH_01",
        merchant_name="Apex Global",
        rec_type=RecommendationType.PAYMENT_LEAKAGE,
        leak_sub_type=LeakSubType.DISPATCHED_UNPAID,
        entity_id="ORD-TEST-101",
        impact_usd=100.0,
        confidence=0.95,
        formula_display="1 * 100 = 100",
        allowed_numbers=[100.0],
    )
    fallback = build_fallback_template(card, tone="VIP 5% Instant-Pay Discount")
    assert "95.00" in fallback["action_draft_en"]
    # Check that code pre-computed and whitelisted 95.0
    assert 95.0 in card.allowed_numbers
