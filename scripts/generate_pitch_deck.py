"""PayLens 7-Slide Institutional Pitch Deck Generator.

Generates high-resolution 16:9 (1920x1080) presentation slides:
- docs/slides/slide_01.png through slide_07.png
- docs/paylens_pitch_deck.pdf (compiled multi-page PDF presentation)

Styling:
- Dark fintech aesthetic (#0b0f19 background, #131b2e panels, #10b981 emerald, #38bdf8 cyan, #f8fafc text).
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs"
SLIDES_DIR = DOCS_DIR / "slides"
OUTPUT_PDF = DOCS_DIR / "paylens_pitch_deck.pdf"

DOCS_DIR.mkdir(parents=True, exist_ok=True)
SLIDES_DIR.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT = 1920, 1080

# -----------------------------------------------------------------------------
# Color Palette
# -----------------------------------------------------------------------------
C_BG = (11, 15, 25)            # #0b0f19
C_PANEL = (19, 27, 46)         # #131b2e
C_PANEL_ALT = (26, 36, 59)     # #1a243b
C_BORDER = (35, 50, 77)        # #23324d
C_BORDER_LIGHT = (59, 79, 115) # #3b4f73
C_WHITE = (248, 250, 252)      # #f8fafc
C_MUTED = (148, 163, 184)      # #94a3b8
C_DIM = (100, 116, 139)        # #64748b
C_DIVIDER = (30, 41, 59)       # #1e293b

C_EMERALD = (16, 185, 129)     # #10b981
C_EMERALD_BG = (12, 45, 36)
C_CYAN = (56, 189, 248)        # #38bdf8
C_CYAN_BG = (14, 43, 62)
C_AMBER = (245, 158, 11)       # #f59e0b
C_AMBER_BG = (55, 38, 12)
C_INDIGO = (129, 140, 248)     # #818cf8
C_INDIGO_BG = (32, 34, 68)
C_PURPLE = (192, 132, 252)     # #c084fc
C_PURPLE_BG = (45, 26, 68)

# -----------------------------------------------------------------------------
# Font Management
# -----------------------------------------------------------------------------
def get_font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if mono:
        candidates = ["consola.ttf", "cour.ttf", "arial.ttf"]
    elif bold:
        candidates = ["segoeuib.ttf", "arialbd.ttf"]
    else:
        candidates = ["segoeui.ttf", "arial.ttf"]

    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()

font_title_hero = get_font(52, bold=True)
font_title_slide = get_font(38, bold=True)
font_subtitle = get_font(20, bold=False)
font_category = get_font(13, bold=True)
font_section_h = get_font(22, bold=True)
font_card_h = get_font(18, bold=True)
font_metric_lg = get_font(44, bold=True)
font_metric_md = get_font(32, bold=True)
font_metric_lbl = get_font(13, bold=True)
font_body = get_font(15, bold=False)
font_body_sm = get_font(13, bold=False)
font_mono = get_font(14, mono=True)
font_mono_sm = get_font(12, mono=True)
font_footer = get_font(12, bold=False)

# -----------------------------------------------------------------------------
# UI Primitive Helpers
# -----------------------------------------------------------------------------
def create_canvas() -> Tuple[Image.Image, ImageDraw.Draw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), C_BG)
    draw = ImageDraw.Draw(img)

    # Ambient grid / accent line at top
    for x in range(0, WIDTH, 120):
        draw.line([(x, 0), (x, HEIGHT)], fill=(15, 20, 32), width=1)
    for y in range(0, HEIGHT, 120):
        draw.line([(0, y), (WIDTH, y)], fill=(15, 20, 32), width=1)

    # Top emerald/cyan brand line
    draw.line([(0, 0), (960, 0)], fill=C_CYAN, width=3)
    draw.line([(960, 0), (WIDTH, 0)], fill=C_EMERALD, width=3)

    return img, draw

def draw_header(draw: ImageDraw.Draw, slide_num: int, category: str, title: str, subtitle: str) -> None:
    # Category pill
    cat_text = category.upper()
    cat_w = int(draw.textlength(cat_text, font=font_category))
    pill_w = cat_w + 24
    draw.rounded_rectangle([(70, 48), (70 + pill_w, 74)], radius=13, fill=C_CYAN_BG, outline=C_CYAN, width=1)
    draw.text((82, 54), cat_text, fill=C_CYAN, font=font_category)

    # Title & Subtitle
    draw.text((70, 84), title, fill=C_WHITE, font=font_title_slide)
    draw.text((70, 134), subtitle, fill=C_MUTED, font=font_subtitle)

def draw_footer(draw: ImageDraw.Draw, slide_num: int) -> None:
    # Divider line
    draw.line([(70, 1020), (WIDTH - 70, 1020)], fill=C_DIVIDER, width=1)

    # Left: Project & Positioning
    draw.text((70, 1035), "PayLens · Autonomous Cross-Rail Revenue Reconciliation", fill=C_DIM, font=font_footer)

    # Center: Track & Hardware Info
    center_text = "Track 3: Reinvent Commerce · AMD Radeon Cloud TokenFactory · Google DeepMind Gemma 4"
    c_w = int(draw.textlength(center_text, font=font_footer))
    draw.text(((WIDTH - c_w) // 2, 1035), center_text, fill=C_DIM, font=font_footer)

    # Right: Slide number
    slide_text = f"{slide_num:02d} / 07"
    s_w = int(draw.textlength(slide_text, font=font_footer))
    draw.text((WIDTH - 70 - s_w, 1035), slide_text, fill=C_MUTED, font=font_footer)

def draw_card(
    draw: ImageDraw.Draw,
    bbox: Tuple[int, int, int, int],
    title: Optional[str] = None,
    accent_color: Optional[Tuple[int, int, int]] = None,
    bg_color: Tuple[int, int, int] = C_PANEL,
    outline_color: Tuple[int, int, int] = C_BORDER,
    radius: int = 12
) -> None:
    draw.rounded_rectangle(bbox, radius=radius, fill=bg_color, outline=outline_color, width=1)
    if accent_color:
        x0, y0, x1, y1 = bbox
        draw.line([(x0 + 16, y0 + 1), (x1 - 16, y0 + 1)], fill=accent_color, width=2)
    if title:
        x0, y0, _, _ = bbox
        draw.text((x0 + 24, y0 + 20), title, fill=C_WHITE, font=font_card_h)

def wrap_text(text: str, max_chars: int) -> List[str]:
    words = text.split()
    lines = []
    curr = []
    curr_len = 0
    for w in words:
        if curr_len + len(w) + 1 <= max_chars:
            curr.append(w)
            curr_len += len(w) + 1
        else:
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
            curr_len = len(w)
    if curr:
        lines.append(" ".join(curr))
    return lines

# -----------------------------------------------------------------------------
# Slide 1: Title & Track
# -----------------------------------------------------------------------------
def render_slide_01() -> Image.Image:
    img, draw = create_canvas()

    # Big Central Hero Card
    card_box = (140, 160, WIDTH - 140, 940)
    draw.rounded_rectangle(card_box, radius=16, fill=C_PANEL, outline=C_BORDER_LIGHT, width=2)

    # Top Brand Bar inside card
    draw.line([(140, 162), (WIDTH - 140, 162)], fill=C_CYAN, width=3)

    # Track Badge
    badge_text = "HACKATHON TRACK: REINVENT COMMERCE · ACT III"
    draw.rounded_rectangle([(200, 210), (590, 240)], radius=15, fill=C_CYAN_BG, outline=C_CYAN, width=1)
    draw.text((214, 217), badge_text, fill=C_CYAN, font=font_category)

    # Main Title & Subtitle
    draw.text((200, 265), "PayLens", fill=C_WHITE, font=font_title_hero)
    draw.text((430, 275), "Deterministic Cross-Rail Revenue Reconciliation", fill=C_EMERALD, font=get_font(34, bold=True))

    draw.text(
        (200, 345),
        "Autonomous Financial Deal Desk for Fragmented E-Commerce Platforms",
        fill=C_MUTED, font=get_font(24, bold=False)
    )

    # Tagline Pill
    tagline = "Live on Streamlit Cloud · AMD Radeon Cloud TokenFactory & Google Gemma 4 REST"
    draw.text((200, 395), tagline, fill=C_CYAN, font=get_font(18, bold=True))

    # 4 Architecture Foundation Pillars (Horizontal row)
    pillars = [
        ("TRACK 3: REINVENT COMMERCE", "Autonomous Deal Desk for Multi-Rail E-Commerce", C_CYAN),
        ("LIVE HARDWARE: AMD RADEON CLOUD", "DeepSeek-V4-Flash on TokenFactory + MI300X vLLM Recipe", C_EMERALD),
        ("AI REASONING: DUAL-ENGINE INFERENCE", "DeepSeek-V4-Flash & Google Gemma 4 with 1-Click Action Dispatch", C_INDIGO),
        ("DETERMINISTIC VERIFICATION", "DuckDB Math Matchers + Holt-Winters + 100% Regex Shield", C_PURPLE),
    ]

    px = 200
    py = 460
    pw = 360
    ph = 180

    for idx, (p_title, p_desc, p_color) in enumerate(pillars):
        bx = px + idx * (pw + 26)
        draw.rounded_rectangle([(bx, py), (bx + pw, py + ph)], radius=12, fill=C_PANEL_ALT, outline=C_BORDER, width=1)
        draw.line([(bx + 12, py + 1), (bx + pw - 12, py + 1)], fill=p_color, width=2)
        draw.text((bx + 18, py + 20), f"PILLAR 0{idx+1}", fill=p_color, font=font_category)
        draw.text((bx + 18, py + 48), p_title, fill=C_WHITE, font=get_font(15, bold=True))
        desc_lines = wrap_text(p_desc, 36)
        ly = py + 95
        for line in desc_lines:
            draw.text((bx + 18, ly), line, fill=C_MUTED, font=font_body_sm)
            ly += 22

    # Bottom Highlight Card: Grounding & Proof
    callout_box = (200, 680, WIDTH - 200, 890)
    draw.rounded_rectangle(callout_box, radius=12, fill=(15, 23, 42), outline=C_EMERALD, width=1)

    draw.text((230, 705), "CORE OPERATING PHILOSOPHY", fill=C_EMERALD, font=font_category)
    draw.text((230, 735), "Code Computes Every Dollar. AMD AI Explains and Recovers.", fill=C_WHITE, font=font_section_h)
    draw.text(
        (230, 775),
        "No LLM floating-point calculations. Zero hallucinated currency figures. All numbers validated against DuckDB ledger.",
        fill=C_MUTED, font=font_body
    )

    meta_items = [
        ("GitHub Repository", "https://github.com/labib-morol/paylens-amd"),
        ("Live Web App", "Streamlit Cloud (Global Deployment)"),
        ("Audit Status", "3-Gate Automated Verification 100% Passed"),
    ]
    mx = 230
    for lbl, val in meta_items:
        draw.text((mx, 825), lbl.upper(), fill=C_DIM, font=font_mono_sm)
        draw.text((mx, 845), val, fill=C_CYAN, font=get_font(14, bold=True))
        mx += 480

    draw_footer(draw, 1)
    return img

# -----------------------------------------------------------------------------
# Slide 2: The Multi-Rail Problem
# -----------------------------------------------------------------------------
def render_slide_02() -> Image.Image:
    img, draw = create_canvas()
    draw_header(draw, 2, "Market Reality & Operational Risk", "The Multi-Rail Reconciliation Problem", "Modern E-Commerce Operates on Disconnected, Asynchronous Financial Rails")

    # 3 Disconnected Pillars (Columns)
    cols = [
        (
            "1. DIGITAL STOREFRONTS",
            "Shopify · WooCommerce · Magento",
            C_CYAN,
            [
                "Asynchronous order dispatch webhooks",
                "Volatile order status flags (Fulfilled vs Pending)",
                "Unrecorded cancellations & split-shipment leaks",
                "High-velocity catalog updates hide silent drops",
            ]
        ),
        (
            "2. PAYMENT GATEWAYS",
            "Stripe · PayPal · bKash · SSLCommerz",
            C_EMERALD,
            [
                "Net payouts obscure individual order deductions",
                "Unrecorded processing fee tiers & rolling reserves",
                "3-day settlement delays create matching drift",
                "Silent authorization failures drop customer funds",
            ]
        ),
        (
            "3. CARRIER REMITTANCES",
            "DHL · FedEx · ExpressBD COD",
            C_AMBER,
            [
                "Cash-on-Delivery (COD) cash collected in the field",
                "Bundled PDF remittance statements with deductions",
                "Return surcharges & lost transit shortfalls",
                "Spreadsheet-based reconciliations happen weeks late",
            ]
        ),
    ]

    col_w = 560
    col_gap = 40
    start_x = 70
    start_y = 190
    col_h = 520

    for idx, (head, sub, color, points) in enumerate(cols):
        cx = start_x + idx * (col_w + col_gap)
        draw_card(draw, (cx, start_y, cx + col_w, start_y + col_h), title=None, accent_color=color, bg_color=C_PANEL, radius=14)

        # Category Header
        draw.text((cx + 30, start_y + 30), f"PILLAR 0{idx+1}", fill=color, font=font_category)
        draw.text((cx + 30, start_y + 55), head, fill=C_WHITE, font=get_font(22, bold=True))
        draw.text((cx + 30, start_y + 90), sub, fill=C_MUTED, font=font_body_sm)

        draw.line([(cx + 30, start_y + 125), (cx + col_w - 30, start_y + 125)], fill=C_BORDER, width=1)

        # Bullet items
        by = start_y + 155
        for pt in points:
            # Bullet icon
            draw.rounded_rectangle([(cx + 30, by + 4), (cx + 40, by + 14)], radius=2, fill=color)
            lines = wrap_text(pt, 50)
            for l in lines:
                draw.text((cx + 52, by), l, fill=C_WHITE, font=font_body)
                by += 26
            by += 18

    # Bottom Impact Callout Card
    bot_y = 750
    bot_h = 230
    draw.rounded_rectangle([(start_x, bot_y), (WIDTH - start_x, bot_y + bot_h)], radius=14, fill=C_PANEL_ALT, outline=C_CRIMSON if 'C_CRIMSON' in globals() else C_AMBER, width=2)
    draw.line([(start_x + 20, bot_y + 2), (WIDTH - start_x - 20, bot_y + 2)], fill=C_AMBER, width=3)

    # Left: Big Metric
    draw.text((start_x + 40, bot_y + 30), "REAL-WORLD AUDIT IMPACT", fill=C_AMBER, font=font_category)
    draw.text((start_x + 40, bot_y + 60), "$10,975.00", fill=C_WHITE, font=font_title_hero)
    draw.text((start_x + 40, bot_y + 140), "Silent Revenue Leakage Detected across 20 Synthetic Storefronts", fill=C_MUTED, font=font_subtitle)

    # Right: Contextual Breakdown
    rx = start_x + 780
    draw.text((rx, bot_y + 30), "WHERE THE MONEY SILENTLY LEAKS", fill=C_CYAN, font=font_category)

    leak_items = [
        ("Dispatched Unpaid Orders", "$1,255.00", "Orders delivered with zero gateway authorization record"),
        ("Carrier Remittance Shortfalls", "$175.00", "Under-settled COD remittances hidden in carrier PDF statements"),
        ("Stockout Margin Exposure", "$1,597.50", "Hero SKU stockouts projected via Holt-Winters forecast"),
    ]

    ly = bot_y + 65
    for l_title, l_amt, l_sub in leak_items:
        draw.text((rx, ly), f"• {l_title}:", fill=C_WHITE, font=get_font(15, bold=True))
        draw.text((rx + 290, ly), l_amt, fill=C_EMERALD, font=get_font(15, bold=True))
        draw.text((rx + 400, ly), f"({l_sub})", fill=C_MUTED, font=font_body_sm)
        ly += 45

    draw_footer(draw, 2)
    return img

# -----------------------------------------------------------------------------
# Slide 3: Core Philosophy — Code Computes. Model Explains.
# -----------------------------------------------------------------------------
def render_slide_03() -> Image.Image:
    img, draw = create_canvas()
    draw_header(draw, 3, "Architectural Foundation", "Core Philosophy: Code Computes. Model Explains.", "Strict Separation of Mathematical Truth and Language Model Reasoning")

    # 3 Stacked Horizontal Layer Cards
    layers = [
        (
            "LAYER 1: DETERMINISTIC ENGINE (DuckDB + statsmodels)",
            "MATHEMATICAL GROUND TRUTH",
            C_CYAN,
            [
                "100% of arithmetic calculations, relational joins, and statistical demand forecasts run in compiled code.",
                "DuckDB exact order matching + 30-minute fuzzy reconciliation joins between orders and payment webhooks.",
                "statsmodels Holt-Winters triple exponential smoothing forecasts stockout margin exposure deterministically.",
                "Zero floating-point hallucination. Zero probabilistic math. Output is verified ledger truth.",
            ]
        ),
        (
            "LAYER 2: NUMERIC GROUNDING SHIELD (Regex Guardrail)",
            "STRICT NUMERIC DEFENSE",
            C_EMERALD,
            [
                "Every single generated number and currency token must come verbatim from ALLOWED_NUMBERS evidence list.",
                "Validates dollar figures against DuckDB source rows (e.g. $1,255.00, $175.00, $1,597.50, quantities).",
                "If an unverified token appears, automatically triggers a 1-turn correction retry citing the ungrounded token.",
                "If correction fails, instantly reverts to deterministic template fallback to guarantee 100% financial integrity.",
            ]
        ),
        (
            "LAYER 3: REASONING LAYER (AMD TokenFactory & Google AI Studio)",
            "EXPLANATION & OUTREACH",
            C_INDIGO,
            [
                "AMD Radeon Cloud TokenFactory (DeepSeek-V4-Flash) and Google Gemma 4 REST API (gemma-4-31b-it).",
                "Translates complex multi-rail ledger discrepancies into actionable, audit-ready plain English summaries.",
                "Auto-drafts dispute messages tailored to merchant tone: Polite Reminder, VIP 5% Discount, Carrier Dispute.",
                "Model only explains and drafts. It never computes.",
            ]
        ),
    ]

    sy = 190
    lh = 230
    gap = 25

    for idx, (title, tag, color, bullets) in enumerate(layers):
        y0 = sy + idx * (lh + gap)
        draw_card(draw, (70, y0, WIDTH - 70, y0 + lh), title=None, accent_color=color, bg_color=C_PANEL, radius=14)

        # Header Pill
        draw.text((105, y0 + 24), f"STAGE 0{idx+1} · {tag}", fill=color, font=font_category)
        draw.text((105, y0 + 48), title, fill=C_WHITE, font=font_section_h)

        draw.line([(105, y0 + 85), (WIDTH - 105, y0 + 85)], fill=C_BORDER, width=1)

        # 4 Bullet Points in 2 Columns
        col1_pts = bullets[:2]
        col2_pts = bullets[2:]

        for c_idx, pts in enumerate([col1_pts, col2_pts]):
            bx = 105 + c_idx * 860
            by = y0 + 105
            for pt in pts:
                draw.rounded_rectangle([(bx, by + 4), (bx + 8, by + 12)], radius=2, fill=color)
                for line in wrap_text(pt, 75):
                    draw.text((bx + 18, by), line, fill=C_WHITE, font=font_body)
                    by += 24
                by += 10

    # Bottom Summary Banner
    b_y = 960
    draw.rounded_rectangle([(70, b_y), (WIDTH - 70, b_y + 45)], radius=8, fill=(15, 23, 42), outline=C_BORDER)
    summary_text = "Rule 1: LLMs explain discrepancies and draft correspondence. Code calculates every dollar. Zero exceptions."
    draw.text((95, b_y + 12), summary_text, fill=C_EMERALD, font=get_font(15, bold=True))

    draw_footer(draw, 3)
    return img

# -----------------------------------------------------------------------------
# Slide 4: Deterministic Detectors & Mathematical Formulations
# -----------------------------------------------------------------------------
def render_slide_04() -> Image.Image:
    img, draw = create_canvas()
    draw_header(draw, 4, "Algorithmic Precision", "Deterministic Detectors & Mathematical Formulations", "Four Specialized Engines Covering Every Dimension of Commerce Risk")

    # 4 Quadrants
    quads = [
        (
            "1. Dispatched Unpaid Matcher",
            "PAYMENT LEAKAGE DETECTOR",
            C_CYAN,
            "2-Pass Exact + 30-Minute Fuzzy Relational Join",
            "dispatched_orders.order_id = rail_payments.order_id\nOR (|order_created_at - payment_created_at| <= 30m)",
            "Dispatched orders with zero payment authorization record within matching window.",
            "Found $1,255.00 unpaid dispatched order (ORD-7819) at store merchant_441."
        ),
        (
            "2. Carrier Remittance Shortfall",
            "LOGISTICS AUDIT ENGINE",
            C_EMERALD,
            "Bundled PDF Parser & Net Remittance Balance Formulation",
            "Expected Net = cod_collected - courier_fee - surcharge\nShortfall = Expected Net - actual_settled",
            "Extracts consignment numbers from carrier settlement statements and joins to ledger.",
            "Detected $175.00 carrier under-settlement across consignments in ExpressBD PDF."
        ),
        (
            "3. Holt-Winters Stockout Forecaster",
            "INVENTORY RISK PREDICTOR",
            C_PURPLE,
            "Triple Additive Exponential Smoothing Demand Formulation",
            "Days of Cover = current_stock / daily_forecast\nLost Margin = (Lead Time - Days of Cover) * daily_forecast * unit_margin",
            "Projects stockout window and lost profit margin over supplier restocking lead time.",
            "Prioritizes Hero Blazer SKU-APX-01 ($1,597.50 margin at risk) under stockout objective."
        ),
        (
            "4. STL Seasonal Residual Anomaly Engine",
            "MACRO VOLUME SURVEILLANCE",
            C_AMBER,
            "LOESS Seasonal-Trend Decomposition Formulation",
            "Y_t = Trend_t + Seasonal_t + Residual_t\nFlag if |z_score(Residual_t)| > 2.2",
            "Separates true revenue anomalies from recurring weekly/monthly seasonal fluctuations.",
            "Provides merchant volume baseline context to prevent false operational alarms."
        ),
    ]

    qw = 860
    qh = 365
    coords = [
        (70, 190),
        (990, 190),
        (70, 580),
        (990, 580),
    ]

    for (head, tag, color, method, formula, desc, example), (qx, qy) in zip(quads, coords):
        draw_card(draw, (qx, qy, qx + qw, qy + qh), title=None, accent_color=color, bg_color=C_PANEL, radius=14)

        # Header
        draw.text((qx + 25, qy + 20), tag, fill=color, font=font_category)
        draw.text((qx + 25, qy + 44), head, fill=C_WHITE, font=get_font(21, bold=True))
        draw.text((qx + 25, qy + 76), f"Methodology: {method}", fill=C_MUTED, font=font_body_sm)

        # Formula Container
        fy = qy + 105
        fh = 75
        draw.rounded_rectangle([(qx + 25, fy), (qx + qw - 25, fy + fh)], radius=8, fill=(13, 19, 33), outline=C_BORDER)
        f_lines = formula.split("\n")
        f_cur_y = fy + 14
        for fl in f_lines:
            draw.text((qx + 40, f_cur_y), fl, fill=C_CYAN, font=font_mono_sm)
            f_cur_y += 24

        # Description
        dy = fy + fh + 18
        draw.text((qx + 25, dy), "Operational Logic:", fill=C_DIM, font=font_category)
        for l in wrap_text(desc, 80):
            dy += 20
            draw.text((qx + 25, dy), l, fill=C_WHITE, font=font_body_sm)

        # Real Proof Example
        ey = dy + 28
        draw.text((qx + 25, ey), "Audited Evidence:", fill=color, font=font_category)
        for l in wrap_text(example, 80):
            ey += 20
            draw.text((qx + 25, ey), l, fill=C_MUTED, font=font_body_sm)

    draw_footer(draw, 4)
    return img

# -----------------------------------------------------------------------------
# Slide 5: Ground Truth & Stress-Test Evaluation
# -----------------------------------------------------------------------------
def render_slide_05() -> Image.Image:
    img, draw = create_canvas()
    draw_header(draw, 5, "Empirical Validation", "Ground Truth & Stress-Test Evaluation", "Audited Evaluation on Adversarial Held-Out Synthetic Datasets (F1: 0.933)")

    # Left: Confusion Matrix & Key Metrics Card
    lx = 70
    ly = 190
    lw = 840
    lh = 770
    draw_card(draw, (lx, ly, lx + lw, ly + lh), title=None, accent_color=C_EMERALD, bg_color=C_PANEL, radius=14)

    draw.text((lx + 30, ly + 25), "HELD-OUT STRESS-TEST BENCHMARK", fill=C_EMERALD, font=font_category)
    draw.text((lx + 30, ly + 52), "30 Planted Anomaly Records", fill=C_WHITE, font=font_section_h)

    # 4 Big KPI Metric Boxes
    kpis = [
        ("F1 SCORE", "0.933", C_EMERALD),
        ("PRECISION", "0.933", C_CYAN),
        ("RECALL", "0.933", C_CYAN),
        ("TRUE POSITIVES", "28 / 30", C_WHITE),
    ]

    kw = 360
    kh = 100
    for idx, (k_lbl, k_val, k_col) in enumerate(kpis):
        kx = lx + 30 + (idx % 2) * (kw + 30)
        ky = ly + 110 + (idx // 2) * (kh + 20)
        draw.rounded_rectangle([(kx, ky), (kx + kw, ky + kh)], radius=10, fill=C_PANEL_ALT, outline=C_BORDER)
        draw.text((kx + 20, ky + 14), k_lbl, fill=C_DIM, font=font_category)
        draw.text((kx + 20, ky + 40), k_val, fill=k_col, font=font_metric_md)

    # Confusion Matrix Visual Table
    my = ly + 360
    draw.text((lx + 30, my), "AUDITED CONFUSION MATRIX BREAKDOWN", fill=C_WHITE, font=font_card_h)

    # Table Grid
    table_x = lx + 30
    table_y = my + 45
    draw.rounded_rectangle([(table_x, table_y), (table_x + 780, table_y + 240)], radius=10, fill=(13, 19, 33), outline=C_BORDER)

    # Header Row
    draw.text((table_x + 30, table_y + 20), "Classification", fill=C_DIM, font=font_category)
    draw.text((table_x + 280, table_y + 20), "Count", fill=C_DIM, font=font_category)
    draw.text((table_x + 400, table_y + 20), "Audit Description", fill=C_DIM, font=font_category)
    draw.line([(table_x + 20, table_y + 50), (table_x + 760, table_y + 50)], fill=C_BORDER, width=1)

    rows = [
        ("True Positives (TP)", "28", C_EMERALD, "Confirmed payment leakages and genuine stockouts captured"),
        ("False Positives (FP)", "2", C_AMBER, "Late settlements flagged for human operator review (e.g. SEPA)"),
        ("False Negatives (FN)", "2", C_DIM, "Complex multi-split consignments under fuzzy threshold"),
        ("True Negatives (TN)", "170", C_WHITE, "Clean settled orders correctly confirmed without alert spam"),
    ]

    ry = table_y + 65
    for c_lbl, c_cnt, c_col, c_desc in rows:
        draw.text((table_x + 30, ry), c_lbl, fill=c_col, font=get_font(14, bold=True))
        draw.text((table_x + 280, ry), c_cnt, fill=C_WHITE, font=font_mono)
        draw.text((table_x + 400, ry), c_desc, fill=C_MUTED, font=font_body_sm)
        ry += 44

    # Bottom Note
    draw.text((lx + 30, ly + lh - 50), "Stress test generated with seed 1337 and adversarial noise injection.", fill=C_DIM, font=font_mono_sm)

    # Right: Documented Edge Case & Transparency Card
    rx = 940
    rw = 910
    draw_card(draw, (rx, ly, rx + rw, ly + lh), title=None, accent_color=C_AMBER, bg_color=C_PANEL, radius=14)

    draw.text((rx + 35, ly + 25), "DOCUMENTED EDGE CASE & AUDIT TRANSPARENCY", fill=C_AMBER, font=font_category)
    draw.text((rx + 35, ly + 52), "Transparent Disclosure: 48h SEPA Wire Delay", fill=C_WHITE, font=font_section_h)

    edge_box = (rx + 35, ly + 105, rx + rw - 35, ly + 375)
    draw.rounded_rectangle(edge_box, radius=10, fill=C_AMBER_BG, outline=C_AMBER, width=1)

    draw.text((rx + 55, ly + 125), "SCENARIO: ORD-FAIL-4303 ($850.00 European Wire)", fill=C_AMBER, font=get_font(16, bold=True))
    sepa_desc = [
        "A legitimate business customer in Germany sent a SEPA bank wire of $850.00.",
        "The merchant dispatched immediately, but European interbank clearing took 48 hours.",
        "Settled 48h later (exceeding 30-min window), so the detector flagged it as leakage.",
        "Outcome: Transparently documented as 1 of the 2 False Positives in our stress-test split.",
    ]
    sy = ly + 165
    for s in sepa_desc:
        for line in wrap_text(s, 72):
            draw.text((rx + 55, sy), line, fill=C_WHITE, font=font_body_sm)
            sy += 22
        sy += 6

    # Human-in-the-Loop Philosophy
    draw.text((rx + 35, ly + 405), "WHY TRANSPARENCY WINS IN ENTERPRISE FINANCE", fill=C_CYAN, font=font_card_h)
    why_points = [
        ("No Fabricated 100% Accuracy", "Competitors claim 100% precision by hiding delayed wires under the rug. PayLens transparently exposes the edge cases."),
        ("1-Click Human Triage", "In the Deal Desk Inspector, operators can review the wire transfer timestamp and clear the flag in a single click."),
        ("Immutable Audit Trail", "All decisions create immutable SHA-256 receipts logged with timestamp, user ID, and model grounding trace."),
    ]

    py = ly + 445
    for p_title, p_body in why_points:
        draw.text((rx + 35, py), f"• {p_title}:", fill=C_WHITE, font=get_font(15, bold=True))
        for l in wrap_text(p_body, 75):
            py += 22
            draw.text((rx + 50, py), l, fill=C_MUTED, font=font_body_sm)
        py += 18

    draw_footer(draw, 5)
    return img

# -----------------------------------------------------------------------------
# Slide 6: Authentic Hardware Telemetry & Scaling
# -----------------------------------------------------------------------------
def render_slide_06() -> Image.Image:
    img, draw = create_canvas()
    draw_header(draw, 6, "Performance & Provenance", "Authentic Hardware Telemetry & Scaling", "Measured Dual-Engine Benchmarks on AMD Radeon Cloud & Google AI Studio")

    # Left: AMD Radeon Cloud TokenFactory (Concurrency Scaling)
    lx = 70
    ly = 190
    lw = 960
    lh = 770
    draw_card(draw, (lx, ly, lx + lw, ly + lh), title=None, accent_color=C_EMERALD, bg_color=C_PANEL, radius=14)

    draw.text((lx + 35, ly + 25), "HARDWARE: AMD RADEON CLOUD TOKENFACTORY", fill=C_EMERALD, font=font_category)
    draw.text((lx + 35, ly + 52), "DeepSeek-V4-Flash Serving Telemetry", fill=C_WHITE, font=font_section_h)
    draw.text((lx + 35, ly + 90), "Real live concurrency requests measured against AMD cloud endpoints", fill=C_MUTED, font=font_body_sm)

    # 3 Concurrency Tiers Cards (using verified benchmark metrics)
    tiers = [
        ("Concurrency Tier 1 (Sequential)", "16.8 tok/s", "7.22s TTFT · 23.02s Latency", 16.8, C_CYAN),
        ("Concurrency Tier 4 (Concurrent Burst)", "45.5 tok/s", "6.97s TTFT · 24.08s Latency", 45.5, C_EMERALD),
        ("Concurrency Tier 8 (High Concurrency)", "62.9 tok/s", "8.32s TTFT · 20.39s Latency", 62.9, C_PURPLE),
    ]

    ty = ly + 130
    for t_name, tok_s, ttft_lat, val, col in tiers:
        draw.rounded_rectangle([(lx + 35, ty), (lx + lw - 35, ty + 120)], radius=10, fill=C_PANEL_ALT, outline=C_BORDER)
        draw.line([(lx + 45, ty + 1), (lx + lw - 45, ty + 1)], fill=col, width=2)

        draw.text((lx + 55, ty + 16), t_name, fill=C_WHITE, font=get_font(16, bold=True))
        draw.text((lx + 55, ty + 46), ttft_lat, fill=C_MUTED, font=font_body_sm)

        # Big throughput metric
        draw.text((lx + lw - 250, ty + 20), tok_s, fill=col, font=font_metric_md)
        draw.text((lx + lw - 250, ty + 70), "THROUGHPUT", fill=C_DIM, font=font_category)

        # Mini visual bar
        bar_w = int((val / 70.0) * 360)
        draw.rounded_rectangle([(lx + 55, ty + 85), (lx + 55 + bar_w, ty + 97)], radius=6, fill=col)
        draw.rounded_rectangle([(lx + 55 + bar_w, ty + 85), (lx + 55 + 360, ty + 97)], radius=6, fill=(20, 26, 40))

        ty += 140

    # Grounding Pass Rate Callout
    callout_box = (lx + 35, ty + 10, lx + lw - 35, ly + lh - 35)
    draw.rounded_rectangle(callout_box, radius=10, fill=(15, 35, 28), outline=C_EMERALD, width=1)
    draw.text((lx + 55, ty + 28), "100% FIRST-PASS MODEL GROUNDING PASS RATE", fill=C_EMERALD, font=get_font(16, bold=True))
    draw.text((lx + 55, ty + 56), "16 of 16 live requests passed numeric regex validation on first pass with zero hallucinations and zero template fallbacks.", fill=C_WHITE, font=font_body_sm)

    # Right: Dual-Engine & Self-Hosting MI300X Card
    rx = 1060
    rw = 790
    draw_card(draw, (rx, ly, rx + rw, ly + lh), title=None, accent_color=C_CYAN, bg_color=C_PANEL, radius=14)

    draw.text((rx + 35, ly + 25), "DUAL-ENGINE ARCHITECTURE & ON-PREM", fill=C_CYAN, font=font_category)
    draw.text((rx + 35, ly + 52), "Google Gemma 4 & AMD MI300X", fill=C_WHITE, font=font_section_h)

    # Google Gemma 4 Card
    gemma_box = (rx + 35, ly + 110, rx + rw - 35, ly + 310)
    draw.rounded_rectangle(gemma_box, radius=10, fill=C_PANEL_ALT, outline=C_BORDER)
    draw.text((rx + 55, ly + 130), "GOOGLE GEMMA 4 REST API BENCHMARK", fill=C_CYAN, font=get_font(16, bold=True))
    draw.text((rx + 55, ly + 160), "Model: gemma-4-31b-it · Direct AI Studio Integration", fill=C_MUTED, font=font_body_sm)

    gemma_stats = [
        ("COMPLETED", "2 of 2 (100%)"),
        ("FIRST-PASS GROUNDING", "100% Pass"),
        ("FALLBACKS", "0 (0.0%)"),
        ("ERRORS", "0"),
    ]
    gx = rx + 55
    gy = ly + 205
    for s_lbl, s_val in gemma_stats:
        draw.text((gx, gy), s_lbl, fill=C_DIM, font=font_category)
        draw.text((gx, gy + 22), s_val, fill=C_WHITE, font=get_font(15, bold=True))
        gx += 165

    # Dedicated AMD Instinct MI300X Recipe Box
    mi_box = (rx + 35, ly + 340, rx + rw - 35, ly + lh - 35)
    draw.rounded_rectangle(mi_box, radius=10, fill=(20, 24, 38), outline=C_PURPLE, width=1)
    draw.text((rx + 55, ly + 365), "DEDICATED AMD INSTINCT MI300X DEPLOYMENT", fill=C_PURPLE, font=get_font(16, bold=True))
    draw.text((rx + 55, ly + 395), "Self-Hosting Recipe provided in paylens-amd for enterprise air-gapped finance:", fill=C_MUTED, font=font_body_sm)

    code_lines = [
        "docker run --device=/dev/kfd --device=/dev/dri \\",
        "  -v /models:/models -p 8000:8000 \\",
        "  vllm/vllm-openai:rocm6.2_mi300x \\",
        "  --model /models/DeepSeek-V4-Flash \\",
        "  --tensor-parallel-size 1 \\",
        "  --max-model-len 8192",
    ]
    cy = ly + 435
    for cl in code_lines:
        draw.text((rx + 55, cy), cl, fill=C_CYAN, font=font_mono_sm)
        cy += 24

    draw_footer(draw, 6)
    return img

# -----------------------------------------------------------------------------
# Slide 7: Human-in-the-Loop Deal Desk & Global Roadmap
# -----------------------------------------------------------------------------
def render_slide_07() -> Image.Image:
    img, draw = create_canvas()
    draw_header(draw, 7, "Operational Delivery & Vision", "Human-in-the-Loop Deal Desk & Global Roadmap", "Empowering Finance Teams from Local Pilots to Global Scale")

    # Left: Deal Desk Features
    lx = 70
    ly = 190
    lw = 860
    lh = 570
    draw_card(draw, (lx, ly, lx + lw, ly + lh), title=None, accent_color=C_EMERALD, bg_color=C_PANEL, radius=14)

    draw.text((lx + 35, ly + 25), "PRODUCTION DEAL DESK CAPABILITIES", fill=C_EMERALD, font=font_category)
    draw.text((lx + 35, ly + 52), "Autonomous Triage & 1-Click Action", fill=C_WHITE, font=font_section_h)

    features = [
        ("Simulated One-Click Action Approval", "Operators approve actions with immutable SHA-256 receipts logged to audit trail."),
        ("Multi-Channel Dispute Receipts", "Live WhatsApp and Email dispute receipts with verified DuckDB evidence attachments."),
        ("Multi-Tone Action Generation", "Auto-drafts Polite Reminders, VIP 5% Instant-Pay Discounts, Carrier Disputes, or Expedited POs."),
        ("Dynamic Objective Steering", "Re-ranks queue on the fly: switch from Urgent Cash Recovery to Prevent Stockouts in 1 click."),
    ]

    fy = ly + 110
    for f_title, f_desc in features:
        draw.rounded_rectangle([(lx + 35, fy), (lx + lw - 35, fy + 95)], radius=8, fill=C_PANEL_ALT, outline=C_BORDER)
        draw.text((lx + 55, fy + 14), f_title, fill=C_WHITE, font=get_font(16, bold=True))
        sub_y = fy + 42
        for line in wrap_text(f_desc, 72):
            draw.text((lx + 55, sub_y), line, fill=C_MUTED, font=font_body_sm)
            sub_y += 20
        fy += 112

    # Right: Global Multi-Rail Roadmap
    rx = 970
    rw = 880
    draw_card(draw, (rx, ly, rx + rw, ly + lh), title=None, accent_color=C_CYAN, bg_color=C_PANEL, radius=14)

    draw.text((rx + 35, ly + 25), "GLOBAL MULTI-RAIL EXPANSION", fill=C_CYAN, font=font_category)
    draw.text((rx + 35, ly + 52), "Architected for Global Commerce Rails", fill=C_WHITE, font=font_section_h)

    roadmap = [
        ("Emerging Market Instant Rails", "Brazil Pix, India UPI, Kenya M-Pesa", "Connecting sub-second settlement ledgers to real-time e-commerce dispatch queues."),
        ("Real-Time Streaming Engine", "Kafka + ClickHouse Architecture", "Replacing nightly batch jobs with microsecond continuous reconciliation."),
        ("Enterprise ERP Connectors", "SAP S/4HANA · Oracle NetSuite", "Direct two-way accounting sync for enterprise treasury and ledger closing."),
        ("Autonomous Carrier Dispute Filing", "Carrier Webhooks & Automated Claims", "Filing courier shortfall claims automatically with attached PDF evidence proofs."),
    ]

    ry = ly + 110
    for r_title, r_sub, r_desc in roadmap:
        draw.rounded_rectangle([(rx + 35, ry), (rx + rw - 35, ry + 95)], radius=8, fill=C_PANEL_ALT, outline=C_BORDER)
        draw.text((rx + 55, ry + 14), r_title, fill=C_WHITE, font=get_font(16, bold=True))
        draw.text((rx + 360, ry + 15), r_sub, fill=C_CYAN, font=font_mono_sm)
        sub_y = ry + 42
        for line in wrap_text(r_desc, 72):
            draw.text((rx + 55, sub_y), line, fill=C_MUTED, font=font_body_sm)
            sub_y += 20
        ry += 112

    # Grand Finale Banner Across Bottom
    fin_y = 790
    fin_h = 190
    draw.rounded_rectangle([(lx, fin_y), (WIDTH - lx, fin_y + fin_h)], radius=14, fill=(15, 23, 42), outline=C_EMERALD, width=2)
    draw.line([(lx + 20, fin_y + 2), (WIDTH - lx - 20, fin_y + 2)], fill=C_EMERALD, width=3)

    draw.text((lx + 45, fin_y + 28), "ENTERPRISE FINANCE MANIFESTO", fill=C_EMERALD, font=font_category)
    draw.text(
        (lx + 45, fin_y + 60),
        "Deterministic arithmetic. Grounded AMD intelligence. Built for enterprise finance.",
        fill=C_WHITE, font=get_font(28, bold=True)
    )
    draw.text(
        (lx + 45, fin_y + 115),
        "PayLens brings mathematical truth back to multi-rail commerce. Every dollar calculated in code. Every action explained on AMD.",
        fill=C_MUTED, font=get_font(18, bold=False)
    )

    draw_footer(draw, 7)
    return img

# -----------------------------------------------------------------------------
# Main Orchestrator & PDF Compilation
# -----------------------------------------------------------------------------
def main():
    print("=" * 70)
    print("PAYLENS 7-SLIDE INSTITUTIONAL PITCH DECK GENERATOR")
    print("=" * 70)

    renderers = [
        (1, "Slide 1: Title & Track", render_slide_01),
        (2, "Slide 2: The Multi-Rail Reconciliation Problem", render_slide_02),
        (3, "Slide 3: Core Philosophy — Code Computes. Model Explains.", render_slide_03),
        (4, "Slide 4: Deterministic Detectors & Formulations", render_slide_04),
        (5, "Slide 5: Ground Truth & Stress-Test Evaluation", render_slide_05),
        (6, "Slide 6: Authentic Hardware Telemetry & Scaling", render_slide_06),
        (7, "Slide 7: Human-in-the-Loop Deal Desk & Global Roadmap", render_slide_07),
    ]

    slide_images: List[Image.Image] = []

    for idx, name, render_func in renderers:
        print(f"Generating {name}...")
        img = render_func()
        slide_images.append(img)

        # Save individual PNG slide
        png_path = SLIDES_DIR / f"slide_{idx:02d}.png"
        img.save(png_path, format="PNG", optimize=True)
        print(f"  -> Saved {png_path} ({os.path.getsize(png_path) / 1024:.1f} KB)")

    # Compile all 7 slides into a single PDF presentation
    print("\nCompiling 7-slide PDF presentation...")
    first_slide = slide_images[0]
    first_slide.save(
        OUTPUT_PDF,
        format="PDF",
        save_all=True,
        append_images=slide_images[1:],
        resolution=100.0,
    )

    pdf_size_mb = os.path.getsize(OUTPUT_PDF) / (1024 * 1024)
    print(f"[SUCCESS] Multi-page pitch deck compiled: {OUTPUT_PDF} ({pdf_size_mb:.2f} MB)")
    print("=" * 70)


if __name__ == "__main__":
    main()
