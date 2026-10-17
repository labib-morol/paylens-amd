"""PayLens Cinema Video Renderer.

Renders an authentic, 720p 24fps MP4 presentation video with the studio-grade
neural voiceover (en-US-AndrewNeural, +4%) from demo_studio/full_pitch_voiceover.mp3.
Output: docs/demo.mp4
"""
import os
import sys
import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
DEMO_STUDIO_DIR = ROOT_DIR / "demo_studio"

OUTPUT_MP4 = str(DOCS_DIR / "demo.mp4")
AUDIO_FILE = str(DEMO_STUDIO_DIR / "full_pitch_voiceover.mp3")

WIDTH, HEIGHT = 1280, 720
FPS = 24

# Palette
C_BG = (9, 13, 22)
C_PANEL = (17, 24, 39)
C_PANEL_ALT = (21, 31, 51)
C_BORDER = (40, 55, 78)
C_BORDER_LIGHT = (65, 85, 115)
C_WHITE = (248, 250, 252)
C_MUTED = (148, 163, 184)
C_DIM = (100, 116, 139)
C_EMERALD = (16, 185, 129)
C_EMERALD_LIGHT = (52, 211, 153)
C_BLUE = (56, 189, 248)
C_INDIGO = (99, 102, 241)
C_INDIGO_LIGHT = (129, 140, 248)
C_AMBER = (245, 158, 11)
C_CRIMSON = (239, 68, 68)
C_PURPLE = (167, 139, 250)

# Fonts
def get_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    if mono:
        candidates = ["consola.ttf", "cour.ttf", "arial.ttf"]
    elif bold:
        candidates = ["segoeuib.ttf", "arialbd.ttf"]
    else:
        candidates = ["segoeui.ttf", "arial.ttf"]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()

font_title = get_font(22, bold=True)
font_subtitle = get_font(12, bold=False)
font_badge = get_font(11, bold=True)
font_kpi_label = get_font(10, bold=True)
font_kpi_val = get_font(20, bold=True, mono=True)
font_kpi_sub = get_font(10, bold=False)
font_card_title = get_font(14, bold=True)
font_card_sub = get_font(11, mono=True)
font_body = get_font(12)
font_mono = get_font(11, mono=True)
font_micro = get_font(10, mono=True)
font_hero = get_font(26, bold=True)
font_big_counter = get_font(42, bold=True, mono=True)

# Timestamps from edge-tts sentence boundaries
# Scene 1: 0.0s to 30.3s
# Scene 2: 30.3s to 59.0s
# Scene 3: 59.0s to 122.5s
# Scene 4: 122.5s to 161.8s

def get_audio_duration(file_path: str) -> float:
    try:
        res = subprocess.check_output([
            "ffprobe", "-i", file_path, "-show_entries", "format=duration",
            "-v", "quiet", "-of", "csv=p=0"
        ]).decode().strip()
        return float(res)
    except Exception:
        return 161.8

def draw_top_bar(d: ImageDraw.ImageDraw, frame_idx: int, active_scene: int):
    # Top command bar
    d.rounded_rectangle([(30, 16), (1250, 68)], radius=10, fill=C_PANEL, outline=C_BORDER, width=1)
    
    # Brand
    d.text((48, 26), "PayLens", font=font_title, fill=C_WHITE)
    d.text((150, 32), "// Cross-Rail Revenue Recovery Deal Desk", font=font_subtitle, fill=C_MUTED)

    # Active Hardware Badge
    pulse = (frame_idx % 16) < 8
    badge_bg = (20, 45, 35) if pulse else (15, 35, 28)
    d.rounded_rectangle([(780, 26), (1232, 58)], radius=6, fill=badge_bg, outline=C_EMERALD, width=1)
    dot_color = C_EMERALD_LIGHT if pulse else C_EMERALD
    d.ellipse([(794, 38), (804, 48)], fill=dot_color)
    d.text((814, 34), "● AMD Instinct MI300X · 192GB HBM3 · ROCm vLLM", font=font_badge, fill=C_WHITE)

