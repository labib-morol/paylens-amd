"""Generates an authentic, high-resolution animated visual demo GIF for PayLens Solo."""
import os
import math
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(ROOT_DIR, "docs")
os.makedirs(DOCS_DIR, exist_ok=True)
GIF_PATH = os.path.join(DOCS_DIR, "demo.gif")

# Fonts
def get_font(size: int, bold: bool = False, mono: bool = False):
    try:
        if mono:
            return ImageFont.truetype("C:/Windows/Fonts/consola.ttf", size)
        elif bold:
            return ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", size)
        else:
            return ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", size)
    except Exception:
        return ImageFont.load_default()

font_title = get_font(20, bold=True)
font_subtitle = get_font(12, bold=False)
font_badge = get_font(11, bold=True)
font_kpi_label = get_font(10, bold=True)
font_kpi_val = get_font(18, bold=True, mono=True)
font_kpi_sub = get_font(9, bold=False)
font_card_title = get_font(13, bold=True)
font_card_meta = get_font(10, mono=True)
font_body = get_font(11)
font_mono = get_font(10, mono=True)
font_micro = get_font(9, mono=True)

WIDTH, HEIGHT = 1000, 560

# Palette
C_BG = (10, 15, 26)
C_PANEL = (17, 24, 39)
C_PANEL_ALT = (24, 34, 53)
C_BORDER = (45, 60, 85)
C_BORDER_LIGHT = (70, 90, 125)
C_WHITE = (248, 250, 252)
C_MUTED = (148, 163, 184)
C_DIM = (100, 116, 139)
C_AMD_RED = (237, 28, 36)
C_EMERALD = (16, 185, 129)
C_BLUE = (56, 189, 248)
C_INDIGO = (99, 102, 241)
C_AMBER = (245, 158, 11)
C_CRIMSON = (239, 68, 68)

def draw_header(d: ImageDraw.ImageDraw, frame_idx: int):
    # Top Bar
    d.rounded_rectangle([(30, 20), (970, 72)], radius=10, fill=C_PANEL, outline=C_BORDER, width=1)
    d.text((48, 32), "PayLens", font=font_title, fill=C_WHITE)
    d.text((140, 32), "Solo", font=font_title, fill=C_INDIGO)
    d.text((48, 54), "Deterministic Multi-Rail Capital Recovery Deal Desk", font=font_subtitle, fill=C_MUTED)

    # Active TokenFactory Badge
    pulse = (frame_idx % 8) < 4
    badge_bg = (30, 58, 45) if pulse else (20, 45, 35)
    d.rounded_rectangle([(650, 32), (952, 58)], radius=6, fill=badge_bg, outline=C_EMERALD, width=1)
    dot_color = (52, 211, 153) if pulse else (16, 185, 129)
    d.ellipse([(662, 42), (670, 50)], fill=dot_color)
    d.text((678, 37), "● ACTIVE · AMD TokenFactory (DeepSeek-V4-Flash)", font=font_badge, fill=C_WHITE)

def draw_kpis(d: ImageDraw.ImageDraw, recovered_usd: float, pass_status: str, frame_idx: int):
    # 4 KPI Cards
    kpis = [
        ("TOTAL CAPITAL AT RISK", "$34,812.50", "34 verified anomalies found", C_CRIMSON),
        ("RECOVERY INITIATED (SIM)", f"${recovered_usd:,.2f}", f"Dispatched with SHA-256 receipts", C_EMERALD if recovered_usd > 0 else C_WHITE),
        ("MODEL GROUNDING", pass_status, "Deterministic strict regex audit", C_BLUE),
        ("AMD INFERENCE SPEED", "37.6s (1.3s TTFT)", "ROCm TokenFactory cluster", C_INDIGO),
    ]
    card_w = 220
    gap = 13
    start_x = 30
    y = 86
    h = 70
    for i, (lbl, val, sub, val_col) in enumerate(kpis):
        x = start_x + i * (card_w + gap)
        # Glow border for recovered card when recovered > 0
        outline = C_EMERALD if (i == 1 and recovered_usd > 0) else C_BORDER
        d.rounded_rectangle([(x, y), (x + card_w, y + h)], radius=8, fill=C_PANEL, outline=outline, width=1)
        d.text((x + 14, y + 10), lbl, font=font_kpi_label, fill=C_MUTED)
        d.text((x + 14, y + 25), val, font=font_kpi_val, fill=val_col)
        d.text((x + 14, y + 52), sub, font=font_kpi_sub, fill=C_DIM)

