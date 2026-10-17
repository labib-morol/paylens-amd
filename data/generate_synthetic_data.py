"""Synthetic Data Generator for PayLens.

Generates 30 days of realistic multi-rail global commerce data for 20 international merchants:
- E-commerce platforms: Shopify, WooCommerce, Magento
- Payment Rails: Stripe Gateway, PayPal Digital Wallet, SEPA/Wire Bank Transfers, and DHL/FedEx Courier COD
- Disconnected payment rail logs with reconciliation gaps
- Carrier COD settlements with planted shortfalls
- Daily inventory snapshots with seasonal demand surges and stockout risks
- Exact ground truth JSON with planted leaks, shortfalls, fuzzy True Negatives, and hero stockout SKUs
- Generates sample carrier settlement PDF for Evolus AI Document Extractor intake
"""

import os
import json
import random
from datetime import datetime, timedelta
import pandas as pd
import duckdb

SEED = 42
random.seed(SEED)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "generated")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 20 Global Merchants across modern commerce verticals
MERCHANTS = [
    {"id": "MERCH_01", "name": "Apex Global Apparel", "platform": "Shopify", "category": "Fashion & Lifestyle"},
    {"id": "MERCH_02", "name": "Lumina Smart Home & Audio", "platform": "WooCommerce", "category": "Consumer Electronics"},
    {"id": "MERCH_03", "name": "Horizon Outdoors & Gear", "platform": "Shopify", "category": "Outdoor & Sporting Goods"},
    {"id": "MERCH_04", "name": "Velvet & Vine Cosmetics", "platform": "Shopify", "category": "Beauty & Personal Care"},
    {"id": "MERCH_05", "name": "Titan Precision Tools", "platform": "Magento", "category": "Hardware & Equipment"},
    {"id": "MERCH_06", "name": "PureArtisan Gourmet Foods", "platform": "WooCommerce", "category": "Food & Beverage"},
    {"id": "MERCH_07", "name": "Nordic Living Studio", "platform": "Shopify", "category": "Furniture & Interior"},
    {"id": "MERCH_08", "name": "Optima Health & Nutrition", "platform": "Shopify", "category": "Supplements & Wellness"},
    {"id": "MERCH_09", "name": "Kroma Mechanical Keyboards", "platform": "WooCommerce", "category": "Computer Peripherals"},
    {"id": "MERCH_10", "name": "Heritage Leather Co.", "platform": "Shopify", "category": "Luxury Leather Goods"},
    {"id": "MERCH_11", "name": "Solara Activewear", "platform": "Shopify", "category": "Athletic Wear"},
    {"id": "MERCH_12", "name": "Vanguard Optical & Eyewear", "platform": "Shopify", "category": "Eyewear"},
    {"id": "MERCH_13", "name": "Zenith Espresso Equipment", "platform": "WooCommerce", "category": "Coffee Machines"},
    {"id": "MERCH_14", "name": "Aura Gemstones & Fine Jewelry", "platform": "Shopify", "category": "Jewelry"},
    {"id": "MERCH_15", "name": "Terra Pet Botanicals", "platform": "Shopify", "category": "Pet Care"},
    {"id": "MERCH_16", "name": "Cortex Robotics & STEM Kits", "platform": "WooCommerce", "category": "Educational Toys"},
    {"id": "MERCH_17", "name": "Equinox Cycling Components", "platform": "Shopify", "category": "Cycling & Bicycles"},
    {"id": "MERCH_18", "name": "Verdant Urban Nursery", "platform": "Shopify", "category": "Plants & Home Gardening"},
    {"id": "MERCH_19", "name": "Pulse Wearable Fitness", "platform": "Shopify", "category": "Wearables & Tech"},
    {"id": "MERCH_20", "name": "Monochrome Minimalist Watches", "platform": "Shopify", "category": "Horology & Accessories"},
]

GLOBAL_FIRST_NAMES = [
    "Alexander", "Sophia", "Lucas", "Emma", "Liam", "Olivia", "Noah", "Ava",
    "Ethan", "Mia", "Oliver", "Isabella", "Mateo", "Charlotte", "Daniel", "Amelia",
    "Marcus", "Elena", "Julian", "Chloe", "David", "Harper", "Sebastian", "Evelyn",
]

GLOBAL_LAST_NAMES = [
    "Vance", "Chen", "Müller", "Dubois", "Smith", "Silva", "Taylor", "Kowalski",
    "Nakamura", "Johansson", "Rossi", "Patel", "Garcia", "Kim", "Anderson", "Martin",
    "O'Connor", "Santos", "Novak", "Lefebvre", "Schneider", "Brown", "Williams", "Davies",
]

EMAIL_DOMAINS = ["gmail.com", "outlook.com", "icloud.com", "yahoo.com", "proton.me", "fastmail.com"]


def generate_customer() -> dict:
    first = random.choice(GLOBAL_FIRST_NAMES)
    last = random.choice(GLOBAL_LAST_NAMES)
    name = f"{first} {last}"
    clean_name = f"{first.lower()}.{last.lower()}{random.randint(10, 99)}"
    domain = random.choice(EMAIL_DOMAINS)
    email = f"{clean_name}@{domain}"
    area_code = random.randint(201, 917)
    exchange = random.randint(200, 899)
    line = random.randint(1000, 9999)
    phone = f"+1-{area_code}-{exchange:03d}-{line:04d}"
    return {"name": name, "email": email, "phone": phone}


