# PRODUCT.md — PayLens Product Context & System Truth

**Project:** PayLens: Multi-Rail Revenue Recovery Deal Desk  
**Ecosystem:** AMD Developer Hackathon (Act III) · E-Commerce FinTech  
**Status:** Active Production / Hackathon Submission  
**Framework:** Impeccable Design Context File  

---

## 1. Audience & Persona

* **Primary Users:** FinTech Operations Managers, E-commerce CFOs, Treasury Analysts, and Deal Desk Operators managing multi-channel retail operations ($1M–$50M GMV).
* **Secondary Users / Evaluators:** Hackathon Judges, AMD Systems Engineers, and Venture Evaluators reviewing live inference scalability, accuracy, and operational ergonomics.
* **User Mindset:** High-cognitive-load, data-dense decision making. Operators need immediate signal clarity, verifiable math provenance, zero tolerance for hallucinations, and fast keyboard/mouse action dispatch.

---

## 2. Core Problem & Product Purpose

* **The Problem:** Modern international merchants sell across heterogeneous commerce rails (Shopify, Stripe, PayPal, local bank transfers, DHL/FedEx cash-on-delivery). Disjointed settlement lifecycles create silent leakage:
  1. *Dispatched-Unpaid Orders:* Goods dispatched prior to verified bank ledger settlement.
  2. *Carrier COD Shortfalls:* Couriers remitting payout amounts below contracted tariff matrices.
  3. *Abandoned Checkouts:* Unrecovered transaction drop-offs with reclaim potential.
  4. *Inventory Stockout Margin Risk:* High-margin hero SKUs stock depleting before supplier lead-time replenishment.
* **The Purpose:** PayLens serves as an operational deal desk combining high-throughput deterministic financial reconciliation (DuckDB + Statsmodels) with AMD-accelerated LLM reasoning (vLLM / TokenFactory) to identify, rank, explain, and recover capital leakage with single-click human-in-the-loop action workflows.

---

## 3. Core Principles & Constraints

1. **"Code Computes, Model Explains":**
   * Arithmetic, multi-pass fuzzy matching, Holt-Winters forecasting, and leakage scoring are 100% deterministic code.
   * The language model never performs raw arithmetic; it contextualizes findings and drafts communications.
2. **Numeric Regex Grounding:**
   * Every number emitted in model explanations is checked against allowed database tokens. Any hallucination triggers deterministic fallback.
3. **Execution Safety & Honesty:**
   * Synthetic data and simulated recovery are labeled explicitly. Real action dispatch outputs verifiable SHA-256 audit receipts.
4. **Latency & Throughput Requirements:**
   * Deal desk interactions must feel instantaneous (< 100ms UI response). Heavy inference runs asynchronously or in batch bursts.

---

## 4. Visual Voice & Aesthetic Direction

* **Design Language:** Linear / Stripe-Grade Dark FinTech Workspace.
* **Dominant Color Palette:**
  * Background Base: `#090D16` (Deep Midnight Obsidian)
  * Surface Panels / Cards: `#111827` (Card / Section Surface)
  * Elevated Inspector: `#151F33` (Active selection highlight)
  * Borders / Dividers: `rgba(255, 255, 255, 0.08)`
  * Primary Accent: `#6366F1` (Indigo Glow)
  * Status Indicators:
    * Critical Risk / Leakage: `#EF4444` / `#F87171`
    * Warning / Shortfall: `#F59E0B` / `#FBBF24`
    * Verified / Recovered: `#10B981` / `#34D399`
    * Info / Analytics / Forecasting: `#38BDF8`
* **Typography:**
  * UI Sans: `Plus Jakarta Sans`, system-ui, -apple-system, sans-serif
  * Numeric / Ledger Monospace: `JetBrains Mono`, monospace
* **Layout Structure:**
  * Top Command Bar: System identity, portfolio scope, hardware badge.
  * Hero KPI Row: 4 key metrics (Capital at Risk, Recovered Today, Accuracy, Grounding).
  * 2-Tab Hierarchy:
    - Tab 1: Deal Desk Workspace (Priority Action Queue + Single-Card Inspector Split View).
    - Tab 2: AMD MI300X & Accuracy Proof (Full-width telemetry, benchmarks, and confusion matrices).

---

## 5. Active Impeccable Vocabulary & Command Mapping

* `/impeccable init`: Initializes product context and truth files (`PRODUCT.md`, `DESIGN.md`).
* `/impeccable audit`: Runs systematic technical inspection across Accessibility, Performance, Theming, Responsiveness, and Implementation Integrity.
* `/impeccable polish`: Resolves pixel alignment, micro-spacing, typography scales, and token consistency.
* `/impeccable typeset`: Calibrates font weights, line heights, monospace tabular numerals, and typographic hierarchy.
* `/impeccable colorize`: Balances contrast ratios, semantic alert palettes, and dark-mode surface elevation.
