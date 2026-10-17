# Team Progress Tracker & Verification Checkpoints

**Project:** PayLens — Multi-Rail Revenue Recovery & Action Centre on AMD Hardware  
**Event:** AMD Developer Hackathon: Act III (Track 3: Reinvent Commerce + Evolus AI Partner Track)  
**Hardware & Models:** AMD Instinct MI300X / AMD TokenFactory / Google Gemma-4-31B-it  

---

## 🚦 Integration Timeline Status

### Checkpoint 1 — Architecture Guardrails & Schema
- [x] **Architecture Rules:** `.agent/rules/paylens.md` enforcing "Code Computes, Model Explains", strict numeric grounding verification, and zero hardcoded secrets.
- [x] **Pydantic v2 Schemas:** `engine/schema.py` defines `GoalWeights`, `RecommendationType`, `LeakSubType`, `EvidenceRow`, `RecommendationCard`, and `grounding_status`.
- [x] **Environment Configuration:** `.env.example` configured for AMD ROCm vLLM, TokenFactory, and Evolus AI with no hardcoded fallback keys or URLs.

### Checkpoint 2 — Deterministic Engine, Synthetic Data & Detectors
- [x] **Synthetic Multi-Rail Generator:** `data/generate_synthetic_data.py` synthesizes 30 days of data for 20 merchants across Card Gateway, Digital Wallets, Bank Transfers, and Courier COD.
- [x] **Noise Injection & Splits:** Supports `--noise`, `--seed 42` tuning split (`paylens.duckdb`), and `--seed 1337` held-out split (`paylens_heldout.duckdb`).
- [x] **Planted Ground Truth:** Dispatched-unpaid leaks, Courier COD shortfalls, Fuzzy-matched True Negatives, Abandoned checkouts, and stockout SKUs planted in `ground_truth.json`.
- [x] **Sample PDF Settlement Statement:** `data/generated/sample_courier_settlement.pdf` generated with planted courier shortfall rows for intake testing.
- [x] **4 Deterministic Detectors:**
  1. 2-Pass Cross-Rail Leak Matcher (Pass 1: Exact Txn Ref; Pass 2: Fuzzy Phone/Email + Exact Amount + 30m window).
  2. Failed-Payment Recovery Scanner with adjustable recovery rate $r$.
  3. statsmodels Holt-Winters Exponential Smoothing SKU stockout forecaster.
  4. statsmodels STL Daily Revenue Anomaly Detector ($|z| > 2.2$).
- [x] **Evaluator & Goal Ranker:** Evaluates precision, recall, and fuzzy True Negative exclusion; dynamic re-ordering of top cards based on GoalWeights.

### Checkpoint 3 — AMD Gemma Agent & Evolus AI Bridge
- [x] **Retrieval Tools:** `agent/tools.py` provides OpenAI tool calling definitions and DuckDB-backed executors.
- [x] **Strict Numeric Grounding Engine:** `agent/grounding.py` extracts numbers, strips formatting, masks IDs/dates/phones, and validates against deterministic allowed lists with 1-retry fallback.
- [x] **Gemma Serving Client:** `agent/gemma_agent.py` supports AMD ROCm vLLM, TokenFactory, and deterministic offline template fallback with honest latency measurement and `logs/inference_log.jsonl` audit logging.
- [x] **Benchmarking Suite:** `benchmarks/run_benchmark.py` authentic runner with concurrency tiers [1, 4, 8, 16, 32] and strict hardware labeling.
- [x] **Evolus AI Partner Track:** `agent/evolus_bridge.py` integrates Ready-Made AI Tools (`document-to-structured-data`, `email-writing`) and agent chat endpoint with dynamic status detection.
- [x] **Global Multi-Rail Connectors:** `engine/connectors.py` provides normalization for Bangladesh MFS, Brazil Pix, India UPI, and Kenya M-Pesa.
- [x] **Live Action Executor:** `agent/action_executor.py` dispatches live actions, sends webhooks, and creates SHA-256 audit receipts.

### Checkpoint 4 — UI Deal Desk, Docker & Submission Readiness
- [x] **Streamlit + Plotly Frontend:** `app.py` delivers 4 tabs: Action Centre Deal Desk, Courier PDF Intake, AMD Hardware Proof, and Global Connectors.
- [x] **Per-Session Sandbox:** Live Anomaly Injector operates on an isolated temporary DuckDB copy with explicit column INSERTs and cache invalidation.
- [x] **Containerization:** `Dockerfile` on `python:3.11-slim` and `docker-compose.yml` for 1-command startup on port 8501.
- [x] **MIT License:** Added `LICENSE` (2026, Labib-morol).
- [x] **Integrity Audit:** Comprehensive `AUDIT.md` and `CHANGES.md` documenting zero fake metrics, honest hardware labels, and verifiable provenance.
- [x] **Test Suite:** Automated pytest test suite verifying numeric grounding, 2-pass matching, and zero forbidden claims.
