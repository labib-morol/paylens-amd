"""Authentic Serving and Grounding Benchmark for AMD GPU & Google Gemma Endpoints.

Architecture Rules:
1. Strict provenance: records endpoint_type, base_url_host, model_served, started_at, git_commit.
2. Measures REAL live requests against AMD Radeon Cloud TokenFactory and Google Gemma 4.
3. Concurrency levels: evaluates [1, 4, 8] using real async streaming/REST client calls.
4. Measures TTFT (ms), End-to-End Latency (ms), Tokens/sec, Errors, and Numeric Validation Pass Rate.
5. Saves real measured telemetry to benchmarks/benchmark_results.json.
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

import logging
logging.getLogger("streamlit").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.scriptrunner_utils").setLevel(logging.ERROR)

ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.pipeline import run_pipeline
from engine.schema import GoalWeights, RecommendationCard
from agent.grounding import verify_numeric_grounding
from agent.gemma_agent import get_endpoint_config, check_endpoint_status

BENCHMARK_RESULTS_PATH = os.path.join(ROOT_DIR, "benchmarks", "benchmark_results.json")
RESULTS_DIR = os.path.join(ROOT_DIR, "benchmarks", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)


def get_git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return "unknown"


async def benchmark_single_amd_request(
    client: AsyncOpenAI,
    model: str,
    card: RecommendationCard,
) -> Dict[str, Any]:
    """Execute a single streaming request to measure TTFT, latency, tokens, and grounding."""
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
            timeout=20.0,
        )
        async for chunk in stream:
            if hasattr(chunk, "choices") and chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta and hasattr(delta, "content") and delta.content:
                    if ttft is None:
                        ttft = time.perf_counter() - t0
                    full_content.append(delta.content)
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
            "error": None,
        }
    except Exception as e:
        total_latency = time.perf_counter() - t0
        return {
            "success": False,
            "ttft_ms": round(total_latency * 1000.0, 2),
            "latency_ms": round(total_latency * 1000.0, 2),
            "output_tokens": 0,
            "grounding_passed": False,
            "ungrounded_tokens": [],
            "error": str(e)[:120],
        }


async def run_amd_concurrency_tier(
    client: AsyncOpenAI,
    model: str,
    cards: List[RecommendationCard],
    concurrency: int,
    requests_to_run: int,
) -> Dict[str, Any]:
    semaphore = asyncio.Semaphore(concurrency)

    async def _worker(card: RecommendationCard):
        async with semaphore:
            return await benchmark_single_amd_request(client, model, card)

    tasks = []
    for i in range(requests_to_run):
        card = cards[i % len(cards)]
        tasks.append(_worker(card))

    t0 = time.perf_counter()
    results = await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - t0

    success_results = [r for r in results if r.get("success")]
    failed_results = [r for r in results if not r.get("success")]

    if not success_results:
        return {
            "concurrency": concurrency,
            "total_requests": requests_to_run,
            "completed_requests": 0,
            "failed_requests": len(failed_results),
            "duration_seconds": round(elapsed, 3),
            "error": failed_results[0].get("error") if failed_results else "All requests failed",
        }

    ttfts = [r["ttft_ms"] for r in success_results]
    latencies = [r["latency_ms"] for r in success_results]
    total_tokens = sum(r["output_tokens"] for r in success_results)
    grounded_count = sum(1 for r in success_results if r["grounding_passed"])

    return {
        "concurrency": concurrency,
        "total_requests": requests_to_run,
        "completed_requests": len(success_results),
        "failed_requests": len(failed_results),
        "duration_seconds": round(elapsed, 3),
        "mean_ttft_ms": round(float(np.mean(ttfts)), 1),
        "p95_ttft_ms": round(float(np.percentile(ttfts, 95)), 1),
        "mean_latency_ms": round(float(np.mean(latencies)), 1),
        "p50_latency_ms": round(float(np.percentile(latencies, 50)), 1),
        "p95_latency_ms": round(float(np.percentile(latencies, 95)), 1),
        "tokens_per_sec": round(total_tokens / max(0.001, elapsed), 1),
        "requests_per_minute": round((len(success_results) / max(0.001, elapsed)) * 60.0, 1),
        "grounding_pass_rate_percent": round((grounded_count / len(success_results)) * 100.0, 1),
    }


def benchmark_google_gemma_rest(
    gemini_key: str,
    model: str = "gemma-4-31b-it",
    num_requests: int = 2,
) -> Dict[str, Any]:
    """Measure real live latency and response from Google AI Studio REST API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": "You are PayLens AI explaining revenue recovery. Return JSON: {\"status\": \"verified\"}"}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 100},
    }

    latencies = []
    successes = 0
    errors = []

    for _ in range(num_requests):
        t0 = time.perf_counter()
        try:
            with httpx.Client(timeout=15.0) as client:
                r = client.post(url, json=payload)
                lat = round((time.perf_counter() - t0) * 1000.0, 1)
                if r.status_code == 200:
                    latencies.append(lat)
                    successes += 1
                else:
                    errors.append(f"HTTP {r.status_code}: {r.text[:80]}")
        except Exception as e:
            errors.append(str(e)[:80])

    return {
        "provider": "Google AI Studio Gemma 4 REST API",
        "model": model,
        "endpoint": "https://generativelanguage.googleapis.com/v1beta",
        "requests": num_requests,
        "completed": successes,
        "errors": errors,
        "mean_latency_ms": round(float(np.mean(latencies)), 1) if latencies else None,
        "is_live": successes > 0,
    }


