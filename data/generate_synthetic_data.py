"""Synthetic Data Generator for PayLens Solo.

Generates 30 days of realistic multi-rail commerce data for 20 Bangladeshi online merchants:
- Orders across MFS, Card Gateways, Bank Transfers, and Courier COD
- Disconnected payment rail logs (bKash, Nagad, SSLCommerz, Bank statements)
- Courier COD settlements (Steadfast, RedX, Pathao) with planted shortfalls
- Daily inventory snapshots with Pre-Eid demand surges and stockout risks
- Exact ground truth JSON with planted leaks, shortfalls, fuzzy True Negatives, and hero stockout SKUs.
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

# 20 Bangladeshi Merchants
MERCHANTS = [
    {"id": "MERCH_01", "name": "Dhaka Threads & Lifestyle", "category": "Apparel & Fashion"},
    {"id": "MERCH_02", "name": "Chattogram Artisans & Home", "category": "Home Decor & Crafts"},
    {"id": "MERCH_03", "name": "Sylhet Tea & Organic Pantry", "category": "Food & Beverage"},
    {"id": "MERCH_04", "name": "Rajshahi Silk Heritage", "category": "Traditional Fashion"},
    {"id": "MERCH_05", "name": "Khulna Marine & Leathercraft", "category": "Leather Goods"},
    {"id": "MERCH_06", "name": "Barishal Agro Essentials", "category": "Agro & Groceries"},
    {"id": "MERCH_07", "name": "Rangpur Loom & Crafts", "category": "Home Textiles"},
    {"id": "MERCH_08", "name": "Mymensingh Dairy & Provisions", "category": "Dairy & Pantry"},
    {"id": "MERCH_09", "name": "Comilla Khadi Collection", "category": "Handloom Fashion"},
    {"id": "MERCH_10", "name": "Bogura Sweets & Delicacies", "category": "Specialty Food"},
    {"id": "MERCH_11", "name": "Cox's Pearl & Coastwear", "category": "Jewelry & Resortwear"},
    {"id": "MERCH_12", "name": "Narayanganj Knitwear Express", "category": "Apparel Manufacturing"},
    {"id": "MERCH_13", "name": "Gazipur Electronics Depot", "category": "Consumer Gadgets"},
    {"id": "MERCH_14", "name": "Tangail Saree Emporium", "category": "Traditional Sarees"},
    {"id": "MERCH_15", "name": "Kushtia Musical & Arts", "category": "Musical & Cultural"},
    {"id": "MERCH_16", "name": "Dinajpur Aromatic Grains", "category": "Premium Rice & Agro"},
    {"id": "MERCH_17", "name": "Pabna Handloom Weaves", "category": "Loom Fabrics"},
    {"id": "MERCH_18", "name": "Faridpur Jute Innovations", "category": "Eco & Jute Lifestyle"},
    {"id": "MERCH_19", "name": "Feni Tech Accessories", "category": "Mobile & PC Parts"},
    {"id": "MERCH_20", "name": "Jessore Floral & Natural Cosmetics", "category": "Herbal Care"},
]

BANGLA_NAMES = [
    "Tanvir Ahmed", "Rahim Uddin", "Farhana Yasmin", "Nusrat Jahan", "Kamal Hossain",
    "Sadia Afrin", "Mahmudul Hasan", "Anika Tabassum", "Zubair Rahman", "Mehedi Hasan",
    "Sultana Razia", "Tariqul Islam", "Rokeya Begum", "Arifur Rahman", "Shakil Khan",
    "Tasnim Ferdous", "Nahid Parvez", "Shirin Akhter", "Kazi Nazrul", "Moniruzzaman",
]

PHONE_PREFIXES = ["017", "018", "019", "016", "013", "014", "015"]

def generate_bangla_phone() -> str:
    prefix = random.choice(PHONE_PREFIXES)
    suffix = "".join([str(random.randint(0, 9)) for _ in range(8)])
    return f"{prefix}{suffix}"

# SKUs catalogue for each merchant
def build_sku_catalog():
    catalog = {}
    for m in MERCHANTS:
        m_id = m["id"]
        if m_id == "MERCH_02":
            # Chattogram Artisans & Home: include Hero SKU
            catalog[m_id] = [
                {
                    "sku": "SKU-CAH-HERO-01",
                    "item_name": "Handcrafted Chittagong Brass Chandelier",
                    "unit_cost_taka": 7900.0,
                    "unit_retail_price_taka": 12550.0,
                    "unit_margin_taka": 4650.0,
                    "supplier_lead_time_days": 7,
                    "initial_stock": 75,
                    "is_hero": True,
                },
                {
                    "sku": "SKU-CAH-02",
                    "item_name": "Teak Wood Nakshi Carved Tray",
                    "unit_cost_taka": 1200.0,
                    "unit_retail_price_taka": 2400.0,
                    "unit_margin_taka": 1200.0,
                    "supplier_lead_time_days": 5,
                    "initial_stock": 120,
                    "is_hero": False,
                },
                {
                    "sku": "SKU-CAH-03",
                    "item_name": "Natural Cane Lounge Chair",
                    "unit_cost_taka": 3500.0,
                    "unit_retail_price_taka": 5800.0,
                    "unit_margin_taka": 2300.0,
                    "supplier_lead_time_days": 10,
                    "initial_stock": 50,
                    "is_hero": False,
                },
            ]
        elif m_id == "MERCH_01":
            catalog[m_id] = [
                {
                    "sku": "SKU-DTL-01",
                    "item_name": "Jamdani Embroidered Panjabi",
                    "unit_cost_taka": 1800.0,
                    "unit_retail_price_taka": 3800.0,
                    "unit_margin_taka": 2000.0,
                    "supplier_lead_time_days": 6,
                    "initial_stock": 140,
                    "is_hero": False,
                },
                {
                    "sku": "SKU-DTL-02",
                    "item_name": "Cotton Formal Trousers",
                    "unit_cost_taka": 850.0,
                    "unit_retail_price_taka": 1650.0,
                    "unit_margin_taka": 800.0,
                    "supplier_lead_time_days": 4,
                    "initial_stock": 200,
                    "is_hero": False,
                },
            ]
        else:
            cat_name = m["category"].split()[0]
            catalog[m_id] = [
                {
                    "sku": f"SKU-{m_id}-A",
                    "item_name": f"{cat_name} Signature Product A",
                    "unit_cost_taka": 1000.0 + (int(m_id.split('_')[1]) * 50),
                    "unit_retail_price_taka": 2200.0 + (int(m_id.split('_')[1]) * 100),
                    "unit_margin_taka": 1200.0 + (int(m_id.split('_')[1]) * 50),
                    "supplier_lead_time_days": 5,
                    "initial_stock": 100,
                    "is_hero": False,
                },
                {
                    "sku": f"SKU-{m_id}-B",
                    "item_name": f"{cat_name} Value Line B",
                    "unit_cost_taka": 450.0,
                    "unit_retail_price_taka": 950.0,
                    "unit_margin_taka": 500.0,
                    "supplier_lead_time_days": 4,
                    "initial_stock": 180,
                    "is_hero": False,
                },
            ]
    return catalog


def main():
    start_date = datetime(2026, 9, 16, 9, 0, 0)
    days_count = 30
    catalog = build_sku_catalog()

    orders = []
    rail_payments = []
    courier_settlements = []

    # Ground truth tracking structures
    ground_truth = {
        "dispatched_unpaid": [],
        "courier_shortfalls": [],
        "fuzzy_true_negatives": [],
        "failed_abandoned_checkouts": [],
        "stockout_skus": [],
    }

    order_seq = 1000
    rail_seq = 5000
    settle_seq = 8000

    # Tracking for daily SKU sales to populate inventory_daily
    daily_sku_sales = {}  # (m_id, sku, day_idx) -> units_sold

    for m in MERCHANTS:
        m_id = m["id"]
        skus = catalog[m_id]
        for s in skus:
            for d in range(days_count):
                daily_sku_sales[(m_id, s["sku"], d)] = 0

    # 1. Generate normal regular orders across the 30 days
    for day_idx in range(days_count):
        current_day = start_date + timedelta(days=day_idx)
        # Pre-Eid surge applies to the last 8 days (day_idx >= 22)
        is_pre_eid = (day_idx >= 22)

        for m in MERCHANTS:
            m_id = m["id"]
            skus = catalog[m_id]

            # Determine number of regular orders today
            base_orders = random.randint(2, 4)
            if is_pre_eid:
                base_orders += random.randint(1, 3)

            for _ in range(base_orders):
                order_seq += 1
                ord_id = f"ORD-{order_seq}"
                sku_info = random.choice(skus)
                qty = random.randint(1, 3)

                # Surge demand for Hero SKU on MERCH_02 during Pre-Eid
                if sku_info.get("is_hero") and is_pre_eid:
                    qty = random.randint(3, 5)

                daily_sku_sales[(m_id, sku_info["sku"], day_idx)] += qty

                order_amt = round(qty * sku_info["unit_retail_price_taka"], 2)
                shipping_cost = 100.0 if random.random() < 0.7 else 150.0
                cust_phone = generate_bangla_phone()
                cust_name = random.choice(BANGLA_NAMES)

                # Order timestamp during business hours
                sec_offset = random.randint(0, 3600 * 12)
                ord_time = current_day + timedelta(seconds=sec_offset)

                rail_choice = random.choices(
                    ["COURIER_COD", "MOBILE_WALLET_MFS", "PAYMENT_GATEWAY", "BANK_TRANSFER"],
                    weights=[0.45, 0.35, 0.12, 0.08]
                )[0]

                if rail_choice == "COURIER_COD":
                    courier_name = random.choice(["Steadfast Courier", "RedX Logistics", "Pathao Courier", "Paperfly"])
                    order_status = "DELIVERED" if day_idx < 27 else "DISPATCHED"
                    orders.append({
                        "order_id": ord_id,
                        "merchant_id": m_id,
                        "customer_name": cust_name,
                        "customer_phone": cust_phone,
                        "order_timestamp": ord_time.isoformat(),
                        "payment_rail": "COURIER_COD",
                        "rail_provider": courier_name,
                        "order_status": order_status,
                        "transaction_ref": "",
                        "order_amount_taka": order_amt,
                        "shipping_cost_taka": shipping_cost,
                        "sku": sku_info["sku"],
                        "item_name": sku_info["item_name"],
                        "quantity": qty,
                        "unit_price_taka": sku_info["unit_retail_price_taka"],
                        "unit_cost_taka": sku_info["unit_cost_taka"],
                    })

                    # If delivered, generate courier settlement
                    if order_status == "DELIVERED":
                        settle_seq += 1
                        consignment_id = f"CONS-{settle_seq}"
                        cod_fee = round(order_amt * 0.01 + 60.0, 2)
                        expected_net = round(order_amt - cod_fee, 2)
                        actual_settled = expected_net  # normal clean settlement

                        courier_settlements.append({
                            "settlement_id": f"SETTLE-{settle_seq}",
                            "merchant_id": m_id,
                            "courier_name": courier_name,
                            "consignment_id": consignment_id,
                            "order_id": ord_id,
                            "cod_collected_taka": order_amt,
                            "courier_fee_taka": cod_fee,
                            "return_fee_taka": 0.0,
                            "expected_net_payout_taka": expected_net,
                            "actual_settled_taka": actual_settled,
                            "settlement_date": (ord_time + timedelta(days=2)).date().isoformat(),
                            "dispute_status": "SETTLED",
                        })

                else:
                    # Digital Rail (MFS, Gateway, Bank)
                    provider = (
                        random.choice(["bKash", "Nagad"]) if rail_choice == "MOBILE_WALLET_MFS"
                        else ("SSLCommerz" if rail_choice == "PAYMENT_GATEWAY" else "City Bank")
                    )
                    txn_ref = f"TXN-{random.randint(10000000, 99999999)}"
                    order_status = "DELIVERED" if day_idx < 26 else "DISPATCHED"

                    orders.append({
                        "order_id": ord_id,
                        "merchant_id": m_id,
                        "customer_name": cust_name,
                        "customer_phone": cust_phone,
                        "order_timestamp": ord_time.isoformat(),
                        "payment_rail": rail_choice,
                        "rail_provider": provider,
                        "order_status": order_status,
                        "transaction_ref": txn_ref,
                        "order_amount_taka": order_amt,
                        "shipping_cost_taka": shipping_cost,
                        "sku": sku_info["sku"],
                        "item_name": sku_info["item_name"],
                        "quantity": qty,
                        "unit_price_taka": sku_info["unit_retail_price_taka"],
                        "unit_cost_taka": sku_info["unit_cost_taka"],
                    })

                    # Corresponding clean rail payment
                    rail_seq += 1
                    pay_time = ord_time + timedelta(minutes=random.randint(1, 10))
                    rail_payments.append({
                        "rail_payment_id": f"RP-{rail_seq}",
                        "merchant_id": m_id,
                        "rail_type": rail_choice,
                        "provider": provider,
                        "transaction_ref": txn_ref,
                        "customer_phone": cust_phone,
                        "amount_taka": order_amt,
                        "fee_taka": round(order_amt * 0.015, 2),
                        "net_amount_taka": round(order_amt * 0.985, 2),
                        "payment_timestamp": pay_time.isoformat(),
                        "status": "SUCCESS",
                    })

    # =========================================================================
    # 2. Plant Ground Truth: Dispatched-Unpaid Orders (Planted Leaks)
    # =========================================================================
    # 12 specific orders marked DISPATCHED/DELIVERED on digital rails with NO payment in rail_payments
    planted_leak_merchants = ["MERCH_01", "MERCH_02", "MERCH_03", "MERCH_05", "MERCH_07", "MERCH_10", "MERCH_13", "MERCH_14"]
    for i, m_id in enumerate(planted_leak_merchants):
        order_seq += 1
        ord_id = f"ORD-LEAK-{order_seq}"
        sku_info = catalog[m_id][0]
        qty = 2
        order_amt = round(qty * sku_info["unit_retail_price_taka"], 2)
        cust_phone = generate_bangla_phone()
        cust_name = random.choice(BANGLA_NAMES)
        ord_time = start_date + timedelta(days=15 + i, hours=11, minutes=20)
        rail_choice = random.choice(["MOBILE_WALLET_MFS", "BANK_TRANSFER", "PAYMENT_GATEWAY"])
        provider = "bKash" if rail_choice == "MOBILE_WALLET_MFS" else ("BRAC Bank" if rail_choice == "BANK_TRANSFER" else "SSLCommerz")
        fake_orphan_ref = f"REF-UNPAID-{order_seq}"

        orders.append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "customer_name": cust_name,
            "customer_phone": cust_phone,
            "order_timestamp": ord_time.isoformat(),
            "payment_rail": rail_choice,
            "rail_provider": provider,
            "order_status": "DISPATCHED",
            "transaction_ref": fake_orphan_ref,  # This ref does NOT exist in rail_payments!
            "order_amount_taka": order_amt,
            "shipping_cost_taka": 120.0,
            "sku": sku_info["sku"],
            "item_name": sku_info["item_name"],
            "quantity": qty,
            "unit_price_taka": sku_info["unit_retail_price_taka"],
            "unit_cost_taka": sku_info["unit_cost_taka"],
        })

        ground_truth["dispatched_unpaid"].append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "amount_taka": order_amt,
            "rail": rail_choice,
            "provider": provider,
        })

    # =========================================================================
    # 3. Plant Ground Truth: Courier COD Settlement Shortfalls
    # =========================================================================
    # 10 consignments where expected_net_payout_taka - actual_settled_taka > 5.0
    cod_shortfall_merchants = ["MERCH_01", "MERCH_02", "MERCH_04", "MERCH_06", "MERCH_08", "MERCH_11", "MERCH_12", "MERCH_16"]
    for i, m_id in enumerate(cod_shortfall_merchants):
        settle_seq += 1
        order_seq += 1
        ord_id = f"ORD-COD-SHORT-{order_seq}"
        consignment_id = f"CONS-SHORT-{settle_seq}"
        courier_name = "Steadfast Courier" if i % 2 == 0 else "RedX Logistics"

        cod_collected = round(random.choice([4800.0, 7200.0, 11500.0, 15800.0, 22000.0]), 2)
        courier_fee = 130.0
        return_fee = 0.0
        expected_net = round(cod_collected - courier_fee - return_fee, 2)
        # Undersettlement amount between ৳500 and ৳3,800
        shortfall = round(random.choice([650.0, 1250.0, 2400.0, 3100.0, 1850.0]), 2)
        actual_settled = round(expected_net - shortfall, 2)

        # Record corresponding delivered order
        orders.append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "customer_name": random.choice(BANGLA_NAMES),
            "customer_phone": generate_bangla_phone(),
            "order_timestamp": (start_date + timedelta(days=10 + i, hours=14)).isoformat(),
            "payment_rail": "COURIER_COD",
            "rail_provider": courier_name,
            "order_status": "DELIVERED",
            "transaction_ref": "",
            "order_amount_taka": cod_collected,
            "shipping_cost_taka": 130.0,
            "sku": catalog[m_id][0]["sku"],
            "item_name": catalog[m_id][0]["item_name"],
            "quantity": 2,
            "unit_price_taka": catalog[m_id][0]["unit_retail_price_taka"],
            "unit_cost_taka": catalog[m_id][0]["unit_cost_taka"],
        })

        courier_settlements.append({
            "settlement_id": f"SETTLE-{settle_seq}",
            "merchant_id": m_id,
            "courier_name": courier_name,
            "consignment_id": consignment_id,
            "order_id": ord_id,
            "cod_collected_taka": cod_collected,
            "courier_fee_taka": courier_fee,
            "return_fee_taka": return_fee,
            "expected_net_payout_taka": expected_net,
            "actual_settled_taka": actual_settled,
            "settlement_date": (start_date + timedelta(days=12 + i)).date().isoformat(),
            "dispute_status": "DISPUTED",
        })

        ground_truth["courier_shortfalls"].append({
            "consignment_id": consignment_id,
            "order_id": ord_id,
            "merchant_id": m_id,
            "courier_name": courier_name,
            "expected_net": expected_net,
            "actual_settled": actual_settled,
            "shortfall_taka": shortfall,
        })

    # =========================================================================
    # 4. Plant Ground Truth: At Least 15 Fuzzy-Matched True Negatives
    # =========================================================================
    # Orders missing transaction_ref in orders.csv, BUT matched by phone + amount + timestamp within 18 mins in rail_payments
    # These MUST NOT be flagged as leaks (Exclusion Rate = 100%)
    for i in range(18):
        order_seq += 1
        rail_seq += 1
        m = MERCHANTS[i % len(MERCHANTS)]
        m_id = m["id"]
        ord_id = f"ORD-FUZZY-TN-{order_seq}"
        sku_info = catalog[m_id][0]
        qty = 1
        order_amt = round(float(sku_info["unit_retail_price_taka"]), 2)
        cust_phone = generate_bangla_phone()
        cust_name = random.choice(BANGLA_NAMES)

        day_num = 5 + i
        ord_time = start_date + timedelta(days=day_num, hours=10 + (i % 8), minutes=12)
        # Payment occurs 7 to 14 minutes after order placement (<= 18 minutes!)
        delay_minutes = 7 + (i % 8)
        pay_time = ord_time + timedelta(minutes=delay_minutes)

        rail_provider = "bKash" if i % 2 == 0 else "Nagad"
        real_txn_ref = f"BKASH-RECON-{random.randint(10000000, 99999999)}"

        # Order has NO transaction ref!
        orders.append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "customer_name": cust_name,
            "customer_phone": cust_phone,
            "order_timestamp": ord_time.isoformat(),
            "payment_rail": "MOBILE_WALLET_MFS",
            "rail_provider": rail_provider,
            "order_status": "DISPATCHED",
            "transaction_ref": "",  # Missing ref!
            "order_amount_taka": order_amt,
            "shipping_cost_taka": 100.0,
            "sku": sku_info["sku"],
            "item_name": sku_info["item_name"],
            "quantity": qty,
            "unit_price_taka": sku_info["unit_retail_price_taka"],
            "unit_cost_taka": sku_info["unit_cost_taka"],
        })

        # Rail payment HAS the payment with matching phone, exact amount, within 18 mins
        rail_payments.append({
            "rail_payment_id": f"RP-FUZZY-{rail_seq}",
            "merchant_id": m_id,
            "rail_type": "MOBILE_WALLET_MFS",
            "provider": rail_provider,
            "transaction_ref": real_txn_ref,
            "customer_phone": cust_phone,
            "amount_taka": order_amt,
            "fee_taka": round(order_amt * 0.015, 2),
            "net_amount_taka": round(order_amt * 0.985, 2),
            "payment_timestamp": pay_time.isoformat(),
            "status": "SUCCESS",
        })

        ground_truth["fuzzy_true_negatives"].append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "phone": cust_phone,
            "amount_taka": order_amt,
            "delay_minutes": delay_minutes,
            "rail_payment_id": f"RP-FUZZY-{rail_seq}",
        })

    # =========================================================================
    # 5. Plant Ground Truth: Failed / Abandoned Gateway Checkouts
    # =========================================================================
    # 14 checkouts where payment failed and customer did NOT complete subsequently
    for i in range(14):
        order_seq += 1
        rail_seq += 1
        m = MERCHANTS[(i + 3) % len(MERCHANTS)]
        m_id = m["id"]
        ord_id = f"ORD-FAIL-{order_seq}"
        sku_info = catalog[m_id][0]
        qty = random.randint(1, 2)
        order_amt = round(qty * sku_info["unit_retail_price_taka"], 2)
        cust_phone = generate_bangla_phone()
        cust_name = random.choice(BANGLA_NAMES)
        ord_time = start_date + timedelta(days=20 + (i % 9), hours=16, minutes=30)
        provider = "SSLCommerz" if i % 2 == 0 else "bKash"
        failed_txn_ref = f"FAIL-TXN-{order_seq}"

        orders.append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "customer_name": cust_name,
            "customer_phone": cust_phone,
            "order_timestamp": ord_time.isoformat(),
            "payment_rail": "PAYMENT_GATEWAY" if provider == "SSLCommerz" else "MOBILE_WALLET_MFS",
            "rail_provider": provider,
            "order_status": "FAILED",
            "transaction_ref": failed_txn_ref,
            "order_amount_taka": order_amt,
            "shipping_cost_taka": 100.0,
            "sku": sku_info["sku"],
            "item_name": sku_info["item_name"],
            "quantity": qty,
            "unit_price_taka": sku_info["unit_retail_price_taka"],
            "unit_cost_taka": sku_info["unit_cost_taka"],
        })

        rail_payments.append({
            "rail_payment_id": f"RP-FAIL-{rail_seq}",
            "merchant_id": m_id,
            "rail_type": "PAYMENT_GATEWAY" if provider == "SSLCommerz" else "MOBILE_WALLET_MFS",
            "provider": provider,
            "transaction_ref": failed_txn_ref,
            "customer_phone": cust_phone,
            "amount_taka": order_amt,
            "fee_taka": 0.0,
            "net_amount_taka": 0.0,
            "payment_timestamp": (ord_time + timedelta(minutes=2)).isoformat(),
            "status": "FAILED",
        })

        ground_truth["failed_abandoned_checkouts"].append({
            "order_id": ord_id,
            "merchant_id": m_id,
            "customer_phone": cust_phone,
            "order_amount_taka": order_amt,
            "provider": provider,
        })

    # =========================================================================
    # 6. Build Daily Inventory Snapshots (30 Days) & Hero SKU Stockout
    # =========================================================================
    inventory_rows = []

    for m in MERCHANTS:
        m_id = m["id"]
        skus = catalog[m_id]

        for s in skus:
            sku_code = s["sku"]
            lead_time = s["supplier_lead_time_days"]
            margin = s["unit_margin_taka"]
            retail_price = s["unit_retail_price_taka"]
            cost = s["unit_cost_taka"]
            current_stock = s["initial_stock"]

            is_hero = s.get("is_hero", False)
            # Plant stockout condition on Hero SKU (MERCH_02) and 2 other SKUs
            plant_stockout = is_hero or (sku_code in ["SKU-DTL-01", "SKU-MERCH_04-A"])

            for day_idx in range(days_count):
                snap_date = (start_date + timedelta(days=day_idx)).date().isoformat()
                sold_today = daily_sku_sales.get((m_id, sku_code, day_idx), 0)

                # Calibrate daily sales for planted stockout SKUs to establish clean Pre-Eid surge
                if plant_stockout:
                    if is_hero:
                        # 2 units/day initially, rising to 3-4 units/day in Pre-Eid surge (last 7 days)
                        sold_today = 2 if day_idx < 23 else (3 if day_idx % 2 == 0 else 4)
                    elif sku_code == "SKU-DTL-01":
                        sold_today = 3 if day_idx < 23 else (4 if day_idx % 2 == 0 else 5)
                    elif sku_code == "SKU-MERCH_04-A":
                        sold_today = 2 if day_idx < 23 else 3
                else:
                    # Regular SKU sales normalized
                    sold_today = min(sold_today, 4)

                # Decrement stock based on sales
                current_stock = max(0, current_stock - sold_today)

                # Replenishment: non-stockout SKUs restock continuously to maintain healthy cover
                if not plant_stockout and current_stock < 50:
                    current_stock += 80

                # Specifically for planted stockouts at Day 29 (latest snapshot):
                # Hero SKU: 7-day demand ~ 33 units, stock = 23 units -> lost_units = 10 -> impact = 10 * ৳4,650 = ৳46,500!
                if is_hero and day_idx == 29:
                    current_stock = 23
                elif sku_code == "SKU-DTL-01" and day_idx == 29:
                    current_stock = 20  # lost_units ~ 10 -> impact = ৳20,000
                elif sku_code == "SKU-MERCH_04-A" and day_idx == 29:
                    current_stock = 14  # lost_units ~ 7 -> impact = ৳8,750

                reorder_point = lead_time * 4

                inventory_rows.append({
                    "snapshot_date": snap_date,
                    "merchant_id": m_id,
                    "sku": sku_code,
                    "item_name": s["item_name"],
                    "category": m["category"],
                    "current_stock": current_stock,
                    "unit_cost_taka": cost,
                    "unit_retail_price_taka": retail_price,
                    "unit_margin_taka": margin,
                    "supplier_lead_time_days": lead_time,
                    "reorder_point_units": reorder_point,
                    "units_sold_today": sold_today,
                })

            if plant_stockout:
                ground_truth["stockout_skus"].append({
                    "merchant_id": m_id,
                    "sku": sku_code,
                    "is_hero": is_hero,
                    "unit_margin_taka": margin,
                    "supplier_lead_time_days": lead_time,
                })

    # Convert to DataFrames
    df_orders = pd.DataFrame(orders)
    df_rail_payments = pd.DataFrame(rail_payments)
    df_courier_settlements = pd.DataFrame(courier_settlements)
    df_inventory = pd.DataFrame(inventory_rows)

    # Save CSVs
    orders_path = os.path.join(OUTPUT_DIR, "orders.csv")
    rail_path = os.path.join(OUTPUT_DIR, "rail_payments.csv")
    courier_path = os.path.join(OUTPUT_DIR, "courier_settlements.csv")
    inventory_path = os.path.join(OUTPUT_DIR, "inventory_daily.csv")
    gt_path = os.path.join(OUTPUT_DIR, "ground_truth.json")

    df_orders.to_csv(orders_path, index=False)
    df_rail_payments.to_csv(rail_path, index=False)
    df_courier_settlements.to_csv(courier_path, index=False)
    df_inventory.to_csv(inventory_path, index=False)

    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    # Populate DuckDB
    duckdb_path = os.path.join(OUTPUT_DIR, "paylens.duckdb")
    if os.path.exists(duckdb_path):
        try:
            os.remove(duckdb_path)
        except Exception:
            pass

    con = duckdb.connect(duckdb_path)
    con.execute("CREATE OR REPLACE TABLE orders AS SELECT * FROM df_orders")
    con.execute("CREATE OR REPLACE TABLE rail_payments AS SELECT * FROM df_rail_payments")
    con.execute("CREATE OR REPLACE TABLE courier_settlements AS SELECT * FROM df_courier_settlements")
    con.execute("CREATE OR REPLACE TABLE inventory_daily AS SELECT * FROM df_inventory")
    con.close()

    print(f"=== Synthetic Data Generation Complete ===")
    print(f"Orders: {len(df_orders)} saved to {orders_path}")
    print(f"Rail Payments: {len(df_rail_payments)} saved to {rail_path}")
    print(f"Courier Settlements: {len(df_courier_settlements)} saved to {courier_path}")
    print(f"Inventory Daily Snapshots: {len(df_inventory)} saved to {inventory_path}")
    print(f"DuckDB database: {duckdb_path}")
    print(f"Ground Truth JSON: {gt_path}")
    print(f"Planted Dispatched-Unpaid: {len(ground_truth['dispatched_unpaid'])}")
    print(f"Planted Courier Shortfalls: {len(ground_truth['courier_shortfalls'])}")
    print(f"Planted Fuzzy True Negatives: {len(ground_truth['fuzzy_true_negatives'])}")
    print(f"Planted Abandoned Checkouts: {len(ground_truth['failed_abandoned_checkouts'])}")
    print(f"Planted Stockout SKUs: {len(ground_truth['stockout_skus'])}")

    # Generate sample Courier COD Settlement PDF for Evolus / PDF intake demo
    pdf_path = os.path.join(OUTPUT_DIR, "sample_courier_settlement.pdf")
    generate_sample_courier_pdf(pdf_path)
    print(f"Sample Courier COD Settlement PDF generated at: {pdf_path}")


def generate_sample_courier_pdf(pdf_path: str):
    """Generate a clean 1-page sample Courier Settlement PDF with planted shortfalls."""
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "DocSub",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
    )

    story.append(Paragraph("ExpressBD Logistics Ltd. — Official Settlement Statement", title_style))
    story.append(Paragraph("Merchant: Dhaka Threads & Lifestyle (MERCH_01) | Statement Date: 2026-10-15 | ID: STMT-EXP-20261015-01", subtitle_style))
    story.append(Spacer(1, 14))

    table_data = [
        ["Consignment ID", "Order ID", "COD Collected", "Fee", "Expected Net", "Actual Settled", "Shortfall", "Status"],
        ["CONS-SHORT-8001", "ORD-COD-SHORT-1001", "7,200.00", "130.00", "7,070.00", "5,820.00", "1,250.00", "DISPUTED"],
        ["CONS-SHORT-8002", "ORD-COD-SHORT-1002", "11,500.00", "130.00", "11,370.00", "8,970.00", "2,400.00", "DISPUTED"],
        ["CONS-SHORT-8003", "ORD-COD-SHORT-1003", "4,800.00", "130.00", "4,670.00", "4,020.00", "650.00", "DISPUTED"],
        ["CONS-NORM-8004", "ORD-1015", "3,800.00", "98.00", "3,702.00", "3,702.00", "0.00", "SETTLED"],
        ["CONS-NORM-8005", "ORD-1019", "5,400.00", "114.00", "5,286.00", "5,286.00", "0.00", "SETTLED"],
    ]

    t = Table(table_data, colWidths=[90, 95, 65, 45, 65, 65, 55, 60])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ("TEXTCOLOR", (6, 1), (6, 3), colors.HexColor("#DC2626")),
        ("FONTNAME", (6, 1), (6, 3), "Helvetica-Bold"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
    ]))

    story.append(t)
    story.append(Spacer(1, 16))
    notice_style = ParagraphStyle("Notice", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#64748B"))
    story.append(Paragraph("Notice: Undersettled consignments are subject to audit and auto-dispute reconciliation via PayLens & Evolus AI.", notice_style))

    doc.build(story)



if __name__ == "__main__":
    main()
