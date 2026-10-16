"""Deterministic Evaluator for PayLens Solo.

Evaluates detector accuracy against planted ground_truth.json:
- Exact Precision, Recall, and F1 scores per recommendation category
- Fuzzy-matched True Negative exclusion rate (must be 100%)
- Overall pipeline accuracy metrics
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.schema import RecommendationCard, RecommendationType, LeakSubType


def _calc_prf(tp: int, fp: int, fn: int) -> Dict[str, float]:
    """Calculate Precision, Recall, and F1 score."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
    }


def evaluate_recommendations(
    cards: List[RecommendationCard],
    ground_truth_path: str,
) -> Dict[str, Any]:
    """Evaluate detected recommendation cards against ground_truth.json."""
    if not os.path.exists(ground_truth_path):
        raise FileNotFoundError(f"Ground truth file not found at: {ground_truth_path}")

    with open(ground_truth_path, "r", encoding="utf-8") as f:
        gt = json.load(f)

    # 1. Dispatched Unpaid Orders
    gt_disp_unpaid: Set[str] = {item["order_id"] for item in gt.get("dispatched_unpaid", [])}
    det_disp_unpaid: Set[str] = {
        c.entity_id for c in cards
        if c.rec_type == RecommendationType.PAYMENT_LEAKAGE and c.leak_sub_type == LeakSubType.DISPATCHED_UNPAID
    }
    tp_disp = len(det_disp_unpaid & gt_disp_unpaid)
    fp_disp = len(det_disp_unpaid - gt_disp_unpaid)
    fn_disp = len(gt_disp_unpaid - det_disp_unpaid)
    disp_metrics = _calc_prf(tp_disp, fp_disp, fn_disp)

    # 2. Courier COD Settlement Shortfalls
    gt_shortfalls: Set[str] = {item["consignment_id"] for item in gt.get("courier_shortfalls", [])}
    det_shortfalls: Set[str] = {
        c.entity_id for c in cards
        if c.rec_type == RecommendationType.PAYMENT_LEAKAGE and c.leak_sub_type == LeakSubType.SETTLEMENT_SHORTFALL
    }
    tp_short = len(det_shortfalls & gt_shortfalls)
    fp_short = len(det_shortfalls - gt_shortfalls)
    fn_short = len(gt_shortfalls - det_shortfalls)
    short_metrics = _calc_prf(tp_short, fp_short, fn_short)

    # 3. Fuzzy-Matched True Negative Exclusion Rate
    gt_fuzzy_tn: Set[str] = {item["order_id"] for item in gt.get("fuzzy_true_negatives", [])}
    # These must NOT appear in ANY payment leakage cards
    all_leak_entity_ids = {c.entity_id for c in cards if c.rec_type == RecommendationType.PAYMENT_LEAKAGE}
    falsely_flagged_tn = gt_fuzzy_tn & all_leak_entity_ids
    correctly_excluded_tn = len(gt_fuzzy_tn) - len(falsely_flagged_tn)
    fuzzy_exclusion_rate = (
        (correctly_excluded_tn / len(gt_fuzzy_tn)) * 100.0 if gt_fuzzy_tn else 100.0
    )

    # 4. Failed-Payment Abandoned Checkouts
    gt_failed: Set[str] = {item["order_id"] for item in gt.get("failed_abandoned_checkouts", [])}
    det_failed: Set[str] = {
        c.entity_id for c in cards
        if c.rec_type == RecommendationType.FAILED_PAYMENT_RECOVERY
    }
    tp_failed = len(det_failed & gt_failed)
    fp_failed = len(det_failed - gt_failed)
    fn_failed = len(gt_failed - det_failed)
    failed_metrics = _calc_prf(tp_failed, fp_failed, fn_failed)

    # 5. Stockout Risk SKUs
    gt_stockout: Set[tuple] = {
        (item["merchant_id"], item["sku"]) for item in gt.get("stockout_skus", [])
    }
    det_stockout: Set[tuple] = {
        (c.merchant_id, c.entity_id) for c in cards
        if c.rec_type == RecommendationType.STOCKOUT_RISK
    }
    tp_stock = len(det_stockout & gt_stockout)
    fp_stock = len(det_stockout - gt_stockout)
    fn_stock = len(gt_stockout - det_stockout)
    stock_metrics = _calc_prf(tp_stock, fp_stock, fn_stock)

    # Total Combined Metrics
    total_tp = tp_disp + tp_short + tp_failed + tp_stock
    total_fp = fp_disp + fp_short + fp_failed + fp_stock
    total_fn = fn_disp + fn_short + fn_failed + fn_stock
    overall_metrics = _calc_prf(total_tp, total_fp, total_fn)

    return {
        "dispatched_unpaid": disp_metrics,
        "courier_shortfalls": short_metrics,
        "failed_payment_recovery": failed_metrics,
        "stockout_risk": stock_metrics,
        "fuzzy_true_negatives": {
            "total_planted_tns": len(gt_fuzzy_tn),
            "correctly_excluded": correctly_excluded_tn,
            "falsely_flagged_leaks": list(falsely_flagged_tn),
            "exclusion_rate_percent": round(fuzzy_exclusion_rate, 2),
        },
        "overall": overall_metrics,
    }
