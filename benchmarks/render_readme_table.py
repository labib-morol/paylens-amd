"""Renders a markdown benchmark table from benchmarks/results/latest.json for the README.

If latest.json is missing or lacks provenance measurements, outputs:
"Not measured yet: run python benchmarks/run_benchmark.py"
"""

import os
import json
from pathlib import Path

LATEST_PATH = Path(__file__).resolve().parent / "results" / "latest.json"


def render_table() -> str:
    if not LATEST_PATH.exists():
        return "Not measured yet: run `python benchmarks/run_benchmark.py` against an active AMD GPU endpoint.\n"

    try:
        with open(LATEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return "Not measured yet: run `python benchmarks/run_benchmark.py` against an active AMD GPU endpoint.\n"

    tiers = data.get("tiers", [])
    if not tiers:
        return "Not measured yet: run `python benchmarks/run_benchmark.py` against an active AMD GPU endpoint.\n"

    lines = [
        f"**Hardware Environment**: `{data.get('hardware_label', 'unknown')}`  ",
        f"**Endpoint Type**: `{data.get('endpoint_type', 'unknown')}` (`{data.get('base_url_host', 'unknown')}`)  ",
        f"**Model Served**: `{data.get('model_served', 'unknown')}`  ",
        f"**Measured At**: `{data.get('started_at', 'unknown')}` | **Git Commit**: `{data.get('git_commit', 'unknown')[:8]}`  \n",
        "| Concurrency | TTFT Mean (ms) | TTFT P95 (ms) | Total Latency P50 (ms) | Total Latency P95 (ms) | Output tok/s | Requests / min | Grounding Pass Rate |",
        "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|",
    ]

    for t in tiers:
        c = t.get("concurrency", "-")
        ttft_m = t.get("mean_ttft_ms", "-")
        ttft_95 = t.get("p95_ttft_ms", "-")
        lat_50 = t.get("p50_latency_ms", "-")
        lat_95 = t.get("p95_latency_ms", "-")
        tok_s = t.get("tokens_per_sec", "-")
        rpm = t.get("requests_per_minute", "-")
        grd = f"{t.get('grounding_pass_rate_percent', '-')}%"
        lines.append(f"| {c} | {ttft_m} | {ttft_95} | {lat_50} | {lat_95} | {tok_s} | {rpm} | {grd} |")

    lines.append("\n*Definition of `recs/min` (recommendations per minute): recommendation cards fully enriched per minute, including multi-objective ranking, DuckDB tool calls, and regex numeric grounding validation.*")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(render_table())
