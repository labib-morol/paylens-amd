#!/usr/bin/env python3
"""PayLens Demo Video Patch Script.

Re-renders Scene 01 with balanced math ($10,975.00 network vs $4,052.50 Store 01),
motion-graphics lower-third subtitle container pill, and splices it back with
the rest of the demo into docs/submission_demo_final.mp4.
"""

import os
import sys
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
os.chdir(ROOT_DIR)

input_video = "user_uploaded_files/ttl=63d/user_uploaded/submission_demo_animated.mp4"
if not os.path.exists(input_video):
    input_video = "submission_demo_animated.mp4"
if not os.path.exists(input_video):
    input_video = "docs/demo.mp4"

if not os.path.exists(input_video):
    print(f"Error: Input video not found at {input_video}")
    sys.exit(1)

os.makedirs("artifacts/video_patch", exist_ok=True)
os.makedirs("docs", exist_ok=True)

audio_file = "artifacts/video_patch/audio.aac"
print(f"Extracting audio from {input_video}...")
subprocess.run(f'ffmpeg -y -i "{input_video}" -vn -acodec copy "{audio_file}"', shell=True, check=True)

WIDTH, HEIGHT = 1920, 1080

def get_font(size: int, bold: bool = False):
    candidates = []
    if bold:
        candidates = [
            "segoeuib.ttf", "arialbd.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"
        ]
    else:
        candidates = [
            "segoeui.ttf", "arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/dejavu/DejaVuSans.ttf"
        ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size)
        except Exception:
            continue
    return ImageFont.load_default()

