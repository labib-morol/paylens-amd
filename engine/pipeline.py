"""Deterministic End-to-End Pipeline for PayLens Solo.

Architecture Rule 1: CODE COMPUTES, MODEL EXPLAINS.
Coordinates data ingestion, anomaly detection, statistical forecasting,
ground-truth evaluation, and multi-objective ranking.
"""

import os
import sys
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import duckdb
from dotenv import load_dotenv

from engine.schema import RecommendationCard, GoalWeights
from engine.detectors import (
    run_stl_anomaly_detector,
    run_leak_matcher,
    run_failed_payment_scanner,
    run_stockout_forecaster,
)
from engine.ranker import rank_cards
from engine.evaluator import evaluate_recommendations

load_dotenv()


def get_merchant_names(con: duckdb.DuckDBPyConnection) -> Dict[str, str]:
    """Retrieve mapping of merchant IDs to human-readable business names."""
    # Canonical names for primary merchants
    name_map = {
        "MERCH_01": "Dhaka Threads & Lifestyle",
        "MERCH_02": "Chattogram Artisans & Home",
        "MERCH_03": "Sylhet Tea & Organic Pantry",
        "MERCH_04": "Rajshahi Silk Heritage",
        "MERCH_05": "Khulna Marine & Leathercraft",
        "MERCH_06": "Barishal Agro Essentials",
        "MERCH_07": "Rangpur Loom & Crafts",
        "MERCH_08": "Mymensingh Dairy & Provisions",
        "MERCH_09": "Comilla Khadi Collection",
        "MERCH_10": "Bogura Sweets & Delicacies",
        "MERCH_11": "Cox's Pearl & Coastwear",
        "MERCH_12": "Narayanganj Knitwear Express",
        "MERCH_13": "Gazipur Electronics Depot",
        "MERCH_14": "Tangail Saree Emporium",
        "MERCH_15": "Kushtia Musical & Arts",
        "MERCH_16": "Dinajpur Aromatic Grains",
        "MERCH_17": "Pabna Handloom Weaves",
        "MERCH_18": "Faridpur Jute Innovations",
        "MERCH_19": "Feni Tech Accessories",
        "MERCH_20": "Jessore Floral & Natural Cosmetics",
    }
    return name_map