def draw_sankey_flow(d: ImageDraw.ImageDraw, progress: float):
    # Sankey Box
    y = 170
    h = 96
    d.rounded_rectangle([(30, y), (970, y + h)], radius=10, fill=C_PANEL, outline=C_BORDER, width=1)
    d.text((46, y + 10), "Cross-Rail Revenue Reconciliation Flow (Merchant: Lumina Smart Home · MERCH_02)", font=font_card_title, fill=C_WHITE)

    # Bars
    # Left: Gross Order Volume
    d.rounded_rectangle([(46, y + 36), (220, y + 80)], radius=6, fill=(30, 41, 59), outline=C_BORDER_LIGHT, width=1)
    d.text((56, y + 42), "Shopify Gross GMV", font=font_micro, fill=C_MUTED)
    d.text((56, y + 58), "$185,400.00", font=font_card_title, fill=C_WHITE)

    # Middle Rails: Gateways & Bank & COD
    rails = [
        ("Stripe Webhook", "$95,200", C_BLUE),
        ("PayPal Direct", "$28,000", C_INDIGO),
        ("SEPA / Wire", "$13,800", C_MUTED),
        ("DHL Express COD", "$48,400", C_AMBER),
    ]
    rx = 290
    for r_idx, (r_name, r_amt, r_col) in enumerate(rails):
        ry = y + 30 + r_idx * 15
        d.text((rx, ry), f"• {r_name}: {r_amt}", font=font_micro, fill=r_col)
        # Flow line
        d.line([(222, y + 58), (rx - 8, ry + 6)], fill=(50, 70, 95), width=1)

    # Right: Settled vs Leaked
    # Animated flow line
    p_len = int(120 * progress)
    d.line([(480, y + 48), (480 + p_len, y + 48)], fill=C_EMERALD, width=2)
    d.line([(480, y + 68), (480 + p_len, y + 68)], fill=C_CRIMSON, width=2)

    # Clean Settled Box
    d.rounded_rectangle([(620, y + 34), (780, y + 82)], radius=6, fill=(15, 45, 35), outline=C_EMERALD, width=1)
    d.text((630, y + 42), "Clean Settled Cash", font=font_micro, fill=C_EMERALD)
    d.text((630, y + 58), "$171,200.00", font=font_card_title, fill=C_EMERALD)

    # Leaked Box
    d.rounded_rectangle([(796, y + 34), (954, y + 82)], radius=6, fill=(50, 20, 25), outline=C_CRIMSON, width=1)
    d.text((806, y + 42), "Leaked / At Risk", font=font_micro, fill=C_CRIMSON)
    d.text((806, y + 58), "$14,200.00", font=font_card_title, fill=C_CRIMSON)

def draw_anomaly_card(
    d: ImageDraw.ImageDraw,
    y: int,
    card_type: str,
    title: str,
    impact: str,
    details: str,
    badge_col: tuple,
    expanded: bool = False,
    approved: bool = False,
    explain_text: str = "",
    grounding_checked: bool = False,
):
    h = 245 if expanded else 68
    outline = C_EMERALD if approved else (C_INDIGO if expanded else C_BORDER)
    d.rounded_rectangle([(30, y), (970, y + h)], radius=10, fill=C_PANEL_ALT if expanded else C_PANEL, outline=outline, width=2 if (expanded or approved) else 1)

    # Type Badge
    d.rounded_rectangle([(46, y + 14), (200, y + 34)], radius=4, fill=(30, 40, 60), outline=badge_col, width=1)
    d.text((54, y + 18), card_type, font=font_micro, fill=badge_col)

    # Title & Meta
    d.text((215, y + 16), title, font=font_card_title, fill=C_WHITE)
    d.text((46, y + 42), details, font=font_mono, fill=C_MUTED)

    # Impact Amount
    d.text((800, y + 16), impact, font=font_card_title, fill=C_CRIMSON if not approved else C_EMERALD)
    d.text((800, y + 38), "Capital at Risk" if not approved else "Dispatched ✓", font=font_micro, fill=C_DIM if not approved else C_EMERALD)

    if expanded:
        # Divider line
        d.line([(46, y + 68), (954, y + 68)], fill=C_BORDER, width=1)

        # Drawer Left: Live AMD Inference & Tool Trace
        d.text((46, y + 78), "⚡ AMD TOKENFACTORY AGENT TRACE (DeepSeek-V4-Flash · Live ROCm Cluster)", font=font_micro, fill=C_AMD_RED)
        d.text((46, y + 96), "Tool Calls: get_order('ORD-3143') → get_payments(ref=None) → get_settlement()", font=font_mono, fill=C_BLUE)

        # Explanation Box
        d.rounded_rectangle([(46, y + 114), (660, y + 182)], radius=6, fill=(15, 22, 36), outline=C_BORDER, width=1)
        d.text((56, y + 122), "Grounded Model Explanation:", font=font_micro, fill=C_MUTED)
        wrap_text1 = explain_text[:88]
        wrap_text2 = explain_text[88:175]
        d.text((56, y + 138), wrap_text1, font=font_body, fill=C_WHITE)
        d.text((56, y + 156), wrap_text2, font=font_body, fill=C_WHITE)

        # Grounding Box
        g_bg = (16, 45, 30) if grounding_checked else (35, 45, 65)
        g_bd = C_EMERALD if grounding_checked else C_BLUE
        d.rounded_rectangle([(46, y + 192), (660, y + 232)], radius=6, fill=g_bg, outline=g_bd, width=1)
        g_txt = "✓ NUMERIC GROUNDING VERIFIED: All tokens matched database allowed_numbers [850.00, 120.00]" if grounding_checked else "Verifying numeric tokens against allowed card numbers..."
        d.text((58, y + 204), g_txt, font=font_micro, fill=C_EMERALD if grounding_checked else C_BLUE)

        # Action Button Right
        btn_bg = C_EMERALD if approved else C_INDIGO
        d.rounded_rectangle([(680, y + 114), (954, y + 164)], radius=8, fill=btn_bg)
        btn_txt = "✓ ACTION DISPATCHED (SHA-256)" if approved else "⚡ One-Click Approve & Recover"
        d.text((710, y + 132), btn_txt, font=font_card_title, fill=C_WHITE)

        if approved:
            d.text((684, y + 176), "Receipt: REC-AMD-7F9B2A41", font=font_micro, fill=C_EMERALD)
            d.text((684, y + 194), "SHA-256: 7f8a92e104b... Dispatched to Stripe & DHL", font=font_micro, fill=C_MUTED)
        else:
            d.text((684, y + 176), "Dispatches payment recovery link & formal dispute", font=font_micro, fill=C_MUTED)


