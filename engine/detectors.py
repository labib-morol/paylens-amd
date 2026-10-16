"""Deterministic Detectors and Statistical Forecasters for PayLens Solo.

Architecture Rule 1: CODE COMPUTES, MODEL EXPLAINS.
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
    """Standardize phone numbers by stripping non-digits and taking the last 11 digits."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", str(phone))
    return digits[-11:] if len(digits) >= 11 else digits


def run_stl_anomaly_detector(
    con: duckdb.DuckDBPyConnection,
    sigma_threshold: float = 2.2,
) -> Dict[str, List[Dict[str, Any]]]:
    """STL daily revenue anomaly detector (statsmodels).

    Decomposes 30-day merchant daily revenue into trend, seasonal (period=7),
    and residual components. Flags days where abs(resid) > sigma_threshold * std(resid).
    """
    query = """
        SELECT 
            merchant_id,
            CAST(order_timestamp AS DATE) as rev_date,
            SUM(order_amount_taka) as daily_revenue
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
    """2-Pass Deterministic Leak Matcher and Courier COD Shortfall Checker.

    Pass 1: Exact matching on transaction_ref between orders and rail_payments.
    Pass 2: Fuzzy matching on customer_phone + exact amount + timestamp within 30 minutes.
    Planted True Negatives are successfully reconciled in Pass 2 and excluded from leaks.
    """
    merchant_names = merchant_names or {}
    stl_anomalies = stl_anomalies or {}

    # Load digital orders that require payment verification
    orders_df = con.execute("""
        SELECT * FROM orders 
        WHERE payment_rail IN ('MOBILE_WALLET_MFS', 'PAYMENT_GATEWAY', 'BANK_TRANSFER')
          AND order_status IN ('DISPATCHED', 'DELIVERED')
    """).df()

    # Load successful rail payments
    payments_df = con.execute("""
        SELECT * FROM rail_payments 
        WHERE status = 'SUCCESS'
    """).df()

    # Index payments for Pass 1 (exact ref)
    pass1_payment_map = {}
    for _, pay in payments_df.iterrows():
        ref = str(pay["transaction_ref"]).strip()
        if ref:
            pass1_payment_map[(pay["merchant_id"], ref)] = pay

    # Prepare for Pass 2 (fuzzy)
    payments_df["clean_phone"] = payments_df["customer_phone"].apply(_clean_phone)
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
    # Match criteria: same merchant + clean phone + exact amount (diff < 1.0) + within 30 mins
    for ord_row in unmatched_pass1:
        m_id = ord_row["merchant_id"]
        ord_phone = _clean_phone(ord_row["customer_phone"])
        ord_amt = float(ord_row["order_amount_taka"])
        ord_dt = pd.to_datetime(ord_row["order_timestamp"])

        # Candidate payments from the same merchant
        candidates = payments_df[
            (payments_df["merchant_id"] == m_id) &
            (payments_df["clean_phone"] == ord_phone)
        ]

        fuzzy_match = None
        for _, pay_row in candidates.iterrows():
            pay_amt = float(pay_row["amount_taka"])
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
            unit_price = float(ord_row["unit_price_taka"])
            qty = float(ord_row["quantity"])
            shipping = float(ord_row["shipping_cost_taka"])

            allowed = sorted(list({impact, unit_price, qty, shipping, 1.0}))
            evidence = [
                EvidenceRow(
                    source_table="orders",
                    row_id=ord_id,
                    summary=f"Dispatched order #{ord_id} on {ord_row['payment_rail']} ({ord_row['rail_provider']}) with no matching payment record.",
                    raw_data={
                        "order_id": ord_id,
                        "merchant_id": m_id,
                        "customer_phone": ord_row["customer_phone"],
                        "order_amount_taka": impact,
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
                impact_taka=impact,
                confidence=0.95,
                formula_display=f"1 dispatched unpaid order * ৳{impact:,.2f} = ৳{impact:,.2f}",
                allowed_numbers=allowed,
                evidence_rows=evidence,
                stl_anomaly_context=(
                    stl_anomalies.get(m_id)[0] if stl_anomalies.get(m_id) else None
                ),
                action_type="RECONCILE_DISPATCH",
            )
            leak_cards.append(card)

    # -------------------------------------------------------------------------
    # Courier COD Settlement Shortfall Check
    # -------------------------------------------------------------------------
    courier_df = con.execute("""
        SELECT * FROM courier_settlements
        WHERE (expected_net_payout_taka - actual_settled_taka) > 5.0
    """).df()

    for _, c_row in courier_df.iterrows():
        m_id = c_row["merchant_id"]
        m_name = merchant_names.get(m_id, m_id)
        consignment_id = c_row["consignment_id"]
        order_id = c_row["order_id"]
        courier_name = c_row["courier_name"]

        expected_net = round(float(c_row["expected_net_payout_taka"]), 2)
        actual_settled = round(float(c_row["actual_settled_taka"]), 2)
        shortfall = round(expected_net - actual_settled, 2)
        cod_collected = round(float(c_row["cod_collected_taka"]), 2)
        courier_fee = round(float(c_row["courier_fee_taka"]), 2)

        allowed = sorted(list({expected_net, actual_settled, shortfall, cod_collected, courier_fee, 5.0}))
        evidence = [
            EvidenceRow(
                source_table="courier_settlements",
                row_id=c_row["settlement_id"],
                summary=f"Settlement #{c_row['settlement_id']} from {courier_name} undersettled by ৳{shortfall:,.2f}.",
                raw_data={
                    "settlement_id": c_row["settlement_id"],
                    "consignment_id": consignment_id,
                    "order_id": order_id,
                    "courier_name": courier_name,
                    "expected_net_payout_taka": expected_net,
                    "actual_settled_taka": actual_settled,
                    "shortfall_taka": shortfall,
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
            title=f"Courier COD Shortfall: {consignment_id} ({courier_name})",
            impact_taka=shortfall,
            confidence=0.98,
            formula_display=f"৳{expected_net:,.2f} expected - ৳{actual_settled:,.2f} actual = ৳{shortfall:,.2f} shortfall",
            allowed_numbers=allowed,
            evidence_rows=evidence,
            stl_anomaly_context=(
                stl_anomalies.get(m_id)[0] if stl_anomalies.get(m_id) else None
            ),
            action_type="DEMAND_SHORTFALL",
        )
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

    failed_df = con.execute("""
        SELECT * FROM orders
        WHERE order_status = 'FAILED'
    """).df()

    if failed_df.empty:
        return []

    # Successful orders for checking recovery
    success_df = con.execute("""
        SELECT merchant_id, customer_phone, order_timestamp
        FROM orders
        WHERE order_status IN ('DELIVERED', 'DISPATCHED')
    """).df()
    success_df["clean_phone"] = success_df["customer_phone"].apply(_clean_phone)
    success_df["ord_dt"] = pd.to_datetime(success_df["order_timestamp"])

    cards: List[RecommendationCard] = []

    for _, row in failed_df.iterrows():
        m_id = row["merchant_id"]
        m_name = merchant_names.get(m_id, m_id)
        ord_id = row["order_id"]
        phone = _clean_phone(row["customer_phone"])
        ord_dt = pd.to_datetime(row["order_timestamp"])
        basket_amt = round(float(row["order_amount_taka"]), 2)

        # Check if customer succeeded subsequently within 24 hours
        subsequent = success_df[
            (success_df["merchant_id"] == m_id) &
            (success_df["clean_phone"] == phone) &
            (success_df["ord_dt"] > ord_dt) &
            (success_df["ord_dt"] <= ord_dt + timedelta(hours=24))
        ]

        if not subsequent.empty:
            continue  # Naturally recovered

        recoverable_impact = round(basket_amt * recovery_rate, 2)
        rate_percent = round(recovery_rate * 100, 1)

        allowed = sorted(list({basket_amt, recovery_rate, recoverable_impact, rate_percent}))
        evidence = [
            EvidenceRow(
                source_table="orders",
                row_id=ord_id,
                summary=f"Failed checkout #{ord_id} ({row['rail_provider']}) basket ৳{basket_amt:,.2f} abandoned.",
                raw_data={
                    "order_id": ord_id,
                    "merchant_id": m_id,
                    "customer_phone": row["customer_phone"],
                    "order_amount_taka": basket_amt,
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
            impact_taka=recoverable_impact,
            confidence=0.70,
            formula_display=f"৳{basket_amt:,.2f} basket * {recovery_rate:.2f} recovery rate = ৳{recoverable_impact:,.2f}",
            allowed_numbers=allowed,
            evidence_rows=evidence,
            stl_anomaly_context=(
                stl_anomalies.get(m_id)[0] if stl_anomalies.get(m_id) else None
            ),
            action_type="RECOVER_ABANDONED_CHECKOUT",
        )
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
    computes lost margin impact deterministically: lost_units * unit_margin_taka.
    """
    merchant_names = merchant_names or {}
    stl_anomalies = stl_anomalies or {}

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
        unit_margin = round(float(latest["unit_margin_taka"]), 2)
        unit_retail = round(float(latest["unit_retail_price_taka"]), 2)
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
                hw_model = ExponentialSmoothing(
                    demand_series,
                    trend="add",
                    seasonal=None,
                    initialization_method="estimated",
                ).fit()
                forecast = hw_model.forecast(lead_time)
            except Exception:
                # Fallback to recent rolling average
                recent_avg = max(1.0, float(np.mean(demand_series[-7:])))
                forecast = np.array([recent_avg] * lead_time)

        forecasted_demand = float(np.sum(np.maximum(0.0, forecast)))
        daily_velocity = forecasted_demand / max(1, lead_time)
        days_of_cover = round(current_stock / daily_velocity, 2) if daily_velocity > 0 else 999.0

        # Stockout condition: stock cannot cover demand through supplier lead time
        if current_stock < forecasted_demand:
            lost_units = max(0, int(math.ceil(forecasted_demand - current_stock)))
            if lost_units > 0:
                impact = round(lost_units * unit_margin, 2)
                forecast_rounded = round(forecasted_demand, 1)

                allowed = sorted(list({
                    float(lost_units),
                    float(unit_margin),
                    float(impact),
                    float(current_stock),
                    float(lead_time),
                    float(unit_retail),
                    forecast_rounded,
                    days_of_cover,
                }))

                evidence = [
                    EvidenceRow(
                        source_table="inventory_daily",
                        row_id=f"{m_id}:{sku}:{latest['snapshot_date']}",
                        summary=(
                            f"SKU {sku} ({item_name}) has {current_stock} units left. "
                            f"Holt-Winters forecasts {forecast_rounded} units demand over {lead_time} days lead time "
                            f"({days_of_cover} days cover). Lost demand: {lost_units} units."
                        ),
                        raw_data={
                            "merchant_id": m_id,
                            "sku": sku,
                            "item_name": item_name,
                            "current_stock": current_stock,
                            "supplier_lead_time_days": lead_time,
                            "unit_margin_taka": unit_margin,
                            "forecasted_demand_lead_time": forecast_rounded,
                            "days_of_cover": days_of_cover,
                            "lost_units": lost_units,
                        },
                        numbers=[float(current_stock), float(lead_time), float(lost_units), unit_margin, impact],
                    )
                ]

                card = RecommendationCard(
                    card_id=f"CARD-STOCKOUT-{m_id}-{sku}",
                    merchant_id=m_id,
                    merchant_name=m_name,
                    rec_type=RecommendationType.STOCKOUT_RISK,
                    leak_sub_type=LeakSubType.NONE,
                    entity_id=sku,
                    title=f"Stockout Surge Risk: {item_name} ({sku})",
                    impact_taka=impact,
                    confidence=0.85,
                    formula_display=f"{lost_units} lost units * ৳{unit_margin:,.2f} margin = ৳{impact:,.2f}",
                    allowed_numbers=allowed,
                    evidence_rows=evidence,
                    stl_anomaly_context=(
                        stl_anomalies.get(m_id)[0] if stl_anomalies.get(m_id) else None
                    ),
                    action_type="PURCHASE_ORDER",
                )
                cards.append(card)

    return cards
