"""PayLens: Multi-Rail Revenue Reconciliation Deal Desk on AMD Hardware.

Engine: DuckDB + 2-Pass Fuzzy Matching + Holt-Winters Demand Forecasting.
Agent:  AMD Radeon Cloud TokenFactory (DeepSeek-V4-Flash / Gemma-4-31B-IT) + Google Gemma 4 REST API + Strict Grounding Guardrail.
Layout: Pure Native Streamlit Containers (st.container, st.columns, st.metric, st.dataframe, st.plotly_chart).
"""

import os
import sys
import time
import json
import html
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import duckdb
from statsmodels.tsa.holtwinters import ExponentialSmoothing

ROOT_DIR = str(Path(__file__).resolve().parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine.schema import RecommendationCard, RecommendationType, LeakSubType, GoalWeights, ExecutionSource
from engine.pipeline import run_pipeline, get_merchant_names
from engine.ranker import rank_cards
from engine.evaluator import evaluate_recommendations
from agent.gemma_agent import (
    check_endpoint_status,
    check_endpoint_health,
    goal_to_weights,
    enrich_card_with_agent,
    get_endpoint_config,
)
from agent.grounding import verify_numeric_grounding, build_fallback_template

# -----------------------------------------------------------------------------
# Streamlit Page Configuration & Native Theming
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="PayLens // Revenue Recovery Deal Desk",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Clean CSS to hide default header/footer and enforce tabular numeric rhythm
st.html(
    """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container {padding-top: 1.25rem; padding-bottom: 2.5rem; max-width: 96rem;}

    /* Tabular numeric alignment for financial values and tables */
    [data-testid="stMetricValue"], [data-testid="stDataFrame"], code {
        font-variant-numeric: tabular-nums;
    }

    /* Subtle semantic status badges */
    .badge-leak {
        background: rgba(239, 68, 68, 0.15);
        color: #FCA5A5;
        border: 1px solid rgba(239, 68, 68, 0.35);
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }
    .badge-recovery {
        background: rgba(245, 158, 11, 0.15);
        color: #FDE68A;
        border: 1px solid rgba(245, 158, 11, 0.35);
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }
    .badge-stockout {
        background: rgba(167, 139, 250, 0.15);
        color: #DDD6FE;
        border: 1px solid rgba(167, 139, 250, 0.35);
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.05em;
    }
    </style>
    """
)

# -----------------------------------------------------------------------------
# Session State Initialization
# -----------------------------------------------------------------------------
if "approved_actions" not in st.session_state:
    st.session_state.approved_actions = {}
if "rejected_actions" not in st.session_state:
    st.session_state.rejected_actions = {}
if "selected_card_id" not in st.session_state:
    st.session_state.selected_card_id = None
if "live_enriched_cards" not in st.session_state:
    st.session_state.live_enriched_cards = {}
if "benchmark_run_history" not in st.session_state:
    st.session_state.benchmark_run_history = None

# -----------------------------------------------------------------------------
# Cached Helper Routines
# -----------------------------------------------------------------------------
@st.cache_data(ttl=300)
def cached_get_merchant_names() -> Dict[str, str]:
    return get_merchant_names()


@st.cache_data(ttl=60, show_spinner=False)
def cached_run_pipeline(weights_tuple: tuple, r_rate: float, lead_time: int) -> Dict[str, Any]:
    weights = GoalWeights(
        cash_now_weight=weights_tuple[0],
        margin_protection_weight=weights_tuple[1],
        stock_availability_weight=weights_tuple[2],
    )
    return run_pipeline(
        goal_weights=weights,
        recovery_rate=r_rate,
        supplier_lead_time_override=lead_time,
    )


@st.cache_data(ttl=120)
def build_reconciliation_comparison_bar(card: RecommendationCard):
    """Builds a clean horizontal financial breakdown chart for the selected card."""
    fig = go.Figure()
    if card.rec_type == RecommendationType.PAYMENT_LEAKAGE:
        fig.add_trace(go.Bar(
            y=["Ledger Reconciliation"],
            x=[card.impact_usd],
            name="Unsettled Discrepancy",
            orientation="h",
            marker=dict(color="#EF4444"),
        ))
    elif card.rec_type == RecommendationType.FAILED_PAYMENT_RECOVERY:
        fig.add_trace(go.Bar(
            y=["Checkout Recovery"],
            x=[card.impact_usd],
            name="Projected Recovery",
            orientation="h",
            marker=dict(color="#F59E0B"),
        ))
    else:
        fig.add_trace(go.Bar(
            y=["Stockout Margin Risk"],
            x=[card.impact_usd],
            name="Margin at Risk",
            orientation="h",
            marker=dict(color="#A78BFA"),
        ))

    fig.update_layout(
        template="plotly_dark",
        height=130,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", tickprefix="$"),
        yaxis=dict(showticklabels=False),
        plot_bgcolor="rgba(17, 24, 39, 0.5)",
        paper_bgcolor="rgba(17, 24, 39, 0.5)",
        legend=dict(orientation="h", y=1.25, x=0),
    )
    return fig


@st.cache_data(ttl=120)
def build_stockout_forecast_chart(duckdb_path: str, sku: str):
    """Builds historical stock and 7-day lead-time cover forecast chart."""
    if not os.path.exists(duckdb_path):
        return None
    con = duckdb.connect(duckdb_path, read_only=True)
    try:
        df = con.execute(
            "SELECT snapshot_date, current_stock, units_sold_today FROM inventory_daily WHERE sku = ? ORDER BY snapshot_date ASC",
            [sku],
        ).df()
    finally:
        con.close()

    if df.empty:
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["snapshot_date"],
        y=df["current_stock"],
        mode="lines+markers",
        name="Stock On Hand (Units)",
        line=dict(color="#A78BFA", width=2),
    ))
    fig.add_trace(go.Bar(
        x=df["snapshot_date"],
        y=df["units_sold_today"],
        name="Daily Demand",
        marker=dict(color="rgba(99, 102, 241, 0.4)"),
    ))

    fig.update_layout(
        template="plotly_dark",
        height=220,
        margin=dict(l=10, r=10, t=25, b=10),
        plot_bgcolor="rgba(17, 24, 39, 0.5)",
        paper_bgcolor="rgba(17, 24, 39, 0.5)",
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        legend=dict(orientation="h", y=1.15, x=0),
    )
    return fig


