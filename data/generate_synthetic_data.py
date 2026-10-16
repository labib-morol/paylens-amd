"""Synthetic Data Generator for PayLens Solo.

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


def build_sku_catalog():
    catalog = {}
    for m in MERCHANTS:
        m_id = m["id"]
        if m_id == "MERCH_02":
            # Lumina Smart Home & Audio: includes Hero high-margin SKU
            catalog[m_id] = [
                {
                    "sku": "SKU-LUM-HERO-01",
                    "item_name": "Aura Wireless Hi-Fi Studio Monitor (Pair)",
                    "unit_cost_usd": 790.0,
                    "unit_retail_price_usd": 1255.0,
                    "unit_margin_usd": 465.0,
                    "supplier_lead_time_days": 7,
                    "initial_stock": 75,
                    "is_hero": True,
                },
                {
                    "sku": "SKU-LUM-02",
                    "item_name": "Lumina Smart Beam Ambient Projector",
                    "unit_cost_usd": 240.0,
                    "unit_retail_price_usd": 480.0,
                    "unit_margin_usd": 240.0,
                    "supplier_lead_time_days": 5,
                    "initial_stock": 120,
                    "is_hero": False,
                },
                {
                    "sku": "SKU-LUM-03",
                    "item_name": "Acoustic Noise-Cancelling Soundbar",
                    "unit_cost_usd": 350.0,
                    "unit_retail_price_usd": 580.0,
                    "unit_margin_usd": 230.0,
                    "supplier_lead_time_days": 10,
                    "initial_stock": 50,
                    "is_hero": False,
                },
            ]
        elif m_id == "MERCH_01":
            catalog[m_id] = [
                {
                    "sku": "SKU-APX-01",
                    "item_name": "Merino Wool Performance Blazer",
                    "unit_cost_usd": 110.0,
                    "unit_retail_price_usd": 275.0,
                    "unit_margin_usd": 165.0,
                    "supplier_lead_time_days": 6,
                    "initial_stock": 150,
                    "is_hero": False,
                },
                {
                    "sku": "SKU-APX-02",
                    "item_name": "Tailored Oxford Tech Shirt",
                    "unit_cost_usd": 35.0,
                    "unit_retail_price_usd": 95.0,
                    "unit_margin_usd": 60.0,
                    "supplier_lead_time_days": 4,
                    "initial_stock": 200,
                    "is_hero": False,
                },
                {
                    "sku": "SKU-APX-03",
                    "item_name": "Water-Repellent Commuter Mac Coat",
                    "unit_cost_usd": 140.0,
                    "unit_retail_price_usd": 320.0,
                    "unit_margin_usd": 180.0,
                    "supplier_lead_time_days": 8,
                    "initial_stock": 80,
                    "is_hero": False,
                },
            ]
        else:
            cat_name = m["category"].split()[0]
            catalog[m_id] = [
                {
                    "sku": f"SKU-{m_id[6:]}-A",
                    "item_name": f"Premium {cat_name} Edition A",
                    "unit_cost_usd": float(random.randint(40, 150)),
                    "unit_retail_price_usd": float(random.randint(160, 350)),
                    "supplier_lead_time_days": random.randint(4, 9),
                    "initial_stock": random.randint(80, 200),
                    "is_hero": False,
                },
                {
                    "sku": f"SKU-{m_id[6:]}-B",
                    "item_name": f"Standard {cat_name} Everyday B",
                    "unit_cost_usd": float(random.randint(20, 60)),
                    "unit_retail_price_usd": float(random.randint(70, 150)),
                    "supplier_lead_time_days": random.randint(3, 7),
                    "initial_stock": random.randint(100, 250),
                    "is_hero": False,
                },
            ]
            for it in catalog[m_id]:
                it["unit_margin_usd"] = it["unit_retail_price_usd"] - it["unit_cost_usd"]
    return catalog


def generate_dataset():
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
            curr_stock = sku_info["initial_stock"]
            lead_time = sku_info["supplier_lead_time_days"]
            is_hero = sku_info.get("is_hero", False)

            for day_idx in range(30):
                snapshot_dt = (base_date + timedelta(days=day_idx)).date()

                # Surge on day 22-30 for hero SKU and pre-holiday demand
                if is_hero and day_idx >= 22:
                    units_sold = random.randint(14, 22)  # Rapid depletion
                elif day_idx >= 24:
                    units_sold = random.randint(8, 16)
                else:
                    units_sold = random.randint(2, 6)

                curr_stock = max(0, curr_stock - units_sold)

                # Restock event on day 15 for normal SKUs
                if day_idx == 15 and not is_hero:
                    curr_stock += random.randint(40, 80)

                inventory_records.append({
                    "snapshot_date": str(snapshot_dt),
                    "merchant_id": m_id,
                    "sku": sku_info["sku"],
                    "item_name": sku_info["item_name"],
                    "current_stock": curr_stock,
                    "units_sold_today": units_sold,
                    "unit_cost_usd": sku_info["unit_cost_usd"],
                    "unit_retail_price_usd": sku_info["unit_retail_price_usd"],
                    "unit_margin_usd": sku_info["unit_margin_usd"],
                    "supplier_lead_time_days": lead_time,
                    "is_hero": is_hero,
                })

            # Ground truth stockout check on latest day
            # If current_stock / avg_sales < lead_time
            recent_sales = [r["units_sold_today"] for r in inventory_records if r["merchant_id"] == m_id and r["sku"] == sku_info["sku"]][-7:]
            avg_daily = sum(recent_sales) / max(1, len(recent_sales))
            days_cover = curr_stock / max(0.1, avg_daily)
            if days_cover < lead_time:
                lost_units = max(0, round((lead_time - days_cover) * avg_daily, 1))
                lost_margin = round(lost_units * sku_info["unit_margin_usd"], 2)
                ground_truth["stockout_skus"].append({
                    "merchant_id": m_id,
                    "sku": sku_info["sku"],
                    "item_name": sku_info["item_name"],
                    "current_stock": curr_stock,
                    "supplier_lead_time_days": lead_time,
                    "forecast_daily_demand": round(avg_daily, 2),
                    "days_of_cover": round(days_cover, 2),
                    "lost_units": lost_units,
                    "unit_margin_usd": sku_info["unit_margin_usd"],
                    "impact_usd": lost_margin,
                    "is_hero": is_hero,
                })

    # 2. Generate Orders and Payment Rail records across 30 days
    # Platforms: Stripe Gateway, PayPal Wallet, SEPA Wire, DHL/FedEx Courier COD
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
            # 4 to 8 orders per merchant per day
            num_orders = random.randint(4, 8)

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

                status = "DELIVERED" if day_idx < 25 else "DISPATCHED"

                order_row = {
                    "order_id": ord_id,
                    "merchant_id": m_id,
                    "customer_name": cust["name"],
                    "customer_email": cust["email"],
                    "customer_phone": cust["phone"],
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
                }
                orders_records.append(order_row)

                # Digital rails generate rail_payments
                if rail_type in ("PAYMENT_GATEWAY", "DIGITAL_WALLET", "BANK_TRANSFER"):
                    payment_seq += 1
                    pay_time = ord_time + timedelta(minutes=random.randint(2, 12))
                    rail_payments_records.append({
                        "payment_id": f"RP-{payment_seq}",
                        "merchant_id": m_id,
                        "rail_provider": rail_prov,
                        "transaction_ref": txn_ref,
                        "amount_usd": total_amt,
                        "currency": "USD",
                        "payment_timestamp": pay_time.isoformat(),
                        "customer_phone": cust["phone"],
                        "customer_email": cust["email"],
                        "status": "SUCCESS",
                    })

                # Courier COD rails generate courier_settlements
                elif rail_type == "COURIER_COD":
                    settle_seq += 1
                    consignment_seq += 1
                    cod_fee = round(total_amt * 0.035 + 8.50, 2)
                    net_expected = round(total_amt - cod_fee, 2)
                    actual_settled = net_expected  # Default clean

                    courier_settlements_records.append({
                        "settlement_id": f"SETTLE-{settle_seq}",
                        "merchant_id": m_id,
                        "consignment_id": f"CONS-{consignment_seq}",
                        "order_id": ord_id,
                        "courier_name": rail_prov,
                        "statement_date": (ord_time + timedelta(days=3)).strftime("%Y-%m-%d"),
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
    # Missing transaction_ref in orders, but matched by phone/email + exact amount + timestamp within 18 mins
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

        # Order has NO transaction_ref
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
            "transaction_ref": "",  # Missing ref!
        })

        # Payment record exists with matching customer, amount, and close timestamp
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

    # Convert to DataFrames
    df_orders = pd.DataFrame(orders_records)
    df_payments = pd.DataFrame(rail_payments_records)
    df_settlements = pd.DataFrame(courier_settlements_records)
    df_inventory = pd.DataFrame(inventory_records)

    # Save to CSV
    df_orders.to_csv(os.path.join(OUTPUT_DIR, "orders.csv"), index=False)
    df_payments.to_csv(os.path.join(OUTPUT_DIR, "rail_payments.csv"), index=False)
    df_settlements.to_csv(os.path.join(OUTPUT_DIR, "courier_settlements.csv"), index=False)
    df_inventory.to_csv(os.path.join(OUTPUT_DIR, "inventory_daily.csv"), index=False)

    # Save Ground Truth JSON
    gt_path = os.path.join(OUTPUT_DIR, "ground_truth.json")
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    # Ingest into DuckDB
    duckdb_path = os.path.join(OUTPUT_DIR, "paylens.duckdb")
    if os.path.exists(duckdb_path):
        os.remove(duckdb_path)

    con = duckdb.connect(duckdb_path)
    con.execute("CREATE TABLE orders AS SELECT * FROM df_orders")
    con.execute("CREATE TABLE rail_payments AS SELECT * FROM df_payments")
    con.execute("CREATE TABLE courier_settlements AS SELECT * FROM df_settlements")
    con.execute("CREATE TABLE inventory_daily AS SELECT * FROM df_inventory")
    con.close()

    print(f"Generated Synthetic Dataset successfully:")
    print(f"  - Orders: {len(df_orders):,} rows")
    print(f"  - Rail Payments: {len(df_payments):,} rows")
    print(f"  - Carrier Settlements: {len(df_settlements):,} rows")
    print(f"  - Inventory Snapshots: {len(df_inventory):,} rows")
    print(f"  - DuckDB: {duckdb_path}")
    print(f"  - Ground Truth: {gt_path}")

    # Generate sample carrier settlement PDF
    generate_sample_courier_pdf()


def generate_sample_courier_pdf():
    """Generate sample carrier settlement PDF with USD amounts for Evolus Document Extractor."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

        pdf_path = os.path.join(OUTPUT_DIR, "sample_courier_settlement.pdf")
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

        # Sample settlement table with shortfall rows
        data = [
            ["Consignment ID", "Order ID", "Carrier", "COD Collected ($)", "Fee ($)", "Expected Net ($)", "Actual Settled ($)", "Status"],
            ["CONS-SHORT-9001", "ORD-COD-SHORT-3143", "DHL Express", "$850.00", "$44.00", "$806.00", "$686.00", "PARTIAL SHORTFALL"],
            ["CONS-SHORT-9002", "ORD-COD-SHORT-3144", "FedEx Ground", "$620.00", "$34.80", "$585.20", "$500.20", "PARTIAL SHORTFALL"],
            ["CONS-CLEAN-9003", "ORD-3120", "DHL Express", "$450.00", "$24.25", "$425.75", "$425.75", "SETTLED"],
            ["CONS-CLEAN-9004", "ORD-3121", "FedEx Ground", "$320.00", "$19.70", "$300.30", "$300.30", "SETTLED"],
            ["CONS-SHORT-9005", "ORD-COD-SHORT-3147", "DHL Express", "$1,100.00", "$54.00", "$1,046.00", "$871.00", "PARTIAL SHORTFALL"],
        ]

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
            ('TEXTCOLOR', (7, 1), (7, 2), colors.HexColor('#DC2626')),
            ('TEXTCOLOR', (7, 5), (7, 5), colors.HexColor('#DC2626')),
        ]))

        story.append(t)
        doc.build(story)
        print(f"  - Sample PDF generated: {pdf_path}")
    except Exception as e:
        print(f"  - PDF generation note: {e}")


if __name__ == "__main__":
    generate_dataset()