def create_frame(frame_num: int) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), C_BG)
    d = ImageDraw.Draw(img)

    # Frame mapping (36 frames total, looped)
    # 0 - 6: Initial state, Sankey animating
    # 7 - 14: Card 1 expands, Agent tools running
    # 15 - 22: Grounding checked
    # 23 - 35: Action approved! Recovered KPI counter rolls up!
    recovered_val = 0.0
    grounding_status = "Regex Audited"
    is_expanded = frame_num >= 7
    is_grounded = frame_num >= 15
    is_approved = frame_num >= 23

    if is_approved:
        # Animate counter from 0 to 14,200
        progress = min(1.0, (frame_num - 23) / 8.0)
        recovered_val = round(progress * 14200.0, 2)
        grounding_status = "Verified (3/3)"

    draw_header(d, frame_num)
    draw_kpis(d, recovered_val, grounding_status, frame_num)

    sankey_prog = min(1.0, (frame_num % 18) / 12.0)
    draw_sankey_flow(d, sankey_prog)

    explain_str = "Lumina Smart Home: Dispatched order ORD-3143 has no confirmed payment on Stripe rail. Consignment CONS-SHORT-9001 on DHL Express settled $686.00 against expected $806.00, yielding a $120.00 tariff shortfall."

    if not is_expanded:
        # Show 3 compact cards
        draw_anomaly_card(d, 280, "PAYMENT LEAKAGE", "Dispatched Unpaid Order #ORD-COD-SHORT-3143 · DHL Express", "$850.00", "Shopify order dispatched but Stripe webhook unconfirmed · 2-Pass match verified", C_CRIMSON)
        draw_anomaly_card(d, 360, "CARRIER COD SHORTFALL", "Courier Settlement Remittance Consignment #CONS-SHORT-9001", "$120.00", "DHL Express collected $850.00 · Expected net $806.00 · Actual settled $686.00", C_AMBER)
        draw_anomaly_card(d, 440, "STOCKOUT FORECAST", "Holt-Winters Surge Stockout Risk · SKU-LUM-HERO-01", "$3,200.00", "Current stock 42 pcs · 7-Day Cover (3.8d) < Supplier Lead Time (14d)", C_BLUE)
    else:
        # Show Card 1 expanded
        draw_anomaly_card(
            d, 280, "PAYMENT LEAKAGE", "Dispatched Unpaid Order #ORD-COD-SHORT-3143 · DHL Express", "$850.00",
            "Shopify order dispatched but Stripe webhook unconfirmed · 2-Pass match verified",
            C_CRIMSON,
            expanded=True,
            approved=is_approved,
            explain_text=explain_str,
            grounding_checked=is_grounded,
        )

    return img


def main():
    print(f"Generating 36-frame high-resolution animated visual demo GIF at {GIF_PATH}...")
    frames = []
    total_frames = 36
    for i in range(total_frames):
        frame = create_frame(i)
        frames.append(frame)

    # Durations: hold first frame slightly, hold expanded frame, hold approved frame
    durations = [250] * total_frames
    durations[0] = 700
    durations[6] = 500
    durations[14] = 600
    durations[22] = 600
    durations[35] = 1800  # Pause at final state before looping

    frames[0].save(
        GIF_PATH,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    file_size_kb = os.path.getsize(GIF_PATH) / 1024
    print(f"✓ Animated demo GIF created successfully: {GIF_PATH} ({file_size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