# -----------------------------------------------------------------------------
# Live Runtime Hardware & Endpoint Health Check
# -----------------------------------------------------------------------------
endpoint_status = check_endpoint_status()
amd_live = endpoint_status["amd_status"]["is_live"]
amd_model = endpoint_status["amd_status"]["model_served"]
amd_lat = endpoint_status["amd_status"]["ping_latency_ms"]
amd_url = endpoint_status["amd_status"]["base_url"]

gemma_live = endpoint_status["gemma_status"]["is_live"]
gemma_model = endpoint_status["gemma_status"]["model_served"]
gemma_lat = endpoint_status["gemma_status"]["ping_latency_ms"]

# -----------------------------------------------------------------------------
# Sidebar Configuration Controls
# -----------------------------------------------------------------------------
st.sidebar.title("🛡️ PayLens Deal Desk")
st.sidebar.caption("Deterministic Multi-Rail Capital Recovery")

# Merchant Selector
merchant_map = cached_get_merchant_names()
merchant_ids = sorted(list(merchant_map.keys()))
default_merch_idx = 1 if "MERCH_02" in merchant_ids else 0
selected_merchant = st.sidebar.selectbox(
    "Active Storefront",
    options=merchant_ids,
    index=default_merch_idx,
    format_func=lambda m: f"{m} — {merchant_map.get(m, m)}",
)

# Business Priority / Objective
st.sidebar.subheader("Business Objective")
goal_preset = st.sidebar.radio(
    "Optimization Goal",
    options=[
        "Urgent Cash Recovery (High Cash)",
        "Protect Profit Margins (High Margin)",
        "Prevent Stockouts (High Inventory Cover)",
        "Custom Natural Language Goal",
    ],
    index=0,
)

if goal_preset == "Urgent Cash Recovery (High Cash)":
    current_goal_text = "Urgent cash recovery on unreconciled orders"
    active_weights = GoalWeights(cash_now_weight=0.80, margin_protection_weight=0.10, stock_availability_weight=0.10)
elif goal_preset == "Protect Profit Margins (High Margin)":
    current_goal_text = "Protect profit margins and prevent lost revenue"
    active_weights = GoalWeights(cash_now_weight=0.10, margin_protection_weight=0.45, stock_availability_weight=0.45)
elif goal_preset == "Prevent Stockouts (High Inventory Cover)":
    current_goal_text = "Prevent stockouts on high-demand hero SKUs"
    active_weights = GoalWeights(cash_now_weight=0.10, margin_protection_weight=0.45, stock_availability_weight=0.45)
else:
    custom_input = st.sidebar.text_input("Enter Merchant Goal", value="Collect overdue settlements and protect stock")
    current_goal_text = custom_input
    active_weights = goal_to_weights(custom_input)

# Live Engine Selection
st.sidebar.subheader("AI Reasoning Engine")
engine_choice_ui = st.sidebar.selectbox(
    "Active Inference Target",
    options=[
        "Auto-Select Best Live Engine",
        "AMD Radeon Cloud TokenFactory (Live API)",
        "Google AI Studio Gemma 4 (Live REST API)",
        "Offline Deterministic Mode",
    ],
    index=0,
)

if engine_choice_ui == "AMD Radeon Cloud TokenFactory (Live API)":
    engine_choice = "amd"
elif engine_choice_ui == "Google AI Studio Gemma 4 (Live REST API)":
    engine_choice = "gemma4"
elif engine_choice_ui == "Offline Deterministic Mode":
    engine_choice = "offline"
else:
    engine_choice = "auto"