def format_phone_with_noise(phone: str, noise: bool = False) -> str:
    """Optionally add noise to phone numbers (stripping country code, varying separators)."""
    if not noise or random.random() > 0.35:
        return phone
    c = random.randint(1, 3)
    if c == 1:
        return phone.replace("+1-", "").replace("-", "")
    elif c == 2:
        raw = phone.replace("+1-", "").replace("-", "")
        return f"0{raw}"
    else:
        return phone.replace("+1-", "").replace("-", ".")


# Planted Stockout SKUs
PLANTED_STOCKOUT_CONFIGS = {
    ("MERCH_02", "SKU-LUM-HERO-01"): {"lead_time": 7, "surge_start": 21, "surge_sales": (6, 9), "end_stock": 8, "is_hero": True},
    ("MERCH_01", "SKU-APX-01"): {"lead_time": 6, "surge_start": 23, "surge_sales": (5, 8), "end_stock": 6, "is_hero": False},
    ("MERCH_03", "SKU-03-A"): {"lead_time": 6, "surge_start": 23, "surge_sales": (5, 8), "end_stock": 5, "is_hero": False},
    ("MERCH_07", "SKU-07-A"): {"lead_time": 7, "surge_start": 23, "surge_sales": (4, 7), "end_stock": 7, "is_hero": False},
}


def build_sku_catalog():
    catalog = {}
    for m in MERCHANTS:
        m_id = m["id"]
        if m_id == "MERCH_02":
            catalog[m_id] = [
                {
                    "sku": "SKU-LUM-HERO-01",
                    "item_name": "Aura Wireless Hi-Fi Studio Monitor (Pair)",
                    "unit_cost_usd": 45.0,
                    "unit_retail_price_usd": 95.0,
                    "unit_margin_usd": 50.0,
                    "supplier_lead_time_days": 7,
                    "initial_stock": 140,
                    "is_hero": True,
                },
                {
                    "sku": "SKU-LUM-02",
                    "item_name": "Lumina Smart Beam Ambient Projector",
                    "unit_cost_usd": 60.0,
                    "unit_retail_price_usd": 120.0,
                    "unit_margin_usd": 60.0,
                    "supplier_lead_time_days": 5,
                    "initial_stock": 180,
                    "is_hero": False,
                },
                {
                    "sku": "SKU-LUM-03",
                    "item_name": "Acoustic Noise-Cancelling Soundbar",
                    "unit_cost_usd": 55.0,
                    "unit_retail_price_usd": 110.0,
                    "unit_margin_usd": 55.0,
                    "supplier_lead_time_days": 6,
                    "initial_stock": 160,
                    "is_hero": False,
                },
            ]
        elif m_id == "MERCH_01":
            catalog[m_id] = [
                {
                    "sku": "SKU-APX-01",
                    "item_name": "Merino Wool Performance Blazer",
                    "unit_cost_usd": 40.0,
                    "unit_retail_price_usd": 85.0,
                    "unit_margin_usd": 45.0,
                    "supplier_lead_time_days": 6,
                    "initial_stock": 150,
                    "is_hero": False,
                },
                {
                    "sku": "SKU-APX-02",
                    "item_name": "Tailored Oxford Tech Shirt",
                    "unit_cost_usd": 30.0,
                    "unit_retail_price_usd": 65.0,
                    "unit_margin_usd": 35.0,
                    "supplier_lead_time_days": 4,
                    "initial_stock": 250,
                    "is_hero": False,
                },
            ]
        else:
            cat_name = m["category"].split()[0]
            catalog[m_id] = [
                {
                    "sku": f"SKU-{m_id[6:]}-A",
                    "item_name": f"Premium {cat_name} Edition A",
                    "unit_cost_usd": float(random.randint(25, 45)),
                    "unit_retail_price_usd": float(random.randint(60, 95)),
                    "supplier_lead_time_days": 6,
                    "initial_stock": 200,
                    "is_hero": False,
                },
                {
                    "sku": f"SKU-{m_id[6:]}-B",
                    "item_name": f"Standard {cat_name} Everyday B",
                    "unit_cost_usd": float(random.randint(15, 30)),
                    "unit_retail_price_usd": float(random.randint(40, 70)),
                    "supplier_lead_time_days": 4,
                    "initial_stock": 250,
                    "is_hero": False,
                },
            ]
            for it in catalog[m_id]:
                it["unit_margin_usd"] = it["unit_retail_price_usd"] - it["unit_cost_usd"]
    return catalog


