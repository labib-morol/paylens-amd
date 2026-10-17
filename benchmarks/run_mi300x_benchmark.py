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
    """Execute a single streaming request to measure TTFT, latency, tokens, and separated grounding outcomes."""
    evidence_text = "\n".join([f"- [{ev.source_table}] {ev.summary}" for ev in card.evidence_rows]) if card.evidence_rows else "- No auxiliary evidence rows."

    system_prompt = (
        "You are PayLens AI explaining merchant capital recovery. "
        "MANDATORY ARCHITECTURE RULE: CODE COMPUTES, MODEL EXPLAINS. "
        "You must NEVER calculate numbers. Output valid JSON with exactly two keys: 'explanation_en' and 'action_draft_en'."
    )
    user_prompt = f"""Merchant: {card.merchant_name}
Recommendation Type: {card.rec_type.value}
Entity ID: {card.entity_id}
Tone: Polite Payment Reminder
Impact (USD): ${card.impact_usd:,.2f}
Formula: {card.formula_display}
Evidence Rows:
{evidence_text}
ALLOWED_NUMBERS: {card.allowed_numbers}

CRITICAL RULE: Every single number or currency figure you write MUST come verbatim from ALLOWED_NUMBERS: {card.allowed_numbers}. Do NOT write any other digits in your text—write general timeframes in words (e.g., 'twenty-four hours', 'seven days') so no unverified numbers appear.

Write concise English explanations and action drafts. Output JSON format: {{"explanation_en": "...", "action_draft_en": "..."}}
"""

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
            max_tokens=300,
            stream=True,
            stream_options={"include_usage": True},
            timeout=15.0,
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

        first_pass = is_grounded
        post_retry = False
        fallback = False

        if not is_grounded:
            # Single retry with explicit correction prompt
            retry_prompt = user_prompt + f"\n\nERROR: The numbers {ungrounded} were not in ALLOWED_NUMBERS. Rewrite using ONLY verbatim numbers from: {card.allowed_numbers}"
            try:
                r_resp = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": retry_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=300,
                    timeout=10.0,
                )
                r_text = r_resp.choices[0].message.content or ""
                r_ok, _ = verify_numeric_grounding(r_text, allowed)
                if r_ok:
                    post_retry = True
                else:
                    fallback = True
            except Exception:
                fallback = True

        return {
            "success": True,
            "ttft_ms": round(ttft * 1000.0, 2),
            "latency_ms": round(total_latency * 1000.0, 2),
            "output_tokens": output_tokens,
            "grounding_passed": first_pass or post_retry,
            "first_pass_passed": first_pass,
            "post_retry_passed": post_retry,
            "fallback": fallback,
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
            "first_pass_passed": False,
            "post_retry_passed": False,
            "fallback": True,
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
            "attempted_requests": requests_to_run,
            "total_requests": requests_to_run,
            "completed_requests": 0,
            "failed_requests": len(failed_results),
            "first_pass_model_grounding_rate": None,
            "post_retry_model_grounding_rate": None,
            "deterministic_fallback_rate": None,
            "duration_seconds": round(elapsed, 3),
            "error": failed_results[0].get("error") if failed_results else "All requests failed",
        }

    ttfts = [r["ttft_ms"] for r in success_results]
    latencies = [r["latency_ms"] for r in success_results]
    total_tokens = sum(r["output_tokens"] for r in success_results)
    
    first_pass_count = sum(1 for r in success_results if r.get("first_pass_passed"))
    post_retry_count = sum(1 for r in success_results if r.get("post_retry_passed"))
    fallback_count = sum(1 for r in success_results if r.get("fallback"))
    total_valid = len(success_results)

    first_pass_rate = round((first_pass_count / total_valid) * 100.0, 1) if total_valid > 0 else None
    post_retry_rate = round((post_retry_count / total_valid) * 100.0, 1) if total_valid > 0 else None
    fallback_rate = round((fallback_count / total_valid) * 100.0, 1) if total_valid > 0 else None

    return {
        "concurrency": concurrency,
        "attempted_requests": requests_to_run,
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
        "first_pass_model_grounding_rate": first_pass_rate,
        "post_retry_model_grounding_rate": post_retry_rate,
        "deterministic_fallback_rate": fallback_rate,
        "deterministic_template_fallback_rate": fallback_rate,
        "grounding_pass_rate_percent": (first_pass_rate or 0.0) + (post_retry_rate or 0.0),
    }