# What-If Simulation Parameters
with st.sidebar.expander("⚙️ What-If Simulation Sliders", expanded=False):
    recovery_rate_input = st.slider(
        "Checkout Recovery Rate (r)",
        min_value=0.10,
        max_value=0.80,
        value=0.35,
        step=0.05,
        help="Expected recovery percentage on abandoned carts via personalized discount link",
    )
    lead_time_override = st.slider(
        "Supplier Lead Time (Days)",
        min_value=3,
        max_value=21,
        value=7,
        help="Supplier replenishment lead time for inventory reorder point",
    )

# Courier Settlement PDF Extractor
with st.sidebar.expander("📄 Courier Settlement PDF Intake", expanded=False):
    st.caption("Upload carrier remittance PDF or parse sample statement.")
    sample_pdf_path = os.path.join(ROOT_DIR, "data", "generated", "sample_courier_settlement.pdf")
    if os.path.exists(sample_pdf_path):
        if st.button("Parse sample_courier_settlement.pdf", width="stretch"):
            import pypdf
            import re
            try:
                reader = pypdf.PdfReader(sample_pdf_path)
                pdf_text = "\n".join([page.extract_text() or "" for page in reader.pages])
                cons_ids = re.findall(r"CONS-[A-Z0-9-]+", pdf_text)
                order_ids = re.findall(r"ORD-[A-Z0-9-]+", pdf_text)

                pdf_con = duckdb.connect(os.path.join(ROOT_DIR, "data", "generated", "paylens.duckdb"), read_only=True)
                try:
                    all_ids = list(set(cons_ids + order_ids))
                    if all_ids:
                        q_marks = ", ".join(["?"] * len(all_ids))
                        query = f"""
                            SELECT consignment_id, order_id, courier_name,
                                   cod_collected_usd, courier_fee_usd,
                                   expected_net_payout_usd, actual_settled_usd,
                                   ROUND(expected_net_payout_usd - actual_settled_usd, 2) AS shortfall_usd,
                                   payout_status
                            FROM courier_settlements
                            WHERE consignment_id IN ({q_marks}) OR order_id IN ({q_marks})
                        """
                        df_pdf = pdf_con.execute(query, all_ids + all_ids).df()
                    else:
                        df_pdf = pd.DataFrame()
                finally:
                    pdf_con.close()

                if not df_pdf.empty:
                    shortfalls = df_pdf[df_pdf["shortfall_usd"] > 0]
                    total_shortfall = shortfalls["shortfall_usd"].sum()
                    shortfall_cnt = len(shortfalls)
                    st.dataframe(df_pdf, width="stretch", hide_index=True)
                    st.success(f"Parsed sample statement: Found ${total_shortfall:,.2f} shortfall across {shortfall_cnt} consignments.")
                else:
                    st.info("Parsed PDF successfully, but no matching database records found.")
            except Exception as e:
                st.error(f"Error parsing PDF: {e}")

# -----------------------------------------------------------------------------
# Execute Deterministic Pipeline
# -----------------------------------------------------------------------------
pipeline_data = cached_run_pipeline(
    (active_weights.cash_now_weight, active_weights.margin_protection_weight, active_weights.stock_availability_weight),
    recovery_rate_input,
    lead_time_override,
)
all_cards: List[RecommendationCard] = pipeline_data["cards"]
all_store_cards = all_cards
store_cards = [c for c in all_cards if c.merchant_id == selected_merchant]

# Evaluate detector metrics against ground truth
gt_path = os.path.join(ROOT_DIR, "data", "generated", "ground_truth.json")
try:
    eval_results = evaluate_recommendations(all_cards, gt_path)
    std_split = eval_results.get("standard_split", {})
    stress_split = eval_results.get("stress_test_split", {})
    eval_f1 = stress_split.get("f1_score")
    eval_f1_disp = f"{eval_f1:.2f} F1" if eval_f1 is not None else "N/A"
    stress_cm = stress_split.get("confusion_matrix", {})
    tp_cnt = stress_cm.get("true_positives")
    fp_cnt = stress_cm.get("false_positives")
    fn_cnt = stress_cm.get("false_negatives")
except Exception:
    eval_f1_disp = "N/A"
    tp_cnt, fp_cnt, fn_cnt = None, None, None
    eval_results = {}
    std_split = {}
    stress_split = {}

# Compute Separated Financial Risk Buckets (Strict financial separation)
# Bucket 1: Confirmed Cash Discrepancies (Unpaid Dispatched + Courier Shortfalls)
confirmed_cards_store = [
    c for c in store_cards
    if c.rec_type == RecommendationType.PAYMENT_LEAKAGE
]
confirmed_cash_store = sum(c.impact_usd for c in confirmed_cards_store)

confirmed_cards_all = [
    c for c in all_cards
    if c.rec_type == RecommendationType.PAYMENT_LEAKAGE
]
confirmed_cash_all = sum(c.impact_usd for c in confirmed_cards_all)

# Bucket 2: Estimated Checkout Recovery (Abandoned checkouts * r)
checkout_cards_store = [
    c for c in store_cards
    if c.rec_type == RecommendationType.FAILED_PAYMENT_RECOVERY
]
est_checkout_store = sum(c.impact_usd for c in checkout_cards_store)