def generate_dataset(
    seed: int = 42,
    noise: bool = False,
    output_dir: str = None,
    is_heldout: bool = False,
):
    random.seed(seed)
    out_dir = output_dir or OUTPUT_DIR
    os.makedirs(out_dir, exist_ok=True)
    catalog = build_sku_catalog()
    base_date = datetime.now() - timedelta(days=30)

    orders_records = []
    rail_payments_records = []
    courier_settlements_records = []
    inventory_records = []

    # Ground truth containers
    ground_truth = {
        "dispatched_unpaid": [],
        "courier_shortfalls": [],
        "fuzzy_true_negatives": [],
        "failed_abandoned_checkouts": [],
        "stockout_skus": [],
    }

    order_seq = 1000
    payment_seq = 5000
    settle_seq = 7000
    consignment_seq = 9000

    # 1. Generate 30 days of inventory & daily sales
    for m in MERCHANTS:
        m_id = m["id"]
        skus = catalog[m_id]

        for sku_info in skus:
            sku = sku_info["sku"]
            lead_time = sku_info["supplier_lead_time_days"]
            is_planted_stockout = (m_id, sku) in PLANTED_STOCKOUT_CONFIGS
            is_hero = sku_info.get("is_hero", False)
            curr_stock = sku_info["initial_stock"]

            cfg = PLANTED_STOCKOUT_CONFIGS.get((m_id, sku), None)

            for day_idx in range(30):
                snapshot_dt = (base_date + timedelta(days=day_idx)).date()

                if is_planted_stockout and cfg is not None:
                    # Surge period
                    if day_idx >= cfg["surge_start"]:
                        units_sold = random.randint(*cfg["surge_sales"])
                    else:
                        units_sold = random.randint(3, 6)
                    curr_stock = max(cfg["end_stock"], curr_stock - units_sold)
                    if day_idx == 29:
                        curr_stock = cfg["end_stock"]  # Enforce exact depleted stock
                else:
                    # Non-planted healthy SKU: steady modest sales & healthy auto-replenishment
                    units_sold = random.randint(2, 5)
                    curr_stock -= units_sold
                    # Keep stock well above lead time cover (current_stock >= 2.5 * lead_time * daily_sales)
                    if curr_stock < (lead_time * 6):
                        curr_stock += 80  # Restock

                inventory_records.append({
                    "snapshot_date": str(snapshot_dt),
                    "merchant_id": m_id,
                    "sku": sku,
                    "item_name": sku_info["item_name"],
                    "current_stock": curr_stock,
                    "units_sold_today": units_sold,
                    "unit_cost_usd": sku_info["unit_cost_usd"],
                    "unit_retail_price_usd": sku_info["unit_retail_price_usd"],
                    "unit_margin_usd": sku_info["unit_margin_usd"],
                    "supplier_lead_time_days": lead_time,
                    "is_hero": is_hero,
                })

            # Record strictly the planted stockout SKUs into ground truth
            if is_planted_stockout and cfg is not None:
                recent_sales = [r["units_sold_today"] for r in inventory_records if r["merchant_id"] == m_id and r["sku"] == sku][-7:]
                avg_daily = sum(recent_sales) / max(1, len(recent_sales))
                days_cover = round(cfg["end_stock"] / max(0.1, avg_daily), 2)
                lost_units = max(0.0, round((lead_time - days_cover) * avg_daily, 1))
                lost_margin = round(lost_units * sku_info["unit_margin_usd"], 2)

                ground_truth["stockout_skus"].append({
                    "merchant_id": m_id,
                    "sku": sku,
                    "item_name": sku_info["item_name"],
                    "current_stock": cfg["end_stock"],
                    "supplier_lead_time_days": lead_time,
                    "forecast_daily_demand": round(avg_daily, 2),
                    "days_of_cover": days_cover,
                    "lost_units": lost_units,
                    "unit_margin_usd": sku_info["unit_margin_usd"],
                    "impact_usd": lost_margin,
                    "is_hero": is_hero,
                })

    # 2. Generate Orders and Payment Rail records across 30 days
    rail_dist = [
        ("PAYMENT_GATEWAY", "Stripe"),
        ("DIGITAL_WALLET", "PayPal"),
        ("BANK_TRANSFER", "SEPA Wire"),
        ("COURIER_COD", "DHL Express"),
        ("COURIER_COD", "FedEx Ground"),
    ]

    for m in MERCHANTS:
        m_id = m["id"]
        skus = catalog[m_id]

        for day_idx in range(30):
            day_dt = base_date + timedelta(days=day_idx)
            num_orders = random.randint(4, 7)

            for _ in range(num_orders):
                order_seq += 1
                ord_id = f"ORD-{order_seq}"
                cust = generate_customer()
                sku_choice = random.choice(skus)
                qty = random.randint(1, 2)
                unit_price = sku_choice["unit_retail_price_usd"]
                shipping = random.choice([0.0, 15.0, 25.0])
                total_amt = round(qty * unit_price + shipping, 2)
                ord_time = day_dt + timedelta(hours=random.randint(8, 22), minutes=random.randint(0, 59))

                rail_type, rail_prov = random.choice(rail_dist)
                txn_ref = f"TXN-STRIPE-{random.randint(100000, 999999)}" if "Stripe" in rail_prov else (
                    f"PAYPAL-PP-{random.randint(100000, 999999)}" if "PayPal" in rail_prov else (
                        f"WIRE-REF-{random.randint(100000, 999999)}" if "SEPA" in rail_prov else ""
                    )
                )
                if noise and random.random() < 0.015:
                    txn_ref = "TXN-CROSS-MERCH-DUP-999"

                status = "DELIVERED" if day_idx < 25 else "DISPATCHED"
                ord_phone = format_phone_with_noise(cust["phone"], noise)

                orders_records.append({
                    "order_id": ord_id,
                    "merchant_id": m_id,
                    "customer_name": cust["name"],
                    "customer_email": cust["email"],
                    "customer_phone": ord_phone,
                    "order_timestamp": ord_time.isoformat(),
                    "order_amount_usd": total_amt,
                    "currency": "USD",
                    "quantity": qty,
                    "unit_price_usd": unit_price,
                    "shipping_cost_usd": shipping,
                    "sku": sku_choice["sku"],
                    "payment_rail": rail_type,
                    "rail_provider": rail_prov,
                    "order_status": status,
                    "transaction_ref": txn_ref,
                })

                # Digital rails generate rail_payments
                if rail_type in ("PAYMENT_GATEWAY", "DIGITAL_WALLET", "BANK_TRANSFER"):
                    payment_seq += 1
                    pay_offset = random.randint(2, 12)
                    pay_time = ord_time + timedelta(minutes=pay_offset)

                    pay_phone = format_phone_with_noise(cust["phone"], noise)
                    pay_amt = total_amt
                    pay_status = "SUCCESS"

                    rail_payments_records.append({
                        "payment_id": f"RP-{payment_seq}",
                        "merchant_id": m_id,
                        "rail_provider": rail_prov,
                        "transaction_ref": txn_ref,
                        "amount_usd": pay_amt,
                        "currency": "USD",
                        "payment_timestamp": pay_time.isoformat(),
                        "customer_phone": pay_phone,
                        "customer_email": cust["email"],
                        "status": pay_status,
                    })

                # Courier COD rails generate courier_settlements
                elif rail_type == "COURIER_COD":
                    settle_seq += 1
                    consignment_seq += 1
                    cod_fee = round(total_amt * 0.035 + 8.50, 2)
                    net_expected = round(total_amt - cod_fee, 2)
                    actual_settled = net_expected  # Default clean

                    stmt_days = 3
                    if noise and random.random() < 0.05:
                        stmt_days = random.randint(15, 28)

                    courier_settlements_records.append({
                        "settlement_id": f"SETTLE-{settle_seq}",
                        "merchant_id": m_id,
                        "consignment_id": f"CONS-{consignment_seq}",
                        "order_id": ord_id,
                        "courier_name": rail_prov,
                        "statement_date": (ord_time + timedelta(days=stmt_days)).strftime("%Y-%m-%d"),
                        "cod_collected_usd": total_amt,
                        "courier_fee_usd": cod_fee,
                        "expected_net_payout_usd": net_expected,
                        "actual_settled_usd": actual_settled,
                        "payout_status": "SETTLED",
                    })

    # 3. Plant Ground-Truth Category A: Dispatched-Unpaid Orders (8 planted leaks)
    leak_merchants = ["MERCH_01", "MERCH_02", "MERCH_03", "MERCH_05", "MERCH_07", "MERCH_10", "MERCH_13", "MERCH_14"]
    for idx, m_id in enumerate(leak_merchants):
        order_seq += 1
        ord_id = f"ORD-LEAK-{order_seq}"
        cust = generate_customer()
        skus = catalog[m_id]
        sku = skus[0]
        amt = round(float(random.choice([480.0, 750.0, 1255.0, 950.0, 620.0])), 2)
        ord_time = base_date + timedelta(days=26, hours=10 + idx)
        rail = "PAYMENT_GATEWAY" if idx % 2 == 0 else "DIGITAL_WALLET"
        prov = "Stripe" if rail == "PAYMENT_GATEWAY" else "PayPal"
        unmatched_ref = f"TXN-ORPHAN-{random.randint(10000, 99999)}"

        orders_records.append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "customer_name": cust["name"],
            "customer_email": cust["email"],
            "customer_phone": cust["phone"],
            "order_timestamp": ord_time.isoformat(),
            "order_amount_usd": amt,
            "currency": "USD",
            "quantity": 1,
            "unit_price_usd": amt,
            "shipping_cost_usd": 0.0,
            "sku": sku["sku"],
            "payment_rail": rail,
            "rail_provider": prov,
            "order_status": "DISPATCHED",
            "transaction_ref": unmatched_ref,
        })

        ground_truth["dispatched_unpaid"].append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "amount_usd": amt,
            "amount_taka": amt,
            "rail": rail,
            "provider": prov,
        })

    # 4. Plant Ground-Truth Category B: Carrier COD Settlement Shortfalls (6 planted shortfalls)
    shortfall_merchants = ["MERCH_01", "MERCH_02", "MERCH_04", "MERCH_08", "MERCH_11", "MERCH_17"]
    for idx, m_id in enumerate(shortfall_merchants):
        order_seq += 1
        settle_seq += 1
        consignment_seq += 1
        ord_id = f"ORD-COD-SHORT-{order_seq}"
        cons_id = f"CONS-SHORT-{consignment_seq}"
        cust = generate_customer()
        cod_amt = float(random.choice([380.0, 620.0, 850.0, 1100.0, 1450.0]))
        courier_name = "DHL Express" if idx % 2 == 0 else "FedEx Ground"
        courier_fee = round(cod_amt * 0.04 + 10.0, 2)
        expected_net = round(cod_amt - courier_fee, 2)
        planted_shortfall = round(float(random.choice([45.0, 85.0, 120.0, 175.0, 240.0])), 2)
        actual_settled = round(expected_net - planted_shortfall, 2)
        ord_time = base_date + timedelta(days=24 + (idx % 4), hours=14)

        orders_records.append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "customer_name": cust["name"],
            "customer_email": cust["email"],
            "customer_phone": cust["phone"],
            "order_timestamp": ord_time.isoformat(),
            "order_amount_usd": cod_amt,
            "currency": "USD",
            "quantity": 1,
            "unit_price_usd": cod_amt,
            "shipping_cost_usd": 0.0,
            "sku": catalog[m_id][0]["sku"],
            "payment_rail": "COURIER_COD",
            "rail_provider": courier_name,
            "order_status": "DELIVERED",
            "transaction_ref": "",
        })

        courier_settlements_records.append({
            "settlement_id": f"SETTLE-SHORT-{settle_seq}",
            "merchant_id": m_id,
            "consignment_id": cons_id,
            "order_id": ord_id,
            "courier_name": courier_name,
            "statement_date": (ord_time + timedelta(days=2)).strftime("%Y-%m-%d"),
            "cod_collected_usd": cod_amt,
            "courier_fee_usd": courier_fee,
            "expected_net_payout_usd": expected_net,
            "actual_settled_usd": actual_settled,
            "payout_status": "PARTIAL",
        })

        ground_truth["courier_shortfalls"].append({
            "consignment_id": cons_id,
            "order_id": ord_id,
            "merchant_id": m_id,
            "courier_name": courier_name,
            "expected_net_usd": expected_net,
            "actual_settled_usd": actual_settled,
            "shortfall_usd": planted_shortfall,
            "shortfall_taka": planted_shortfall,
        })

    # 5. Plant Ground-Truth Category C: 18 Fuzzy-Matched True Negatives
    for idx in range(18):
        m_id = MERCHANTS[idx % len(MERCHANTS)]["id"]
        order_seq += 1
        payment_seq += 1
        ord_id = f"ORD-FUZZY-TN-{order_seq}"
        cust = generate_customer()
        amt = round(float(random.choice([145.0, 220.0, 310.0, 480.0, 560.0])), 2)
        ord_time = base_date + timedelta(days=10 + idx, hours=11, minutes=15)
        pay_time = ord_time + timedelta(minutes=random.randint(3, 16))
        rail_prov = "Stripe" if idx % 2 == 0 else "PayPal"

        orders_records.append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "customer_name": cust["name"],
            "customer_email": cust["email"],
            "customer_phone": cust["phone"],
            "order_timestamp": ord_time.isoformat(),
            "order_amount_usd": amt,
            "currency": "USD",
            "quantity": 1,
            "unit_price_usd": amt,
            "shipping_cost_usd": 0.0,
            "sku": catalog[m_id][0]["sku"],
            "payment_rail": "PAYMENT_GATEWAY" if rail_prov == "Stripe" else "DIGITAL_WALLET",
            "rail_provider": rail_prov,
            "order_status": "DELIVERED",
            "transaction_ref": "",
        })

        rail_payments_records.append({
            "payment_id": f"RP-FUZZY-{payment_seq}",
            "merchant_id": m_id,
            "rail_provider": rail_prov,
            "transaction_ref": f"TXN-STRIPE-ALT-{random.randint(100000, 999999)}",
            "amount_usd": amt,
            "currency": "USD",
            "payment_timestamp": pay_time.isoformat(),
            "customer_phone": cust["phone"],
            "customer_email": cust["email"],
            "status": "SUCCESS",
        })

        ground_truth["fuzzy_true_negatives"].append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "customer_phone": cust["phone"],
            "customer_email": cust["email"],
            "amount_usd": amt,
            "amount_taka": amt,
            "expected_outcome": "RECONCILED_VIA_PASS2",
        })

    # 6. Plant Ground-Truth Category D: Failed/Abandoned Checkouts
    failed_merchants = ["MERCH_01", "MERCH_02", "MERCH_03", "MERCH_06", "MERCH_09", "MERCH_12", "MERCH_15", "MERCH_18"]
    for idx, m_id in enumerate(failed_merchants):
        order_seq += 1
        ord_id = f"ORD-FAIL-{order_seq}"
        cust = generate_customer()
        basket_amt = round(float(random.choice([180.0, 320.0, 540.0, 890.0, 1150.0])), 2)
        fail_time = base_date + timedelta(days=28, hours=15 + (idx % 6))

        orders_records.append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "customer_name": cust["name"],
            "customer_email": cust["email"],
            "customer_phone": cust["phone"],
            "order_timestamp": fail_time.isoformat(),
            "order_amount_usd": basket_amt,
            "currency": "USD",
            "quantity": 1,
            "unit_price_usd": basket_amt,
            "shipping_cost_usd": 0.0,
            "sku": catalog[m_id][0]["sku"],
            "payment_rail": "PAYMENT_GATEWAY",
            "rail_provider": "Stripe",
            "order_status": "FAILED",
            "transaction_ref": "",
        })

        ground_truth["failed_abandoned_checkouts"].append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "customer_phone": cust["phone"],
            "customer_email": cust["email"],
            "basket_amount_usd": basket_amt,
            "basket_amount_taka": basket_amt,
            "rail_provider": "Stripe",
        })

    # 7. Plant Ground-Truth Category E: 6 Hard Stress-Test Edge Cases
    # Case 1 & 2: 2 Delayed 48-Hour Bank Settlement orders (legitimate payment settled 48h after order)
    # Case 3 & 4: 2 Partial Payment orders (customer paid 60% via wallet and 40% via bank wire)
    # Case 5 & 6: 2 Ambiguous Duplicate Phone orders (same customer placed 2 identical orders within 20m, paid for 1)
    ground_truth["stress_test_edge_cases"] = []

    stress_delay_merchants = ["MERCH_01", "MERCH_02"]
    for idx, m_id in enumerate(stress_delay_merchants):
        ord_id = f"ORD-STRESS-DELAY-{idx + 1}"
        cust = generate_customer()
        amt = 850.0 if idx == 0 else 1255.0
        ord_time = base_date + timedelta(days=22 + idx, hours=10)
        pay_time = ord_time + timedelta(hours=48)  # 48 hours later, outside 30-min window!

        orders_records.append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "customer_name": cust["name"],
            "customer_email": cust["email"],
            "customer_phone": cust["phone"],
            "order_timestamp": ord_time.isoformat(),
            "order_amount_usd": amt,
            "currency": "USD",
            "quantity": 1,
            "unit_price_usd": amt,
            "shipping_cost_usd": 0.0,
            "sku": catalog[m_id][0]["sku"],
            "payment_rail": "BANK_TRANSFER",
            "rail_provider": "SEPA Wire",
            "order_status": "DISPATCHED",
            "transaction_ref": "",
        })

        rail_payments_records.append({
            "payment_id": f"RP-STRESS-DELAY-{idx + 1}",
            "merchant_id": m_id,
            "rail_provider": "SEPA Wire",
            "transaction_ref": f"WIRE-LATE-{random.randint(100000, 999999)}",
            "amount_usd": amt,
            "currency": "USD",
            "payment_timestamp": pay_time.isoformat(),
            "customer_phone": cust["phone"],
            "customer_email": cust["email"],
            "status": "SUCCESS",
        })

        ground_truth["stress_test_edge_cases"].append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "case_type": "DELAYED_48H_SETTLEMENT",
            "expected_classification": "FALSE_POSITIVE",
            "is_actual_leak": False,
            "amount_usd": amt,
            "explanation": "Legitimate SEPA Wire settled 48h after order dispatch, exceeding the 30-minute fuzzy matching window",
        })

    stress_partial_merchants = ["MERCH_03", "MERCH_04"]
    for idx, m_id in enumerate(stress_partial_merchants):
        ord_id = f"ORD-STRESS-PARTIAL-{idx + 1}"
        cust = generate_customer()
        total_amt = 500.0 if idx == 0 else 650.0
        amt_60 = round(total_amt * 0.60, 2)
        amt_40 = round(total_amt * 0.40, 2)
        ord_time = base_date + timedelta(days=20 + idx, hours=12)

        orders_records.append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "customer_name": cust["name"],
            "customer_email": cust["email"],
            "customer_phone": cust["phone"],
            "order_timestamp": ord_time.isoformat(),
            "order_amount_usd": total_amt,
            "currency": "USD",
            "quantity": 1,
            "unit_price_usd": total_amt,
            "shipping_cost_usd": 0.0,
            "sku": catalog[m_id][0]["sku"],
            "payment_rail": "DIGITAL_WALLET",
            "rail_provider": "PayPal",
            "order_status": "DISPATCHED",
            "transaction_ref": "",
        })

        rail_payments_records.append({
            "payment_id": f"RP-STRESS-PARTIAL-{idx + 1}-A",
            "merchant_id": m_id,
            "rail_provider": "PayPal",
            "transaction_ref": f"PAYPAL-PARTIAL-{random.randint(100000, 999999)}",
            "amount_usd": amt_60,
            "currency": "USD",
            "payment_timestamp": (ord_time + timedelta(minutes=5)).isoformat(),
            "customer_phone": cust["phone"],
            "customer_email": cust["email"],
            "status": "SUCCESS",
        })

        rail_payments_records.append({
            "payment_id": f"RP-STRESS-PARTIAL-{idx + 1}-B",
            "merchant_id": m_id,
            "rail_provider": "SEPA Wire",
            "transaction_ref": f"WIRE-PARTIAL-{random.randint(100000, 999999)}",
            "amount_usd": amt_40,
            "currency": "USD",
            "payment_timestamp": (ord_time + timedelta(hours=2)).isoformat(),
            "customer_phone": cust["phone"],
            "customer_email": cust["email"],
            "status": "SUCCESS",
        })

        ground_truth["stress_test_edge_cases"].append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "case_type": "PARTIAL_SPLIT_PAYMENT",
            "expected_classification": "TRUE_POSITIVE",
            "is_actual_leak": True,
            "amount_usd": total_amt,
            "explanation": f"Customer split payment (${amt_60} wallet + ${amt_40} wire); single-transaction matching cannot reconcile multi-leg split payments",
        })

    stress_dup_merchants = ["MERCH_05", "MERCH_06"]
    for idx, m_id in enumerate(stress_dup_merchants):
        ord_id_1 = f"ORD-STRESS-DUP-{idx * 2 + 1}"
        ord_id_2 = f"ORD-STRESS-DUP-{idx * 2 + 2}"
        cust = generate_customer()
        dup_amt = 320.0
        ord_time_1 = base_date + timedelta(days=21 + idx, hours=14, minutes=10)
        ord_time_2 = ord_time_1 + timedelta(minutes=18)

        orders_records.append({
            "order_id": ord_id_1,
            "merchant_id": m_id,
            "customer_name": cust["name"],
            "customer_email": cust["email"],
            "customer_phone": cust["phone"],
            "order_timestamp": ord_time_1.isoformat(),
            "order_amount_usd": dup_amt,
            "currency": "USD",
            "quantity": 1,
            "unit_price_usd": dup_amt,
            "shipping_cost_usd": 0.0,
            "sku": catalog[m_id][0]["sku"],
            "payment_rail": "PAYMENT_GATEWAY",
            "rail_provider": "Stripe",
            "order_status": "DELIVERED",
            "transaction_ref": "",
        })

        orders_records.append({
            "order_id": ord_id_2,
            "merchant_id": m_id,
            "customer_name": cust["name"],
            "customer_email": cust["email"],
            "customer_phone": cust["phone"],
            "order_timestamp": ord_time_2.isoformat(),
            "order_amount_usd": dup_amt,
            "currency": "USD",
            "quantity": 1,
            "unit_price_usd": dup_amt,
            "shipping_cost_usd": 0.0,
            "sku": catalog[m_id][0]["sku"],
            "payment_rail": "PAYMENT_GATEWAY",
            "rail_provider": "Stripe",
            "order_status": "DISPATCHED",
            "transaction_ref": "",
        })

        rail_payments_records.append({
            "payment_id": f"RP-STRESS-DUP-{idx + 1}",
            "merchant_id": m_id,
            "rail_provider": "Stripe",
            "transaction_ref": f"TXN-STRIPE-DUP-{random.randint(100000, 999999)}",
            "amount_usd": dup_amt,
            "currency": "USD",
            "payment_timestamp": (ord_time_1 + timedelta(minutes=6)).isoformat(),
            "customer_phone": cust["phone"],
            "customer_email": cust["email"],
            "status": "SUCCESS",
        })

        ground_truth["stress_test_edge_cases"].append({
            "order_id": ord_id_2,
            "merchant_id": m_id,
            "case_type": "AMBIGUOUS_DUPLICATE_ORDER",
            "expected_classification": "TRUE_POSITIVE",
            "is_actual_leak": True,
            "amount_usd": dup_amt,
            "explanation": "Duplicate order placed 18m apart with identical phone and amount; only first order paid, second dispatched without payment",
        })

    # Convert to DataFrames
    df_orders = pd.DataFrame(orders_records)
    df_payments = pd.DataFrame(rail_payments_records)
    df_settlements = pd.DataFrame(courier_settlements_records)
    df_inventory = pd.DataFrame(inventory_records)

    # Save to CSV
    suffix = "_heldout" if is_heldout else ""
    df_orders.to_csv(os.path.join(out_dir, f"orders{suffix}.csv"), index=False)
    df_payments.to_csv(os.path.join(out_dir, f"rail_payments{suffix}.csv"), index=False)
    df_settlements.to_csv(os.path.join(out_dir, f"courier_settlements{suffix}.csv"), index=False)
    df_inventory.to_csv(os.path.join(out_dir, f"inventory_daily{suffix}.csv"), index=False)

    # Save Ground Truth JSON
    gt_filename = "ground_truth_heldout.json" if is_heldout else "ground_truth.json"
    gt_path = os.path.join(out_dir, gt_filename)
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    # Ingest into DuckDB
    duckdb_filename = "paylens_heldout.duckdb" if is_heldout else "paylens.duckdb"
    duckdb_path = os.path.join(out_dir, duckdb_filename)
    if os.path.exists(duckdb_path):
        os.remove(duckdb_path)

    con = duckdb.connect(duckdb_path)
    con.execute("CREATE TABLE orders AS SELECT * FROM df_orders")
    con.execute("CREATE TABLE rail_payments AS SELECT * FROM df_payments")
    con.execute("CREATE TABLE courier_settlements AS SELECT * FROM df_settlements")
    con.execute("CREATE TABLE inventory_daily AS SELECT * FROM df_inventory")
    con.close()

    print(f"Generated Synthetic Dataset ({'held-out seed 1337' if is_heldout else 'seed ' + str(seed)}):")
    print(f"  - Orders: {len(df_orders):,} rows")
    print(f"  - Rail Payments: {len(df_payments):,} rows")
    print(f"  - Carrier Settlements: {len(df_settlements):,} rows")
    print(f"  - Inventory Snapshots: {len(df_inventory):,} rows")
    print(f"  - DuckDB: {duckdb_path}")
    print(f"  - Ground Truth: {gt_path}")

    # Generate sample carrier settlement PDF if not held-out
    if not is_heldout:
        generate_sample_courier_pdf(out_dir)


