"""Deterministic Evaluator for PayLens.

Evaluates detector accuracy against ground_truth.json:
- Exact Precision, Recall, and F1 scores per recommendation category
- Evaluates both baseline split and hard stress-test split (with non-1.00 confusion matrix)
- Reports False Positives (e.g. 48-hour delayed bank settlements) and False Negatives with diagnostic explanations
- Fuzzy-matched True Negative exclusion rate
- Never defaults missing metrics to 1.0
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.schema import RecommendationCard, RecommendationType, LeakSubType


def _calc_prf(tp: int, fp: int, fn: int) -> Dict[str, Any]:
    """Calculate Precision, Recall, and F1 score without defaulting to 1.0."""
    precision = (tp / (tp + fp)) if (tp + fp) > 0 else None
    recall = (tp / (tp + fn)) if (tp + fn) > 0 else None
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = (2 * precision * recall) / (precision + recall)
    else:
        f1 = None
    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "f1_score": round(f1, 4) if f1 is not None else None,
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

    # Filter for standard baseline evaluation (excluding stress test edge cases)
    baseline_cards = [c for c in cards if not c.entity_id.startswith("ORD-STRESS-")]

    # 1. Dispatched Unpaid Orders (Baseline)
    gt_disp_unpaid: Set[str] = {item["order_id"] for item in gt.get("dispatched_unpaid", [])}
    det_disp_unpaid: Set[str] = {
        c.entity_id for c in baseline_cards
        if c.rec_type == RecommendationType.PAYMENT_LEAKAGE and c.leak_sub_type == LeakSubType.DISPATCHED_UNPAID
    }
    tp_disp = len(det_disp_unpaid & gt_disp_unpaid)
    fp_disp = len(det_disp_unpaid - gt_disp_unpaid)
    fn_disp = len(gt_disp_unpaid - det_disp_unpaid)
    disp_metrics = _calc_prf(tp_disp, fp_disp, fn_disp)

    # 2. Courier COD Settlement Shortfalls (Baseline)
    gt_shortfalls: Set[str] = {item["consignment_id"] for item in gt.get("courier_shortfalls", [])}
    det_shortfalls: Set[str] = {
        c.entity_id for c in baseline_cards
        if c.rec_type == RecommendationType.PAYMENT_LEAKAGE and c.leak_sub_type == LeakSubType.SETTLEMENT_SHORTFALL
    }
    tp_short = len(det_shortfalls & gt_shortfalls)
    fp_short = len(det_shortfalls - gt_shortfalls)
    fn_short = len(gt_shortfalls - det_shortfalls)
    short_metrics = _calc_prf(tp_short, fp_short, fn_short)

    # 3. Fuzzy-Matched True Negative Exclusion Rate
    gt_fuzzy_tn: Set[str] = {item["order_id"] for item in gt.get("fuzzy_true_negatives", [])}
    all_leak_entity_ids = {c.entity_id for c in cards if c.rec_type == RecommendationType.PAYMENT_LEAKAGE}
    falsely_flagged_tn = gt_fuzzy_tn & all_leak_entity_ids
    correctly_excluded_tn = len(gt_fuzzy_tn) - len(falsely_flagged_tn)
    fuzzy_exclusion_rate = (
        (correctly_excluded_tn / len(gt_fuzzy_tn)) * 100.0 if gt_fuzzy_tn else None
    )

    # 4. Failed-Payment Abandoned Checkouts (Baseline)
    gt_failed: Set[str] = {item["order_id"] for item in gt.get("failed_abandoned_checkouts", [])}
    det_failed: Set[str] = {
        c.entity_id for c in cards
        if c.rec_type == RecommendationType.FAILED_PAYMENT_RECOVERY
    }
    tp_failed = len(det_failed & gt_failed)
    fp_failed = len(det_failed - gt_failed)
    fn_failed = len(gt_failed - det_failed)
    failed_metrics = _calc_prf(tp_failed, fp_failed, fn_failed)

    # 5. Stockout Risk SKUs (Baseline)
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

    # Baseline Combined Overall Metrics
    base_tp = tp_disp + tp_short + tp_failed + tp_stock
    base_fp = fp_disp + fp_short + fp_failed + fp_stock
    base_fn = fn_disp + fn_short + fn_failed + fn_stock
    baseline_overall = _calc_prf(base_tp, base_fp, base_fn)

    # -------------------------------------------------------------------------
    # 6. Hard Stress-Test Split (Includes the 6 Hard Edge Cases)
    # -------------------------------------------------------------------------
    stress_cases = gt.get("stress_test_edge_cases", [])
    stress_fps: List[Dict[str, Any]] = []
    stress_tps: List[Dict[str, Any]] = []
    stress_fns: List[Dict[str, Any]] = []

    for sc in stress_cases:
        oid = sc["order_id"]
        is_detected = oid in all_leak_entity_ids
        if sc.get("is_actual_leak", False):
            # Should be detected
            if is_detected:
                stress_tps.append(sc)
            else:
                stress_fns.append(sc)
        else:
            # Legitimate payment; if detected, it is a False Positive
            if is_detected:
                stress_fps.append(sc)

    stress_tp = base_tp + len(stress_tps)
    stress_fp = base_fp + len(stress_fps)
    stress_fn = base_fn + len(stress_fns)
    stress_overall = _calc_prf(stress_tp, stress_fp, stress_fn)

    stress_split = {
        "confusion_matrix": {
            "true_positives": stress_tp,
            "false_positives": stress_fp,
            "false_negatives": stress_fn,
            "true_negatives_fuzzy": correctly_excluded_tn,
        },
        "precision": stress_overall["precision"],
        "recall": stress_overall["recall"],
        "f1_score": stress_overall["f1_score"],
        "false_positive_ids": [fp["order_id"] for fp in stress_fps],
        "false_positive_details": stress_fps,
        "false_negative_ids": [fn["order_id"] for fn in stress_fns],
        "false_negative_details": stress_fns,
        "total_edge_cases_tested": len(stress_cases),
    }

    return {
        "dispatched_unpaid": disp_metrics,
        "courier_shortfalls": short_metrics,
        "failed_payment_recovery": failed_metrics,
        "stockout_risk": stock_metrics,
        "fuzzy_true_negatives": {
            "total_planted_tns": len(gt_fuzzy_tn),
            "correctly_excluded": correctly_excluded_tn,
            "falsely_flagged_leaks": list(falsely_flagged_tn),
            "exclusion_rate_percent": round(fuzzy_exclusion_rate, 2) if fuzzy_exclusion_rate is not None else None,
        },
        "standard_split": baseline_overall,
        "stress_test_split": stress_split,
        # Keep overall pointing to standard_split for backward compatibility, with stress_test_split explicitly available
        "overall": baseline_overall,
    }
