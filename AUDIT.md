# AUDIT.md — PayLens Pre-Submission Audit

**Repository:** `labib-morol/paylens-amd`  
**Audit Timestamp:** 2026-10-17T09:20:00+06:00  
**Scope:** Integrity, provenance, live inference readiness, and hackathon rule compliance.

---

## 1. Executive Summary

This audit catalogs every hardcoded claim, unverified benchmark number, fake grounding assertion, undocumented API path, and missing safety mechanism across the PayLens codebase before the remediation pass.

---

## 2. Issue Mapping by Task

### Task P0-1: Fake Grounding Claims
* `app.py:519`: Fixed header pill `<span class="grounding-pill">✓ 100% Numeric Grounding Verified</span>`.
* `app.py:614-617`: Fixed KPI card `<div class="kpi-value" style="color: #38BDF8;">100.0%</div><div class="kpi-sub">0 Hallucinations · Strict regex audit</div>`.
* `app.py:941`: Per-card pill `<span class="grounding-pill">✓ Grounding Check Passed (0 Hallucinations)</span>`.
* `app.py:935`: Red-team expander pill `<span class="grounding-pill">✓ 100% Numeric Grounding Restored (0 Hallucinations)</span>`.
* `app.py:1112`: Tab 3 metric label `m_col4.metric("Fuzzy TN Exclusion Rate", ..., help="Must be 100% to guarantee 0 false alarms on missing transaction IDs!")`.
* `engine/schema.py:90-95`: Missing `grounding_status` field on `RecommendationCard` (only had `grounding_passed: bool`).
* `agent/gemma_agent.py:256, 315, 337, 356, 390, 401`: Did not set explicit `grounding_status` values (`PASSED`, `RETRIED_PASSED`, `TEMPLATE_FALLBACK`, `NOT_APPLICABLE_OFFLINE`).

### Task P0-2: Benchmark Integrity & Static Metrics
* `app.py:814-825` (now lines ~1130-1145): Hand-typed concurrency chart list `throughputs = [350, 1100, 1850, 2400, ref_bench['benchmark_results']['token_throughput_per_sec']]`.
* `benchmarks/mi300x_vllm_bench_serve.json:1-38`: Hand-typed / unverified reference file lacking provenance fields (`source`, `measured_at`, `endpoint_type`, `command`, `git_commit`).
* `agent/gemma_agent.py:42-56`: `import_vllm_bench_serve_json()` loading this unverified reference file.
* `app.py:623-635`: KPI Card 4 displaying `ref_bench['benchmark_results']['token_throughput_per_sec']:,.0f tok/s` when offline.
* `README.md:129-130`: Hardcoded claims `2,842.6 tokens / second`, `1,286.9 requests / minute`.
* `README.md:220`: Conflicting claim `82,898 recs/min`.
* `PROGRESS.md:31`: Conflicting claim `70,658 recs/min`.
* `README.md:123`: Unverified host claim `ROCm 6.2 + vLLM 0.6.3`.
* `app.py:251-258`: Sidebar static hardware specs ("304 CDNA 3 Compute Units", "192 GB HBM3 @ 5.3 TB/s", "KV Cache Free ~129.6 GB", "32+ concurrency").
* `app.py:516`: Header badge hardcoded `<span ...>AMD Instinct MI300X · Gemma 4</span>`.

### Task P0-3: AMD Live Inference & Endpoint Configuration
* `Dockerfile:26`: `ENV OFFLINE_MODE=true` hardcoding offline mode inside the image.
* `agent/gemma_agent.py:33-36`: Environment variables having hardcoded defaults (`MODEL_NAME = os.getenv("VLLM_MODEL", "google/gemma-4-31B-it")`, `PRIMARY_URL = ... "http://localhost:8000/v1"`, `API_KEY = ... "mock-key-for-local-dev"`). Missing `st.secrets` precedence.
* `app.py:229`: Health check returning `0.0 ms` latency when offline without dynamic model validation against `/models`.
* Missing `logs/inference_log.jsonl` audit log recording real prompt/completion token usage and latency.
* `agent/gemma_agent.py:128-160`: `goal_to_weights` not cached, recalculating repeatedly.

### Task P0-4: Secrets Safety & Git History
* Git log search (`api_key`, `hf_`, `sk-`, `Bearer`, `X-ApiKey`, `evo_`, `rc-`) confirmed: No live production keys ever committed to Git.
* `.gitignore:1-32`: Missing `logs/`, `*.duckdb`.
* `.dockerignore`: Missing file entirely.

### Task P1-1: Evolus Honesty
* `agent/evolus_bridge.py:126-154`: Undocumented path `POST /api/v1/extractors/{id}/run`.
* `agent/evolus_bridge.py:382-520`: `run_evolus_telemetry_ping` mocking receipts and hardcoding claims of prize eligibility.
* `app.py:261-265`: Sidebar showing "Connected (Live Multi-Block)" even when API returned HTTP 401.

### Task P1-2: Claims Sweep
* `README.md:4`: `AMD Instinct™ MI300X Prize ($5,000)`, `Google DeepMind Gemma Prize ($5,000)`, `Evolus AI Partner Track (€1,011.50)`.
* `PROGRESS.md:5`: `Target Prizes: AMD Prize ($5,000) + Google Gemma Prize ($5,000) ... (€1,011.50)`.
* `README.md:11`: Unverified statistic `leaks 3%–7% of gross merchandise volume`.
* `README.md:1, 17`, `app.py:1, 514, 1003`: Overstated terms `Autonomous` and `Zero-Hallucination`.
* `README.md:62`, `app.py:990`: Overstated term `Cryptographic Audit Hash`.

### Task P1-3: Metric Names
* `app.py:603`: "Recovered & Approved Today" implies real financial movement.
* `app.py:592`: "Total Capital at Risk Found" needs "(synthetic data)" suffix.
* Missing persistent banner declaring synthetic data and simulated execution.

### Task P1-4: Judge Anomaly Injection Sandbox
* `app.py:669-724`: Injects directly into shared `duckdb_path` without per-session sandboxing.
* `app.py:674`: Hardcoded judge email `judge.alex@amd-hackathon.org`.
* `app.py:706-720`: Hand-builds a `RecommendationCard` with fixed confidence `0.99` and bypasses the real detector pipeline.

### Task P1-5: Mermaid Diagram Rendering
* `app.py:1180-1204`: Renders Mermaid via `st.markdown("""```mermaid ... ```""")`, which Streamlit renders as raw unformatted code block text.

### Task P1-6: Caching & Performance
* `app.py:570`: `run_pipeline` called without `st.cache_data`.
* `app.py:769-780`: Slider change re-runs `run_pipeline` twice in the same render pass.
* `app.py:794`: Enriches all cards immediately on page load rather than top 3 cards with on-demand buttons.

### Task P1-7: Synthetic Data Generator & Noise
* `data/generate_synthetic_data.py:1-664`: Generates idealized clean data without realistic noise cases (duplicate txn IDs, timestamp offsets, 50% partial payments, delayed courier settlements).
* Single seed (42) without separate held-out seed evaluation.

### Task P1-8: Grounding Checker Review
* `agent/grounding.py:41-60`: Missing support for `INJ-` IDs and lakh formatting; lacks pre-computed discount amount for `VIP 5% Instant-Pay Discount`.
* Missing comprehensive unit tests in `tests/`.

### Task P1-9: Repo Hygiene
* Missing `LICENSE` (MIT).
* `.agents/skills/` and `skills-lock.json` tracked in Git.
* Missing `tests/` test suite with forbidden string assertion test.

---
This audit guides every change in the remediation plan below.