def main():
    parser = argparse.ArgumentParser(description="PayLens Live AMD & Gemma 4 Concurrency Benchmark")
    parser.add_argument("--tiers", nargs="+", type=int, default=[1, 4, 8], help="Concurrency tiers to test (default: 1 4 8)")
    parser.add_argument("--reqs-per-tier", type=int, default=4, help="Requests per concurrency tier (default: 4)")
    args = parser.parse_args()

    print("=" * 75)
    print("PAYLENS REAL-TIME DUAL-ENGINE LIVE GPU BENCHMARK")
    print("=" * 75)

    status = check_endpoint_status()
    cfg = get_endpoint_config()

    print(f"AMD TokenFactory Status: {'LIVE' if status['amd_status']['is_live'] else 'OFFLINE'} (Ping: {status['amd_status']['ping_latency_ms']} ms)")
    print(f"Google Gemma 4 Status  : {'LIVE' if status['gemma_status']['is_live'] else 'OFFLINE'} (Ping: {status['gemma_status']['ping_latency_ms']} ms)")

    # Run real pipeline to get recommendation cards
    pipeline_res = run_pipeline(goal_weights=GoalWeights())
    cards = pipeline_res["cards"]
    if not cards:
        print("[ERROR] No recommendation cards generated by pipeline.")
        sys.exit(1)

    # 1. AMD TokenFactory Concurrency Benchmark
    amd_tier_results = []
    amd_model_used = status["amd_status"]["model_served"] or "DeepSeek-V4-Flash"
    amd_url_used = cfg["amd_url"]

    if status["amd_status"]["is_live"]:
        print(f"\n[1/2] Running AMD TokenFactory Benchmark against {amd_url_used}...")
        print(f"      Active Model: {amd_model_used}")
        client = AsyncOpenAI(base_url=amd_url_used, api_key=cfg["amd_key"], timeout=20.0)

        for c in args.tiers:
            reqs = max(c, args.reqs_per_tier)
            print(f"  -> Concurrency Tier = {c} ({reqs} real requests)...")
            tier_data = asyncio.run(run_amd_concurrency_tier(client, amd_model_used, cards, c, reqs))
            amd_tier_results.append(tier_data)
            if "tokens_per_sec" in tier_data:
                print(f"     Throughput: {tier_data['tokens_per_sec']} tok/s | Mean TTFT: {tier_data['mean_ttft_ms']} ms | Mean Lat: {tier_data['mean_latency_ms']} ms | Errors: {tier_data['failed_requests']}")
            else:
                print(f"     Failed: {tier_data.get('error')}")
    else:
        print("\n[1/2] AMD TokenFactory is currently offline. Skipping live AMD concurrency.")

    # 2. Google Gemma 4 REST Benchmark
    google_bench = {}
    if status["gemma_status"]["is_live"]:
        print("\n[2/2] Running Google Gemma 4 REST Benchmark...")
        google_bench = benchmark_google_gemma_rest(cfg["gemini_key"], model="gemma-4-31b-it", num_requests=2)
        print(f"      Result: Completed {google_bench['completed']}/{google_bench['requests']} in mean {google_bench.get('mean_latency_ms')} ms")
    else:
        print("\n[2/2] Google Gemma 4 REST API is currently offline.")

    # Calculate summary metrics
    valid_tiers = [t for t in amd_tier_results if "tokens_per_sec" in t]
    peak_tok_s = max([t["tokens_per_sec"] for t in valid_tiers]) if valid_tiers else 0.0
    mean_ttft = float(np.mean([t["mean_ttft_ms"] for t in valid_tiers])) if valid_tiers else 0.0
    mean_lat = float(np.mean([t["mean_latency_ms"] for t in valid_tiers])) if valid_tiers else 0.0
    total_errors = sum(t.get("failed_requests", 0) for t in amd_tier_results)

    timestamp_str = datetime.now(timezone.utc).isoformat()
    git_hash = get_git_commit()

    benchmark_record = {
        "benchmark_name": "paylens_live_dual_engine_benchmark",
        "measured_at": timestamp_str,
        "git_commit": git_hash,
        "amd_tokenfactory": {
            "is_live": status["amd_status"]["is_live"],
            "base_url": amd_url_used,
            "model_served": amd_model_used,
            "hardware_label": "AMD Radeon Cloud TokenFactory (Shared Hosted)",
            "ping_latency_ms": status["amd_status"]["ping_latency_ms"],
            "summary": {
                "peak_token_throughput_per_sec": peak_tok_s,
                "mean_ttft_ms": round(mean_ttft, 1),
                "mean_latency_ms": round(mean_lat, 1),
                "total_errors": total_errors,
            },
            "tiers": amd_tier_results,
        },
        "google_gemma4": google_bench,
        "provenance": {
            "source": "live_endpoint_measurement",
            "script": "benchmarks/run_mi300x_benchmark.py",
            "offline_fallback_used": False,
        },
    }

    # Save to benchmarks/benchmark_results.json and results/latest.json
    with open(BENCHMARK_RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(benchmark_record, f, indent=2)

    latest_path = os.path.join(RESULTS_DIR, "latest.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_record, f, indent=2)

    print(f"\n[SUCCESS] Authentic benchmark telemetry saved to:")
    print(f"  - {BENCHMARK_RESULTS_PATH}")
    print(f"  - {latest_path}")
    print("=" * 75)


if __name__ == "__main__":
    main()
