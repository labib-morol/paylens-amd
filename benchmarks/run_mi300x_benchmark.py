"""AMD Instinct MI300X Serving & Grounding Benchmark for PayLens Solo.

Evaluates:
1. Multi-tenant recommendation card throughput and latency
2. Execution Source reporting (LIVE_AMD_MI300X_VLLM vs LIVE_AMD_TOKENFACTORY vs LOCAL_DETERMINISTIC_FALLBACK)
3. Strict 100% Numeric Grounding Verification across Global English texts
4. Multi-objective GoalWeights dynamic reordering
5. Authentic AMD Instinct MI300X (192GB HBM3) vLLM reference metrics
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
from agent.gemma_agent import run_mi300x_parallel_burst, goal_to_weights, import_vllm_bench_serve_json
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
    cash_goal = "Recover uncollected cash from dispatched Shopify orders and carrier COD settlement shortfalls immediately"
    stock_goal = "Maximize gross profit margins and prevent stockouts on top-selling audio and smart hardware"

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
    total_impact = pipeline_result["total_impact_usd"]
    eval_res = pipeline_result.get("evaluation", {})

    print(f"  Generated {len(cards)} recommendation cards across 20 merchants in {t_pipeline_dur:.2f}s")
    print(f"  Total merchant capital at risk: ${total_impact:,.2f}")
    if eval_res:
        print(f"  Deterministic Detector Accuracy: {eval_res['overall']['precision']*100:.1f}% Precision, "
              f"{eval_res['overall']['recall']*100:.1f}% Recall, {eval_res['overall']['f1_score']*100:.1f}% F1")
        print(f"  Fuzzy True Negative Exclusion  : {eval_res['fuzzy_true_negatives']['exclusion_rate_percent']:.1f}%")

    # 3. Serving Burst & Execution Source Audit
    print("\n[Step 3] Executing Serving Burst across cards (Concurrency = 32)...")
    burst_results = run_mi300x_parallel_burst(cards, max_concurrency=32, tone="Polite Payment Reminder")

    exec_source = burst_results["execution_source"]
    print(f"  Execution Source Detected : {exec_source}")
    print(f"  Active Mode Description   : {burst_results.get('mode_display', exec_source)}")
    print(f"  Wall-clock Duration       : {burst_results['wall_clock_seconds']}s")

    # 4. Strict Independent Audit of Numeric Grounding
    print("\n[Step 4] Running Independent 100% Numeric Grounding Audit on All Output Texts...")
    grounding_failures = 0
    total_texts_audited = 0

    for card in burst_results["cards"]:
        allowed = card.allowed_numbers + [card.impact_usd]
        for field_name in ("explanation_en", "action_draft_en"):
            text = getattr(card, field_name, "")
            total_texts_audited += 1
            ok, ungrounded = verify_numeric_grounding(text, allowed)
            if not ok:
                grounding_failures += 1
                print(f"  [FAIL] {card.card_id} {field_name}: ungrounded {ungrounded} vs allowed {allowed}")

    final_pass_rate = ((total_texts_audited - grounding_failures) / max(1, total_texts_audited)) * 100.0
    print(f"  Audited {total_texts_audited} English generated texts.")
    print(f"  Grounding Failures : {grounding_failures}")
    print(f"  Final Grounding Accuracy: {final_pass_rate:.1f}%")

    # 5. Compile Benchmark Results with Honest Telemetry
    ref_mi300x = import_vllm_bench_serve_json()

    benchmark_payload = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "execution_source": exec_source,
        "is_offline": burst_results["is_offline"],
        "model": burst_results["model"],
        "endpoint": burst_results["endpoint"],
        "concurrency": burst_results["max_concurrency"],
        "currency": "USD",
        "grounding_pass_rate_percent": final_pass_rate,
        "runtime_metrics": {
            "total_merchants": 20,
            "total_recommendations": burst_results["total_cards"],
            "wall_clock_seconds": burst_results["wall_clock_seconds"],
            "grounding_accuracy_percent": final_pass_rate,
        },
        "amd_mi300x_hardware_benchmark_reference": ref_mi300x,
        "deterministic_evaluation": eval_res,
    }

    if exec_source == "LOCAL_DETERMINISTIC_FALLBACK":
        benchmark_payload["local_cpu_note"] = (
            "Local CPU fallback mode active in current terminal session. "
            "Connect live AMD Instinct MI300X ROCm vLLM or TokenFactory in .env/sidebar for live GPU token metrics."
        )
        print(f"\n[Step 5] Local CPU Mode: Generated {burst_results['total_cards']} cards in {burst_results['wall_clock_seconds']}s")
        print(f"  AMD MI300X Reference Serving Throughput : {ref_mi300x['benchmark_results']['token_throughput_per_sec']:,} tok/s (Concurrency=32)")
        print(f"  AMD MI300X Reference Mean TTFT          : {ref_mi300x['benchmark_results']['mean_ttft_ms']} ms")
    else:
        benchmark_payload["live_gpu_metrics"] = {
            "recommendations_per_minute": burst_results.get("recommendations_per_minute"),
            "mean_ttft_ms": burst_results.get("mean_ttft_ms"),
            "output_tokens_per_sec": burst_results.get("output_tokens_per_sec"),
        }
        print(f"\n[Step 5] Live AMD GPU Metrics:")
        print(f"  Recommendations / min : {burst_results.get('recommendations_per_minute')}")
        print(f"  Output tokens / sec   : {burst_results.get('output_tokens_per_sec')}")
        print(f"  Mean TTFT             : {burst_results.get('mean_ttft_ms')} ms")

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(benchmark_payload, f, indent=2)

    print(f"  Benchmark results written to {RESULTS_PATH}")
    print(f"  Final Grounding Accuracy: {final_pass_rate:.1f}%")
    print("=" * 75)


if __name__ == "__main__":
    main()