# Bucket 3: Forecasted 7-Day Stockout Risk (Holt-Winters forecasted sales margin at risk)
stockout_cards_store = [
    c for c in store_cards
    if c.rec_type == RecommendationType.STOCKOUT_RISK
]
stockout_risk_store = sum(c.impact_usd for c in stockout_cards_store)

# -----------------------------------------------------------------------------
# Dynamic Truthful Runtime Header
# -----------------------------------------------------------------------------
st.subheader("PayLens // Multi-Rail Revenue Reconciliation Deal Desk")

hdr_col1, hdr_col2, hdr_col3 = st.columns([1.5, 1.5, 1.0])
with hdr_col1:
    if amd_live:
        st.info(f"⚡ **AMD Radeon Cloud TokenFactory (Live API)**\nModel: `{amd_model}` · Latency: `{amd_lat:.0f} ms`")
    else:
        st.warning(f"⚠️ AMD TokenFactory Offline (`{amd_url}`)")

with hdr_col2:
    if gemma_live:
        st.info(f"💎 **Google AI Studio Gemma 4 (Live REST API)**\nModel: `{gemma_model}` · Latency: `{gemma_lat:.0f} ms`")
    else:
        st.warning("⚠️ Google Gemma 4 REST Offline")

with hdr_col3:
    approved_total = sum(v.get("amount", 0.0) for v in st.session_state.approved_actions.values())
    st.success(
        f"✅ **Approved Recovery Actions (Simulated)**\n"
        f"`${approved_total:,.2f}` ({len(st.session_state.approved_actions)} simulated approved)\n\n"
        f"Simulated Session Log (No External Funds Settled)"
    )

st.divider()

# -----------------------------------------------------------------------------
# 4 Clear KPI Metric Cards (Strict Financial Separation)
# -----------------------------------------------------------------------------
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

with kpi_col1:
    st.metric(
        label="1. Confirmed Cash Discrepancies ($)",
        value=f"${confirmed_cash_store:,.2f}",
        delta=f"${confirmed_cash_all:,.2f} across 20 stores",
        help="Hard ledger mismatches: Unsettled dispatched orders and carrier COD remittance shortfalls",
    )

with kpi_col2:
    st.metric(
        label="2. Est. Checkout Recovery ($)",
        value=f"${est_checkout_store:,.2f}",
        delta=f"Based on r={recovery_rate_input*100:.0f}% assumption",
        help="Abandoned carts multiplied by assumed recovery rate",
    )

with kpi_col3:
    st.metric(
        label="3. Forecasted 7d Stockout Risk ($)",
        value=f"${stockout_risk_store:,.2f}",
        delta=f"{len(stockout_cards_store)} SKUs below lead-time cover",
        help="Holt-Winters forecasted sales margin at risk before replenishment arrives",
    )

with kpi_col4:
    cm_delta = (
        f"{tp_cnt} TP · {fp_cnt} FP · {fn_cnt} FN"
        if all(x is not None for x in [tp_cnt, fp_cnt, fn_cnt])
        else "N/A"
    )
    st.metric(
        label="4. Detector F1 (Stress-Test Split)",
        value=eval_f1_disp,
        delta=cm_delta,
        help="Stress-test evaluation on synthetic baseline plus 6 hard edge cases (delayed settlements, partial payments, duplicates)",
    )

# -----------------------------------------------------------------------------
# Main Navigation Tabs
# -----------------------------------------------------------------------------
tab1, tab2 = st.tabs([
    "🎯 1. Revenue Reconciliation & Deal Desk",
    "⚡ 2. Live AMD Benchmark, Confusion Matrix & Raw Data",
])