def run_pipeline(
    duckdb_path: Optional[str] = None,
    goal_weights: Optional[GoalWeights] = None,
    recovery_rate: float = 0.35,
    ground_truth_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute complete deterministic detection, forecasting, and ranking pipeline."""
    if duckdb_path is None:
        duckdb_path = os.getenv("DUCKDB_PATH", "data/generated/paylens.duckdb")

    if not os.path.exists(duckdb_path):
        raise FileNotFoundError(f"DuckDB database not found at {duckdb_path}. Run generate_synthetic_data.py first.")

    goal_weights = goal_weights or GoalWeights()

    con = duckdb.connect(duckdb_path, read_only=True)
    merchant_names = get_merchant_names(con)

    # 1. Run STL daily revenue anomaly detector
    stl_sigma = float(os.getenv("STL_SIGMA_THRESHOLD", "2.2"))
    stl_anomalies = run_stl_anomaly_detector(con, sigma_threshold=stl_sigma)

    # 2. Run 2-Pass Leak Matcher and Courier Shortfall Checker
    leak_cards, leak_telemetry = run_leak_matcher(con, merchant_names, stl_anomalies)

    # 3. Run Failed-Payment Recovery Scanner
    recovery_cards = run_failed_payment_scanner(
        con, recovery_rate=recovery_rate, merchant_names=merchant_names, stl_anomalies=stl_anomalies
    )

    # 4. Run Holt-Winters Stockout Forecaster
    stockout_cards = run_stockout_forecaster(con, merchant_names, stl_anomalies)

    con.close()

    # Combine all deterministic cards
    all_cards: List[RecommendationCard] = leak_cards + recovery_cards + stockout_cards

    # 5. Multi-Objective Ranking
    ranked_cards = rank_cards(all_cards, goal_weights)

    # 6. Evaluation against Ground Truth (if available)
    evaluation_results = None
    if ground_truth_path is None:
        default_gt = os.path.join(os.path.dirname(duckdb_path), "ground_truth.json")
        if os.path.exists(default_gt):
            ground_truth_path = default_gt

    if ground_truth_path and os.path.exists(ground_truth_path):
        evaluation_results = evaluate_recommendations(all_cards, ground_truth_path)

    total_impact = round(sum(c.impact_taka for c in ranked_cards), 2)

    return {
        "cards": ranked_cards,
        "goal_weights": goal_weights.model_dump(),
        "total_cards": len(ranked_cards),
        "total_impact_taka": total_impact,
        "leak_telemetry": leak_telemetry,
        "stl_anomalies_detected": len(stl_anomalies),
        "evaluation": evaluation_results,
    }


def main():
    """CLI verification runner for the deterministic pipeline."""
    print("=" * 70)
    print("PAYLENS DETERMINISTIC PIPELINE VERIFICATION")
    print("=" * 70)

    # Test Scenario 1: Cash Recovery Priority
    cash_priority_weights = GoalWeights(
        cash_now_weight=0.8,
        margin_protection_weight=0.1,
        stock_availability_weight=0.1,
        rationale="Urgent Cash Recovery Priority",
    )
    result_cash = run_pipeline(goal_weights=cash_priority_weights)

    eval_res = result_cash["evaluation"]
    print("\n--- GROUND TRUTH EVALUATION METRICS ---")
    if eval_res:
        print(f"Overall Precision : {eval_res['overall']['precision'] * 100:.1f}%")
        print(f"Overall Recall    : {eval_res['overall']['recall'] * 100:.1f}%")
        print(f"Overall F1 Score  : {eval_res['overall']['f1_score'] * 100:.1f}%")
        print(f"Dispatched Unpaid : Precision {eval_res['dispatched_unpaid']['precision']*100:.1f}%, Recall {eval_res['dispatched_unpaid']['recall']*100:.1f}%")
        print(f"Courier Shortfalls: Precision {eval_res['courier_shortfalls']['precision']*100:.1f}%, Recall {eval_res['courier_shortfalls']['recall']*100:.1f}%")
        print(f"Failed Recovery   : Precision {eval_res['failed_payment_recovery']['precision']*100:.1f}%, Recall {eval_res['failed_payment_recovery']['recall']*100:.1f}%")
        print(f"Stockout Risk     : Precision {eval_res['stockout_risk']['precision']*100:.1f}%, Recall {eval_res['stockout_risk']['recall']*100:.1f}%")
        print(f"Fuzzy True Negatives: {eval_res['fuzzy_true_negatives']['correctly_excluded']} / {eval_res['fuzzy_true_negatives']['total_planted_tns']} "
              f"({eval_res['fuzzy_true_negatives']['exclusion_rate_percent']}%) correctly excluded from leaks!")

    print("\n--- TOP CARDS UNDER CASH PRIORITY (cash_now=0.8) ---")
    for i, card in enumerate(result_cash["cards"][:3], 1):
        print(f"#{i} [{card.rec_type.value}] {card.title} | Merchant: {card.merchant_name} | Impact: ৳{card.impact_taka:,.2f} | Score: {card.ranking_score}")

    # Test Scenario 2: Margin & Stock Availability Priority
    margin_stock_weights = GoalWeights(
        cash_now_weight=0.1,
        margin_protection_weight=0.45,
        stock_availability_weight=0.45,
        rationale="Pre-Eid Margin & Inventory Protection Priority",
    )
    result_margin = run_pipeline(goal_weights=margin_stock_weights)

    print("\n--- TOP CARDS UNDER MARGIN & STOCK PRIORITY (margin=0.45, stock=0.45) ---")
    for i, card in enumerate(result_margin["cards"][:3], 1):
        print(f"#{i} [{card.rec_type.value}] {card.title} | Merchant: {card.merchant_name} | Impact: ৳{card.impact_taka:,.2f} | Score: {card.ranking_score}")

    top_cash_id = result_cash["cards"][0].card_id
    top_margin_id = result_margin["cards"][0].card_id
    hero_card = next((c for c in result_margin["cards"] if "SKU-CAH-HERO-01" in c.card_id), None)

    print("\n--- REORDERING VERIFICATION ---")
    print(f"Top card under Cash Priority        : {top_cash_id} (Score: {result_cash['cards'][0].ranking_score})")
    print(f"Top card under Margin/Stock Priority: {top_margin_id} (Score: {result_margin['cards'][0].ranking_score})")
    if hero_card:
        print(f"Hero SKU (SKU-CAH-HERO-01) on MERCH_02: Impact ৳{hero_card.impact_taka:,.2f}, Score: {hero_card.ranking_score}")
        print(f"Is Hero SKU #1 under Margin/Stock Priority? {result_margin['cards'][0].card_id == hero_card.card_id}")


if __name__ == "__main__":
    main()
