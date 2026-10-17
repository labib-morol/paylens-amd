"""Capture high-definition live application screenshots with Playwright Chrome."""

import os
import sys
import time
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "temp_video_build" / "live_screens"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 8599
URL = f"http://localhost:{PORT}"

def main():
    print("=" * 60)
    print("CAPTURING ALL LIVE HIGH-RES APP SCREENS FOR VIDEO")
    print("=" * 60)

    env = os.environ.copy()
    env["STREAMLIT_SERVER_HEADLESS"] = "true"
    env["STREAMLIT_SERVER_PORT"] = str(PORT)
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.port", str(PORT), "--server.headless", "true"],
        cwd=str(ROOT_DIR),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        time.sleep(7)
        print("[1/3] Connecting with Playwright Chrome at 1920x1080...")

        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=CHROME_PATH, headless=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)

            print(f"  - Navigating to {URL}...")
            page.goto(URL, timeout=60000)
            print("  - Waiting for dashboard metrics to render...")
            page.wait_for_selector("text=CONFIRMED CASH DISCREPANCIES", timeout=60000)
            time.sleep(5)

            # Screen 1: Deal Desk Live with ORD-LEAK-4348 ($1,255.00) at #1
            s1_path = str(OUTPUT_DIR / "01_deal_desk_live.png")
            page.screenshot(path=s1_path, full_page=False)
            print(f"  [SAVED] {s1_path}")

            # Screen 2: Scroll Right Inspector down to show Evidence + Grounded Draft
            print("  - Scrolling right inspector to show Evidence and Grounded Action Notice...")
            try:
                page.locator("text=Numeric Claim Validation Result").scroll_into_view_if_needed()
            except Exception:
                page.mouse.wheel(0, 450)
            time.sleep(2)
            s2_path = str(OUTPUT_DIR / "02_evidence_and_action.png")
            page.screenshot(path=s2_path, full_page=False)
            print(f"  [SAVED] {s2_path}")

            # Reset scroll to top
            page.mouse.wheel(0, -1000)
            time.sleep(1)

            # Screen 3: Switch Objective to Prevent Stockouts
            print("  - Switching Optimization Goal to 'Prevent Stockouts'...")
            page.locator("label:has-text('Prevent Stockouts')").click()
            time.sleep(4)
            page.wait_for_selector("text=SKU-APX-01", timeout=30000)
            time.sleep(2)

            s3_path = str(OUTPUT_DIR / "03_stockout_promoted.png")
            page.screenshot(path=s3_path, full_page=False)
            print(f"  [SAVED] {s3_path}")

            # Screen 4: Switch to Tab 2 (Live Benchmark & Confusion Matrix)
            print("  - Navigating to Tab 2 (Live Benchmark & Confusion Matrix)...")
            tab2_btn = page.locator("button[role='tab']:has-text('Live Benchmark')")
            if tab2_btn.count() > 0:
                tab2_btn.first.click()
            else:
                tabs = page.locator("button[role='tab']").all()
                if len(tabs) >= 2:
                    tabs[1].click()

            print("  - Waiting for Tab 2 benchmark content...")
            page.locator("text=Live AMD Radeon Cloud TokenFactory Concurrency Benchmark").wait_for(state="visible", timeout=30000)
            time.sleep(5)

            s4_path = str(OUTPUT_DIR / "04_amd_benchmark_scaling.png")
            page.screenshot(path=s4_path, full_page=False)
            print(f"  [SAVED] {s4_path}")

            # Screen 5: Scroll down in Tab 2 to show Stress Confusion Matrix
            print("  - Scrolling down in Tab 2 to show Stress Confusion Matrix...")
            cm_heading = page.locator("text=Realistic Stress-Test Confusion Matrix")
            if cm_heading.count() > 0:
                cm_heading.first.scroll_into_view_if_needed()
            time.sleep(3)
            s5_path = str(OUTPUT_DIR / "05_stress_confusion_matrix.png")
            page.screenshot(path=s5_path, full_page=False)
            print(f"  [SAVED] {s5_path}")

            browser.close()

    finally:
        print("[2/3] Terminating Streamlit server...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except Exception:
            proc.kill()

    print("[3/3] Screenshot capture complete!")

if __name__ == "__main__":
    main()