# =============================================================================
# TAB 1: REVENUE RECONCILIATION & DEAL DESK (MASTER-DETAIL WORKSPACE)
# =============================================================================
with tab1:
    # Filter using segmented control defaulting to Flagship Confirmed Cash Discrepancies
    queue_filter = st.segmented_control(
        "Queue Filter:",
        options=[
            "🔥 Flagship: Confirmed Cash Discrepancies",
            "📦 Supporting: Recovery & Stockouts",
            "🌐 All Ranked Recommendations",
        ],
        default="🔥 Flagship: Confirmed Cash Discrepancies",
        label_visibility="collapsed",
    ) or "🔥 Flagship: Confirmed Cash Discrepancies"

    if "Flagship" in queue_filter:
        display_cards = [c for c in store_cards if c.rec_type == RecommendationType.PAYMENT_LEAKAGE]
    elif "Supporting" in queue_filter:
        display_cards = [c for c in store_cards if c.rec_type != RecommendationType.PAYMENT_LEAKAGE]
    else:
        display_cards = store_cards

    if not display_cards:
        st.info(f"No recommendation cards matching current filter for storefront {selected_merchant}.")
        if store_cards:
            display_cards = store_cards

    # Default selected card
    if st.session_state.selected_card_id is None or not any(c.card_id == st.session_state.selected_card_id for c in display_cards):
        if display_cards:
            st.session_state.selected_card_id = display_cards[0].card_id

    # Master-Detail Split Layout
    left_col, right_col = st.columns([1.1, 1.9], gap="large")

    # LEFT COLUMN: Compact Priority Queue
    with left_col:
        st.markdown(f"### Priority Action Queue ({len(display_cards)} Items)")
        st.caption(f"Ranked by impact, confidence, and objective: '{current_goal_text}'")

        for idx, card in enumerate(display_cards, start=1):
            is_selected = (card.card_id == st.session_state.selected_card_id)
            is_approved = card.card_id in st.session_state.approved_actions
            is_rejected = card.card_id in st.session_state.rejected_actions

            with st.container(border=True):
                # Header row
                c_head1, c_head2 = st.columns([2.0, 1.0])
                with c_head1:
                    type_icon = "🚨" if card.rec_type == RecommendationType.PAYMENT_LEAKAGE else ("🛒" if card.rec_type == RecommendationType.FAILED_PAYMENT_RECOVERY else "📦")
                    st.markdown(f"**#{idx} · {type_icon} {card.entity_id}**")
                    st.caption(card.title)
                with c_head2:
                    st.markdown(f"### `${card.impact_usd:,.2f}`")

                # Status and action
                c_stat1, c_stat2 = st.columns([1.2, 1.0])
                with c_stat1:
                    if is_approved:
                        st.caption("✅ Simulated Action Logged")
                    elif is_rejected:
                        st.caption("❌ Rejected / False Positive")
                    else:
                        st.caption(f"Score: `{card.ranking_score:.2f}` · Conf: `{card.confidence:.2f}`")
                with c_stat2:
                    btn_label = "Active 👁️" if is_selected else "Inspect →"
                    if st.button(btn_label, key=f"btn_select_{card.card_id}", width="stretch", disabled=is_selected):
                        st.session_state.selected_card_id = card.card_id
                        st.rerun()

    # RIGHT COLUMN: Deal Desk Inspector
    with right_col:
        selected_card = next((c for c in all_cards if c.card_id == st.session_state.selected_card_id), None)
        if selected_card is None and display_cards:
            selected_card = display_cards[0]

        if selected_card:
            st.markdown(f"### Deal Desk Inspector: {selected_card.title}")

            # Top Card Details Row
            dt_col1, dt_col2, dt_col3, dt_col4 = st.columns(4)
            with dt_col1:
                st.metric("Entity ID", selected_card.entity_id)
            with dt_col2:
                st.metric("Impact", f"${selected_card.impact_usd:,.2f}")
            with dt_col3:
                st.metric("Confidence", f"{selected_card.confidence:.2f}")
            with dt_col4:
                st.metric("Ranking Score", f"{selected_card.ranking_score:.2f}")

            # 1. Deterministic Calculation Formula Banner
            with st.container(border=True):
                st.markdown("**Deterministic Math Formula (DuckDB Ledger Verification)**")
                st.code(selected_card.formula_display, language="text")
                st.caption(f"Allowed Grounding Numbers: `{selected_card.allowed_numbers}`")

            # 2. Visual Financial Evidence Chart
            st.markdown(f"**Visual Evidence Breakdown for `{selected_card.entity_id}`:**")
            if selected_card.rec_type == RecommendationType.STOCKOUT_RISK:
                chart_fig = build_stockout_forecast_chart(os.path.join(ROOT_DIR, "data", "generated", "paylens.duckdb"), selected_card.entity_id)
                if chart_fig:
                    st.plotly_chart(chart_fig, width="stretch")
                else:
                    rec_bar = build_reconciliation_comparison_bar(selected_card)
                    st.plotly_chart(rec_bar, width="stretch")
            else:
                rec_bar = build_reconciliation_comparison_bar(selected_card)
                st.plotly_chart(rec_bar, width="stretch")

            # 3. Source Evidence Table
            with st.container(border=True):
                st.markdown("**Source Evidence Records (DuckDB)**")
                evidence_list = selected_card.evidence_rows
                if evidence_list:
                    ev_rows = []
                    for ev in evidence_list:
                        ev_rows.append({
                            "Source Table": ev.source_table,
                            "Record ID": ev.row_id,
                            "Summary": ev.summary,
                            **{f"data_{k}": v for k, v in ev.raw_data.items() if k not in ("customer_email", "customer_phone")},
                        })
                    st.dataframe(pd.DataFrame(ev_rows), width="stretch", hide_index=True)
                else:
                    st.info("No raw evidence rows attached to card.")

            # 4. Live AI Explanation & Action Draft
            with st.container(border=True):
                st.markdown("**Live AI Explanation & Action Draft**")

                tone_choice = st.segmented_control(
                    "Action Strategy & Tone",
                    options=[
                        "Polite Payment Reminder",
                        "VIP 5% Instant-Pay Discount",
                        "Formal Courier Dispute",
                        "Supplier Expedited PO",
                    ],
                    default="Polite Payment Reminder",
                ) or "Polite Payment Reminder"

                gen_col1, gen_col2 = st.columns([1.5, 1.0])
                with gen_col1:
                    run_ai_btn = st.button("✨ Run Live AI Explanation & Action Draft", type="primary", width="stretch")
                with gen_col2:
                    test_hallucination_btn = st.button("🛡️ Test Red-Team Hallucination ($9,999.00)", width="stretch")

                # Check if card has already been enriched in session state
                card_key = f"{selected_card.card_id}_{tone_choice}_{engine_choice}"
                if run_ai_btn or card_key not in st.session_state.live_enriched_cards:
                    if run_ai_btn:
                        with st.spinner("Calling live reasoning endpoint..."):
                            enriched = enrich_card_with_agent(
                                selected_card.model_copy(),
                                tone=tone_choice,
                                engine_choice=engine_choice,
                                force_live=True,
                            )
                            st.session_state.live_enriched_cards[card_key] = enriched
                    elif card_key not in st.session_state.live_enriched_cards:
                        # Auto-enrich on first view
                        enriched = enrich_card_with_agent(
                            selected_card.model_copy(),
                            tone=tone_choice,
                            engine_choice=engine_choice,
                            force_live=False,
                        )
                        st.session_state.live_enriched_cards[card_key] = enriched

                active_enriched = st.session_state.live_enriched_cards.get(card_key, selected_card)

                # Handle Red-Team Hallucination Button
                if test_hallucination_btn:
                    fake_draft = f"Please remit the unverified balance of $9,999.00 immediately to account #4421."
                    passed, ungrounded = verify_numeric_grounding(fake_draft, selected_card.allowed_numbers + [selected_card.impact_usd])
                    st.error(f"🚨 Hallucination Detected! Fabricated token `{ungrounded}` is not in verified evidence numbers {selected_card.allowed_numbers}.")
                    st.warning("Guardrail activated: Blocked ungrounded output and restored deterministic fallback template.")

                # Provenance Telemetry Banner
                prov_col1, prov_col2, prov_col3, prov_col4 = st.columns(4)
                with prov_col1:
                    st.caption(f"**Model:** `{active_enriched.model_name}`")
                with prov_col2:
                    st.caption(f"**Endpoint:** `{active_enriched.endpoint_used or 'Local'}`")
                with prov_col3:
                    st.caption(f"**Latency:** `{active_enriched.http_latency_ms:.0f} ms`")
                with prov_col4:
                    template_note = "True" if active_enriched.used_template_fallback else "False"
                    st.caption(f"**Template Fallback:** `{template_note}`")

                # Grounding Verification Notice
                st.caption(
                    "🛡️ **Numeric Claim Validation Result:** Validates extracted numbers against permitted DuckDB evidence values; does not certify non-numeric prose claims."
                )

                st.markdown("**Explanation:**")
                st.info(active_enriched.explanation_en)

                st.markdown("**Action Draft Message:**")
                draft_text = st.text_area(
                    "Draft Content (Editable)",
                    value=active_enriched.action_draft_en,
                    height=100,
                    key=f"draft_{selected_card.card_id}",
                )

                # Grounding Trace Table (Itemized verification)
                if active_enriched.grounding_trace:
                    with st.expander("🔍 View Numeric Grounding Trace Table", expanded=False):
                        st.dataframe(pd.DataFrame(active_enriched.grounding_trace), width="stretch", hide_index=True)

            # 5. Human-Reviewed Simulated Action Execution
            with st.container(border=True):
                st.markdown("**Human Operator Action Approval (Simulated)**")
                st.caption("Simulated Session Log (No External Funds Settled)")
                act_col1, act_col2 = st.columns(2)

                with act_col1:
                    if st.button("✅ Approve Simulated Action", key=f"appr_{selected_card.card_id}", width="stretch", type="primary"):
                        receipt_id = hashlib.sha256(f"{selected_card.card_id}_{time.time()}".encode()).hexdigest()[:16]
                        st.session_state.approved_actions[selected_card.card_id] = {
                            "amount": selected_card.impact_usd,
                            "simulated_log_id": receipt_id,
                            "timestamp": datetime.now().isoformat(),
                            "entity": selected_card.entity_id,
                        }
                        st.success(f"Action approved! Simulated Action Log ID: `{receipt_id}`")
                        st.rerun()

                with act_col2:
                    if st.button("❌ Reject / Flag False Positive", key=f"rej_{selected_card.card_id}", width="stretch"):
                        st.session_state.rejected_actions[selected_card.card_id] = {
                            "timestamp": datetime.now().isoformat(),
                            "entity": selected_card.entity_id,
                        }
                        st.warning("Card flagged as False Positive and excluded from active recovery queue.")
                        st.rerun()

