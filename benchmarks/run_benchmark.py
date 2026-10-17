"""Authentic Serving and Grounding Benchmark for AMD GPU Endpoints.

Architecture Rules:
1. Strict provenance: records endpoint_type, base_url_host, model_served, started_at, git_commit.
2. Refuses to run if OFFLINE: never writes fake or simulated AMD benchmark numbers.
3. Concurrency levels: evaluates [1, 4, 8, 16, 32] using real streaming client calls.
4. Hardware labelling: 'AMD TokenFactory (shared hosted; hardware not under our control)'
   or user-specified --hardware (only for OWN_VLLM).
"""

import os
import sys
import json
import time
import argparse
import asyncio
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from openai import AsyncOpenAI
import numpy as np

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.pipeline import run_pipeline
from engine.schema import GoalWeights, RecommendationCard
from agent.grounding import verify_numeric_grounding

RESULTS_DIR = os.path.join(ROOT_DIR, "benchmarks", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def get_git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


def get_vllm_version(base_url: str) -> str:
    try:
        root_url = base_url.replace("/v1", "").rstrip("/")
        resp = httpx.get(f"{root_url}/version", timeout=2.0)
        if resp.status_code == 200:
            data = resp.json()
            return str(data.get("version", "unknown"))
    except Exception:
        pass
    return "unknown"


def detect_endpoint() -> Tuple[str, Optional[str], Optional[str], Optional[str]]:
    """Detects active endpoint: (endpoint_type, base_url, api_key, model_name).

    Precedence:
    1. AMD_VLLM_BASE_URL (OWN_VLLM)
    2. AMD_TOKENFACTORY_BASE_URL (TOKENFACTORY)
    3. OFFLINE
    """
    offline_override = os.getenv("OFFLINE_MODE", "false").lower() in ("true", "1", "yes")
    if offline_override:
        return "OFFLINE", None, None, None

    vllm_url = os.getenv("AMD_VLLM_BASE_URL")
    if vllm_url:
        try:
            resp = httpx.get(f"{vllm_url.rstrip('/')}/models", timeout=2.5)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id") for m in data.get("data", [])]
                model = models[0] if models else os.getenv("MODEL_NAME", "google/gemma-4-31B-it")
                return "OWN_VLLM", vllm_url, os.getenv("AMD_API_KEY", "EMPTY"), model
        except Exception:
            pass

    tf_url = os.getenv("AMD_TOKENFACTORY_BASE_URL")
    tf_key = os.getenv("AMD_API_KEY")
    if tf_url and tf_key:
        try:
            headers = {"Authorization": f"Bearer {tf_key}"}
            resp = httpx.get(f"{tf_url.rstrip('/')}/models", headers=headers, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("id") for m in data.get("data", [])]
                model = os.getenv("MODEL_NAME")
                if not model and models:
                    model = models[0]
                return "TOKENFACTORY", tf_url, tf_key, model or "unknown"
        except Exception:
            pass

    return "OFFLINE", None, None, None


async def benchmark_single_request(
    client: AsyncOpenAI,
    model: str,
    card: RecommendationCard,
) -> Dict[str, Any]:
    system_prompt = (
        "You are PayLens AI explaining merchant capital recovery. "
        "MANDATORY RULE: Never calculate arithmetic. Mention ONLY numbers from ALLOWED_NUMBERS. "
        "Output valid JSON: {'explanation_en': '...', 'action_draft_en': '...'}"
    )
    user_prompt = (
        f"Merchant: {card.merchant_name}\n"
        f"Type: {card.rec_type.value}\n"
        f"Impact USD: ${card.impact_usd:,.2f}\n"
        f"ALLOWED_NUMBERS: {card.allowed_numbers}\n"
    )

    t0 = time.perf_counter()
    ttft: Optional[float] = None
    output_tokens = 0
    full_content = []

    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            stream=True,
            stream_options={"include_usage": True},
        )
        async for chunk in stream:
            if ttft is None and chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                ttft = time.perf_counter() - t0
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                full_content.append(chunk.choices[0].delta.content)
            if hasattr(chunk, "usage") and chunk.usage:
                output_tokens = chunk.usage.completion_tokens or output_tokens

        total_latency = time.perf_counter() - t0
        if ttft is None:
            ttft = total_latency

        generated_text = "".join(full_content)
        if output_tokens == 0:
            output_tokens = max(1, len(generated_text.split()))

        allowed = card.allowed_numbers + [card.impact_usd]
        is_grounded, ungrounded = verify_numeric_grounding(generated_text, allowed)

        return {
            "success": True,
            "ttft_ms": round(ttft * 1000.0, 2),
            "latency_ms": round(total_latency * 1000.0, 2),
            "output_tokens": output_tokens,
            "grounding_passed": is_grounded,
            "ungrounded_tokens": ungrounded,
        }
    except Exception as e:
        total_latency = time.perf_counter() - t0
        return {
            "success": False,
            "ttft_ms": round(total_latency * 1000.0, 2),
            "latency_ms": round(total_latency * 1000.0, 2),
            "output_tokens": 0,
            "grounding_passed": False,
            "error": str(e),
        }


