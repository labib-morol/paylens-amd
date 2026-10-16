"""AMD Instinct MI300X High-Throughput Serving & Grounding Benchmark for PayLens Solo.

Evaluates:
1. Multi-tenant recommendation card throughput (cards/min)
2. Mean Time-To-First-Token (TTFT) and token generation velocity
3. Strict 100% Numeric Grounding Verification across English and Bangla texts
4. Multi-objective GoalWeights reordering
"""

import os
import sys
import json
import time
from pathlib import Path

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.pipeline import run_pipeline
from engine.schema import GoalWeights
from agent.gemma_agent import run_mi300x_parallel_burst, goal_to_weights
from agent.grounding import verify_numeric_grounding

OUTPUT_DIR = os.path.join(ROOT_DIR, "benchmarks")
os.makedirs(OUTPUT_DIR, exist_ok=True)
RESULTS_PATH = os.path.join(OUTPUT_DIR, "benchmark_results.json")


def main():
    print("=" * 75)
    print("PAYLENS SOLO: AMD INSTINCT MI300X SERVING & GROUNDING BENCHMARK")
    print("=" * 75)

    # 1. Test Goal-to-Weights Natural Language Translation
    print("\n[Step 1] Testing Goal-to-Weights NL Translation:")
    cash_goal = "Recover all uncollected cash from dispatched orders and courier COD leaks immediately"
    stock_goal = "Maximize gross profit margin and prevent stockouts on best-seller items for Pre-Eid festival"

    w_cash = goal_to_weights(cash_goal)
    w_stock = goal_to_weights(stock_goal)

    print(f"  Cash Goal -> cash: {w_cash.cash_now_weight}, margin: {w_cash.margin_protection_weight}, stock: {w_cash.stock_availability_weight}")
    print(f"  Stock Goal -> cash: {w_stock.cash_now_weight}, margin: {w_stock.margin_protection_weight}, stock: {w_stock.stock_availability_weight}")

    # 2. Run Deterministic Pipeline across all 20 merchants
    print("\n[Step 2] Executing Deterministic Detection & Forecasting Layer:")
    t_start_pipeline = time.perf_counter()
    pipeline_result = run_pipeline(goal_weights=w_stock)
    t_pipeline_dur = time.perf_counter() - t_start_pipeline

    cards = pipeline_result["cards"]
    total_impact = pipeline_result["total_impact_taka"]
    eval_res = pipeline_result.get("evaluation", {})

    print(f"  Generated {len(cards)} recommendation cards across 20 merchants in {t_pipeline_dur:.2f}s")
    print(f"  Total merchant capital at risk: ৳{total_impact:,.2f}")
    if eval_res:
        print(f"  Deterministic Detector Accuracy: {eval_res['overall']['precision']*100:.1f}% Precision, "
              f"{eval_res['overall']['recall']*100:.1f}% Recall, {eval_res['overall']['f1_score']*100:.1f}% F1")
        print(f"  Fuzzy True Negative Exclusion  : {eval_res['fuzzy_true_negatives']['exclusion_rate_percent']:.1f}%")

    # 3. High-Concurrency Parallel Burst on AMD MI300X Serving Endpoint
    print("\n[Step 3] Launching Parallel Serving Burst (Concurrency = 32)...")
    burst_results = run_mi300x_parallel_burst(cards, max_concurrency=32, tone="Polite Reminder")

    # 4. Strict Independent Audit of Numeric Grounding
    print("\n[Step 4] Running Independent 100% Numeric Grounding Audit on All Output Texts...")
    grounding_failures = 0
    total_texts_audited = 0

    for card in burst_results["cards"]:
        allowed = card.allowed_numbers + [card.impact_taka]
        for field_name in ("explanation_en", "explanation_bn", "action_draft_en", "action_draft_bn"):
            text = getattr(card, field_name, "")
            total_texts_audited += 1
            ok, ungrounded = verify_numeric_grounding(text, allowed)
            if not ok:
                grounding_failures += 1
                print(f"  [FAIL] {card.card_id} {field_name}: ungrounded {ungrounded} vs allowed {allowed}")

    final_pass_rate = ((total_texts_audited - grounding_failures) / max(1, total_texts_audited)) * 100.0
    print(f"  Audited {total_texts_audited} English & Bangla generated texts.")
    print(f"  Grounding Failures : {grounding_failures}")
    print(f"  Final Grounding Accuracy: {final_pass_rate:.1f}%")

    # 5. Compile Benchmark Results
    benchmark_payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hardware_target": "AMD Instinct MI300X (192GB HBM3)",
        "model": burst_results["model"],
        "offline_fallback_active": burst_results["offline_mode"],
        "concurrency": burst_results["max_concurrency"],
        "metrics": {
            "total_merchants": 20,
            "total_recommendations": burst_results["total_cards"],
            "wall_clock_seconds": burst_results["wall_clock_seconds"],
            "recommendations_per_minute": burst_results["recommendations_per_minute"],
            "mean_ttft_ms": burst_results["mean_ttft_ms"],
            "total_output_tokens": burst_results["total_output_tokens"],
            "output_tokens_per_sec": burst_results["output_tokens_per_sec"],
            "grounding_pass_rate_percent": final_pass_rate,
        },
        "detector_accuracy": eval_res,
        "sample_top_cards": [
            {
                "card_id": c.card_id,
                "merchant": c.merchant_name,
                "type": c.rec_type.value,
                "impact_taka": c.impact_taka,
                "ranking_score": c.ranking_score,
                "explanation_en": c.explanation_en,
                "explanation_bn": c.explanation_bn,
                "action_draft_en": c.action_draft_en,
                "action_draft_bn": c.action_draft_bn,
            }
            for c in burst_results["cards"][:3]
        ],
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(benchmark_payload, f, indent=2)

    print(f"\n[Step 5] Benchmark results saved to: {RESULTS_PATH}")
    print("\n" + "=" * 75)
    print("BENCHMARK SUMMARY")
    print("=" * 75)
    print(f"Hardware Serving Target        : AMD Instinct MI300X")
    print(f"Model                          : {burst_results['model']}")
    print(f"Recommendations Processed      : {burst_results['total_cards']} cards")
    print(f"Wall-Clock Duration            : {burst_results['wall_clock_seconds']} s")
    print(f"Throughput Velocity            : {burst_results['recommendations_per_minute']} recs/min")
    print(f"Mean TTFT                      : {burst_results['mean_ttft_ms']} ms")
    print(f"Generation Velocity            : {burst_results['output_tokens_per_sec']} tokens/s")
    print(f"Final Numeric Grounding Rate   : {final_pass_rate:.1f}%")
    print("=" * 75)


if __name__ == "__main__":
    main()