def create_scene1_frame():
    im = Image.new("RGB", (WIDTH, HEIGHT), "#0B0F17")
    draw = ImageDraw.Draw(im)
    
    font_large = get_font(44, bold=True)
    font_mid_bold = get_font(26, bold=True)
    font_mid = get_font(22)
    font_sub = get_font(18)
    font_badge = get_font(16, bold=True)

    # Header
    draw.text((100, 70), "01 — THE PROBLEM", fill="#38BDF8", font=font_badge)
    draw.text((100, 105), "Messages. Payouts. Discrepancies.", fill="#F8FAFC", font=font_large)
    draw.text((100, 170), "Shopify says sales are booming. Stripe sent a payout. But did every dollar actually settle?", fill="#94A3B8", font=font_mid)
    
    # Left Box: Disconnected Rails
    draw.rounded_rectangle([100, 240, 920, 880], radius=16, fill="#111827", outline="#1E293B", width=2)
    draw.text((140, 275), "DISCONNECTED COMMERCE RAILS", fill="#10B981", font=font_badge)
    
    rails = [
        ("Shopify & WooCommerce", "Digital storefront cart checkout; inventory de-allocated before settlement."),
        ("Stripe, PayPal & SEPA", "Payment gateways operating on independent net-term settlement windows."),
        ("DHL & FedEx Courier COD", "Cash-on-delivery remittances with tariff deductions and hidden fee creep."),
        ("Warehouse Inventory", "High-margin hero SKUs stockout before supplier reorder lead time.")
    ]
    y_rail = 330
    for r_title, r_desc in rails:
        draw.text((140, y_rail), f"•  {r_title}", fill="#F8FAFC", font=font_mid_bold)
        draw.text((140, y_rail + 38), r_desc, fill="#94A3B8", font=font_sub)
        y_rail += 125

    # Right Box: Reconciled Financials
    draw.rounded_rectangle([1000, 240, 1820, 880], radius=16, fill="#111827", outline="#1E293B", width=2)
    draw.rounded_rectangle([1040, 275, 1420, 310], radius=8, fill="#1E293B")
    draw.text((1055, 283), "SYNTHETIC DEMONSTRATION DATASET", fill="#38BDF8", font=font_badge)
    
    draw.text((1040, 335), "20-STORE NETWORK TOTAL", fill="#94A3B8", font=font_sub)
    draw.text((1040, 370), "$10,975.00", fill="#F8FAFC", font=font_large)
    draw.text((1040, 430), "Store 01 (Apex Global) Immediate Shortfall: $4,052.50", fill="#10B981", font=font_mid_bold)
    
    draw.line([(1040, 480), (1780, 480)], fill="#1E293B", width=2)
    
    categories = [
        ("Dispatched Unpaid Orders", "$2,280.00", "Hard ledger mismatches on Stripe, SEPA & COD"),
        ("Carrier COD Remittance Shortfalls", "$175.00", "Under-settled courier cash collections"),
        ("Forecasted 7-Day Stockout Margin", "$1,597.50", "High-margin revenue loss from supplier lead time")
    ]
    y_cat = 510
    for c_title, c_val, c_sub in categories:
        draw.text((1040, y_cat), c_title, fill="#E2E8F0", font=font_mid)
        draw.text((1600, y_cat), c_val, fill="#F8FAFC", font=font_mid_bold)
        draw.text((1040, y_cat + 32), c_sub, fill="#64748B", font=font_sub)
        y_cat += 90

    # Reconciliation Guarantee Pill
    draw.rounded_rectangle([1040, 790, 1780, 845], radius=10, fill="#0F172A", outline="#10B981", width=1)
    draw.text((1060, 805), "Reconciled Store 01 Sum: $2,280.00 + $175.00 + $1,597.50 = $4,052.50", fill="#10B981", font=font_sub)
    
    # Motion Graphics Lower-Third Subtitle Pill
    sub_text = "If you run an e-commerce brand, do you actually know where every single dollar went today?"
    draw.rounded_rectangle([260, 960, 1660, 1025], radius=14, fill="#0F172A", outline="#334155", width=2)
    draw.text((WIDTH // 2, 992), sub_text, fill="#F8FAFC", font=font_mid, anchor="mm")
    
    return im

def main():
    print("Generating Scene 01 balanced frame...")
    sample_scene1 = create_scene1_frame()
    sample_scene1_path = "artifacts/video_patch/scene1_base.png"
    sample_scene1.save(sample_scene1_path)

    scene1_mp4 = "artifacts/video_patch/scene1.mp4"
    print("Encoding Scene 01 video clip (20.5s @ 30fps)...")
    subprocess.run(
        f'ffmpeg -y -loop 1 -i "{sample_scene1_path}" -t 20.5 -c:v libx264 -pix_fmt yuv420p -r 30 "{scene1_mp4}"',
        shell=True,
        check=True
    )

    remainder_mp4 = "artifacts/video_patch/remainder.mp4"
    print("Extracting remainder of demo video from 20.5s...")
    subprocess.run(
        f'ffmpeg -y -ss 20.5 -i "{input_video}" -c:v copy -an "{remainder_mp4}"',
        shell=True,
        check=True
    )

    concat_list = "artifacts/video_patch/concat.txt"
    with open(concat_list, "w") as f:
        f.write("file 'scene1.mp4'\nfile 'remainder.mp4'\n")

    patched_video_no_audio = "artifacts/video_patch/video_no_audio.mp4"
    print("Concatenating Scene 01 with remainder...")
    res = subprocess.run(
        f'ffmpeg -y -f concat -safe 0 -i "{concat_list}" -c copy "{patched_video_no_audio}"',
        shell=True
    )
    if res.returncode != 0:
        print("Fast concat copy returned non-zero, using filter_complex concat...")
        subprocess.run(
            f'ffmpeg -y -i "{scene1_mp4}" -i "{remainder_mp4}" -filter_complex "[0:v][1:v]concat=n=2:v=1:a=0[outv]" -map "[outv]" -c:v libx264 -pix_fmt yuv420p -preset veryfast -crf 20 "{patched_video_no_audio}"',
            shell=True,
            check=True
        )

    output_final_mp4 = "docs/submission_demo_final.mp4"
    print(f"Muxing audio into {output_final_mp4}...")
    subprocess.run(
        f'ffmpeg -y -i "{patched_video_no_audio}" -i "{audio_file}" -c:v copy -c:a aac -shortest "{output_final_mp4}"',
        shell=True,
        check=True
    )

    if os.path.exists(output_final_mp4):
        size_mb = os.path.getsize(output_final_mp4) / (1024 * 1024)
        print(f"\n[SUCCESS] Patched video successfully saved to {output_final_mp4} ({size_mb:.2f} MB)")
    else:
        print(f"\n[ERROR] Output file {output_final_mp4} not found!")
        sys.exit(1)

if __name__ == "__main__":
    main()