async def run_concurrency_tier(
    client: AsyncOpenAI,
    model: str,
    cards: List[RecommendationCard],
    concurrency: int,
    requests_to_run: int,
) -> Dict[str, Any]:
    semaphore = asyncio.Semaphore(concurrency)

    async def _worker(card: RecommendationCard):
        async with semaphore:
            return await benchmark_single_request(client, model, card)

    # Sample requests
    tasks = []
    for i in range(requests_to_run):
        card = cards[i % len(cards)]
        tasks.append(_worker(card))

    t0 = time.perf_counter()
    results = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - t0

    success_results = [r for r in results if r.get("success")]
    if not success_results:
        return {
            "concurrency": concurrency,
            "total_requests": requests_to_run,
            "completed_requests": 0,
            "error": "All requests failed",
        }

    ttfts = [r["ttft_ms"] for r in success_results]
    latencies = [r["latency_ms"] for r in success_results]
    total_tokens = sum(r["output_tokens"] for r in success_results)
    grounded_count = sum(1 for r in success_results if r["grounding_passed"])

    return {
        "concurrency": concurrency,
        "total_requests": requests_to_run,
        "completed_requests": len(success_results),
        "failed_requests": requests_to_run - len(success_results),
        "duration_seconds": round(elapsed, 3),
        "mean_ttft_ms": round(float(np.mean(ttfts)), 2),
        "p95_ttft_ms": round(float(np.percentile(ttfts, 95)), 2),
        "p50_latency_ms": round(float(np.percentile(latencies, 50)), 2),
        "p95_latency_ms": round(float(np.percentile(latencies, 95)), 2),
        "tokens_per_sec": round(total_tokens / max(0.001, elapsed), 1),
        "requests_per_minute": round((len(success_results) / max(0.001, elapsed)) * 60.0, 1),
        "grounding_pass_rate_percent": round((grounded_count / len(success_results)) * 100.0, 1),
    }