def generate_sample_courier_pdf(output_dir=None):
    """Generate sample carrier settlement PDF with USD amounts for Evolus Document Extractor."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        out_dir = output_dir or OUTPUT_DIR
        pdf_path = os.path.join(out_dir, "sample_courier_settlement.pdf")
        doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=8,
        )
        sub_style = ParagraphStyle(
            'SubStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#475569'),
            spaceAfter=14,
        )

        story.append(Paragraph("DHL Express / FedEx Commercial COD Settlement Statement", title_style))
        story.append(Paragraph(f"Merchant: Lumina Smart Home & Audio (MERCH_02) | Statement Date: 2026-10-15 | Currency: USD ($)", sub_style))
        story.append(Spacer(1, 10))

        real_rows = []
        db_file = os.path.join(out_dir, "paylens.duckdb")
        if os.path.exists(db_file):
            import duckdb
            c_db = duckdb.connect(db_file, read_only=True)
            try:
                sf = c_db.execute("SELECT consignment_id, order_id, courier_name, cod_collected_usd, courier_fee_usd, expected_net_payout_usd, actual_settled_usd, payout_status FROM courier_settlements WHERE actual_settled_usd < expected_net_payout_usd LIMIT 3").fetchall()
                stld = c_db.execute("SELECT consignment_id, order_id, courier_name, cod_collected_usd, courier_fee_usd, expected_net_payout_usd, actual_settled_usd, payout_status FROM courier_settlements WHERE actual_settled_usd = expected_net_payout_usd LIMIT 2").fetchall()
                for r in sf:
                    real_rows.append([r[0], r[1], r[2], f"${r[3]:,.2f}", f"${r[4]:,.2f}", f"${r[5]:,.2f}", f"${r[6]:,.2f}", "PARTIAL SHORTFALL"])
                for r in stld:
                    real_rows.append([r[0], r[1], r[2], f"${r[3]:,.2f}", f"${r[4]:,.2f}", f"${r[5]:,.2f}", f"${r[6]:,.2f}", "SETTLED"])
            finally:
                c_db.close()

        if not real_rows:
            real_rows = [
                ["CONS-SHORT-9001", "ORD-COD-SHORT-3143", "DHL Express", "$850.00", "$44.00", "$806.00", "$686.00", "PARTIAL SHORTFALL"],
                ["CONS-SHORT-9002", "ORD-COD-SHORT-3144", "FedEx Ground", "$620.00", "$34.80", "$585.20", "$500.20", "PARTIAL SHORTFALL"],
                ["CONS-CLEAN-9003", "ORD-3120", "DHL Express", "$450.00", "$24.25", "$425.75", "$425.75", "SETTLED"],
                ["CONS-CLEAN-9004", "ORD-3121", "FedEx Ground", "$320.00", "$19.70", "$300.30", "$300.30", "SETTLED"],
                ["CONS-SHORT-9005", "ORD-COD-SHORT-3147", "DHL Express", "$1,100.00", "$54.00", "$1,046.00", "$871.00", "PARTIAL SHORTFALL"],
            ]

        data = [
            ["Consignment ID", "Order ID", "Carrier", "COD Collected ($)", "Fee ($)", "Expected Net ($)", "Actual Settled ($)", "Status"]
        ] + real_rows

        t = Table(data, colWidths=[90, 95, 75, 75, 50, 75, 75, 75])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1E293B')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TEXTCOLOR', (7, 1), (7, len(real_rows)), colors.HexColor('#DC2626')),
        ]))

        story.append(t)
        doc.build(story)
        print(f"  - Sample PDF generated: {pdf_path}")
    except Exception as e:
        print(f"  - PDF generation note: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Synthetic Data Generator for PayLens")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default 42)")
    parser.add_argument("--noise", action="store_true", help="Inject realistic noise cases")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory")
    parser.add_argument("--generate-both-seeds", action="store_true", help="Generate both seed 42 and seed 1337 held-out")
    args = parser.parse_args()

    target_dir = args.output_dir or OUTPUT_DIR
    if args.generate_both_seeds:
        print("Generating tuning dataset (seed 42)...")
        generate_dataset(seed=42, noise=args.noise, output_dir=target_dir, is_heldout=False)
        print("\nGenerating held-out dataset (seed 1337)...")
        generate_dataset(seed=1337, noise=args.noise, output_dir=target_dir, is_heldout=True)
    else:
        generate_dataset(seed=args.seed, noise=args.noise, output_dir=target_dir, is_heldout=(args.seed != 42))

