# Master Team Progress Tracker & Verification Checkpoints

**Project:** PayLens Solo — Cross-Rail Revenue Recovery & Action Centre on AMD Instinct MI300X  
**Event:** AMD Developer Hackathon: Act III (Track 3: Reinvent Commerce + Evolus AI Partner Track)  
**Target Prizes:** AMD Prize ($5,000) + Google Gemma Prize ($5,000) + Vibe Generation Prize (AirPods 5) + Evolus AI Prize (€1,011.50)  

---

## 🚦 Integration Timeline Status

### Checkpoint 1 — Contract Lock & Architecture Guardrails (Hours 0–2)
- [x] **Architecture Rules:** `.agent/rules/paylens.md` enforcing "Code Computes, Model Explains", strict numeric grounding, and zero hardcoded secrets.
- [x] **Pydantic v2 Schemas:** `engine/schema.py` defines `GoalWeights`, `RecommendationType`, `LeakSubType`, `EvidenceRow`, `RecommendationCard`.
- [x] **Environment Configuration:** `.env.example` and local `.env` configured for AMD MI300X ROCm vLLM, TokenFactory fallback, and Evolus AI.

### Checkpoint 2 — Deterministic Engine, Synthetic Data & Detectors (Hours 2–10)
- [x] **Synthetic Multi-Rail Generator:** `data/generate_synthetic_data.py` synthesizes 30 days of data for 20 merchants across MFS, Card Gateway, Bank Transfers, and Courier COD.
- [x] **Planted Ground Truth:** 8 Dispatched-unpaid leaks, 8 Courier COD shortfalls, 18 Fuzzy-matched True Negatives, 14 Abandoned checkouts, and 3 Pre-Eid stockouts planted in `ground_truth.json`.
- [x] **Sample PDF Settlement Statement:** `data/generated/sample_courier_settlement.pdf` generated with 3 planted courier shortfall rows.
- [x] **4 Deterministic Detectors:**
  1. 2-Pass Cross-Rail Leak Matcher (Exact Txn Ref + Fuzzy Phone/Amount/30m window).
  2. Failed-Payment Recovery Scanner with adjustable recovery rate $r$.
  3. statsmodels Holt-Winters Exponential Smoothing SKU stockout forecaster.
  4. statsmodels STL Daily Revenue Anomaly Detector ($|z| > 2.2$).
- [x] **Evaluator & Goal Ranker:** 100% precision, 100% recall, 100% fuzzy True Negative exclusion rate; dynamic re-ordering of top cards based on GoalWeights.

### Checkpoint 3 — AMD Instinct MI300X Gemma Agent & Evolus AI Bridge (Hours 10–18)
- [x] **Retrieval Tools:** `agent/tools.py` provides OpenAI tool calling definitions and DuckDB-backed executors.
- [x] **Strict Numeric Grounding Engine:** `agent/grounding.py` extracts all numbers (translating Bengali numerals to ASCII), strips formatting, and validates against whitelist with 1-retry fallback.
- [x] **Gemma 4 Client & Serving:** `agent/gemma_agent.py` supports MI300X ROCm vLLM, TokenFactory, and deterministic offline template fallback.
- [x] **MI300X High-Concurrency Burst:** `run_mi300x_parallel_burst` benchmark processes 33 cards at 70,658 recs/min with 100.0% numeric grounding rate.
- [x] **Evolus Building Block 1 (Document Extractor):** `agent/evolus_bridge.py` extracts courier PDFs into structured JSON via REST API with local pypdf fallback.
- [x] **Evolus Building Block 2 (Dispute Workflow):** `agent/evolus_bridge.py` triggers dispute workflows on connected AMD Gemma model.
- [x] **Global Multi-Rail Connectors:** `engine/connectors.py` provides normalization for Bangladesh (bKash/SSL/Steadfast), Brazil Pix, India UPI, and Kenya M-Pesa.
- [x] **Live Action Executor:** `agent/action_executor.py` dispatches live actions, sends webhooks, and creates cryptographic receipts.

### Checkpoint 4 — UI Deal Desk, Docker & Submission Packaging (Hours 18–28)
- [x] **Streamlit + Plotly Frontend:** `app.py` delivers 4 tabs: Action Centre Deal Desk, Courier PDF Intake, Global Connectors, and MI300X Benchmark Proof.
- [x] **Containerization:** `Dockerfile` on `python:3.11-slim` and `docker-compose.yml` for 1-command startup on port 8501.
- [x] **Judge-Ready Documentation:** `README.md` complete with Mermaid diagrams, formulas, ROCm vLLM launch commands, and benchmark tables.
- [x] **Zero Errors Test:** Verified `streamlit run app.py --server.headless true` running cleanly on port 8501.