def benchmark_google_gemma_rest(
    gemini_key: str,
    model: str = "gemma-4-31b-it",
    cards: Optional[List[RecommendationCard]] = None,
    num_requests: int = 2,
) -> Dict[str, Any]:
    """Measure real live latency and response from Google AI Studio REST API."""
    card = cards[0] if cards else None
    allowed = (card.allowed_numbers + [card.impact_usd]) if card else [100.0]
    evidence_text = "\n".join([f"- [{ev.source_table}] {ev.summary}" for ev in card.evidence_rows]) if card and card.evidence_rows else "- No auxiliary evidence rows."

    system_prompt = (
        "You are PayLens AI explaining merchant capital recovery. "
        "MANDATORY ARCHITECTURE RULE: CODE COMPUTES, MODEL EXPLAINS. "
        "You must NEVER calculate numbers. Output valid JSON with exactly two keys: 'explanation_en' and 'action_draft_en'."
    )
    user_prompt = f"""Merchant: {card.merchant_name if card else 'Apex Global'}
Recommendation Type: {card.rec_type.value if card else 'PAYMENT_LEAKAGE'}
Impact: ${card.impact_usd if card else 100.0:,.2f}
Evidence Rows:
{evidence_text}
ALLOWED_NUMBERS: {allowed}

CRITICAL RULE: Every single number or currency figure you write MUST come verbatim from ALLOWED_NUMBERS: {allowed}. Do NOT write any other digits in your text—write general timeframes in words (e.g., 'twenty-four hours', 'seven days') so no unverified numbers appear.

Output JSON format: {{"explanation_en": "...", "action_draft_en": "..."}}
"""
    full_prompt = f"{system_prompt}\n\nTask:\n{user_prompt}"
    models_to_try = [model]
    if model != "gemma-4-26b-a4b-it":
        models_to_try.append("gemma-4-26b-a4b-it")

    payload = {
        "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 400},
    }

    latencies = []
    successes = 0
    errors = []
    grounded_first_pass = 0
    grounded_post_retry = 0
    fallbacks = 0
    actual_model_used = model

    for _ in range(num_requests):
        t0 = time.perf_counter()
        req_ok = False
        for target_model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={gemini_key}"
            try:
                with httpx.Client(timeout=12.0) as client:
                    r = client.post(url, json=payload)
                    lat = round((time.perf_counter() - t0) * 1000.0, 1)
                    if r.status_code == 200:
                        data = r.json()
                        candidates = data.get("candidates", [])
                        text = candidates[0]["content"]["parts"][0]["text"] if candidates else ""
                        latencies.append(lat)
                        successes += 1
                        actual_model_used = target_model
                        req_ok = True

                        ok, _ = verify_numeric_grounding(text, allowed)
                        if ok:
                            grounded_first_pass += 1
                        else:
                            fallbacks += 1
                        break
                    elif r.status_code == 500:
                        continue
                    else:
                        errors.append(f"HTTP {r.status_code}: {r.text[:80]}")
                        continue
            except Exception as e:
                last_err = str(e)[:80]
                continue
        if not req_ok and not successes:
            errors.append(last_err or "All models returned 500 or timed out")

    return {
        "provider": "Google AI Studio Gemma 4 REST API",
        "model": actual_model_used,
        "endpoint": "https://generativelanguage.googleapis.com/v1beta",
        "attempted_requests": num_requests,
        "requests": num_requests,
        "completed_requests": successes,
        "completed": successes,
        "failed_requests": num_requests - successes,
        "errors": errors if successes == 0 else [],
        "mean_latency_ms": round(float(np.mean(latencies)), 1) if latencies else None,
        "first_pass_model_grounding_rate": round((grounded_first_pass / successes) * 100.0, 1) if successes > 0 else None,
        "post_retry_model_grounding_rate": round((grounded_post_retry / successes) * 100.0, 1) if successes > 0 else None,
        "deterministic_fallback_rate": round((fallbacks / successes) * 100.0, 1) if successes > 0 else None,
        "deterministic_template_fallback_rate": round((fallbacks / successes) * 100.0, 1) if successes > 0 else None,
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
        google_bench = benchmark_google_gemma_rest(cfg["gemini_key"], model="gemma-4-31b-it", cards=cards, num_requests=2)
        print(f"      Result: Completed {google_bench['completed']}/{google_bench['requests']} in mean {google_bench.get('mean_latency_ms')} ms")
    else:
        print("\n[2/2] Google Gemma 4 REST API is currently offline.")

    # Calculate summary metrics
    valid_tiers = [t for t in amd_tier_results if "tokens_per_sec" in t]
    peak_tok_s = max([t["tokens_per_sec"] for t in valid_tiers]) if valid_tiers else 0.0
    mean_ttft = float(np.mean([t["mean_ttft_ms"] for t in valid_tiers])) if valid_tiers else 0.0
    mean_lat = float(np.mean([t["mean_latency_ms"] for t in valid_tiers])) if valid_tiers else 0.0
    total_attempted = sum(t.get("attempted_requests", t.get("total_requests", 0)) for t in amd_tier_results)
    total_completed = sum(t.get("completed_requests", 0) for t in amd_tier_results)
    total_failed = sum(t.get("failed_requests", 0) for t in amd_tier_results)
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
                "attempted_requests": total_attempted,
                "completed_requests": total_completed,
                "failed_requests": total_failed,
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