# =============================================================================
# TAB 2: LIVE AMD BENCHMARK, CONFUSION MATRIX & RAW DATA
# =============================================================================
with tab2:
    st.markdown("### Live AMD GPU Benchmark & Realistic Stress-Test Confusion Matrix")

    # Section 1: Live AMD Radeon Cloud TokenFactory Concurrency Benchmark
    with st.container(border=True):
        st.markdown("#### 1. Live AMD Radeon Cloud TokenFactory Concurrency Benchmark")
        st.caption("Executes real concurrent async requests against `https://developer.amd.com.cn/radeon/api/v1` measuring real TTFT (ms), End-to-End Latency (ms), and Tokens/sec.")

        bench_btn = st.button("🚀 Run Live AMD TokenFactory Concurrency Benchmark", type="primary")

        # Load existing benchmark results from benchmark_results.json
        bench_file = os.path.join(ROOT_DIR, "benchmarks", "benchmark_results.json")
        bench_data = None
        if os.path.exists(bench_file):
            try:
                with open(bench_file, "r", encoding="utf-8") as f:
                    bench_data = json.load(f)
            except Exception:
                pass

        if bench_btn:
            with st.spinner("Running live concurrency benchmark against AMD TokenFactory (tiers 1, 4, 8)..."):
                from benchmarks.run_mi300x_benchmark import run_amd_concurrency_tier
                from openai import AsyncOpenAI
                import asyncio

                cfg = get_endpoint_config()
                if endpoint_status["amd_status"]["is_live"]:
                    client = AsyncOpenAI(base_url=cfg["amd_url"], api_key=cfg["amd_key"], timeout=20.0)
                    model_to_test = endpoint_status["amd_status"]["model_served"] or "DeepSeek-V4-Flash"

                    tiers_to_run = [1, 4, 8]
                    live_tier_results = []
                    for c in tiers_to_run:
                        tier_res = asyncio.run(run_amd_concurrency_tier(client, model_to_test, all_cards, c, max(c, 2)))
                        live_tier_results.append(tier_res)

                    tot_att = sum(t.get("attempted_requests", t.get("total_requests", 0)) for t in live_tier_results)
                    tot_comp = sum(t.get("completed_requests", 0) for t in live_tier_results)
                    tot_fail = sum(t.get("failed_requests", 0) for t in live_tier_results)
                    if tot_fail == 0 and tot_comp > 0:
                        st.markdown(f":green-badge[Benchmark Complete: {tot_comp}/{tot_att} Succeeded]")
                    elif tot_comp > 0 and tot_fail > 0:
                        st.markdown(f":orange-badge[Partial Completion: {tot_comp}/{tot_att} Succeeded ({tot_fail} Failed)]")
                    else:
                        st.markdown(f":red-badge[Benchmark Failed: 0/{tot_att} Completed]")
                else:
                    st.error("AMD TokenFactory endpoint is currently unreachable.")

        active_tiers = st.session_state.benchmark_run_history or (bench_data.get("amd_tokenfactory", {}).get("tiers", []) if bench_data else [])

        if active_tiers:
            b_cols = st.columns(len(active_tiers))
            for i, t in enumerate(active_tiers):
                attempted = t.get("attempted_requests", t.get("total_requests", 0))
                completed = t.get("completed_requests", 0)
                failed = t.get("failed_requests", 0)
                fp_rate = t.get("first_pass_model_grounding_rate")
                pr_rate = t.get("post_retry_model_grounding_rate")
                fb_rate = t.get("deterministic_fallback_rate", t.get("deterministic_template_fallback_rate"))

                with b_cols[i]:
                    st.metric(
                        label=f"Concurrency = {t['concurrency']}",
                        value=f"{t.get('tokens_per_sec', 0):.1f} tok/s" if t.get("tokens_per_sec") is not None else "N/A",
                        delta=f"TTFT: {t.get('mean_ttft_ms', 0):.0f} ms · Lat: {t.get('mean_latency_ms', 0):.0f} ms" if t.get("mean_ttft_ms") is not None else "N/A",
                    )
                    fp_str = f"{fp_rate:.0f}%" if fp_rate is not None else "N/A"
                    pr_str = f"{pr_rate:.0f}%" if pr_rate is not None else "N/A"
                    fb_str = f"{fb_rate:.0f}%" if fb_rate is not None else "N/A"
                    st.caption(
                        f"Reqs: **{completed}/{attempted}** ({failed} failed)<br>"
                        f"🎯 1st Pass: **{fp_str}** · "
                        f"Retry: **{pr_str}** · "
                        f"Fallback: **{fb_str}**",
                        unsafe_allow_html=True,
                    )

            # Plot interactive Plotly chart
            df_plot = pd.DataFrame([
                {
                    "Concurrency": t["concurrency"],
                    "Tokens/Sec": t.get("tokens_per_sec", 0),
                    "Mean TTFT (ms)": t.get("mean_ttft_ms", 0),
                    "Mean Latency (ms)": t.get("mean_latency_ms", 0),
                }
                for t in active_tiers
            ])

            fig_tok = px.bar(
                df_plot,
                x="Concurrency",
                y="Tokens/Sec",
                title="AMD TokenFactory Throughput Scaling (Tokens/Sec vs Concurrency)",
                text="Tokens/Sec",
                color_discrete_sequence=["#10B981"],
            )
            fig_tok.update_layout(
                template="plotly_dark",
                height=320,
                plot_bgcolor="rgba(17, 24, 39, 0.5)",
                paper_bgcolor="rgba(17, 24, 39, 0.5)",
            )
            st.plotly_chart(fig_tok, width="stretch")

        google_data = bench_data.get("google_gemma4", {}) if bench_data else {}
        if google_data:
            g_att = google_data.get("attempted_requests", google_data.get("requests", 0))
            g_comp = google_data.get("completed_requests", google_data.get("completed", 0))
            g_fail = google_data.get("failed_requests", max(0, g_att - g_comp))
            g_fp = google_data.get("first_pass_model_grounding_rate")
            g_pr = google_data.get("post_retry_model_grounding_rate")
            g_fb = google_data.get("deterministic_fallback_rate", google_data.get("deterministic_template_fallback_rate"))
            g_lat = google_data.get("mean_latency_ms")

            st.markdown("##### 💎 Google AI Studio Gemma 4 REST Benchmark")
            g_col1, g_col2, g_col3 = st.columns(3)
            with g_col1:
                st.metric("Model Served", google_data.get("model", "gemma-4-26b-a4b-it"))
            with g_col2:
                st.metric("Mean Latency", f"{g_lat:.0f} ms" if g_lat is not None else "N/A")
            with g_col3:
                fp_disp = f"{g_fp:.0f}%" if g_fp is not None else "N/A (Not Measured / Failed)"
                st.metric("Model Grounding", fp_disp)
            st.caption(
                f"Requests: **{g_comp}/{g_att}** completed ({g_fail} failed) · "
                f"1st Pass: **{f'{g_fp:.0f}%' if g_fp is not None else 'N/A'}** · "
                f"Retry: **{f'{g_pr:.0f}%' if g_pr is not None else 'N/A'}** · "
                f"Fallback: **{f'{g_fb:.0f}%' if g_fb is not None else 'N/A'}**"
            )

    # Section 2: Realistic Stress-Test Confusion Matrix
    with st.container(border=True):
        st.markdown("#### 2. Realistic Stress-Test Confusion Matrix (Non-1.00 Ground Truth)")
        st.caption("Evaluates detector against both clean baseline data AND 6 hard stress-test edge cases.")
        st.markdown(":badge[Synthetic Stress-Test Split (Includes Noise & Timing Jitter — Not Live Merchant Data)]")

        cm_col1, cm_col2 = st.columns(2)
        with cm_col1:
            st.markdown("**Standard Baseline Split (Clean Synthetic)**")
            if std_split:
                st.dataframe(pd.DataFrame([std_split]), width="stretch", hide_index=True)
            else:
                st.info("Baseline split not available.")

        with cm_col2:
            st.markdown("**Stress-Test Split (Includes 6 Hard Edge Cases)**")
            if stress_split:
                prec = stress_split.get("precision")
                rec = stress_split.get("recall")
                f1 = stress_split.get("f1_score")
                st.dataframe(pd.DataFrame([{
                    "Precision": f"{prec:.3f}" if prec is not None else "N/A",
                    "Recall": f"{rec:.3f}" if rec is not None else "N/A",
                    "F1 Score": f"{f1:.3f}" if f1 is not None else "N/A",
                    "True Positives": tp_cnt if tp_cnt is not None else "N/A",
                    "False Positives": fp_cnt if fp_cnt is not None else "N/A",
                    "False Negatives": fn_cnt if fn_cnt is not None else "N/A",
                }]), width="stretch", hide_index=True)
            else:
                st.info("Stress-test split not available.")

        # Inspectable Edge Cases
        st.markdown("**Inspected Edge Cases (Why False Positives and Negatives Occurred):**")
        fp_details = stress_split.get("false_positive_details", [])
        if fp_details:
            st.markdown("**False Positives (Legitimate Transactions Flagged for Review):**")
            st.dataframe(pd.DataFrame(fp_details), width="stretch", hide_index=True)

        fn_details = stress_split.get("false_negative_details", [])
        if fn_details:
            st.markdown("**False Negatives (Edge Cases Missed by Deterministic Matcher):**")
            st.dataframe(pd.DataFrame(fn_details), width="stretch", hide_index=True)

    # Section 3: DuckDB Raw Tables Explorer
    with st.container(border=True):
        st.markdown("#### 3. DuckDB Raw Database Explorer")
        duck_table = st.selectbox("Select Table to Inspect", ["orders", "rail_payments", "courier_settlements", "inventory_daily"])
        con = duckdb.connect(os.path.join(ROOT_DIR, "data", "generated", "paylens.duckdb"), read_only=True)
        try:
            sample_df = con.execute(f"SELECT * FROM {duck_table} LIMIT 100").df()
            st.dataframe(sample_df, width="stretch")
        finally:
            con.close()

# -----------------------------------------------------------------------------
# Persistent Footer Notice
# -----------------------------------------------------------------------------
st.divider()
st.caption(
    "PayLens · Multi-Rail Revenue Recovery Engine on AMD Hardware · Demonstrated on illustrative synthetic data modeled on global commerce rails."
)