def main():
    parser = argparse.ArgumentParser(description="PayLens Authentic AMD GPU Serving Benchmark")
    parser.add_argument("--hardware", default="unknown", help="Hardware identifier for OWN_VLLM (e.g. MI300X)")
    parser.add_argument("--requests-per-tier", type=int, default=16, help="Requests to run per concurrency tier")
    args = parser.parse_args()

    print("=" * 75)
    print("PAYLENS AUTHENTIC AMD GPU SERVING BENCHMARK")
    print("=" * 75)

    endpoint_type, base_url, api_key, model_name = detect_endpoint()
    print(f"Endpoint Type Detected: {endpoint_type}")

    if endpoint_type == "OFFLINE" or not base_url:
        print("\n[ERROR] Benchmark refused to run: No active AMD GPU endpoint detected.")
        print("Set AMD_VLLM_BASE_URL or AMD_TOKENFACTORY_BASE_URL + AMD_API_KEY with OFFLINE_MODE=false.")
        print("Refusing to write fake, simulated, or offline benchmark numbers to results.")
        sys.exit(1)

    host = urlparse(base_url).netloc
    vllm_ver = get_vllm_version(base_url)
    git_hash = get_git_commit()

    if endpoint_type == "TOKENFACTORY":
        hardware_label = "AMD TokenFactory (shared hosted; hardware not under our control)"
    else:
        hardware_label = args.hardware if args.hardware != "unknown" else "AMD Instinct GPU (Self-Hosted)"

    print(f"Base URL Host: {host}")
    print(f"Model Served : {model_name}")
    print(f"Hardware     : {hardware_label}")
    print(f"vLLM Version : {vllm_ver}")
    print(f"Git Commit   : {git_hash}")

    # Load recommendation cards to benchmark real queries
    pipeline_res = run_pipeline(goal_weights=GoalWeights())
    cards = pipeline_res["cards"]
    if not cards:
        print("[ERROR] No recommendation cards generated by pipeline to benchmark.")
        sys.exit(1)

    client = AsyncOpenAI(base_url=base_url, api_key=api_key or "EMPTY", timeout=15.0)

    concurrency_tiers = [1, 4, 8, 16, 32]
    tier_results = []

    print("\nRunning concurrency tiers [1, 4, 8, 16, 32]...")
    for c in concurrency_tiers:
        num_reqs = max(c, args.requests_per_tier)
        print(f"  -> Concurrency = {c} ({num_reqs} requests)...")
        tier_data = asyncio.run(run_concurrency_tier(client, model_name, cards, c, num_reqs))
        tier_results.append(tier_data)
        if "tokens_per_sec" in tier_data:
            print(f"     Throughput: {tier_data['tokens_per_sec']} tok/s | Mean TTFT: {tier_data['mean_ttft_ms']}ms | Grounding: {tier_data['grounding_pass_rate_percent']}%")
        else:
            print(f"     Failed: {tier_data.get('error')}")

    # Summary peak
    valid_tiers = [t for t in tier_results if "tokens_per_sec" in t]
    peak_tok_s = max([t["tokens_per_sec"] for t in valid_tiers]) if valid_tiers else 0.0
    mean_ttft = float(np.mean([t["mean_ttft_ms"] for t in valid_tiers])) if valid_tiers else 0.0
    overall_grounding = float(np.mean([t["grounding_pass_rate_percent"] for t in valid_tiers])) if valid_tiers else 0.0

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    benchmark_record = {
        "benchmark_name": "paylens_serving_benchmark",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "endpoint_type": endpoint_type,
        "base_url_host": host,
        "model_served": model_name,
        "vllm_version": vllm_ver,
        "hardware_label": hardware_label,
        "git_commit": git_hash,
        "provenance": {
            "source": "live_endpoint_measurement",
            "measured_by": "benchmarks/run_benchmark.py",
            "offline_fallback_used": False,
        },
        "summary": {
            "peak_token_throughput_per_sec": peak_tok_s,
            "mean_ttft_ms": round(mean_ttft, 2),
            "mean_grounding_pass_rate_percent": round(overall_grounding, 1),
        },
        "tiers": tier_results,
    }

    # Save timestamped results and latest.json
    out_file = os.path.join(RESULTS_DIR, f"{timestamp_str}.json")
    latest_file = os.path.join(RESULTS_DIR, "latest.json")

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_record, f, indent=2)

    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_record, f, indent=2)

    print(f"\n[SUCCESS] Authentic benchmark results saved to:")
    print(f"  - {out_file}")
    print(f"  - {latest_file}")
    print("=" * 75)


if __name__ == "__main__":
    main()