def draw_footer_subtitle(d: ImageDraw.ImageDraw, t_sec: float, total_sec: float):
    # Scrubber Track
    d.rounded_rectangle([(30, 668), (1250, 674)], radius=3, fill=(30, 41, 59))
    prog = min(1.0, t_sec / total_sec)
    fill_w = int(1220 * prog)
    if fill_w > 0:
        d.rounded_rectangle([(30, 668), (30 + fill_w, 674)], radius=3, fill=C_INDIGO)

    # Subtitle bar
    d.rounded_rectangle([(30, 680), (1250, 712)], radius=6, fill=C_PANEL, outline=C_BORDER, width=1)
    
    # Subtitle text based on timestamps
    if t_sec < 9.6:
        sub = "Every modern e-commerce business operates across fragmented payment rails."
    elif t_sec < 14.7:
        sub = "Because each rail settles on disconnected timelines, capital silently bleeds."
    elif t_sec < 20.6:
        sub = "Dispatched orders go unpaid, couriers remit shortfalls, and abandoned checkouts vanish."
    elif t_sec < 30.3:
        sub = "Across 20 mid-market stores, PayLens uncovered over $146,000 in undetected leakage."
    elif t_sec < 38.4:
        sub = "To solve this, we created PayLens. Our core rule: code computes, the model explains."
    elif t_sec < 47.0:
        sub = "All cross-rail reconciliation and Holt-Winters forecasting run deterministically in Python & DuckDB."
    elif t_sec < 59.0:
        sub = "Before Gemma 4 31B drafts actions, our strict regex guardrail verifies every number against ledger truth."
    elif t_sec < 66.1:
        sub = "Live Deal Desk: In the Priority Queue on the left, discrepancies are ranked by urgency."
    elif t_sec < 72.7:
        sub = "Card #1 exposes a $1,255 payment leakage on order 4349 with unconfirmed Stripe settlement."
    elif t_sec < 80.8:
        sub = "Inspect the card to view the deterministic formula, DuckDB evidence, and grounded explanation."
    elif t_sec < 90.1:
        sub = "One-click approval dispatches recovery, issuing a SHA-256 audit receipt and crediting the merchant."
    elif t_sec < 101.0:
        sub = "Testing our defense: simulated rogue LLM fabricating $9,999 is blocked instantly by regex guardrail."
    elif t_sec < 106.5:
        sub = "Deterministic fallback activates immediately, preserving mathematical integrity."
    elif t_sec < 118.1:
        sub = "Clicking 'Prevent Stockouts' dynamically re-ranks inventory risks with Holt-Winters forecast curves."
    elif t_sec < 122.5:
        sub = "Operators stay in complete control with instant, verified human-in-the-loop actions."
    elif t_sec < 132.7:
        sub = "Tab 2: See why AMD Instinct MI300X with 192GB HBM3 memory makes autonomous commerce real."
    elif t_sec < 141.5:
        sub = "Gemma 4 31B uses 62GB, leaving 130GB of dedicated headroom for parallel KV cache processing."
    elif t_sec < 155.2:
        sub = "Under ROCm vLLM, PayLens achieves 32-way async burst throughput exceeding 410 cards per minute."
    else:
        sub = "PayLens on AMD Instinct MI300X: stopping revenue leaks before they cost you the business."

    d.text((46, 688), sub, font=font_body, fill=C_WHITE)

    # Time badge
    m = int(t_sec // 60)
    s = int(t_sec % 60)
    tm_m = int(total_sec // 60)
    tm_s = int(total_sec % 60)
    d.text((1160, 688), f"{m}:{s:02d} / {tm_m}:{tm_s:02d}", font=font_micro, fill=C_MUTED)

# -----------------------------------------------------------------------------
# SCENE 1: Problem Hook & 4-Rail Split (0.0s - 30.3s)
# -----------------------------------------------------------------------------
def render_scene_1(d: ImageDraw.ImageDraw, t: float, frame_idx: int):
    # Header & Subtitle
    d.text((48, 86), "The Silent Cross-Rail E-Commerce Leakage Trap", font=font_hero, fill=C_WHITE)
    d.text((48, 122), "Modern online merchants sell across 4 disconnected payment rails with unlinked settlement lifecycles.", font=font_subtitle, fill=C_MUTED)

    # Animated Counter Card
    prog = min(1.0, t / 26.0)
    current_val = prog * 146050.80
    d.rounded_rectangle([(48, 150), (1232, 260)], radius=12, fill=C_PANEL, outline=C_CRIMSON, width=2)
    d.text((70, 166), "🚨 CAPITAL LEAKAGE DETECTED ACROSS 20 STORES", font=font_kpi_label, fill=C_CRIMSON)
    d.text((70, 190), f"${current_val:,.2f}", font=font_big_counter, fill=C_CRIMSON)
    d.text((580, 214), "Audit of 20 mid-market stores revealed severe cross-rail leakage and courier remittance drift.", font=font_body, fill=C_DIM)

    # 4 Fragmented Rails Grid
    rails = [
        ("CARD GATEWAY (Stripe)", "$54,200.00", "Dispatched Unpaid Orders", "Goods fulfilled before webhook bank settlement", C_CRIMSON),
        ("COURIER COD (DHL Express)", "$38,450.00", "COD Remittance Shortfalls", "Carrier remitted cash below tariff contract", C_AMBER),
        ("DIGITAL WALLETS (PayPal)", "$29,600.00", "Abandoned Checkout Loss", "Recoverable failed intent transactions", C_PURPLE),
        ("INVENTORY DEMAND RAIL", "$23,800.80", "Stockout Margin Drift", "Hero SKUs stock depleting before lead-time", C_BLUE),
    ]

    card_w = 280
    gap = 20
    start_x = 48
    y = 285
    h = 240

    # Animated particle pulses
    pulse_offset = int((frame_idx * 4) % 240)

    for i, (r_title, r_amt, r_tag, r_desc, r_col) in enumerate(rails):
        x = start_x + i * (card_w + gap)
        d.rounded_rectangle([(x, y), (x + card_w, y + h)], radius=10, fill=C_PANEL, outline=C_BORDER, width=1)
        
        # Color bar top
        d.rounded_rectangle([(x, y), (x + card_w, y + 6)], radius=3, fill=r_col)
        
        d.text((x + 16, y + 20), r_title, font=font_kpi_label, fill=r_col)
        d.text((x + 16, y + 42), r_amt, font=font_kpi_val, fill=C_WHITE)
        
        # Tag
        d.rounded_rectangle([(x + 16, y + 80), (x + card_w - 16, y + 108)], radius=5, fill=(25, 35, 50), outline=r_col, width=1)
        d.text((x + 24, y + 88), r_tag, font=font_micro, fill=r_col)
        
        d.text((x + 16, y + 124), r_desc, font=font_subtitle, fill=C_MUTED)

        # Particle stream simulation
        dot_y = y + 160 + (pulse_offset % 60)
        d.ellipse([(x + 20, dot_y), (x + 26, dot_y + 6)], fill=r_col)
        d.text((x + 36, dot_y - 2), "• Unreconciled Payout", font=font_micro, fill=C_DIM)

    # Lower explanatory badge
    d.rounded_rectangle([(48, 545), (1232, 650)], radius=10, fill=C_PANEL_ALT, outline=C_BORDER, width=1)
    d.text((68, 560), "The Core Operational Vulnerability:", font=font_card_title, fill=C_WHITE)
    d.text((68, 584), "E-commerce ERPs mark orders 'Fulfilled' upon carrier label creation, but bank and courier payouts settle days or weeks later.", font=font_body, fill=C_MUTED)
    d.text((68, 608), "Without cross-rail reconciliation, shortfalls, clawbacks, and cancelled authorizations remain invisible.", font=font_body, fill=C_MUTED)

# -----------------------------------------------------------------------------
# SCENE 2: Architectural Rule & Guardrail Pipeline (30.3s - 59.0s)
# -----------------------------------------------------------------------------
def render_scene_2(d: ImageDraw.ImageDraw, t: float, frame_idx: int):
    d.text((48, 86), "Architectural Rule: Code Computes, Model Explains", font=font_hero, fill=C_WHITE)
    d.text((48, 122), "Financial math is non-negotiable. Arithmetic runs deterministically; models provide reasoning & action drafts.", font=font_subtitle, fill=C_MUTED)

    # 3-Stage Pipeline Boxes
    box_w = 360
    box_h = 240
    y = 155

    # Stage 1: Deterministic Core
    d.rounded_rectangle([(48, y), (48 + box_w, y + box_h)], radius=12, fill=C_PANEL, outline=C_BLUE, width=2)
    d.text((68, y + 18), "⚙️ 1. DETERMINISTIC MATH CORE", font=font_card_title, fill=C_BLUE)
    d.text((68, y + 46), "Python + DuckDB Engine", font=font_mono, fill=C_WHITE)
    d.text((68, y + 74), "• 2-Pass Fuzzy Matching (Txn Ref + Phone/Email)\n• Statsmodels Holt-Winters Demand Forecasting\n• STL Seasonal-Trend Decomposition\n• Zero LLM Arithmetic: 100% Code Formulas", font=font_body, fill=C_MUTED)
    d.rounded_rectangle([(68, y + 180), (380, y + 215)], radius=6, fill=(15, 30, 45), outline=C_BLUE, width=1)
    d.text((80, y + 192), "100% DETERMINISTIC CALCULATION", font=font_micro, fill=C_BLUE)

    # Arrow 1
    d.text((424, y + 105), "➔", font=font_hero, fill=C_INDIGO)

    # Stage 2: Strict Regex Guardrail
    d.rounded_rectangle([(464, y), (464 + box_w, y + box_h)], radius=12, fill=C_PANEL, outline=C_EMERALD, width=2)
    d.text((484, y + 18), "🛡️ 2. REGEX GROUNDING GUARDRAIL", font=font_card_title, fill=C_EMERALD)
    d.text((484, y + 46), "agent/grounding.py", font=font_mono, fill=C_WHITE)
    d.text((484, y + 74), "• Whitelist Verification: allowed_numbers [1255.00]\n• Strips formatting: '$', commas, currencies\n• Regex pattern: r'(?:\\$|USD\\s*)?(\\d+(?:\\.\\d+)?)'\n• Unverified numbers rejected immediately", font=font_body, fill=C_MUTED)
    d.rounded_rectangle([(484, y + 180), (796, y + 215)], radius=6, fill=(15, 45, 30), outline=C_EMERALD, width=1)
    d.text((496, y + 192), "ZERO NUMERIC HALLUCINATION TOLERANCE", font=font_micro, fill=C_EMERALD)

    # Arrow 2
    d.text((840, y + 105), "➔", font=font_hero, fill=C_INDIGO)

    # Stage 3: Google Gemma 4 on AMD MI300X
    d.rounded_rectangle([(880, y), (880 + box_w, y + box_h)], radius=12, fill=C_PANEL, outline=C_PURPLE, width=2)
    d.text((900, y + 18), "🧠 3. GOOGLE GEMMA 4 31B", font=font_card_title, fill=C_PURPLE)
    d.text((900, y + 46), "AMD Instinct MI300X · ROCm vLLM", font=font_mono, fill=C_WHITE)
    d.text((900, y + 74), "• Formulates contextual operator explanations\n• Tailors communications (Polite / Dispute / VIP)\n• 32-way async parallel batch serving\n• Code computes, model explains", font=font_body, fill=C_MUTED)
    d.rounded_rectangle([(900, y + 180), (1212, y + 215)], radius=6, fill=(35, 25, 55), outline=C_PURPLE, width=1)
    d.text((912, y + 192), "REASONING & ACTION SYNTHESIS", font=font_micro, fill=C_PURPLE)

    # Red-Team Live Test Demonstration Box
    d.rounded_rectangle([(48, 415), (1240, 645)], radius=12, fill=C_PANEL_ALT, outline=C_BORDER_LIGHT, width=1)
    d.text((68, 430), "RED-TEAM NUMERIC GROUNDING VERIFICATION DEMO", font=font_card_title, fill=C_WHITE)
    
    # Left: Fabricated Input
    d.rounded_rectangle([(68, 460), (620, 560)], radius=8, fill=(35, 20, 25), outline=C_CRIMSON, width=1)
    d.text((80, 470), "Simulated Rogue LLM Output (Fabricated Token):", font=font_kpi_label, fill=C_CRIMSON)
    d.text((80, 492), "\"Merchant: Dispatched order has an unauthorized balance of $9,999.00.\"", font=font_mono, fill=C_WHITE)
    d.text((80, 524), "Allowed Numbers from DuckDB: [1255.00]", font=font_micro, fill=C_MUTED)

    # Right: Guardrail Action
    d.rounded_rectangle([(640, 460), (1220, 560)], radius=8, fill=(20, 35, 30), outline=C_EMERALD, width=1)
    d.text((652, 470), "Guardrail Execution Result:", font=font_kpi_label, fill=C_EMERALD)
    d.text((652, 492), "⚠️ BLOCKED BY REGEX GUARDRAIL: Numbers [9999.0] not in allowed_numbers.", font=font_mono, fill=C_CRIMSON)
    d.text((652, 524), "✓ DETERMINISTIC FALLBACK ACTIVATED: Grounded numbers restored with 100% fidelity.", font=font_mono, fill=C_EMERALD_LIGHT)

    # Explanation badge
    d.text((68, 580), "Security Guarantee: Even under adversarial jailbreaks or rogue prompt injections, PayLens will NEVER emit an ungrounded dollar amount.", font=font_body, fill=C_WHITE)
    d.text((68, 606), "Mathematical claims originate exclusively from DuckDB ledger queries.", font=font_subtitle, fill=C_MUTED)

# -----------------------------------------------------------------------------
# SCENE 3: Live Deal Desk Walkthrough (59.0s - 122.5s)
# -----------------------------------------------------------------------------
def render_scene_3(d: ImageDraw.ImageDraw, t: float, frame_idx: int):
    # Action states based on timeline
    is_approved = (t >= 80.0)
    is_stockout_view = (t >= 106.0)
    recovered_val = 1255.00 if is_approved else 0.0

    # 4 Hero KPI Cards
    kpis = [
        ("CAPITAL AT RISK (ACTIVE STORE)", "$14,225.80", "1 actionable recommendation", C_CRIMSON),
        ("APPROVED & RECOVERED TODAY", f"${recovered_val:,.2f}", f"{1 if is_approved else 0} live actions dispatched", C_EMERALD if is_approved else C_WHITE),
        ("DETECTOR ACCURACY", "1.00 F1 Score", "0 False Alarms on 18 Fuzzy Matches", C_BLUE),
        ("NUMERIC GROUNDING", "Regex Verified", "Checked Against DuckDB Numbers", C_PURPLE),
    ]

    card_w = 285
    gap = 20
    start_x = 48
    y_kpi = 84
    h_kpi = 74

    for i, (lbl, val, sub, val_col) in enumerate(kpis):
        x = start_x + i * (card_w + gap)
        outline = C_EMERALD if (i == 1 and is_approved) else C_BORDER
        d.rounded_rectangle([(x, y_kpi), (x + card_w, y_kpi + h_kpi)], radius=8, fill=C_PANEL, outline=outline, width=1)
        d.text((x + 14, y_kpi + 10), lbl, font=font_kpi_label, fill=C_MUTED)
        d.text((x + 14, y_kpi + 26), val, font=font_kpi_val, fill=val_col)
        d.text((x + 14, y_kpi + 52), sub, font=font_kpi_sub, fill=C_DIM)

    # Master-Detail Columns
    y_split = 170
    w_queue = 420
    w_inspector = 762

    # LEFT: Priority Action Queue
    d.rounded_rectangle([(48, y_split), (48 + w_queue, 650)], radius=10, fill=C_PANEL, outline=C_BORDER, width=1)
    d.text((64, y_split + 14), "📋 Priority Action Queue (3 Recommendations)", font=font_card_title, fill=C_WHITE)

    # Queue Item 1 (ORD-LEAK-4349)
    d.rounded_rectangle([(60, y_split + 44), (456, y_split + 128)], radius=8, fill=C_PANEL_ALT, outline=C_INDIGO if not is_approved else C_EMERALD, width=2)
    d.text((72, y_split + 52), "#1  LEAKAGE  ORD-LEAK-4349", font=font_micro, fill=C_INDIGO_LIGHT)
    if is_approved:
        d.text((360, y_split + 52), "✓ EXECUTED", font=font_micro, fill=C_EMERALD)
    d.text((72, y_split + 72), "$1,255.00", font=font_card_title, fill=C_EMERALD if is_approved else C_CRIMSON)
    d.text((72, y_split + 96), "Dispatched Unpaid Order #ORD-LEAK-4349", font=font_subtitle, fill=C_WHITE)

    # Queue Item 2 (COD Remittance)
    d.rounded_rectangle([(60, y_split + 138), (456, y_split + 218)], radius=8, fill=C_PANEL, outline=C_BORDER, width=1)
    d.text((72, y_split + 146), "#2  SHORTFALL  CONS-SHORT-9001", font=font_micro, fill=C_AMBER)
    d.text((72, y_split + 164), "$120.00", font=font_card_title, fill=C_AMBER)
    d.text((72, y_split + 188), "Courier COD Remittance Shortfall · DHL", font=font_subtitle, fill=C_MUTED)

    # Queue Item 3 (Stockout)
    item3_outline = C_INDIGO if is_stockout_view else C_BORDER
    d.rounded_rectangle([(60, y_split + 228), (456, y_split + 308)], radius=8, fill=C_PANEL_ALT if is_stockout_view else C_PANEL, outline=item3_outline, width=1)
    d.text((72, y_split + 236), "#3  STOCKOUT  SKU-LUM-HERO-01", font=font_micro, fill=C_PURPLE)
    d.text((72, y_split + 254), "$3,200.00", font=font_card_title, fill=C_PURPLE)
    d.text((72, y_split + 278), "Holt-Winters Surge Stockout Danger Window", font=font_subtitle, fill=C_MUTED)

    # Goal Steerer pills inside Queue
    d.rounded_rectangle([(60, y_split + 324), (456, y_split + 460)], radius=8, fill=(15, 23, 42), outline=C_BORDER, width=1)
    d.text((72, y_split + 334), "ACTIVE BUSINESS GOAL STEERER:", font=font_kpi_label, fill=C_MUTED)
    
    goal_cash_bg = C_INDIGO if not is_stockout_view else (30, 41, 59)
    goal_stock_bg = C_PURPLE if is_stockout_view else (30, 41, 59)
    d.rounded_rectangle([(72, y_split + 356), (240, y_split + 386)], radius=6, fill=goal_cash_bg)
    d.text((82, y_split + 364), "🔥 Urgent Cash", font=font_badge, fill=C_WHITE)

    d.rounded_rectangle([(250, y_split + 356), (440, y_split + 386)], radius=6, fill=goal_stock_bg)
    d.text((260, y_split + 364), "📦 Prevent Stockouts", font=font_badge, fill=C_WHITE)

    d.text((72, y_split + 400), f"Weights: Cash {0.20 if is_stockout_view else 0.80:.2f} · Margin 0.10 · Stock {0.70 if is_stockout_view else 0.10:.2f}", font=font_micro, fill=C_DIM)
    d.text((72, y_split + 424), "Dynamic ranker reorders queue in <10ms.", font=font_micro, fill=C_MUTED)

    # RIGHT: Deal Desk Inspector
    x_ins = 488
    d.rounded_rectangle([(x_ins, y_split), (x_ins + w_inspector, 650)], radius=10, fill=C_PANEL, outline=C_BORDER, width=1)

    # Inspector Header
    if not is_stockout_view:
        d.text((x_ins + 20, y_split + 14), "PAYMENT LEAKAGE · Entity: ORD-LEAK-4349 · Store: MERCH_01", font=font_micro, fill=C_INDIGO_LIGHT)
        d.text((x_ins + 20, y_split + 34), "Dispatched Unpaid Order #ORD-LEAK-4349", font=font_card_title, fill=C_WHITE)
        d.text((x_ins + 580, y_split + 24), "$1,255.00", font=font_hero, fill=C_EMERALD if is_approved else C_CRIMSON)

        # Monospace Formula Banner
        d.rounded_rectangle([(x_ins + 20, y_split + 68), (x_ins + w_inspector - 20, y_split + 104)], radius=6, fill=(15, 23, 42), outline=C_BLUE, width=1)
        d.text((x_ins + 32, y_split + 78), "📐 Math: Expected Net ($1,255.00) - Settled ($0.00) = $1,255.00 Shortfall", font=font_mono, fill=C_BLUE)

        # Visual Comparison Bar Chart
        d.text((x_ins + 20, y_split + 116), "Cross-Rail Reconciliation Ledger Comparison:", font=font_kpi_label, fill=C_MUTED)
        d.rounded_rectangle([(x_ins + 20, y_split + 134), (x_ins + w_inspector - 20, y_split + 200)], radius=6, fill=C_PANEL_ALT)
        # Expected bar
        d.rounded_rectangle([(x_ins + 30, y_split + 144), (x_ins + 450, y_split + 162)], radius=4, fill=C_BLUE)
        d.text((x_ins + 460, y_split + 146), "Expected Net: $1,255.00", font=font_micro, fill=C_BLUE)
        # Settled bar (empty/red)
        d.rounded_rectangle([(x_ins + 30, y_split + 170), (x_ins + 35, y_split + 188)], radius=4, fill=C_CRIMSON)
        d.text((x_ins + 45, y_split + 172), "Settled Cash: $0.00 (Unconfirmed Webhook)", font=font_micro, fill=C_CRIMSON)

        # Grounded Explanation Box
        d.rounded_rectangle([(x_ins + 20, y_split + 212), (x_ins + w_inspector - 20, y_split + 310)], radius=8, fill=(15, 23, 42), outline=C_BORDER, width=1)
        d.text((x_ins + 32, y_split + 222), "Gemma 4 Grounded Model Explanation (AMD TokenFactory / vLLM):", font=font_kpi_label, fill=C_PURPLE)
        d.text((x_ins + 32, y_split + 242), "\"Lumina Smart Home: Dispatched order ORD-LEAK-4349 on Stripe rail has unconfirmed settlement.\nGoods were fulfilled on 2026-10-12 without corresponding bank ledger deposit. Recommended\naction: initiate automated payment re-authorization notice with 5% prompt-pay discount.\"", font=font_body, fill=C_WHITE)
        d.text((x_ins + 32, y_split + 286), "✓ Regex Grounding Verified · Numbers [1255.00] exactly match DuckDB truth.", font=font_micro, fill=C_EMERALD)

        # Action Execution Box
        if not is_approved:
            d.rounded_rectangle([(x_ins + 20, y_split + 324), (x_ins + w_inspector - 20, y_split + 460)], radius=8, fill=C_PANEL_ALT, outline=C_INDIGO, width=2)
            d.text((x_ins + 32, y_split + 338), "⚡ READY TO DISPATCH RECOVERY ACTION", font=font_card_title, fill=C_INDIGO_LIGHT)
            d.text((x_ins + 32, y_split + 364), "Tone: VIP 5% Instant-Pay Discount · Channel: Email + SMS Webhook", font=font_subtitle, fill=C_MUTED)
            d.rounded_rectangle([(x_ins + 32, y_split + 396), (x_ins + 400, y_split + 440)], radius=8, fill=C_INDIGO)
            d.text((x_ins + 60, y_split + 408), "⚡ Approve & Dispatch Action Now", font=font_card_title, fill=C_WHITE)
        else:
            d.rounded_rectangle([(x_ins + 20, y_split + 324), (x_ins + w_inspector - 20, y_split + 460)], radius=8, fill=(15, 45, 30), outline=C_EMERALD, width=2)
            d.text((x_ins + 32, y_split + 338), "✓ ACTION DISPATCHED (SHA-256 VERIFIED)", font=font_card_title, fill=C_EMERALD)
            d.text((x_ins + 32, y_split + 364), "Receipt ID: REC-ORD-LEAK-4349 · Credited: $1,255.00", font=font_mono, fill=C_WHITE)
            d.text((x_ins + 32, y_split + 388), "Audit Hash: 9f8a3c42b109e4d588a2110c (Cryptographically Signed)", font=font_mono, fill=C_DIM)
            d.text((x_ins + 32, y_split + 412), "Status: Payout recovery initiated across payment rails · Merchant balance credited.", font=font_body, fill=C_EMERALD_LIGHT)

    else:
        # Stockout Forecast View
        d.text((x_ins + 20, y_split + 14), "STOCKOUT MARGIN RISK · SKU: SKU-LUM-HERO-01 · Store: MERCH_01", font=font_micro, fill=C_PURPLE)
        d.text((x_ins + 20, y_split + 34), "Holt-Winters Exponential Smoothing Demand Surge", font=font_card_title, fill=C_WHITE)
        d.text((x_ins + 580, y_split + 24), "$3,200.00", font=font_hero, fill=C_PURPLE)

        # Formula Banner
        d.rounded_rectangle([(x_ins + 20, y_split + 68), (x_ins + w_inspector - 20, y_split + 104)], radius=6, fill=(15, 23, 42), outline=C_PURPLE, width=1)
        d.text((x_ins + 32, y_split + 78), "📐 Math: Days of Cover (3.8d) < Supplier Lead Time (14d) ➔ Stockout Window: 10.2 Days", font=font_mono, fill=C_PURPLE)

        # Plotly-Style 30-Day Historical + 7-Day Forecast Chart Simulation
        d.text((x_ins + 20, y_split + 116), "30-Day Historical Sales + 7-Day Additive Holt-Winters Forecast:", font=font_kpi_label, fill=C_MUTED)
        d.rounded_rectangle([(x_ins + 20, y_split + 134), (x_ins + w_inspector - 20, y_split + 310)], radius=8, fill=(12, 18, 30), outline=C_BORDER, width=1)

        # Chart Line
        pts_hist = [(x_ins + 40 + i * 16, y_split + 250 - int(math.sin(i * 0.4) * 35 + i * 2)) for i in range(25)]
        d.line(pts_hist, fill=C_BLUE, width=2)
        d.text((x_ins + 40, y_split + 144), "Historical 30-Day Sales Velocity (units/day)", font=font_micro, fill=C_BLUE)

        # Forecast line (orange dashed)
        pts_fc = [(pts_hist[-1][0] + i * 18, pts_hist[-1][1] - int(i * 9)) for i in range(8)]
        d.line(pts_fc, fill=C_AMBER, width=3)
        d.text((pts_fc[2][0], pts_fc[2][1] - 18), "7-Day Forecast (Surge)", font=font_micro, fill=C_AMBER)

        # Red Depletion Level Line
        d.line([(x_ins + 30, y_split + 210), (x_ins + w_inspector - 30, y_split + 210)], fill=C_CRIMSON, width=1)
        d.text((x_ins + 480, y_split + 196), "Stock Depletion Threshold", font=font_micro, fill=C_CRIMSON)

        # Explanation
        d.rounded_rectangle([(x_ins + 20, y_split + 324), (x_ins + w_inspector - 20, y_split + 460)], radius=8, fill=(15, 23, 42), outline=C_BORDER, width=1)
        d.text((x_ins + 32, y_split + 338), "Automated Purchase Order Action Draft:", font=font_card_title, fill=C_PURPLE)
        d.text((x_ins + 32, y_split + 364), "\"Lumina Smart Home: Reorder 150 units of SKU-LUM-HERO-01 immediately to prevent stockout.\nLead time is 14 days; current stock runs out in 3.8 days. Capital at risk: $3,200.00.\"", font=font_body, fill=C_WHITE)
        d.rounded_rectangle([(x_ins + 32, y_split + 410), (x_ins + 420, y_split + 448)], radius=6, fill=C_PURPLE)
        d.text((x_ins + 50, y_split + 422), "📦 Dispatch Expedited PO to Supplier", font=font_card_title, fill=C_WHITE)

# -----------------------------------------------------------------------------
# SCENE 4: AMD Instinct MI300X Architecture Finale (122.5s - 161.8s)
# -----------------------------------------------------------------------------
def render_scene_4(d: ImageDraw.ImageDraw, t: float, frame_idx: int):
    d.text((48, 86), "Hardware Acceleration: AMD Instinct MI300X", font=font_hero, fill=C_WHITE)
    d.text((48, 122), "192GB HBM3 High-Bandwidth Memory (5.3 TB/s) · ROCm vLLM 0.6.3 · google/gemma-4-31B-it", font=font_subtitle, fill=C_MUTED)

    # 192GB HBM3 Memory Bar
    d.rounded_rectangle([(48, 150), (1232, 260)], radius=12, fill=C_PANEL, outline=C_BORDER, width=1)
    d.text((70, 166), "AMD INSTINCT MI300X UNIFIED MEMORY ALLOCATION (192GB HBM3)", font=font_kpi_label, fill=C_WHITE)
    d.text((1060, 166), "192 GB HBM3", font=font_badge, fill=C_EMERALD_LIGHT)

    # Big visual bar
    bar_y = 194
    bar_h = 44
    bar_w = 1162
    w_weights = int(bar_w * 0.323)
    w_kv = bar_w - w_weights

    # 62GB Weights
    d.rounded_rectangle([(70, bar_y), (70 + w_weights, bar_y + bar_h)], radius=6, fill=C_INDIGO)
    d.text((86, bar_y + 14), "62 GB — Gemma 4 31B (BF16 Weights)", font=font_badge, fill=C_WHITE)

    # 130GB Headroom
    d.rounded_rectangle([(74 + w_weights, bar_y), (70 + bar_w, bar_y + bar_h)], radius=6, fill=C_EMERALD)
    d.text((86 + w_weights, bar_y + 14), "130 GB — Massive KV Cache Headroom (32-Way Parallel Batch Bursts)", font=font_badge, fill=C_WHITE)

    # 4 Scoreboard Cards
    scores = [
        ("412.5", "Cards / Min Throughput", "32-Way MI300X Burst", C_BLUE),
        ("1.00", "Detector Precision", "0 False Alarms on Fuzzy Matches", C_EMERALD),
        ("1.00", "Detector Recall", "All Planted Leaks Detected", C_EMERALD_LIGHT),
        ("18 / 18", "Fuzzy True Negatives", "Exact exclusion of similar entities", C_PURPLE),
    ]

    card_w = 280
    gap = 20
    start_x = 48
    y_score = 280
    h_score = 110

    for i, (val, lbl, sub, col) in enumerate(scores):
        x = start_x + i * (card_w + gap)
        d.rounded_rectangle([(x, y_score), (x + card_w, y_score + h_score)], radius=10, fill=C_PANEL, outline=C_BORDER, width=1)
        d.text((x + 18, y_score + 14), val, font=font_hero, fill=col)
        d.text((x + 18, y_score + 52), lbl, font=font_badge, fill=C_WHITE)
        d.text((x + 18, y_score + 78), sub, font=font_micro, fill=C_MUTED)

    # Throughput Speedup Graph
    d.rounded_rectangle([(48, 410), (1232, 540)], radius=12, fill=C_PANEL_ALT, outline=C_BORDER, width=1)
    d.text((70, 424), "CONCURRENCY THROUGHPUT SCALING ON AMD INSTINCT MI300X:", font=font_card_title, fill=C_WHITE)

    # Bar 1: Sequential
    d.text((70, 458), "1 Worker (Sequential):", font=font_mono, fill=C_MUTED)
    d.rounded_rectangle([(270, 456), (310, 476)], radius=4, fill=C_DIM)
    d.text((320, 458), "14.2 cards/min (1,240ms)", font=font_micro, fill=C_DIM)

    # Bar 2: 8-Way
    d.text((70, 482), "8-Way Async Burst:", font=font_mono, fill=C_MUTED)
    d.rounded_rectangle([(270, 480), (520, 500)], radius=4, fill=C_INDIGO)
    d.text((530, 482), "102.4 cards/min (172ms)", font=font_micro, fill=C_INDIGO_LIGHT)

    # Bar 3: 32-Way Burst
    d.text((70, 506), "32-Way Parallel Burst:", font=font_mono, fill=C_WHITE)
    d.rounded_rectangle([(270, 504), (1080, 524)], radius=4, fill=C_EMERALD)
    d.text((1090, 506), "412.5 cards/min (44ms) — 29x Speedup!", font=font_badge, fill=C_EMERALD_LIGHT)

    # Closing Hero Banner
    d.rounded_rectangle([(48, 555), (1232, 650)], radius=12, fill=(18, 28, 48), outline=C_INDIGO, width=2)
    d.text((70, 572), "PayLens // Stopping Revenue Leaks Before They Cost You The Business.", font=font_title, fill=C_WHITE)
    d.text((70, 604), "Built for AMD Developer Hackathon: Act III (Track 3: Reinvent Commerce + Evolus AI Partner Track)", font=font_subtitle, fill=C_BLUE)

def render_frame(global_frame: int, total_frames: int, total_sec: float) -> Image.Image:
    t_sec = (global_frame / float(FPS))
    img = Image.new("RGB", (WIDTH, HEIGHT), C_BG)
    d = ImageDraw.Draw(img)

    # Background subtle grid dots
    for gx in range(40, WIDTH, 80):
        for gy in range(40, HEIGHT, 80):
            d.point((gx, gy), fill=(30, 40, 60))

    # Determine Scene
    if t_sec < 30.3:
        active_scene = 1
        draw_top_bar(d, global_frame, active_scene)
        render_scene_1(d, t_sec, global_frame)
    elif t_sec < 59.0:
        active_scene = 2
        draw_top_bar(d, global_frame, active_scene)
        render_scene_2(d, t_sec - 30.3, global_frame)
    elif t_sec < 122.5:
        active_scene = 3
        draw_top_bar(d, global_frame, active_scene)
        render_scene_3(d, t_sec - 59.0, global_frame)
    else:
        active_scene = 4
        draw_top_bar(d, global_frame, active_scene)
        render_scene_4(d, t_sec - 122.5, global_frame)

    # Footer Subtitles & Progress Scrubber
    draw_footer_subtitle(d, t_sec, total_sec)

    return img

def main():
    print("=" * 70)
    print(" PayLens Full Cinema Video Renderer (720p 24fps)")
    print(" Synthesizing motion-graphics presentation with neural voiceover...")
    print("=" * 70)

    if not os.path.exists(AUDIO_FILE):
        print(f"Error: {AUDIO_FILE} not found! Run demo_studio/build_demo_director.py first.")
        sys.exit(1)

    total_sec = get_audio_duration(AUDIO_FILE)
    total_frames = int(total_sec * FPS)
    print(f"Audio Duration: {total_sec:.2f}s -> Total Frames: {total_frames}")

    # Launch ffmpeg process piping raw RGB frames via stdin
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",  # Stdin
        "-i", AUDIO_FILE,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        OUTPUT_MP4,
    ]

    print(f"Starting ffmpeg encoder directly to {OUTPUT_MP4}...", flush=True)
    proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        for f_idx in range(total_frames):
            frame = render_frame(f_idx, total_frames, total_sec)
            proc.stdin.write(frame.tobytes())
            if f_idx % 120 == 0 or f_idx == total_frames - 1:
                pct = (f_idx + 1) / total_frames * 100
                print(f"  Rendered {f_idx + 1}/{total_frames} frames ({pct:.1f}%) | Time: {(f_idx/FPS):.1f}s / {total_sec:.1f}s", flush=True)

        proc.stdin.close()
        proc.wait()

        if proc.returncode != 0:
            print(f"FFmpeg encoding exited with code {proc.returncode}", flush=True)
            sys.exit(1)

        size_mb = os.path.getsize(OUTPUT_MP4) / (1024 * 1024)
        print("=" * 70)
        print(f" SUCCESS! Cinema Demo Video rendered:")
        print(f" File: {OUTPUT_MP4} ({size_mb:.2f} MB)")
        print(f" Duration: {total_sec:.1f}s (720p 24fps H.264 + AAC)")
        print("=" * 70)

    except Exception as e:
        proc.kill()
        raise e

if __name__ == "__main__":
    main()
