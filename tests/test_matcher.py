"""Tests for deterministic 2-pass payment leakage matching."""
import duckdb
import pytest
from datetime import datetime
from engine.detectors import detect_payment_leakages
from engine.schema import LeakSubType


@pytest.fixture
def test_db():
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE orders (
            order_id VARCHAR,
            merchant_id VARCHAR,
            customer_name VARCHAR,
            customer_email VARCHAR,
            customer_phone VARCHAR,
            order_timestamp TIMESTAMP,
            order_amount_usd DOUBLE,
            currency VARCHAR,
            quantity INTEGER,
            unit_price_usd DOUBLE,
            shipping_cost_usd DOUBLE,
            sku VARCHAR,
            payment_rail VARCHAR,
            rail_provider VARCHAR,
            order_status VARCHAR,
            transaction_ref VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE rail_payments (
            payment_id VARCHAR,
            merchant_id VARCHAR,
            rail_provider VARCHAR,
            transaction_ref VARCHAR,
            amount_usd DOUBLE,
            currency VARCHAR,
            payment_timestamp TIMESTAMP,
            customer_phone VARCHAR,
            customer_email VARCHAR,
            status VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE courier_settlements (
            settlement_id VARCHAR,
            merchant_id VARCHAR,
            consignment_id VARCHAR,
            order_id VARCHAR,
            courier_name VARCHAR,
            statement_date VARCHAR,
            cod_collected_usd DOUBLE,
            courier_fee_usd DOUBLE,
            expected_net_payout_usd DOUBLE,
            actual_settled_usd DOUBLE,
            payout_status VARCHAR
        )
    """)

    # 1. Clean exact match
    con.execute("INSERT INTO orders VALUES ('ORD-01', 'M1', 'Alice', 'alice@test.com', '+12015550101', '2026-10-01 10:00:00', 100.0, 'USD', 1, 100.0, 0.0, 'SKU-1', 'PAYMENT_GATEWAY', 'Stripe', 'DELIVERED', 'TXN-01')")
    con.execute("INSERT INTO rail_payments VALUES ('P-01', 'M1', 'Stripe', 'TXN-01', 100.0, 'USD', '2026-10-01 10:02:00', '+12015550101', 'alice@test.com', 'SETTLED')")

    # 2. Fuzzy match (Pass 2 True Negative: missing transaction_ref but matching email, amount, and 30-min window)
    con.execute("INSERT INTO orders VALUES ('ORD-02', 'M1', 'Bob', 'bob@test.com', '+12015550102', '2026-10-01 11:00:00', 250.0, 'USD', 1, 250.0, 0.0, 'SKU-2', 'DIGITAL_WALLET', 'PayPal', 'DELIVERED', '')")
    con.execute("INSERT INTO rail_payments VALUES ('P-02', 'M1', 'PayPal', 'TXN-02-ALT', 250.0, 'USD', '2026-10-01 11:15:00', '+12015550102', 'bob@test.com', 'SETTLED')")

    # 3. Dispatched unpaid leak (order dispatched, no matching payment anywhere)
    con.execute("INSERT INTO orders VALUES ('ORD-LEAK', 'M1', 'Charlie', 'charlie@test.com', '+12015550103', '2026-10-01 12:00:00', 400.0, 'USD', 1, 400.0, 0.0, 'SKU-3', 'PAYMENT_GATEWAY', 'Stripe', 'DISPATCHED', 'TXN-UNMATCHED')")

    # 4. Courier COD shortfall
    con.execute("INSERT INTO courier_settlements VALUES ('SET-01', 'M1', 'CONS-SHORT-1', 'ORD-04', 'DHL Express', '2026-10-02', 500.0, 30.0, 470.0, 370.0, 'PARTIAL SHORTFALL')")

    yield con
    con.close()


def test_detect_payment_leakages(test_db):
    cards = detect_payment_leakages(test_db, merchant_names={"M1": "Merchant 1"})
    entity_ids = [c.entity_id for c in cards]

    # Clean match and fuzzy match must NOT be flagged as leaks
    assert "ORD-01" not in entity_ids
    assert "ORD-02" not in entity_ids

    # Unpaid dispatched order must be flagged
    assert "ORD-LEAK" in entity_ids
    leak_card = next(c for c in cards if c.entity_id == "ORD-LEAK")
    assert leak_card.impact_usd == 400.0
    assert leak_card.leak_sub_type == LeakSubType.DISPATCHED_UNPAID

    # Courier shortfall must be flagged
    assert "CONS-SHORT-1" in entity_ids
    shortfall_card = next(c for c in cards if c.entity_id == "CONS-SHORT-1")
    assert shortfall_card.impact_usd == 100.0  # 470 expected - 370 actual
    assert shortfall_card.leak_sub_type == LeakSubType.SETTLEMENT_SHORTFALL
