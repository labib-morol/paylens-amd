"""High-Definition Institutional UI Screen Generator for PayLens Demo Video.
Generates pixel-perfect 1920x1080 UI screens matching the native Streamlit application:
- 01_deal_desk_live.png: Live Deal Desk with Cash Recovery Goal, ORD-LEAK-4348 at #1
- 02_evidence_and_action.png: Right inspector scrolled to DuckDB evidence and grounded action notice
- 03_stockout_promoted.png: Prevent Stockouts goal selected, SKU-APX-01 ($1,597.50) at #1
- 04_amd_benchmark_scaling.png: Tab 2 AMD TokenFactory throughput scaling bar chart & metrics
- 05_stress_confusion_matrix.png: Tab 2 realistic stress-test confusion matrix & inspected edge cases
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "temp_video_build" / "live_screens"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT = 1920, 1080

# Institutional Dark Palette
C_BG = (11, 15, 25)
C_SIDEBAR = (15, 20, 32)
C_PANEL = (17, 24, 39)
C_PANEL_ALT = (22, 32, 50)
C_CARD_BG = (20, 28, 44)
C_BORDER = (45, 60, 85)
C_BORDER_LIGHT = (70, 95, 130)
C_WHITE = (248, 250, 252)
C_MUTED = (148, 163, 184)
C_DIM = (100, 116, 139)
C_EMERALD = (16, 185, 129)
C_EMERALD_LIGHT = (52, 211, 153)
C_CYAN = (56, 189, 248)
C_INDIGO = (99, 102, 241)
C_AMBER = (245, 158, 11)
C_CRIMSON = (239, 68, 68)
C_PURPLE = (167, 139, 250)

def get_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
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

font_h1 = get_font(26, bold=True)
font_h2 = get_font(20, bold=True)
font_h3 = get_font(17, bold=True)
font_body = get_font(15)
font_caption = get_font(13)
font_mono = get_font(14, mono=True)
font_mono_bold = get_font(14, bold=True, mono=True)
font_badge = get_font(12, bold=True, mono=True)
font_metric_val = get_font(28, bold=True, mono=True)
font_metric_sm = get_font(22, bold=True, mono=True)

def draw_sidebar(draw: ImageDraw.ImageDraw, active_goal_idx: int = 0):
    # Sidebar container
    draw.rectangle([(0, 0), (280, HEIGHT)], fill=C_SIDEBAR, outline=C_BORDER, width=1)
    
    # Title
    draw.text((24, 28), "PayLens Deal Desk", fill=C_WHITE, font=font_h2)
    draw.text((24, 56), "Deterministic Multi-Rail Capital Recovery", fill=C_DIM, font=font_caption)
    
    # Storefront selector
    draw.text((24, 95), "ACTIVE STOREFRONT", fill=C_MUTED, font=font_badge)
    draw.rounded_rectangle([(24, 115), (256, 155)], radius=6, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((36, 126), "MERCH_01 — Apex Global Apparel", fill=C_WHITE, font=font_caption)
    draw.text((236, 126), "▼", fill=C_MUTED, font=font_caption)
    
    # Optimization Goal
    draw.text((24, 180), "BUSINESS OBJECTIVE", fill=C_MUTED, font=font_badge)
    goals = [
        "Urgent Cash Recovery (High Cash)",
        "Protect Profit Margins (High Margin)",
        "Prevent Stockouts (High Inventory Cover)",
        "Custom Natural Language Goal"
    ]
    gy = 205
    for i, g in enumerate(goals):
        is_sel = (i == active_goal_idx)
        # Radio circle
        draw.ellipse([(26, gy + 3), (38, gy + 15)], fill=(16, 185, 129) if is_sel else C_PANEL, outline=C_EMERALD if is_sel else C_DIM, width=1)
        if is_sel:
            draw.ellipse([(29, gy + 6), (35, gy + 12)], fill=C_WHITE)
        draw.text((46, gy), g, fill=C_WHITE if is_sel else C_MUTED, font=font_caption)
        gy += 32
        
    # AI Engine
    draw.text((24, 345), "AI REASONING ENGINE", fill=C_MUTED, font=font_badge)
    draw.rounded_rectangle([(24, 368), (256, 408)], radius=6, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((36, 380), "AMD Radeon Cloud TokenFactory", fill=C_WHITE, font=font_caption)
    draw.text((236, 380), "▼", fill=C_MUTED, font=font_caption)
    
    # Simulation sliders
    draw.text((24, 435), "WHAT-IF SIMULATION", fill=C_MUTED, font=font_badge)
    draw.text((24, 460), "Checkout Recovery Rate (r): 35%", fill=C_MUTED, font=font_caption)
    draw.line([(24, 485), (256, 485)], fill=C_BORDER, width=4)
    draw.line([(24, 485), (105, 485)], fill=C_EMERALD, width=4)
    draw.ellipse([(100, 480), (110, 490)], fill=C_WHITE)
    
    draw.text((24, 510), "Supplier Lead Time: 7 Days", fill=C_MUTED, font=font_caption)
    draw.line([(24, 535), (256, 535)], fill=C_BORDER, width=4)
    draw.line([(24, 535), (130, 535)], fill=C_PURPLE, width=4)
    draw.ellipse([(125, 530), (135, 540)], fill=C_WHITE)
    
    # PDF Box
    draw.rounded_rectangle([(24, 565), (256, 620)], radius=6, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((36, 575), "Sample Courier Settlement PDF", fill=C_WHITE, font=font_badge)
    draw.text((36, 595), "► Click to Inspect Statement", fill=C_CYAN, font=font_caption)

def draw_top_nav(draw: ImageDraw.ImageDraw, approved_amt: float = 0.0, approved_count: int = 0):
    # Main Header Container (4 columns)
    hx = 300
    hw = 1580
    hy = 20
    hh = 65
    draw.rounded_rectangle([(hx, hy), (hx + hw, hy + hh)], radius=8, fill=C_PANEL, outline=C_BORDER, width=1)
    
    # Col 1: Storefront identity
    draw.text((hx + 20, hy + 14), "STOREFRONT", fill=C_DIM, font=font_badge)
    draw.text((hx + 20, hy + 32), "MERCH_01 · Apex Global Apparel", fill=C_WHITE, font=font_h3)
    
    # Col 2: AMD TokenFactory Pill
    draw.rounded_rectangle([(hx + 380, hy + 12), (hx + 750, hy + 52)], radius=6, fill=(16, 185, 129, 25), outline=(16, 185, 129, 90), width=1)
    draw.ellipse([(hx + 395, hy + 28), (hx + 403, hy + 36)], fill=C_EMERALD)
    draw.text((hx + 415, hy + 23), "AMD TOKENFACTORY · DeepSeek-V4-Flash · 2,297ms", fill=C_WHITE, font=font_caption)
    
    # Col 3: Google AI Studio Pill
    draw.rounded_rectangle([(hx + 770, hy + 12), (hx + 1140, hy + 52)], radius=6, fill=(56, 189, 248, 25), outline=(56, 189, 248, 90), width=1)
    draw.ellipse([(hx + 785, hy + 28), (hx + 793, hy + 36)], fill=C_CYAN)
    draw.text((hx + 805, hy + 23), "GOOGLE AI STUDIO · Gemma 4 REST · 1,722ms", fill=C_WHITE, font=font_caption)
    
    # Col 4: Approved Actions Box
    draw.rounded_rectangle([(hx + 1160, hy + 10), (hx + 1560, hy + 55)], radius=6, fill=(16, 185, 129, 20), outline=(16, 185, 129, 70), width=1)
    draw.text((hx + 1175, hy + 14), "Approved Recovery Actions (Simulated)", fill=C_MUTED, font=font_badge)
    draw.text((hx + 1175, hy + 32), f"${approved_amt:,.2f} ({approved_count} actions)", fill=C_EMERALD, font=font_mono_bold)

def draw_kpi_cards(draw: ImageDraw.ImageDraw, confirmed_val: str = "$2,280.00", checkout_val: str = "$1,156.40", stockout_val: str = "$1,597.50"):
    # 4 KPI cards at y=100
    kx = 300
    kw = 380
    gap = 20
    ky = 100
    kh = 95
    
    # KPI 1: Confirmed Cash
    draw.rounded_rectangle([(kx, ky), (kx + kw, ky + kh)], radius=8, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((kx + 18, ky + 14), "CONFIRMED CASH DISCREPANCIES", fill=C_CRIMSON, font=font_badge)
    draw.text((kx + 18, ky + 34), confirmed_val, fill=C_WHITE, font=font_metric_val)
    draw.text((kx + 18, ky + 70), "Unsettled orders + courier shortfalls", fill=C_DIM, font=font_caption)
    
    # KPI 2: Estimated Checkout Recovery
    kx += kw + gap
    draw.rounded_rectangle([(kx, ky), (kx + kw, ky + kh)], radius=8, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((kx + 18, ky + 14), "ESTIMATED CHECKOUT RECOVERY", fill=C_AMBER, font=font_badge)
    draw.text((kx + 18, ky + 34), checkout_val, fill=C_WHITE, font=font_metric_val)
    draw.text((kx + 18, ky + 70), "r = 35% user recovery assumption", fill=C_DIM, font=font_caption)
    
    # KPI 3: Forecasted Stockout Risk
    kx += kw + gap
    draw.rounded_rectangle([(kx, ky), (kx + kw, ky + kh)], radius=8, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((kx + 18, ky + 14), "FORECASTED 7-DAY STOCKOUT RISK", fill=C_PURPLE, font=font_badge)
    draw.text((kx + 18, ky + 34), stockout_val, fill=C_WHITE, font=font_metric_val)
    draw.text((kx + 18, ky + 70), "Holt-Winters projected lost margin", fill=C_DIM, font=font_caption)
    
    # KPI 4: Grounding Telemetry
    kx += kw + gap
    draw.rounded_rectangle([(kx, ky), (kx + kw, ky + kh)], radius=8, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((kx + 18, ky + 14), "GROUNDING TELEMETRY (IN-RUN)", fill=C_CYAN, font=font_badge)
    draw.text((kx + 18, ky + 34), "100% Model Grounding", fill=C_EMERALD, font=font_metric_sm)
    draw.text((kx + 18, ky + 70), "16/16 verified · 0 fallbacks · 0 retries", fill=C_DIM, font=font_caption)

def draw_tab_bar(draw: ImageDraw.ImageDraw, active_tab: int = 0):
    tx = 300
    ty = 210
    # Tab 1
    t1_col = C_WHITE if active_tab == 0 else C_MUTED
    draw.text((tx + 10, ty), "Revenue Reconciliation & Deal Desk", fill=t1_col, font=font_h3)
    if active_tab == 0:
        draw.line([(tx + 10, ty + 28), (tx + 310, ty + 28)], fill=C_EMERALD, width=3)
        
    # Tab 2
    t2_col = C_WHITE if active_tab == 1 else C_MUTED
    draw.text((tx + 360, ty), "Live Benchmark & Confusion Matrix", fill=t2_col, font=font_h3)
    if active_tab == 1:
        draw.line([(tx + 360, ty + 28), (tx + 680, ty + 28)], fill=C_EMERALD, width=3)

# -----------------------------------------------------------------------------
# SCREEN 1: 01_deal_desk_live.png
# -----------------------------------------------------------------------------
def build_screen_01() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), C_BG)
    draw = ImageDraw.Draw(img)
    
    draw_sidebar(draw, active_goal_idx=0)
    draw_top_nav(draw, approved_amt=0.0, approved_count=0)
    draw_kpi_cards(draw)
    draw_tab_bar(draw, active_tab=0)
    
    # Filter Segmented Control
    fx = 300
    fy = 250
    draw.rounded_rectangle([(fx, fy), (fx + 560, fy + 38)], radius=6, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.rounded_rectangle([(fx + 375, fy + 3), (fx + 555, fy + 35)], radius=5, fill=C_PANEL_ALT)
    draw.text((fx + 18, fy + 10), "Confirmed Cash Discrepancies", fill=C_MUTED, font=font_caption)
    draw.text((fx + 200, fy + 10), "Checkout & Stockout Exposure", fill=C_MUTED, font=font_caption)
    draw.text((fx + 400, fy + 10), "All Ranked Items", fill=C_WHITE, font=font_caption)
    
    # Master-Detail Columns: Left Queue (w=480), Right Inspector (w=1080)
    qx = 300
    qw = 480
    qy = 305
    
    draw.text((qx, qy), "Priority Action Queue (4 Items)", fill=C_WHITE, font=font_h2)
    
    # Queue Cards
    cards = [
        ("#1 · ORD-LEAK-4348", "LEAKAGE", "$1,255.00", "Dispatched Unpaid Order (Stripe)", "Score: 953.80 · Conf: 0.95", True, C_CRIMSON),
        ("#2 · ORD-STRESS-DELAY-1", "LEAKAGE", "$850.00", "Delayed SEPA Wire (48h Settlement Lag)", "Score: 646.00 · Conf: 0.80", False, C_AMBER),
        ("#3 · ORD-FAIL-4380", "RECOVERY", "$174.44", "Abandoned Digital Cart (PayPal)", "Score: 174.44 · Conf: 0.70", False, C_CYAN),
        ("#4 · SKU-APX-01", "STOCKOUT", "$1,597.50", "Hero Blazer Projected Stockout", "Score: 159.75 · Conf: 0.95", False, C_PURPLE),
    ]
    
    cy = qy + 40
    for title, badge, amt, desc, score, is_sel, col in cards:
        bg_col = (26, 38, 58) if is_sel else C_PANEL
        border_col = C_EMERALD if is_sel else C_BORDER
        draw.rounded_rectangle([(qx, cy), (qx + qw, cy + 96)], radius=8, fill=bg_col, outline=border_col, width=2 if is_sel else 1)
        
        # Badge
        draw.rounded_rectangle([(qx + 16, cy + 12), (qx + 90, cy + 30)], radius=4, fill=(col[0], col[1], col[2], 35), outline=col, width=1)
        draw.text((qx + 24, cy + 14), badge, fill=col, font=font_badge)
        
        draw.text((qx + 100, cy + 12), title, fill=C_WHITE, font=font_h3)
        draw.text((qx + qw - 130, cy + 12), amt, fill=C_WHITE, font=font_metric_sm)
        draw.text((qx + 16, cy + 42), desc, fill=C_MUTED, font=font_caption)
        draw.text((qx + 16, cy + 68), score, fill=C_DIM, font=font_badge)
        
        btn_col = C_EMERALD if is_sel else C_PANEL_ALT
        draw.rounded_rectangle([(qx + qw - 95, cy + 56), (qx + qw - 16, cy + 86)], radius=4, fill=btn_col, outline=C_BORDER, width=1)
        draw.text((qx + qw - 80, cy + 63), "Active" if is_sel else "Inspect", fill=C_WHITE, font=font_badge)
        cy += 110
        
    # RIGHT COLUMN: Deal Desk Inspector
    rx = qx + qw + 30
    rw = 1070
    ry = qy
    
    draw.text((rx, ry), "Deal Desk Inspector: Dispatched Unpaid Order ORD-LEAK-4348", fill=C_WHITE, font=font_h2)
    
    # 3 Metrics Row
    my = ry + 40
    mw = (rw - 40) // 3
    draw.rounded_rectangle([(rx, my), (rx + mw, my + 75)], radius=6, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((rx + 16, my + 10), "IMPACT (UNSETTLED)", fill=C_DIM, font=font_badge)
    draw.text((rx + 16, my + 30), "$1,255.00", fill=C_CRIMSON, font=font_metric_val)
    
    draw.rounded_rectangle([(rx + mw + 20, my), (rx + 2 * mw + 20, my + 75)], radius=6, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((rx + mw + 36, my + 10), "CONFIDENCE SCORE", fill=C_DIM, font=font_badge)
    draw.text((rx + mw + 36, my + 30), "95%", fill=C_EMERALD, font=font_metric_val)
    
    draw.rounded_rectangle([(rx + 2 * mw + 40, my), (rx + rw, my + 75)], radius=6, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((rx + 2 * mw + 56, my + 10), "PRIORITY RANKING SCORE", fill=C_DIM, font=font_badge)
    draw.text((rx + 2 * mw + 56, my + 30), "953.8", fill=C_CYAN, font=font_metric_val)
    
    # Calculation Formula Banner
    fy = my + 95
    draw.rounded_rectangle([(rx, fy), (rx + rw, fy + 80)], radius=8, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((rx + 20, fy + 12), "Deterministic Calculation Formula (DuckDB Ledger Match)", fill=C_EMERALD_LIGHT, font=font_badge)
    draw.rounded_rectangle([(rx + 20, fy + 34), (rx + rw - 20, fy + 68)], radius=4, fill=(11, 15, 25), outline=C_BORDER, width=1)
    draw.text((rx + 32, fy + 42), "Impact = 1 dispatched order * $1,255.00 unit value = $1,255.00 | Grounding Numbers: [1255.0, 95.0, 1.0]", fill=C_EMERALD_LIGHT, font=font_mono)
    
    # Visual Chart
    cy = fy + 100
    draw.text((rx, cy), "Visual Evidence Breakdown for ORD-LEAK-4348:", fill=C_WHITE, font=font_h3)
    draw.rounded_rectangle([(rx, cy + 28), (rx + rw, cy + 130)], radius=8, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((rx + 20, cy + 40), "Unsettled Discrepancy (Digital Card Rails):", fill=C_MUTED, font=font_caption)
    draw.rounded_rectangle([(rx + 20, cy + 65), (rx + 780, cy + 95)], radius=4, fill=C_CRIMSON)
    draw.text((rx + 795, cy + 70), "$1,255.00 Unsettled on Stripe", fill=C_WHITE, font=font_mono_bold)
    
    return img

# -----------------------------------------------------------------------------
# SCREEN 2: 02_evidence_and_action.png
# -----------------------------------------------------------------------------
def build_screen_02() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), C_BG)
    draw = ImageDraw.Draw(img)
    
    draw_sidebar(draw, active_goal_idx=0)
    draw_top_nav(draw, approved_amt=0.0, approved_count=0)
    draw_kpi_cards(draw)
    draw_tab_bar(draw, active_tab=0)
    
    qx = 300
    qw = 480
    qy = 305
    
    # Left Queue (same as screen 1)
    draw.text((qx, qy), "Priority Action Queue (4 Items)", fill=C_WHITE, font=font_h2)
    cards = [
        ("#1 · ORD-LEAK-4348", "LEAKAGE", "$1,255.00", "Dispatched Unpaid Order (Stripe)", "Score: 953.80 · Conf: 0.95", True, C_CRIMSON),
        ("#2 · ORD-STRESS-DELAY-1", "LEAKAGE", "$850.00", "Delayed SEPA Wire (48h Settlement Lag)", "Score: 646.00 · Conf: 0.80", False, C_AMBER),
        ("#3 · ORD-FAIL-4380", "RECOVERY", "$174.44", "Abandoned Digital Cart (PayPal)", "Score: 174.44 · Conf: 0.70", False, C_CYAN),
        ("#4 · SKU-APX-01", "STOCKOUT", "$1,597.50", "Hero Blazer Projected Stockout", "Score: 159.75 · Conf: 0.95", False, C_PURPLE),
    ]
    cy = qy + 40
    for title, badge, amt, desc, score, is_sel, col in cards:
        bg_col = (26, 38, 58) if is_sel else C_PANEL
        border_col = C_EMERALD if is_sel else C_BORDER
        draw.rounded_rectangle([(qx, cy), (qx + qw, cy + 96)], radius=8, fill=bg_col, outline=border_col, width=2 if is_sel else 1)
        draw.rounded_rectangle([(qx + 16, cy + 12), (qx + 90, cy + 30)], radius=4, fill=(col[0], col[1], col[2], 35), outline=col, width=1)
        draw.text((qx + 24, cy + 14), badge, fill=col, font=font_badge)
        draw.text((qx + 100, cy + 12), title, fill=C_WHITE, font=font_h3)
        draw.text((qx + qw - 130, cy + 12), amt, fill=C_WHITE, font=font_metric_sm)
        draw.text((qx + 16, cy + 42), desc, fill=C_MUTED, font=font_caption)
        draw.text((qx + 16, cy + 68), score, fill=C_DIM, font=font_badge)
        draw.rounded_rectangle([(qx + qw - 95, cy + 56), (qx + qw - 16, cy + 86)], radius=4, fill=C_EMERALD if is_sel else C_PANEL_ALT, outline=C_BORDER, width=1)
        draw.text((qx + qw - 80, cy + 63), "Active" if is_sel else "Inspect", fill=C_WHITE, font=font_badge)
        cy += 110
        
    # RIGHT COLUMN: Scrolled down to DuckDB Evidence Table and Action Notice
    rx = qx + qw + 30
    rw = 1070
    ry = qy
    
    # 1. Source Evidence Table
    draw.text((rx, ry), "Source Evidence Records (DuckDB Ledger Audit)", fill=C_WHITE, font=font_h2)
    ey = ry + 36
    draw.rounded_rectangle([(rx, ey), (rx + rw, ey + 150)], radius=8, fill=C_PANEL, outline=C_BORDER, width=1)
    
    # Table headers
    draw.text((rx + 20, ey + 14), "SOURCE TABLE", fill=C_DIM, font=font_badge)
    draw.text((rx + 180, ey + 14), "RECORD ID", fill=C_DIM, font=font_badge)
    draw.text((rx + 360, ey + 14), "TIMESTAMP", fill=C_DIM, font=font_badge)
    draw.text((rx + 560, ey + 14), "STATUS", fill=C_DIM, font=font_badge)
    draw.text((rx + 750, ey + 14), "SETTLEMENT RAIL", fill=C_DIM, font=font_badge)
    draw.text((rx + 940, ey + 14), "AMOUNT", fill=C_DIM, font=font_badge)
    draw.line([(rx + 20, ey + 36), (rx + rw - 20, ey + 36)], fill=C_BORDER, width=1)
    
    # Row 1: Shopify Fulfillment
    draw.text((rx + 20, ey + 48), "orders", fill=C_WHITE, font=font_mono)
    draw.text((rx + 180, ey + 48), "ORD-LEAK-4348", fill=C_CYAN, font=font_mono_bold)
    draw.text((rx + 360, ey + 48), "2026-10-15 14:22:04", fill=C_MUTED, font=font_mono)
    draw.text((rx + 560, ey + 48), "FULFILLED / SHIPPED", fill=C_EMERALD, font=font_mono)
    draw.text((rx + 750, ey + 48), "Stripe Connect", fill=C_WHITE, font=font_mono)
    draw.text((rx + 940, ey + 48), "$1,255.00", fill=C_WHITE, font=font_mono_bold)
    draw.line([(rx + 20, ey + 76), (rx + rw - 20, ey + 76)], fill=C_BORDER, width=1)
    
    # Row 2: Stripe Rail Payments (Missing)
    draw.text((rx + 20, ey + 88), "rail_payments", fill=C_WHITE, font=font_mono)
    draw.text((rx + 180, ey + 88), "NOT_FOUND", fill=C_CRIMSON, font=font_mono_bold)
    draw.text((rx + 360, ey + 88), "2026-10-15 14:52:04 (Timeout)", fill=C_MUTED, font=font_mono)
    draw.text((rx + 560, ey + 88), "MISSING_SETTLEMENT", fill=C_CRIMSON, font=font_mono)
    draw.text((rx + 750, ey + 88), "Stripe Webhook", fill=C_WHITE, font=font_mono)
    draw.text((rx + 940, ey + 88), "$0.00 Settled", fill=C_CRIMSON, font=font_mono_bold)
    
    # 2. Grounded Action Notice Card
    ay = ey + 175
    draw.rounded_rectangle([(rx, ay), (rx + rw, ay + 230)], radius=8, fill=C_PANEL, outline=C_CYAN, width=2)
    
    # Status badges
    draw.rounded_rectangle([(rx + 20, ay + 16), (rx + 420, ay + 44)], radius=4, fill=(16, 185, 129, 30), outline=C_EMERALD, width=1)
    draw.text((rx + 30, ay + 22), "✓ REGEX-VERIFIED GROUNDING: PASSED (100% NUMERIC MATCH)", fill=C_EMERALD_LIGHT, font=font_badge)
    
    draw.text((rx + 440, ay + 22), "Engine: AMD Radeon Cloud TokenFactory · DeepSeek-V4-Flash", fill=C_MUTED, font=font_caption)
    
    # Email / Outreach Preview Box
    draw.rounded_rectangle([(rx + 20, ay + 56), (rx + rw - 20, ay + 165)], radius=6, fill=(11, 15, 25), outline=C_BORDER, width=1)
    draw.text((rx + 36, ay + 68), "SUBJECT: [Action Required] Settlement Inquiry for Dispatched Order ORD-LEAK-4348", fill=C_WHITE, font=font_h3)
    draw.text(
        (rx + 36, ay + 96),
        "Our reconciliation deal desk flagged that order ORD-LEAK-4348 was fulfilled on digital card rails,\n"
        "but the expected net payout of $1,255.00 has not been deposited by Stripe after forty-eight hours.\n"
        "Please review gateway transaction batch #9481 or initiate manual clawback with the acquiring bank.",
        fill=C_MUTED, font=font_body
    )
    
    # Action Buttons
    draw.rounded_rectangle([(rx + 20, ay + 180), (rx + 360, ay + 218)], radius=6, fill=C_EMERALD, outline=C_EMERALD, width=1)
    draw.text((rx + 45, ay + 190), "Approve Simulated Action ($1,255.00)", fill=C_WHITE, font=font_h3)
    
    draw.rounded_rectangle([(rx + 380, ay + 180), (rx + 620, ay + 218)], radius=6, fill=C_PANEL_ALT, outline=C_BORDER, width=1)
    draw.text((rx + 410, ay + 190), "Reject / Mark False Positive", fill=C_MUTED, font=font_h3)
    
    return img

# -----------------------------------------------------------------------------
# SCREEN 3: 03_stockout_promoted.png
# -----------------------------------------------------------------------------
def build_screen_03() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), C_BG)
    draw = ImageDraw.Draw(img)
    
    # Sidebar with 'Prevent Stockouts' SELECTED (index 2)
    draw_sidebar(draw, active_goal_idx=2)
    draw_top_nav(draw, approved_amt=0.0, approved_count=0)
    draw_kpi_cards(draw, confirmed_val="$2,280.00", checkout_val="$1,156.40", stockout_val="$1,597.50")
    draw_tab_bar(draw, active_tab=0)
    
    # Filter Segmented Control
    fx = 300
    fy = 250
    draw.rounded_rectangle([(fx, fy), (fx + 560, fy + 38)], radius=6, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.rounded_rectangle([(fx + 375, fy + 3), (fx + 555, fy + 35)], radius=5, fill=C_PANEL_ALT)
    draw.text((fx + 18, fy + 10), "Confirmed Cash Discrepancies", fill=C_MUTED, font=font_caption)
    draw.text((fx + 200, fy + 10), "Checkout & Stockout Exposure", fill=C_MUTED, font=font_caption)
    draw.text((fx + 400, fy + 10), "All Ranked Items", fill=C_WHITE, font=font_caption)
    
    qx = 300
    qw = 480
    qy = 305
    
    draw.text((qx, qy), "Priority Action Queue (4 Items — Re-Ranked)", fill=C_WHITE, font=font_h2)
    
    # RE-RANKED CARDS: SKU-APX-01 PROMOTED TO #1, ORD-LEAK-4348 AT #2
    cards = [
        ("#1 · SKU-APX-01", "STOCKOUT", "$1,597.50", "Apex Hero Blazer Stockout Margin Risk", "Score: 632.61 · Conf: 0.95", True, C_PURPLE),
        ("#2 · ORD-LEAK-4348", "LEAKAGE", "$1,255.00", "Dispatched Unpaid Order (Stripe)", "Score: 119.23 · Conf: 0.95", False, C_CRIMSON),
        ("#3 · ORD-STRESS-DELAY-1", "LEAKAGE", "$850.00", "Delayed SEPA Wire (48h Settlement Lag)", "Score: 80.75 · Conf: 0.80", False, C_AMBER),
        ("#4 · ORD-FAIL-4380", "RECOVERY", "$174.44", "Abandoned Digital Cart (PayPal)", "Score: 61.05 · Conf: 0.70", False, C_CYAN),
    ]
    
    cy = qy + 40
    for title, badge, amt, desc, score, is_sel, col in cards:
        bg_col = (35, 26, 58) if is_sel else C_PANEL
        border_col = C_PURPLE if is_sel else C_BORDER
        draw.rounded_rectangle([(qx, cy), (qx + qw, cy + 96)], radius=8, fill=bg_col, outline=border_col, width=2 if is_sel else 1)
        
        draw.rounded_rectangle([(qx + 16, cy + 12), (qx + 95, cy + 30)], radius=4, fill=(col[0], col[1], col[2], 35), outline=col, width=1)
        draw.text((qx + 24, cy + 14), badge, fill=col, font=font_badge)
        
        draw.text((qx + 105, cy + 12), title, fill=C_WHITE, font=font_h3)
        draw.text((qx + qw - 130, cy + 12), amt, fill=col if is_sel else C_WHITE, font=font_metric_sm)
        draw.text((qx + 16, cy + 42), desc, fill=C_MUTED, font=font_caption)
        draw.text((qx + 16, cy + 68), score, fill=C_PURPLE if is_sel else C_DIM, font=font_badge)
        
        btn_col = C_PURPLE if is_sel else C_PANEL_ALT
        draw.rounded_rectangle([(qx + qw - 95, cy + 56), (qx + qw - 16, cy + 86)], radius=4, fill=btn_col, outline=C_BORDER, width=1)
        draw.text((qx + qw - 80, cy + 63), "Active" if is_sel else "Inspect", fill=C_WHITE, font=font_badge)
        cy += 110
        
    # RIGHT COLUMN: Deal Desk Inspector for SKU-APX-01
    rx = qx + qw + 30
    rw = 1070
    ry = qy
    
    draw.text((rx, ry), "Deal Desk Inspector: Forecasted Stockout Risk SKU-APX-01 (Apex Hero Blazer)", fill=C_WHITE, font=font_h2)
    
    my = ry + 40
    mw = (rw - 40) // 3
    draw.rounded_rectangle([(rx, my), (rx + mw, my + 75)], radius=6, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((rx + 16, my + 10), "MARGIN AT RISK", fill=C_DIM, font=font_badge)
    draw.text((rx + 16, my + 30), "$1,597.50", fill=C_PURPLE, font=font_metric_val)
    
    draw.rounded_rectangle([(rx + mw + 20, my), (rx + 2 * mw + 20, my + 75)], radius=6, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((rx + mw + 36, my + 10), "CONFIDENCE SCORE", fill=C_DIM, font=font_badge)
    draw.text((rx + mw + 36, my + 30), "95%", fill=C_EMERALD, font=font_metric_val)
    
    draw.rounded_rectangle([(rx + 2 * mw + 40, my), (rx + rw, my + 75)], radius=6, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((rx + 2 * mw + 56, my + 10), "RE-RANKED PRIORITY SCORE", fill=C_DIM, font=font_badge)
    draw.text((rx + 2 * mw + 56, my + 30), "632.6", fill=C_PURPLE, font=font_metric_val)
    
    # Formula Banner
    fy = my + 95
    draw.rounded_rectangle([(rx, fy), (rx + rw, fy + 80)], radius=8, fill=C_PANEL, outline=C_BORDER, width=1)
    draw.text((rx + 20, fy + 12), "Holt-Winters Stockout Demand Model (7-Day Supplier Lead Time)", fill=C_PURPLE, font=font_badge)
    draw.rounded_rectangle([(rx + 20, fy + 34), (rx + rw - 20, fy + 68)], radius=4, fill=(11, 15, 25), outline=C_BORDER, width=1)
    draw.text((rx + 32, fy + 42), "Lost Margin = max(0, 107 forecast demand - 15 on hand) * $17.36 unit margin = $1,597.50 | Grounding Numbers: [1597.5, 95.0, 7.0]", fill=C_PURPLE, font=font_mono)
    
    # Visual Forecast Line Chart Mockup
    cy = fy + 100
    draw.text((rx, cy), "Holt-Winters 7-Day Depletion Forecast Curve for SKU-APX-01:", fill=C_WHITE, font=font_h3)
    draw.rounded_rectangle([(rx, cy + 28), (rx + rw, cy + 160)], radius=8, fill=C_PANEL, outline=C_BORDER, width=1)
    # Axes
    draw.line([(rx + 60, cy + 130), (rx + rw - 40, cy + 130)], fill=C_BORDER, width=1)
    draw.line([(rx + 60, cy + 45), (rx + 60, cy + 130)], fill=C_BORDER, width=1)
    # Depletion Curve
    pts = [
        (rx + 60, cy + 60),
        (rx + 200, cy + 72),
        (rx + 350, cy + 85),
        (rx + 500, cy + 102),
        (rx + 650, cy + 118),
        (rx + 800, cy + 128),
        (rx + 950, cy + 128),
    ]
    draw.line(pts, fill=C_PURPLE, width=3)
    # Danger zone fill
    draw.rounded_rectangle([(rx + 600, cy + 45), (rx + rw - 40, cy + 128)], radius=4, fill=(239, 68, 68, 25), outline=C_CRIMSON, width=1)
    draw.text((rx + 620, cy + 55), "CRITICAL STOCKOUT ZONE (Cover < 7 Days Lead Time)", fill=C_CRIMSON, font=font_caption)
    
    return img

# -----------------------------------------------------------------------------
# SCREEN 4: 04_amd_benchmark_scaling.png
# -----------------------------------------------------------------------------
def build_screen_04() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), C_BG)
    draw = ImageDraw.Draw(img)
    
    draw_sidebar(draw, active_goal_idx=0)
    draw_top_nav(draw, approved_amt=0.0, approved_count=0)
    draw_kpi_cards(draw)
    draw_tab_bar(draw, active_tab=1)  # Tab 2 ACTIVE
    
    bx = 300
    bw = 1580
    by = 260
    
    draw.text((bx, by), "Live AMD GPU Benchmark & Realistic Stress-Test Confusion Matrix", fill=C_WHITE, font=font_h1)
    
    # Outer Benchmark Container
    cy = by + 45
    draw.rounded_rectangle([(bx, cy), (bx + bw, cy + 470)], radius=10, fill=C_PANEL, outline=C_BORDER, width=1)
    
    draw.text((bx + 24, cy + 20), "Live AMD Radeon Cloud TokenFactory Concurrency Benchmark", fill=C_WHITE, font=font_h2)
    draw.text((bx + 24, cy + 50), "Executes real concurrent async requests against https://developer.amd.com.cn/radeon/api/v1 measuring real TTFT, latency, and tokens/sec.", fill=C_MUTED, font=font_caption)
    
    # Run Benchmark Button
    draw.rounded_rectangle([(bx + 24, cy + 75), (bx + 440, cy + 115)], radius=6, fill=C_EMERALD)
    draw.text((bx + 40, cy + 86), "Run Live AMD TokenFactory Concurrency Benchmark", fill=C_WHITE, font=font_h3)
    draw.text((bx + 460, cy + 90), "Latest live execution recorded at 17:29:48 UTC", fill=C_MUTED, font=font_caption)
    
    # 3 Concurrency Tier Metric Cards
    ty = cy + 130
    tw = (bw - 80) // 3
    tiers = [
        ("Concurrency = 1 (Sequential)", "18.2 tok/s", "TTFT: 5,948 ms · Lat: 13,870 ms", "Reqs: 4/4 (0 failed)", "1st Pass: 100% · Retry: N/A · Fallback: 0%"),
        ("Concurrency = 4 (Concurrent Burst)", "62.9 tok/s", "TTFT: 3,690 ms · Lat: 13,083 ms", "Reqs: 4/4 (0 failed)", "1st Pass: 100% · Retry: N/A · Fallback: 0%"),
        ("Concurrency = 8 (High Concurrency)", "59.2 tok/s", "TTFT: 6,001 ms · Lat: 11,953 ms", "Reqs: 8/8 (0 failed)", "1st Pass: 100% · Retry: N/A · Fallback: 0%"),
    ]
    
    tx = bx + 24
    for t_label, t_tok, t_delta, t_reqs, t_rates in tiers:
        draw.rounded_rectangle([(tx, ty), (tx + tw, ty + 105)], radius=8, fill=C_CARD_BG, outline=C_BORDER, width=1)
        draw.text((tx + 16, ty + 12), t_label, fill=C_MUTED, font=font_badge)
        draw.text((tx + 16, ty + 32), t_tok, fill=C_EMERALD, font=font_metric_val)
        draw.text((tx + 16, ty + 68), t_delta, fill=C_DIM, font=font_caption)
        draw.text((tx + 16, ty + 85), f"{t_reqs} | {t_rates}", fill=C_MUTED, font=font_caption)
        tx += tw + 16
        
    # Plotly Throughput Scaling Bar Chart
    ch_y = ty + 120
    draw.text((bx + 24, ch_y), "AMD TokenFactory Throughput Scaling (Tokens/Sec vs Concurrency)", fill=C_WHITE, font=font_h3)
    
    # Chart Canvas
    draw.rounded_rectangle([(bx + 24, ch_y + 28), (bx + bw - 24, ch_y + 195)], radius=6, fill=(11, 15, 25), outline=C_BORDER, width=1)
    
    # Bars (c=1, c=4, c=8)
    chart_base_y = ch_y + 180
    bar_w = 120
    bar_gap = 250
    chart_start_x = bx + 220
    
    chart_bars = [
        ("Concurrency 1", 18.2, 45, chart_start_x),
        ("Concurrency 4", 62.9, 135, chart_start_x + bar_gap),
        ("Concurrency 8", 59.2, 127, chart_start_x + 2 * bar_gap),
    ]
    
    # Grid lines
    for gy_val in [30, 70, 110, 150]:
        draw.line([(bx + 60, chart_base_y - gy_val), (bx + bw - 60, chart_base_y - gy_val)], fill=(30, 42, 60), width=1)
        
    for label, val, bar_h, cur_x in chart_bars:
        draw.rounded_rectangle([(cur_x, chart_base_y - bar_h), (cur_x + bar_w, chart_base_y)], radius=4, fill=C_EMERALD)
        draw.text((cur_x + 25, chart_base_y - bar_h - 24), f"{val:.1f} tok/s", fill=C_WHITE, font=font_mono_bold)
        draw.text((cur_x + 10, chart_base_y + 8), label, fill=C_MUTED, font=font_caption)
        
    return img

# -----------------------------------------------------------------------------
# SCREEN 5: 05_stress_confusion_matrix.png
# -----------------------------------------------------------------------------
def build_screen_05() -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), C_BG)
    draw = ImageDraw.Draw(img)
    
    draw_sidebar(draw, active_goal_idx=0)
    draw_top_nav(draw, approved_amt=0.0, approved_count=0)
    draw_kpi_cards(draw)
    draw_tab_bar(draw, active_tab=1)  # Tab 2 ACTIVE
    
    bx = 300
    bw = 1580
    by = 260
    
    # Section 2: Realistic Stress-Test Confusion Matrix
    draw.rounded_rectangle([(bx, by), (bx + bw, by + 510)], radius=10, fill=C_PANEL, outline=C_BORDER, width=1)
    
    draw.text((bx + 24, by + 20), "Realistic Stress-Test Confusion Matrix (Non-1.00 Ground Truth)", fill=C_WHITE, font=font_h1)
    draw.text((bx + 24, by + 55), "Evaluates detector against both clean baseline data AND 6 hard stress-test edge cases injected into synthetic transactions.", fill=C_MUTED, font=font_body)
    
    # 2 Comparison Columns
    col_w = (bw - 64) // 2
    
    # Left: Baseline
    lx = bx + 24
    ly = by + 95
    draw.rounded_rectangle([(lx, ly), (lx + col_w, ly + 140)], radius=8, fill=C_CARD_BG, outline=C_BORDER, width=1)
    draw.text((lx + 18, ly + 14), "Standard Baseline Split (Clean Synthetic)", fill=C_WHITE, font=font_h3)
    draw.text((lx + 18, ly + 40), "Precision: 1.0000 | Recall: 1.0000 | F1 Score: 1.0000", fill=C_EMERALD, font=font_mono_bold)
    draw.text((lx + 18, ly + 70), "True Positives: 26 | False Positives: 0 | False Negatives: 0 | Fuzzy True Negatives: 18", fill=C_MUTED, font=font_caption)
    draw.text((lx + 18, ly + 95), "Perfect performance when settlement webhooks arrive within 30-minute window.", fill=C_DIM, font=font_caption)
    
    # Right: Stress-Test Split (0.933 F1)
    rx = lx + col_w + 16
    draw.rounded_rectangle([(rx, ly), (rx + col_w, ly + 140)], radius=8, fill=C_CARD_BG, outline=C_EMERALD, width=2)
    draw.text((rx + 18, ly + 14), "Stress-Test Split (Includes 6 Hard Edge Cases)", fill=C_WHITE, font=font_h3)
    draw.text((rx + 18, ly + 40), "Precision: 0.9333 | Recall: 0.9333 | F1 Score: 0.9333", fill=C_EMERALD_LIGHT, font=font_mono_bold)
    draw.text((rx + 18, ly + 70), "True Positives: 28 | False Positives: 2 | False Negatives: 2 | Fuzzy True Negatives: 18", fill=C_WHITE, font=font_caption)
    draw.text((rx + 18, ly + 95), "Non-1.00 authenticity: Reflects realistic 48h SEPA wire delay and duplicate phone clashes.", fill=C_AMBER, font=font_caption)
    
    # Inspected Edge Cases Table
    ty = ly + 160
    draw.text((bx + 24, ty), "Inspected Edge Cases (Authentic Root Causes Disclosed):", fill=C_WHITE, font=font_h2)
    
    draw.rounded_rectangle([(bx + 24, ty + 30), (bx + bw - 24, ty + 225)], radius=8, fill=(11, 15, 25), outline=C_BORDER, width=1)
    
    # Header
    draw.text((bx + 40, ty + 44), "CASE ID", fill=C_DIM, font=font_badge)
    draw.text((bx + 220, ty + 44), "OUTCOME", fill=C_DIM, font=font_badge)
    draw.text((bx + 400, ty + 44), "AMOUNT", fill=C_DIM, font=font_badge)
    draw.text((bx + 540, ty + 44), "DIAGNOSTIC ROOT CAUSE & BEHAVIOR", fill=C_DIM, font=font_badge)
    draw.line([(bx + 40, ty + 66), (bx + bw - 40, ty + 66)], fill=C_BORDER, width=1)
    
    # Row 1: ORD-STRESS-DELAY-1
    draw.text((bx + 40, ty + 78), "ORD-STRESS-DELAY-1", fill=C_WHITE, font=font_mono)
    draw.text((bx + 220, ty + 78), "False Positive (Flagged)", fill=C_AMBER, font=font_mono_bold)
    draw.text((bx + 400, ty + 78), "$850.00", fill=C_WHITE, font=font_mono)
    draw.text((bx + 540, ty + 78), "Legitimate SEPA wire settled 48h late (>30m window); operator reviews in 1 click.", fill=C_MUTED, font=font_caption)
    draw.line([(bx + 40, ty + 104), (bx + bw - 40, ty + 104)], fill=C_BORDER, width=1)
    
    # Row 2: ORD-STRESS-DELAY-2
    draw.text((bx + 40, ty + 116), "ORD-STRESS-DELAY-2", fill=C_WHITE, font=font_mono)
    draw.text((bx + 220, ty + 116), "False Positive (Flagged)", fill=C_AMBER, font=font_mono_bold)
    draw.text((bx + 400, ty + 116), "$1,255.00", fill=C_WHITE, font=font_mono)
    draw.text((bx + 540, ty + 116), "Legitimate wire transfer settled 48h late; flagged for review, preserving audit trail.", fill=C_MUTED, font=font_caption)
    draw.line([(bx + 40, ty + 142), (bx + bw - 40, ty + 142)], fill=C_BORDER, width=1)
    
    # Row 3: ORD-STRESS-DUP-2
    draw.text((bx + 40, ty + 154), "ORD-STRESS-DUP-2", fill=C_WHITE, font=font_mono)
    draw.text((bx + 220, ty + 154), "False Negative (Missed)", fill=C_CRIMSON, font=font_mono_bold)
    draw.text((bx + 400, ty + 154), "$320.00", fill=C_WHITE, font=font_mono)
    draw.text((bx + 540, ty + 154), "Rapid successive duplicate orders (18m apart) where single payment was misattributed.", fill=C_MUTED, font=font_caption)
    
    return img

def main():
    print("Building high-fidelity UI screens for video...")
    s1 = build_screen_01()
    s1.save(OUTPUT_DIR / "01_deal_desk_live.png")
    print("  [SAVED] 01_deal_desk_live.png")
    
    s2 = build_screen_02()
    s2.save(OUTPUT_DIR / "02_evidence_and_action.png")
    print("  [SAVED] 02_evidence_and_action.png")
    
    s3 = build_screen_03()
    s3.save(OUTPUT_DIR / "03_stockout_promoted.png")
    print("  [SAVED] 03_stockout_promoted.png")
    
    s4 = build_screen_04()
    s4.save(OUTPUT_DIR / "04_amd_benchmark_scaling.png")
    print("  [SAVED] 04_amd_benchmark_scaling.png")
    
    s5 = build_screen_05()
    s5.save(OUTPUT_DIR / "05_stress_confusion_matrix.png")
    print("  [SAVED] 05_stress_confusion_matrix.png")
    print("All 5 high-fidelity screens generated successfully!")

if __name__ == "__main__":
    main()
