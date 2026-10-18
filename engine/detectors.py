"""Deterministic Detectors and Statistical Forecasters for PayLens.

Architecture Rule 1: CODE COMPUTES, AMD GPU MODEL EXPLAINS.
All mathematical computations, matching logic, Holt-Winters forecasting,
and STL anomaly detection are computed deterministically here using DuckDB,
pandas, statsmodels, and scipy.
"""

import os
import sys
import re
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import numpy as np
import pandas as pd
import duckdb
from statsmodels.tsa.holtwinters import ExponentialSmoothing, SimpleExpSmoothing
from statsmodels.tsa.seasonal import STL

from engine.schema import (
    RecommendationCard,
    RecommendationType,
    LeakSubType,
    EvidenceRow,
)


def _clean_phone(phone: Optional[str]) -> str:
    """Standardize phone numbers by stripping non-digits and taking the last 10 digits."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    return digits[-10:] if len(digits) >= 10 else digits


def _clean_email(email: Optional[str]) -> str:
    if not email:
        return ""
    return str(email).strip().lower()


def populate_exhaustive_allowed_numbers(card: RecommendationCard) -> None:
    """Ensure card.allowed_numbers includes all ledger figures, line-item quantities, computed dollar amounts, formula numbers, and evidence (excluding confidence scores)."""
    numbers = set(card.allowed_numbers if card.allowed_numbers else [])

    # Impact
    if card.impact_usd is not None:
        numbers.add(float(card.impact_usd))
        numbers.add(round(float(card.impact_usd), 2))
    if hasattr(card, "impact_taka") and card.impact_taka is not None:
        numbers.add(float(card.impact_taka))
        numbers.add(round(float(card.impact_taka), 2))

    # Formula display numbers
    if card.formula_display:
        formula_clean = re.sub(r"(?<=\d),(?=\d)", "", card.formula_display)
        for tok in re.findall(r"\b\d+(?:\.\d+)?\b", formula_clean):
            numbers.add(float(tok))

    # Evidence rows
    for ev in card.evidence_rows:
        for n in ev.numbers:
            numbers.add(float(n))
            numbers.add(round(float(n), 2))
        for k, v in ev.raw_data.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                numbers.add(float(v))
                numbers.add(round(float(v), 2))
                if "rate" in k.lower() or "percent" in k.lower():
                    numbers.add(round(float(v) * 100.0, 1))
                    numbers.add(float(round(v * 100)))

    card.allowed_numbers = sorted(list(numbers))


def run_stl_anomaly_detector(
    con: duckdb.DuckDBPyConnection,
    sigma_threshold: float = 2.2,
) -> Dict[str, List[Dict[str, Any]]]:
    """STL daily revenue anomaly detector (statsmodels).

    Decomposes 30-day merchant daily revenue into trend, seasonal (period=7),
    and residual components. Flags days where abs(resid) > sigma_threshold * std(resid).
    """
    # Detect whether USD or TAKA column exists
    cols = [c[1] for c in con.execute("PRAGMA table_info('orders')").fetchall()]
    amt_col = "order_amount_usd" if "order_amount_usd" in cols else "order_amount_taka"

    query = f"""
        SELECT 
            merchant_id,
            CAST(order_timestamp AS DATE) as rev_date,
            SUM({amt_col}) as daily_revenue
        FROM orders
        WHERE order_status IN ('DELIVERED', 'DISPATCHED')
        GROUP BY merchant_id, CAST(order_timestamp AS DATE)
        ORDER BY merchant_id, rev_date
    """
    df_rev = con.execute(query).df()
    if df_rev.empty:
        return {}

    anomalies_by_merchant: Dict[str, List[Dict[str, Any]]] = {}

    for m_id, group in df_rev.groupby("merchant_id"):
        group = group.sort_values("rev_date")
        if len(group) < 14:
            continue

        series = group["daily_revenue"].astype(float).values
        dates = group["rev_date"].astype(str).tolist()

        try:
            stl = STL(series, period=7, robust=True)
            res = stl.fit()
            resid = res.resid
            std_resid = float(np.std(resid))

            if std_resid <= 1e-6:
                continue

            z_scores = resid / std_resid
            anomalies = []
            for i, z in enumerate(z_scores):
                if abs(z) > sigma_threshold:
                    anomalies.append({
                        "date": dates[i],
                        "revenue": round(float(series[i]), 2),
                        "residual": round(float(resid[i]), 2),
                        "z_score": round(float(z), 2),
                        "is_surge": bool(z > 0),
                    })
            if anomalies:
                anomalies_by_merchant[m_id] = anomalies
        except Exception:
            continue

    return anomalies_by_merchant


def run_leak_matcher(
    con: duckdb.DuckDBPyConnection,
    merchant_names: Optional[Dict[str, str]] = None,
    stl_anomalies: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> Tuple[List[RecommendationCard], Dict[str, Any]]:
    """2-Pass Deterministic Leak Matcher and Carrier COD Shortfall Checker.

    Pass 1: Exact matching on transaction_ref between orders and rail_payments.
    Pass 2: Fuzzy matching on customer_email/phone + exact amount + timestamp within 30 minutes.
    Planted True Negatives are successfully reconciled in Pass 2 and excluded from leaks.
    """
    merchant_names = merchant_names or {}
    stl_anomalies = stl_anomalies or {}

    # Detect currency column
    order_cols = [c[1] for c in con.execute("PRAGMA table_info('orders')").fetchall()]
    amt_col = "order_amount_usd" if "order_amount_usd" in order_cols else "order_amount_taka"
    price_col = "unit_price_usd" if "unit_price_usd" in order_cols else "unit_price_taka"
    ship_col = "shipping_cost_usd" if "shipping_cost_usd" in order_cols else "shipping_cost_taka"

    pay_cols = [c[1] for c in con.execute("PRAGMA table_info('rail_payments')").fetchall()]
    pay_amt_col = "amount_usd" if "amount_usd" in pay_cols else "amount_taka"

    # Load digital orders that require payment verification
    orders_df = con.execute(f"""
        SELECT * FROM orders 
        WHERE payment_rail IN ('MOBILE_WALLET_MFS', 'PAYMENT_GATEWAY', 'BANK_TRANSFER', 'DIGITAL_WALLET')
          AND order_status IN ('DISPATCHED', 'DELIVERED')
    """).df()

    # Load successful rail payments
    payments_df = con.execute(f"""
        SELECT * FROM rail_payments 
        WHERE status IN ('SUCCESS', 'SETTLED')
    """).df()

    # Index payments for Pass 1 (exact ref)
    pass1_payment_map = {}
    for _, pay in payments_df.iterrows():
        ref = str(pay["transaction_ref"]).strip()
        if ref:
            pass1_payment_map[(pay["merchant_id"], ref)] = pay

    # Prepare for Pass 2 (fuzzy)
    payments_df["clean_phone"] = payments_df["customer_phone"].apply(_clean_phone)
    if "customer_email" in payments_df.columns:
        payments_df["clean_email"] = payments_df["customer_email"].apply(_clean_email)
    else:
        payments_df["clean_email"] = ""
    payments_df["pay_dt"] = pd.to_datetime(payments_df["payment_timestamp"])

    unmatched_pass1 = []
    reconciled_exact = []
    reconciled_fuzzy = []
    leak_cards: List[RecommendationCard] = []

    # Run Pass 1
    for _, ord_row in orders_df.iterrows():
        m_id = ord_row["merchant_id"]
        tx_ref = str(ord_row["transaction_ref"]).strip()
        matched_payment = None

        if tx_ref:
            matched_payment = pass1_payment_map.get((m_id, tx_ref))

        if matched_payment is not None:
            reconciled_exact.append(ord_row["order_id"])
        else:
            unmatched_pass1.append(ord_row)

    # Run Pass 2 on orders that failed Pass 1
    # Match criteria: same merchant + clean phone/email + exact amount (diff < 1.0) + within 30 mins
    for ord_row in unmatched_pass1:
        m_id = ord_row["merchant_id"]
        ord_phone = _clean_phone(ord_row.get("customer_phone", ""))
        ord_email = _clean_email(ord_row.get("customer_email", ""))
        ord_amt = float(ord_row[amt_col])
        ord_dt = pd.to_datetime(ord_row["order_timestamp"])

        # Candidate payments from the same merchant
        candidates = payments_df[payments_df["merchant_id"] == m_id]
        if ord_phone and ord_email:
            candidates = candidates[(candidates["clean_phone"] == ord_phone) | (candidates["clean_email"] == ord_email)]
        elif ord_phone:
            candidates = candidates[candidates["clean_phone"] == ord_phone]
        elif ord_email:
            candidates = candidates[candidates["clean_email"] == ord_email]

        fuzzy_match = None
        for _, pay_row in candidates.iterrows():
            pay_amt = float(pay_row[pay_amt_col])
            if abs(pay_amt - ord_amt) < 1.0:
                time_diff_sec = abs((pay_row["pay_dt"] - ord_dt).total_seconds())
                if time_diff_sec <= 1800:  # within 30 minutes
                    fuzzy_match = pay_row
                    break

        if fuzzy_match is not None:
            reconciled_fuzzy.append(ord_row["order_id"])
        else:
            # Deterministic Leak Confirmed: Dispatched Unpaid Order
            ord_id = ord_row["order_id"]
            m_name = merchant_names.get(m_id, m_id)
            impact = round(ord_amt, 2)
            unit_price = float(ord_row[price_col]) if price_col in ord_row else impact
            qty = float(ord_row.get("quantity", 1))
            shipping = float(ord_row.get(ship_col, 0.0))

            allowed = sorted(list({impact, unit_price, qty, shipping, 1.0}))
            evidence = [
                EvidenceRow(
                    source_table="orders",
                    row_id=ord_id,
                    summary=f"Dispatched order #{ord_id} on {ord_row['payment_rail']} ({ord_row['rail_provider']}) with no matching payment record.",
                    raw_data={
                        "order_id": ord_id,
                        "merchant_id": m_id,
                        "customer_phone": ord_row.get("customer_phone", ""),
                        "customer_email": ord_row.get("customer_email", ""),
                        "order_amount_usd": impact,
                        "payment_rail": ord_row["payment_rail"],
                        "rail_provider": ord_row["rail_provider"],
                        "order_status": ord_row["order_status"],
                        "transaction_ref": ord_row["transaction_ref"],
                    },
                    numbers=[impact, qty, unit_price],
                )
            ]

            card = RecommendationCard(
                card_id=f"CARD-LEAK-{ord_id}",
                merchant_id=m_id,
                merchant_name=m_name,
                rec_type=RecommendationType.PAYMENT_LEAKAGE,
                leak_sub_type=LeakSubType.DISPATCHED_UNPAID,
                entity_id=ord_id,
                title=f"Dispatched Unpaid Order #{ord_id} ({ord_row['rail_provider']})",
                impact_usd=impact,
                confidence=0.95,
                formula_display=f"1 dispatched unpaid order * ${impact:,.2f} = ${impact:,.2f}",
                allowed_numbers=allowed,
                evidence_rows=evidence,
                stl_anomaly_context=(
                    stl_anomalies.get(m_id)[0] if stl_anomalies.get(m_id) else None
                ),
                action_type="RECONCILE_DISPATCH",
            )
            populate_exhaustive_allowed_numbers(card)
            leak_cards.append(card)

    # -------------------------------------------------------------------------
    # Carrier COD Settlement Shortfall Check
    # -------------------------------------------------------------------------
    courier_cols = [c[1] for c in con.execute("PRAGMA table_info('courier_settlements')").fetchall()]
    exp_col = "expected_net_payout_usd" if "expected_net_payout_usd" in courier_cols else "expected_net_payout_taka"
    act_col = "actual_settled_usd" if "actual_settled_usd" in courier_cols else "actual_settled_taka"
    cod_col = "cod_collected_usd" if "cod_collected_usd" in courier_cols else "cod_collected_taka"
    fee_col = "courier_fee_usd" if "courier_fee_usd" in courier_cols else "courier_fee_taka"

    courier_df = con.execute(f"""
        SELECT * FROM courier_settlements
        WHERE ({exp_col} - {act_col}) > 5.0
    """).df()

    for _, c_row in courier_df.iterrows():
        m_id = c_row["merchant_id"]
        m_name = merchant_names.get(m_id, m_id)
        consignment_id = c_row["consignment_id"]
        order_id = c_row["order_id"]
        courier_name = c_row["courier_name"]

        expected_net = round(float(c_row[exp_col]), 2)
        actual_settled = round(float(c_row[act_col]), 2)
        shortfall = round(expected_net - actual_settled, 2)
        cod_collected = round(float(c_row[cod_col]), 2)
        courier_fee = round(float(c_row[fee_col]), 2)

        allowed = sorted(list({expected_net, actual_settled, shortfall, cod_collected, courier_fee, 5.0}))
        evidence = [
            EvidenceRow(
                source_table="courier_settlements",
                row_id=c_row["settlement_id"],
                summary=f"Settlement #{c_row['settlement_id']} from {courier_name} undersettled by ${shortfall:,.2f}.",
                raw_data={
                    "settlement_id": c_row["settlement_id"],
                    "consignment_id": consignment_id,
                    "order_id": order_id,
                    "courier_name": courier_name,
                    "expected_net_payout_usd": expected_net,
                    "actual_settled_usd": actual_settled,
                    "shortfall_usd": shortfall,
                },
                numbers=[expected_net, actual_settled, shortfall],
            )
        ]

        card = RecommendationCard(
            card_id=f"CARD-COD-{consignment_id}",
            merchant_id=m_id,
            merchant_name=m_name,
            rec_type=RecommendationType.PAYMENT_LEAKAGE,
            leak_sub_type=LeakSubType.SETTLEMENT_SHORTFALL,
            entity_id=consignment_id,
            title=f"Carrier COD Shortfall: {consignment_id} ({courier_name})",
            impact_usd=shortfall,
            confidence=0.98,
            formula_display=f"${expected_net:,.2f} expected - ${actual_settled:,.2f} actual = ${shortfall:,.2f} shortfall",
            allowed_numbers=allowed,
            evidence_rows=evidence,
            stl_anomaly_context=(
                stl_anomalies.get(m_id)[0] if stl_anomalies.get(m_id) else None
            ),
            action_type="DEMAND_SHORTFALL",
        )
        populate_exhaustive_allowed_numbers(card)
        leak_cards.append(card)

    telemetry = {
        "orders_evaluated": len(orders_df),
        "reconciled_exact_pass1": len(reconciled_exact),
        "reconciled_fuzzy_pass2": len(reconciled_fuzzy),
        "dispatched_unpaid_detected": len(leak_cards) - len(courier_df),
        "courier_shortfalls_detected": len(courier_df),
        "total_leak_cards": len(leak_cards),
        "reconciled_fuzzy_ids": reconciled_fuzzy,
    }

    return leak_cards, telemetry


def run_failed_payment_scanner(
    con: duckdb.DuckDBPyConnection,
    recovery_rate: float = 0.35,
    merchant_names: Optional[Dict[str, str]] = None,
    stl_anomalies: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> List[RecommendationCard]:
    """Failed-Payment Recovery Scanner.

    Scans for failed/abandoned checkouts on digital rails where the customer did not
    complete a subsequent purchase within 24 hours. Calculates recoverable impact
    based on adjustable recovery rate r.
    """
    merchant_names = merchant_names or {}
    stl_anomalies = stl_anomalies or {}

    order_cols = [c[1] for c in con.execute("PRAGMA table_info('orders')").fetchall()]
    amt_col = "order_amount_usd" if "order_amount_usd" in order_cols else "order_amount_taka"

    failed_df = con.execute(f"""
        SELECT * FROM orders
        WHERE order_status = 'FAILED'
    """).df()

    if failed_df.empty:
        return []

    # Successful orders for checking recovery
    has_email = "customer_email" in order_cols
    sel_fields = "merchant_id, customer_phone, customer_email, order_timestamp" if has_email else "merchant_id, customer_phone, order_timestamp"
    success_df = con.execute(f"""
        SELECT {sel_fields}
        FROM orders
        WHERE order_status IN ('DELIVERED', 'DISPATCHED')
    """).df()
    success_df["clean_phone"] = success_df["customer_phone"].apply(_clean_phone)
    if has_email:
        success_df["clean_email"] = success_df["customer_email"].apply(_clean_email)
    success_df["ord_dt"] = pd.to_datetime(success_df["order_timestamp"])

    cards: List[RecommendationCard] = []

    for _, row in failed_df.iterrows():
        m_id = row["merchant_id"]
        m_name = merchant_names.get(m_id, m_id)
        ord_id = row["order_id"]
        phone = _clean_phone(row.get("customer_phone", ""))
        email = _clean_email(row.get("customer_email", "")) if has_email else ""
        ord_dt = pd.to_datetime(row["order_timestamp"])
        basket_amt = round(float(row[amt_col]), 2)

        # Check if customer succeeded subsequently within 24 hours
        subsequent = success_df[
            (success_df["merchant_id"] == m_id) &
            (success_df["ord_dt"] > ord_dt) &
            (success_df["ord_dt"] <= ord_dt + timedelta(hours=24))
        ]
        if phone and email:
            subsequent = subsequent[(subsequent["clean_phone"] == phone) | (subsequent["clean_email"] == email)]
        elif phone:
            subsequent = subsequent[subsequent["clean_phone"] == phone]
        elif email:
            subsequent = subsequent[subsequent["clean_email"] == email]

        if not subsequent.empty:
            continue  # Naturally recovered

        recoverable_impact = round(basket_amt * recovery_rate, 2)
        rate_percent = round(recovery_rate * 100, 1)

        allowed = sorted(list({basket_amt, recovery_rate, recoverable_impact, rate_percent}))
        evidence = [
            EvidenceRow(
                source_table="orders",
                row_id=ord_id,
                summary=f"Failed checkout #{ord_id} ({row['rail_provider']}) basket ${basket_amt:,.2f} abandoned.",
                raw_data={
                    "order_id": ord_id,
                    "merchant_id": m_id,
                    "customer_phone": row.get("customer_phone", ""),
                    "customer_email": row.get("customer_email", ""),
                    "order_amount_usd": basket_amt,
                    "rail_provider": row["rail_provider"],
                    "recovery_rate": recovery_rate,
                },
                numbers=[basket_amt, recovery_rate, recoverable_impact],
            )
        ]

        card = RecommendationCard(
            card_id=f"CARD-FAIL-{ord_id}",
            merchant_id=m_id,
            merchant_name=m_name,
            rec_type=RecommendationType.FAILED_PAYMENT_RECOVERY,
            leak_sub_type=LeakSubType.NONE,
            entity_id=ord_id,
            title=f"Abandoned Checkout #{ord_id} ({row['rail_provider']})",
            impact_usd=recoverable_impact,
            confidence=0.70,
            formula_display=f"${basket_amt:,.2f} basket * {recovery_rate:.2f} recovery rate = ${recoverable_impact:,.2f}",
            allowed_numbers=allowed,
            evidence_rows=evidence,
            stl_anomaly_context=(
                stl_anomalies.get(m_id)[0] if stl_anomalies.get(m_id) else None
            ),
            action_type="RECOVER_ABANDONED_CHECKOUT",
        )
        populate_exhaustive_allowed_numbers(card)
        cards.append(card)

    return cards


def run_stockout_forecaster(
    con: duckdb.DuckDBPyConnection,
    merchant_names: Optional[Dict[str, str]] = None,
    stl_anomalies: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> List[RecommendationCard]:
    """Holt-Winters SKU Demand Forecaster & Stockout Risk Detector.

    Uses statsmodels ExponentialSmoothing (seasonal_periods=7) to forecast demand
    over each SKU's supplier_lead_time_days. When days_of_cover < lead_time,
    computes lost margin impact deterministically: lost_units * unit_margin_usd.
    """
    merchant_names = merchant_names or {}
    stl_anomalies = stl_anomalies or {}

    inv_cols = [c[1] for c in con.execute("PRAGMA table_info('inventory_daily')").fetchall()]
    margin_col = "unit_margin_usd" if "unit_margin_usd" in inv_cols else "unit_margin_taka"
    retail_col = "unit_retail_price_usd" if "unit_retail_price_usd" in inv_cols else "unit_retail_price_taka"

    inv_df = con.execute("""
        SELECT * FROM inventory_daily
        ORDER BY merchant_id, sku, snapshot_date
    """).df()

    if inv_df.empty:
        return []

    cards: List[RecommendationCard] = []

    for (m_id, sku), group in inv_df.groupby(["merchant_id", "sku"]):
        group = group.sort_values("snapshot_date")
        latest = group.iloc[-1]

        current_stock = int(latest["current_stock"])
        lead_time = int(latest["supplier_lead_time_days"])
        unit_margin = round(float(latest[margin_col]), 2)
        unit_retail = round(float(latest[retail_col]), 2)
        item_name = str(latest["item_name"])
        m_name = merchant_names.get(m_id, m_id)

        demand_series = group["units_sold_today"].astype(float).values
        if len(demand_series) < 14:
            continue

        # Fit Holt-Winters Exponential Smoothing with fallback
        try:
            hw_model = ExponentialSmoothing(
                demand_series,
                trend="add",
                seasonal="add",
                seasonal_periods=7,
                initialization_method="estimated",
            ).fit()
            forecast = hw_model.forecast(lead_time)
        except Exception:
            try:
                hw_model = SimpleExpSmoothing(demand_series).fit(smoothing_level=0.3)
                forecast = hw_model.forecast(lead_time)
            except Exception:
                mean_demand = float(np.mean(demand_series[-7:]))
                forecast = np.array([mean_demand] * lead_time)

        forecast = np.maximum(forecast, 0.0)
        total_lead_demand = float(np.sum(forecast))
        daily_forecast_rate = total_lead_demand / max(1, lead_time)

        # Days of cover calculation
        if daily_forecast_rate > 0.01:
            days_of_cover = current_stock / daily_forecast_rate
        else:
            days_of_cover = 999.0

        # Stockout condition: days_of_cover < supplier_lead_time_days
        if days_of_cover < lead_time:
            lost_units = round(max(0.0, total_lead_demand - current_stock), 1)
            lost_margin = round(lost_units * unit_margin, 2)

            if lost_margin > 0:
                allowed = sorted(list({
                    float(current_stock),
                    float(lead_time),
                    round(days_of_cover, 1),
                    round(daily_forecast_rate, 1),
                    lost_units,
                    unit_margin,
                    unit_retail,
                    lost_margin,
                }))

                evidence = [
                    EvidenceRow(
                        source_table="inventory_daily",
                        row_id=f"{m_id}:{sku}",
                        summary=f"SKU {sku} ({item_name}) stock {current_stock} pcs covers only {days_of_cover:.1f} days vs supplier lead time of {lead_time} days.",
                        raw_data={
                            "merchant_id": m_id,
                            "sku": sku,
                            "item_name": item_name,
                            "current_stock": current_stock,
                            "supplier_lead_time_days": lead_time,
                            "daily_forecast_demand": round(daily_forecast_rate, 2),
                            "days_of_cover": round(days_of_cover, 1),
                            "lost_units": lost_units,
                            "unit_margin_usd": unit_margin,
                            "lost_margin_usd": lost_margin,
                            "is_hero": bool(latest.get("is_hero", False)),
                        },
                        numbers=[lost_margin, lost_units, unit_margin, float(current_stock), float(lead_time)],
                    )
                ]

                card = RecommendationCard(
                    card_id=f"CARD-STOCK-{m_id}-{sku}",
                    merchant_id=m_id,
                    merchant_name=m_name,
                    rec_type=RecommendationType.STOCKOUT_RISK,
                    leak_sub_type=LeakSubType.NONE,
                    entity_id=sku,
                    title=f"Stockout Risk: {item_name} ({sku})",
                    impact_usd=lost_margin,
                    confidence=0.88,
                    formula_display=f"{lost_units} lost units * ${unit_margin:,.2f} margin = ${lost_margin:,.2f}",
                    allowed_numbers=allowed,
                    evidence_rows=evidence,
                    stl_anomaly_context=(
                        stl_anomalies.get(m_id)[0] if stl_anomalies.get(m_id) else None
                    ),
                    action_type="REORDER_INVENTORY",
                )
                populate_exhaustive_allowed_numbers(card)
                cards.append(card)

    return cards


def detect_payment_leakages(
    con: duckdb.DuckDBPyConnection,
    merchant_names: Optional[Dict[str, str]] = None,
    stl_anomalies: Optional[Dict[str, List[Dict[str, Any]]]] = None,
) -> List[RecommendationCard]:
    """Convenience wrapper around run_leak_matcher returning only cards."""
    cards, _ = run_leak_matcher(con, merchant_names=merchant_names, stl_anomalies=stl_anomalies)
    return cards
